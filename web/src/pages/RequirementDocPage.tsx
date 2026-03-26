import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  getProductRequirement,
  getRequirementDoc,
  saveRequirementDoc,
  listDocVersions,
  getDocDiff,
  streamGenerateDoc,
  streamPreGenerateChat,
  getDocGenerationStatus,
  listProductRequirementsTree,
  canGenerateChildren,
  streamGenerateChildrenDocs,
  ApiError,
  type CanGenerateChildrenResponse,
  type ProductRequirement,
  type DocVersion,
  type SplitSuggestion,
  type DocWorkflowEventType,
} from "../api/client";
import { MarkdownRenderer } from "../components/MarkdownRenderer";
import { MarkdownDiffRenderer } from "../components/MarkdownDiffRenderer";
import { MarkdownDiffReviewer } from "../components/MarkdownDiffReviewer";
import { SplitSuggestionsModal } from "../components/SplitSuggestionsModal";
import { useAgentSession } from "../contexts/AgentSessionContext";

type ViewMode = "edit" | "preview" | "diff" | "review";
type DocLoadState = "idle" | "loading" | "ready" | "missing" | "error";
type VisibleStatus =
  | "loading"
  | "empty"
  | "ready"
  | "generating"
  | "generate_failed"
  | "load_failed"
  | "review"
  | "dirty"
  | "saved";

type WorkflowStepStatus = "pending" | "running" | "done" | "failed";

interface WorkflowStepItem {
  key: string;
  label: string;
  status: WorkflowStepStatus;
  detail?: string | null;
}

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  options?: string[]; // AI 消息的快捷选项
}

interface ChildGenerationGateInfo {
  allowed: boolean;
  reason: string | null;
  detail: string | null;
  reasonCode: CanGenerateChildrenResponse["reason_code"];
}

interface ChildGenerationEntry {
  reqId: number;
  title: string;
  status: "pending" | "running" | "completed" | "failed";
  step?: string | null;
  detail?: string | null;
  error?: string | null;
}

const STEP_LABELS: Record<string, string> = {
  collect_context: "收集上下文",
  code_search: "代码检索",
  graph_search: "图谱检索",
  synthesize: "合并结果",
  generate_doc: "生成文档",
  save_draft: "保存草稿",
  generate_split_suggestions: "生成拆分建议",
};

const WORKFLOW_STEP_ORDER = [
  "collect_context",
  "code_search",
  "graph_search",
  "synthesize",
  "generate_doc",
  "save_draft",
  "generate_split_suggestions",
] as const;

function buildWorkflowSteps(activeStep: string | null = null): WorkflowStepItem[] {
  return WORKFLOW_STEP_ORDER.map((step) => ({
    key: step,
    label: STEP_LABELS[step] ?? step,
    status: activeStep === step ? "running" : "pending",
    detail: null,
  }));
}

function toChildGateInfo(response: CanGenerateChildrenResponse): ChildGenerationGateInfo {
  return {
    allowed: response.can_generate_children,
    reason: response.reason ?? null,
    detail: response.detail ?? null,
    reasonCode: response.reason_code ?? null,
  };
}

function deriveChildGenerationGate(
  req: ProductRequirement,
  allRequirements: ProductRequirement[],
): ChildGenerationGateInfo {
  const level = (req.level || "").toLowerCase();
  if (level !== "epic" && level !== "story") {
    return {
      allowed: false,
      reason: "只有 Epic / Story 可以生成子级文档",
      detail: "Task 不再向下生成子文档；请在 Epic 或 Story 上触发该流程。",
      reasonCode: "invalid_level",
    };
  }

  const docStatus = req.doc_status ?? (req.has_doc ? "ready" : "none");
  if (docStatus === "pending" || docStatus === "generating") {
    return {
      allowed: false,
      reason: "当前文档仍在生成中，完成后再生成子级文档",
      detail: "父文档还在生成流程中，子文档入口会先锁定，避免拆分依据不稳定。",
      reasonCode: "doc_generating",
    };
  }
  if (docStatus === "failed") {
    return {
      allowed: false,
      reason: "当前文档生成失败，请先重试或修正后再生成子级文档",
      detail: "请先把父文档恢复到可用状态，再继续向下批量生成子文档。",
      reasonCode: "doc_failed",
    };
  }
  if (!req.has_doc) {
    return {
      allowed: false,
      reason: "请先完成当前需求文档后再生成子级文档",
      detail: "当前父需求还没有已落盘的需求文档；请先生成或保存父文档。",
      reasonCode: "doc_missing",
    };
  }

  const childLevel = level === "epic" ? "Story" : "Task";
  const childCount = allRequirements.filter((item) => item.parent_id === req.id).length;
  return {
    allowed: true,
    reason: null,
    detail: childCount > 0
      ? `当前${level === "epic" ? " Epic " : " Story "}文档已就绪，可开始批量生成 ${childCount} 个子级 ${childLevel} 文档。`
      : `当前${level === "epic" ? " Epic " : " Story "}文档已就绪；生成流程会先基于拆分结果创建子级 ${childLevel}，再批量生成文档。`,
    reasonCode: null,
  };
}

export function RequirementDocPage() {
  const { productId: productIdParam, requirementId: requirementIdParam } = useParams<{
    productId: string;
    requirementId: string;
  }>();
  const productId = productIdParam ? Number(productIdParam) : 0;
  const requirementId = requirementIdParam ? Number(requirementIdParam) : 0;
  const navigate = useNavigate();

  const [requirement, setRequirement] = useState<ProductRequirement | null>(null);
  const [content, setContent] = useState("");
  const [savedContent, setSavedContent] = useState("");
  const [currentVersion, setCurrentVersion] = useState<number | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>("edit");
  const [versions, setVersions] = useState<DocVersion[]>([]);
  const [diffV1, setDiffV1] = useState<number | null>(null);
  const [diffV2, setDiffV2] = useState<number | null>(null);
  const [diffContent, setDiffContent] = useState<{ v1_content: string; v2_content: string } | null>(null);
  const [diffLoading, setDiffLoading] = useState(false);
  const [diffError, setDiffError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [docLoadState, setDocLoadState] = useState<DocLoadState>("idle");
  const [docLoadError, setDocLoadError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [generationError, setGenerationError] = useState<string | null>(null);
  const [saveFeedback, setSaveFeedback] = useState<string | null>(null);
  const [lastSavedVersion, setLastSavedVersion] = useState<number | null>(null);
  const [generationNotice, setGenerationNotice] = useState<string | null>(null);
  const [workflowSteps, setWorkflowSteps] = useState<WorkflowStepItem[]>(() => buildWorkflowSteps());

  // Review mode (agent → direct edit)
  const [pendingContent, setPendingContent] = useState<string | null>(null);
  const [preChangeContent, setPreChangeContent] = useState<string>("");
  const [reviewSource, setReviewSource] = useState<"agent" | "draft">("agent");

  // Generation
  const [generateStreaming, setGenerateStreaming] = useState(false);
  const [generateStep, setGenerateStep] = useState<string | null>(null);
  const [splitSuggestions, setSplitSuggestions] = useState<SplitSuggestion[] | null>(null);
  const [showSplitModal, setShowSplitModal] = useState(false);

  // Generation status persistence
  const [generationStatus, setGenerationStatus] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Pre-generate modal (Epic)
  const [showGenerateModal, setShowGenerateModal] = useState(false);
  const [preGenChatHistory, setPreGenChatHistory] = useState<ChatMessage[]>([]);
  const [preGenInput, setPreGenInput] = useState("");
  const [preGenStreaming, setPreGenStreaming] = useState(false);
  const [preGenSessionId] = useState(() => `pre-gen-${Date.now()}`);
  const preGenAbortRef = useRef<{ abort: () => void } | null>(null);
  const preGenChatEndRef = useRef<HTMLDivElement>(null);

  const streamAbortRef = useRef<{ abort: () => void } | null>(null);
  const contentAreaRef = useRef<HTMLDivElement>(null);
  const draftBeforeGenerateRef = useRef("");
  const generationHasContentRef = useRef(false);

  const isDirty = content !== savedContent;
  const hasUnsavedTransitionState = isDirty || pendingContent !== null;

  // ── 侧边栏需求树 ──
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [treeRequirements, setTreeRequirements] = useState<ProductRequirement[]>([]);
  const [treeCollapsed, setTreeCollapsed] = useState<Set<number>>(new Set());
  const [childGenParentId, setChildGenParentId] = useState<number | null>(null);
  const [childGenEntries, setChildGenEntries] = useState<ChildGenerationEntry[]>([]);
  const [currentChildGate, setCurrentChildGate] = useState<ChildGenerationGateInfo | null>(null);
  const childGenAbortRef = useRef<{ abort: () => void } | null>(null);

  const loadTree = useCallback(async () => {
    if (!productId) return;
    try {
      const vId = requirement?.version_id;
      const reqs = await listProductRequirementsTree(productId, vId ?? undefined);
      setTreeRequirements(reqs);
    } catch (e) {
      setError((prev) => prev ?? (e instanceof Error ? e.message : "需求树加载失败"));
    }
  }, [productId, requirement?.version_id]);

  useEffect(() => { loadTree(); }, [loadTree]);

  const toggleTreeCollapse = (id: number) =>
    setTreeCollapsed((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });

  const handleTreeNavigate = (reqId: number) => {
    if (reqId === requirementId) return;
    if (isGenerating) {
      setError("当前文档仍在生成中，暂不允许切换需求，避免状态混乱。若要放弃本次流式结果，请先停止生成。");
      return;
    }
    if (hasUnsavedTransitionState && !confirm(pendingContent !== null ? "当前还有待审阅/未落盘的改动，确定切换需求并放弃当前审阅状态吗？" : "有未保存的更改，确定切换？")) {
      return;
    }
    navigate(`/products/${productId}/requirements/${reqId}/doc`);
  };

  const handleGenerateChildrenDocs = async (parentId: number) => {
    if (childGenParentId !== null || isGenerating) return;
    try {
      const response = await canGenerateChildren(productId, parentId);
      if (!response.can_generate_children) {
        setError(response.detail ?? response.reason ?? "??????????????????");
        if (parentId === requirementId) {
          setCurrentChildGate(toChildGateInfo(response));
        }
        return;
      }
      setChildGenParentId(parentId);
      setChildGenEntries([]);
      setError(null);
      if (parentId === requirementId) {
        setGenerationNotice("????????????????????????????????????????");
      }
      // ?????
      setTreeCollapsed((prev) => { const n = new Set(prev); n.delete(parentId); return n; });

      childGenAbortRef.current = streamGenerateChildrenDocs(productId, parentId, {
        decompose_done: (data: unknown) => {
          const d = data as { children: { requirement_id: number; title: string }[] };
          setChildGenEntries(d.children.map((c) => ({
            reqId: c.requirement_id,
            title: c.title,
            status: "pending",
            step: null,
            detail: "????",
            error: null,
          })));
        },
        child_start: (data: unknown) => {
          const { requirement_id } = data as { requirement_id: number };
          setChildGenEntries((prev) => prev.map((c) => c.reqId === requirement_id
            ? { ...c, status: "running", step: null, detail: "????", error: null }
            : c));
        },
        child_progress: (data: unknown) => {
          const { requirement_id, step, status, detail } = data as {
            requirement_id: number;
            step?: string;
            status?: string;
            detail?: string | null;
          };
          if (!requirement_id) return;
          setChildGenEntries((prev) => prev.map((c) => {
            if (c.reqId !== requirement_id) return c;
            if (status === "failed") {
              return { ...c, status: "failed", step: step ?? c.step ?? null, detail: detail ?? "????", error: detail ?? "????" };
            }
            if (status === "done") {
              return { ...c, status: "running", step: step ?? c.step ?? null, detail: `${STEP_LABELS[step ?? ""] ?? step ?? "????"} ? ???` };
            }
            return { ...c, status: "running", step: step ?? c.step ?? null, detail: detail ?? (step ? `${STEP_LABELS[step] ?? step} ? ???` : "???") };
          }));
        },
        child_done: (data: unknown) => {
          const { requirement_id, status, error } = data as { requirement_id: number; status: string; error?: string };
          setChildGenEntries((prev) => prev.map((c) => c.reqId === requirement_id
            ? {
              ...c,
              status: status === "completed" ? "completed" : "failed",
              detail: status === "completed" ? "???????" : error ?? "????",
              error: status === "completed" ? null : (error ?? "????"),
            }
            : c));
          void loadTree();
        },
        error: (data: unknown) => {
          const d = data as { message?: string };
          setError(d.message ?? "???????????????????????");
        },
        workflow_done: () => {
          setChildGenParentId(null);
          childGenAbortRef.current = null;
          if (parentId === requirementId) {
            setGenerationNotice("?????????????????????????????");
          }
          void loadRequirement();
          void loadDoc();
          void loadVersions();
          void loadTree();
          void canGenerateChildren(productId, requirementId)
            .then((gateResponse) => setCurrentChildGate(toChildGateInfo(gateResponse)))
            .catch(() => undefined);
        },
      } as Partial<Record<DocWorkflowEventType, (data: unknown) => void>>);
    } catch (e) {
      setChildGenParentId(null);
      setError(e instanceof Error ? e.message : "???????");
    }
  };


  const loadRequirement = useCallback(async () => {
    if (!productId || !requirementId) return;
    try {
      const req = await getProductRequirement(productId, requirementId);
      setRequirement(req);
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载需求失败");
    }
  }, [productId, requirementId]);

  const loadDoc = useCallback(async () => {
    if (!productId || !requirementId) return;
    setLoading(true);
    setDocLoadState("loading");
    setDocLoadError(null);
    try {
      const doc = await getRequirementDoc(productId, requirementId);
      setContent(doc.content);
      setSavedContent(doc.content);
      setCurrentVersion(doc.version);
      setDocLoadState("ready");
    } catch (e) {
      setContent("");
      setSavedContent("");
      setCurrentVersion(null);
      if (e instanceof ApiError && e.status === 404) {
        setDocLoadState("missing");
        return;
      }
      setDocLoadState("error");
      setDocLoadError(e instanceof Error ? e.message : "加载文档失败");
    } finally {
      setLoading(false);
    }
  }, [productId, requirementId]);

  const loadVersions = useCallback(async () => {
    if (!productId || !requirementId) return;
    try {
      const list = await listDocVersions(productId, requirementId);
      setVersions(list);
    } catch (e) {
      setVersions([]);
      setError((prev) => prev ?? (e instanceof Error ? e.message : "版本列表加载失败"));
    }
  }, [productId, requirementId]);

  useEffect(() => { loadRequirement(); }, [loadRequirement]);
  useEffect(() => { loadDoc(); loadVersions(); }, [loadDoc, loadVersions]);

  useEffect(() => {
    if (!productId || !requirementId || !requirement) {
      setCurrentChildGate(null);
      return;
    }
    if (requirement.level !== "epic" && requirement.level !== "story") {
      setCurrentChildGate(null);
      return;
    }
    let alive = true;
    canGenerateChildren(productId, requirementId)
      .then((response) => {
        if (alive) {
          setCurrentChildGate(toChildGateInfo(response));
        }
      })
      .catch((e) => {
        if (alive) {
          setCurrentChildGate({
            allowed: false,
            reason: e instanceof Error ? e.message : "子文档门禁校验失败",
            detail: "当前无法确认是否允许生成子文档，请稍后重试。",
            reasonCode: null,
          });
        }
      });
    return () => {
      alive = false;
    };
  }, [productId, requirement, requirementId, currentVersion, generationStatus, generationError, saveFeedback]);

  useEffect(() => {
    setViewMode("edit");
    setDiffV1(null);
    setDiffV2(null);
    setDiffContent(null);
    setDiffError(null);
    setPendingContent(null);
    setPreChangeContent("");
    setReviewSource("agent");
    setError(null);
    setGenerationError(null);
    setGenerationNotice(null);
    setSaveFeedback(null);
    setLastSavedVersion(null);
    setGenerateStep(null);
    setWorkflowSteps(buildWorkflowSteps());
    setSplitSuggestions(null);
    setShowSplitModal(false);
    setGenerationStatus(null);
    setCurrentChildGate(null);
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, [requirementId]);

  useEffect(() => {
    if (!saveFeedback) return;
    const timer = window.setTimeout(() => setSaveFeedback(null), 2400);
    return () => window.clearTimeout(timer);
  }, [saveFeedback]);

  // ── Unsaved changes warning ──

  useEffect(() => {
    const handler = (e: BeforeUnloadEvent) => {
      if (hasUnsavedTransitionState) { e.preventDefault(); }
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [hasUnsavedTransitionState]);

  // ── Keyboard shortcuts ──

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "s") {
        e.preventDefault();
        if (!saving && !loading && isDirty) handleSave();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  });

  // ── Generation status polling ──

  const checkGenerationStatus = useCallback(async () => {
    if (!productId || !requirementId) return;
    try {
      const st = await getDocGenerationStatus(productId, requirementId);
      setGenerationStatus(st.generation_status);
      if (st.generation_status === "running") {
        setGenerationNotice("页面已恢复后台生成状态，会继续轮询直到生成完成或失败。");
        setWorkflowSteps((prev) => prev.some((step) => step.status !== "pending") ? prev : buildWorkflowSteps());
      } else if (st.generation_status === "completed") {
        if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
        setGenerationStatus(null);
        setGenerationNotice("后台生成已完成，已自动同步最新草稿。");
        void loadDoc();
        void loadVersions();
        void loadTree();
      } else if (st.generation_status === "failed") {
        if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
        setGenerationStatus(null);
        setGenerationError(st.generation_error || "生成失败");
        setGenerationNotice("后台生成失败，已保留你生成前的草稿，可直接继续编辑或重试。" );
        setContent((prev) => prev || draftBeforeGenerateRef.current);
        void loadTree();
      }
    } catch (e) {
      setGenerationNotice((prev) => prev ?? (e instanceof Error ? `生成状态同步失败：${e.message}` : "生成状态同步失败，请稍后重试刷新。"));
    }
  }, [productId, requirementId, loadDoc, loadVersions]);

  useEffect(() => {
    // Check on mount
    if (productId && requirementId) {
      checkGenerationStatus();
    }
  }, [checkGenerationStatus]);

  useEffect(() => {
    if (generationStatus === "running" && !generateStreaming) {
      pollRef.current = setInterval(checkGenerationStatus, 3000);
      return () => { if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; } };
    }
  }, [generationStatus, generateStreaming, checkGenerationStatus]);

  // ── Pre-gen chat auto-scroll ──

  useEffect(() => {
    preGenChatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [preGenChatHistory]);

  // ── Cleanup ──

  useEffect(() => {
    return () => {
      streamAbortRef.current?.abort();
      preGenAbortRef.current?.abort();
      childGenAbortRef.current?.abort();
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  // ── 注册文档编辑上下文到全局 AgentPanel ──

  const { setDocContext } = useAgentSession();
  const contentRef = useRef(content);
  useEffect(() => { contentRef.current = content; }, [content]);

  useEffect(() => {
    if (!productId || !requirementId) return;
    setDocContext({
      requirementId,
      getCurrentContent: () => contentRef.current,
      onDocSnapshot: (snapshot: string) => {
        setContent(snapshot);
      },
      onModifiedDoc: (modified: string, preChange: string) => {
        setPreChangeContent(preChange || contentRef.current);
        setPendingContent(modified);
        setReviewSource("agent");
        setViewMode("review");
      },
    });
    return () => setDocContext(null);
  }, [productId, requirementId, setDocContext]);

  // ── Actions ──

  const handleSave = async () => {
    if (!productId || !requirementId) return;
    setSaving(true);
    setError(null);
    setGenerationError(null);
    try {
      const doc = await saveRequirementDoc(productId, requirementId, content, "manual");
      setCurrentVersion(doc.version);
      setLastSavedVersion(doc.version);
      setSavedContent(content);
      setDocLoadState("ready");
      setSaveFeedback(`已保存为 v${doc.version}`);
      void loadVersions();
      void loadTree();
    } catch (e) {
      setError(e instanceof Error ? e.message : "保存失败");
    } finally {
      setSaving(false);
    }
  };

  const handleGenerateClick = () => {
    if (!productId || !requirementId) return;
    if (requirement?.level === "epic") {
      // Epic: 打开对话式引导弹窗
      setShowGenerateModal(true);
      setPreGenChatHistory([]);
      setPreGenInput("");
      // 自动触发 AI 首次引导
      setTimeout(() => triggerPreGenChat("请根据当前需求信息，帮我理清这个 Epic 的边界和目标。"), 100);
    } else {
      // Story/Task: 直接生成
      handleGenerate();
    }
  };

  const handleGenerate = (userOverview?: string) => {
    if (!productId || !requirementId) return;
    draftBeforeGenerateRef.current = content;
    generationHasContentRef.current = false;
    setGenerateStreaming(true);
    setGenerateStep(null);
    setError(null);
    setGenerationError(null);
    setGenerationNotice("正在生成文档。生成期间会禁用保存、切换需求和差异对比；你仍然可以查看当前状态。\n失败后会保留原草稿，便于继续编辑或重试。");
    setSaveFeedback(null);
    setSplitSuggestions(null);
    setWorkflowSteps(buildWorkflowSteps());
    setViewMode("edit");
    setShowGenerateModal(false);
    streamAbortRef.current = streamGenerateDoc(productId, requirementId, {
      token: (data: unknown) => {
        const text = typeof data === "string" ? data : (data as { text?: string; content?: string })?.text ?? (data as { content?: string })?.content ?? "";
        if (!text) return;
        setContent((prev) => {
          if (!generationHasContentRef.current) {
            generationHasContentRef.current = true;
            return text;
          }
          return prev + text;
        });
      },
      workflow_step: (data: unknown) => {
        const d = data as { step?: string; status?: string; detail?: string | null };
        if (!d?.step) return;
        if (d.status === "running") {
          setGenerateStep(d.step);
        }
        setWorkflowSteps((prev) => {
          const activeIndex = WORKFLOW_STEP_ORDER.indexOf(d.step as (typeof WORKFLOW_STEP_ORDER)[number]);
          return prev.map((step, index) => {
            if (step.key === d.step) {
              return {
                ...step,
                status: d.status === "failed" ? "failed" : d.status === "done" ? "done" : "running",
                detail: d.detail ?? null,
              };
            }
            if (d.status === "running" && activeIndex >= 0 && index < activeIndex && step.status === "running") {
              return { ...step, status: "done" };
            }
            return step;
          });
        });
        if (d?.status === "failed") {
          setGenerateStreaming(false);
          setGenerateStep(null);
          setGenerationError(d.detail || "生成失败");
          setGenerationNotice("本次生成在流程中断开，已恢复到生成前草稿。你可以继续编辑，或直接重试续生成。");
          setContent(draftBeforeGenerateRef.current);
          streamAbortRef.current = null;
        }
      },
      split_suggestions: (data: unknown) => {
        const d = data as { suggestions?: SplitSuggestion[] };
        if (d?.suggestions && d.suggestions.length > 0) {
          setSplitSuggestions(d.suggestions);
          setShowSplitModal(true);
        }
      },
      error: (data: unknown) => {
        const d = data as { message?: string };
        setGenerateStreaming(false);
        setGenerateStep(null);
        setGenerationError(d.message ?? "生成连接已中断");
        setGenerationNotice("SSE 连接中断。若后台仍在运行，页面会继续轮询；否则你可以继续编辑或手动重试。" );
        setContent((prev) => prev || draftBeforeGenerateRef.current);
        streamAbortRef.current = null;
      },
      workflow_done: (data: unknown) => {
        setGenerateStreaming(false);
        setGenerateStep(null);
        streamAbortRef.current = null;
        const d = data as { status?: string; error?: string };
        if (d?.status === "failed") {
          setGenerationError(d.error ?? "生成失败");
          setGenerationNotice("文档生成失败，已保留原草稿。你可以修正文档后续生成，或继续手动编辑。" );
          setContent(draftBeforeGenerateRef.current);
          void loadTree();
          return;
        }
        setWorkflowSteps((prev) => prev.map((step) => (step.status === "pending" ? step : { ...step, status: "done" })));
        setGenerationNotice("文档生成完成，已同步最新草稿。现在会直接进入“当前稿 vs 上一版本”的差异审阅路径。" );
        setDiffContent(null);
        setDiffError(null);
        setViewMode("diff");
        void loadDoc();
        void loadVersions();
        void loadTree();
      },
    }, userOverview);
  };

  const handleStopStream = () => {
    streamAbortRef.current?.abort();
    streamAbortRef.current = null;
    if (generateStreaming) {
      setGenerateStreaming(false);
      setGenerateStep(null);
      setGenerationNotice("已停止当前流式连接。若后端已继续执行，页面仍会通过状态轮询恢复结果；当前先保留生成前草稿。" );
      setContent(draftBeforeGenerateRef.current);
    }
  };

  // ── Pre-generate modal chat ──

  const triggerPreGenChat = (msg: string) => {
    if (!msg.trim() || !productId || !requirementId || preGenStreaming) return;
    setPreGenChatHistory((prev) => [...prev, { role: "user", content: msg }]);
    setPreGenChatHistory((prev) => [...prev, { role: "assistant", content: "" }]);
    setPreGenStreaming(true);
    preGenAbortRef.current = streamPreGenerateChat(productId, requirementId, msg, preGenSessionId, {
      token: (data: unknown) => {
        const text = typeof data === "string" ? data : "";
        if (text) {
          setPreGenChatHistory((prev) => {
            const next = [...prev];
            const last = next[next.length - 1];
            if (last?.role === "assistant") {
              next[next.length - 1] = { ...last, content: last.content + text };
            }
            return next;
          });
        }
      },
      done: (data: unknown) => {
        const d = data as { content?: string };
        if (d?.content) {
          setPreGenChatHistory((prev) => {
            const next = [...prev];
            const last = next[next.length - 1];
            if (last?.role === "assistant") {
              next[next.length - 1] = { ...last, content: d.content! };
            }
            return next;
          });
        }
        // 不在这里停止流式状态，等待 options 事件或 SSE 连接关闭
      },
      options: (data: unknown) => {
        const d = data as { options?: string[] };
        if (Array.isArray(d?.options) && d.options.length > 0) {
          // 将选项附加到最后一条 AI 消息
          setPreGenChatHistory((prev) => {
            const next = [...prev];
            const last = next[next.length - 1];
            if (last?.role === "assistant") {
              next[next.length - 1] = { ...last, options: d.options };
            }
            return next;
          });
        }
        // 收到 options 后停止流式状态
        setPreGenStreaming(false);
        preGenAbortRef.current = null;
      },
      error: () => {
        setPreGenStreaming(false);
        preGenAbortRef.current = null;
      },
    });
  };

  const handlePreGenSend = (overrideMsg?: string) => {
    const msg = (overrideMsg ?? preGenInput).trim();
    if (!msg) return;
    setPreGenInput("");
    triggerPreGenChat(msg);
  };

  const handleStartGenerateFromModal = () => {
    // 拼接对话为 userOverview
    const overview = preGenChatHistory
      .map((m) => `${m.role === "user" ? "用户" : "AI"}：${m.content}`)
      .join("\n\n");
    handleGenerate(overview);
  };

  const loadDiff = useCallback(async (v1: number, v2: number) => {
    if (!productId || !requirementId) return;
    setDiffLoading(true);
    setDiffError(null);
    try {
      const d = await getDocDiff(productId, requirementId, v1, v2);
      setDiffContent(d);
    } catch (e) {
      setDiffContent(null);
      setDiffError(e instanceof Error ? e.message : "加载版本对比失败");
    } finally {
      setDiffLoading(false);
    }
  }, [productId, requirementId]);

  const handleSwitchToDiff = () => {
    setViewMode("diff");
    setDiffError(null);
    // 默认走“当前稿 vs 上一版本”的最短路径
    if (versions.length >= 2) {
      const sorted = [...versions].sort((a, b) => a.version - b.version);
      const latest = currentVersion ?? sorted[sorted.length - 1].version;
      const earlierVersions = sorted.filter((item) => item.version < latest);
      const previous = earlierVersions[earlierVersions.length - 1]?.version ?? sorted[sorted.length - 2].version;
      if (latest != null && previous != null && (diffV1 !== previous || diffV2 !== latest || diffContent == null)) {
        setDiffV1(previous);
        setDiffV2(latest);
        void loadDiff(previous, latest);
      }
      return;
    }
    if (diffV1 != null && diffV2 != null) {
      void loadDiff(diffV1, diffV2);
    }
  };

  const handleApplySelection = async (rebuiltContent: string) => {
    if (!productId || !requirementId) return;
    setSaving(true);
    setError(null);
    setGenerationError(null);
    try {
      const doc = await saveRequirementDoc(
        productId,
        requirementId,
        rebuiltContent,
        reviewSource === "agent" ? "agent" : "manual",
      );
      setContent(rebuiltContent);
      setSavedContent(rebuiltContent);
      setCurrentVersion(doc.version);
      setLastSavedVersion(doc.version);
      setDocLoadState("ready");
      setSaveFeedback(`已保存为 v${doc.version}`);
      void loadVersions();
      void loadTree();
      setPendingContent(null);
      setPreChangeContent("");
      setReviewSource("agent");
      setViewMode("edit");
    } catch (e) {
      setError(e instanceof Error ? e.message : "保存失败");
    } finally {
      setSaving(false);
    }
  };

  const handleRejectChanges = () => {
    setPendingContent(null);
    setPreChangeContent("");
    setReviewSource("agent");
    setViewMode("edit");
  };

  const handleReviewCurrentDraft = () => {
    if (!diffContent) return;
    setPreChangeContent(diffContent.v1_content);
    setPendingContent(diffContent.v2_content);
    setReviewSource("draft");
    setViewMode("review");
  };

  const hasPersistedDoc = docLoadState === "ready" || versions.length > 0 || savedContent.trim().length > 0;
  const hasAnyContent = content.trim().length > 0 || savedContent.trim().length > 0;
  const hasComparableVersions = versions.length >= 2;
  const hasReviewChanges = pendingContent !== null;
  const isGenerating = generateStreaming || generationStatus === "running";
  const hasBlockingLoadError = docLoadState === "error" && !hasPersistedDoc;
  const hasGenerationFailure = generationError !== null;
  const primaryGenerateLabel = hasPersistedDoc || hasAnyContent ? "续生成" : "生成文档";
  const saveButtonLabel = saveFeedback ? "已保存" : saving ? "保存中..." : "保存";
  const statusMeta = useMemo(() => {
    const meta: Record<VisibleStatus, { tone: "neutral" | "info" | "success" | "warning" | "danger"; title: string; description: string; cta?: "save" | "generate" | "retry_load" | "review" }> = {
      loading: {
        tone: "neutral",
        title: "正在加载文档",
        description: "先同步当前需求、文档和版本信息。",
      },
      empty: {
        tone: "neutral",
        title: "当前还没有需求文档",
        description: "可以先手写草稿，或直接用 AI 生成第一版。",
        cta: "generate",
      },
      ready: {
        tone: "success",
        title: hasPersistedDoc ? "已有草稿 / 文档" : "文档已就绪",
        description: currentVersion != null
          ? `当前版本为 v${currentVersion}，建议先看“当前稿 vs 上一版本”差异，再决定是否继续编辑。`
          : "可以继续编辑、预览或查看版本差异。",
      },
      generating: {
        tone: "info",
        title: "文档生成中",
        description: generateStreaming
          ? `正在执行 ${generateStep ? STEP_LABELS[generateStep] ?? generateStep : "生成步骤"}。`
          : "后台仍在生成，页面会自动同步结果。",
      },
      generate_failed: {
        tone: "danger",
        title: "文档生成失败",
        description: generationError ?? "本次生成没有完成，请修正后重试或续生成。",
        cta: "generate",
      },
      load_failed: {
        tone: "danger",
        title: "文档加载失败",
        description: docLoadError ?? "当前无法读取文档，请稍后重试。",
        cta: "retry_load",
      },
      review: {
        tone: "warning",
        title: "待审阅",
        description: reviewSource === "draft"
          ? "当前稿与上一版本存在差异，先审阅并决定是否应用，再继续保存或编辑。"
          : "Agent 修改已生成，先审阅并决定是否应用，再继续保存或生成。",
        cta: "review",
      },
      dirty: {
        tone: "warning",
        title: "有未保存改动",
        description: "当前编辑内容还没有保存到文档版本中。",
        cta: "save",
      },
      saved: {
        tone: "success",
        title: lastSavedVersion != null ? `保存完成 · 已生成 v${lastSavedVersion}` : "保存完成",
        description: lastSavedVersion != null
          ? `最新修改已经写入当前需求文档，版本列表已刷新到 v${lastSavedVersion}。`
          : "最新修改已经写入当前需求文档。",
      },
    };
    return meta;
  }, [currentVersion, docLoadError, generateStep, generateStreaming, generationError, hasPersistedDoc, lastSavedVersion, reviewSource]);
  const visibleStatus: VisibleStatus =
    loading ? "loading"
      : isGenerating ? "generating"
        : hasBlockingLoadError ? "load_failed"
          : hasGenerationFailure ? "generate_failed"
            : hasReviewChanges ? "review"
              : isDirty ? "dirty"
                : saveFeedback ? "saved"
                  : hasPersistedDoc ? "ready"
                    : "empty";
  const statusInfo = statusMeta[visibleStatus];
  const canEnterPreview = !hasBlockingLoadError && !isGenerating;
  const canSwitchToDiff = !isGenerating && (hasComparableVersions || diffContent !== null || diffV1 != null || diffV2 != null);
  const canSave = !loading && !saving && !isGenerating && !hasReviewChanges && isDirty;
  const canGenerate = !loading && !saving && !hasReviewChanges && !isGenerating;
  const currentRequirementChildGate = useMemo(() => {
    if (!requirement || (requirement.level !== "epic" && requirement.level !== "story")) {
      return null;
    }
    return currentChildGate ?? deriveChildGenerationGate(requirement, treeRequirements);
  }, [currentChildGate, requirement, treeRequirements]);

  useEffect(() => {
    if (viewMode === "review" && !hasReviewChanges) {
      setViewMode("edit");
    }
  }, [hasReviewChanges, viewMode]);

  useEffect(() => {
    if (viewMode === "diff" && !canSwitchToDiff) {
      setViewMode("preview");
    }
  }, [canSwitchToDiff, viewMode]);

  useEffect(() => {
    if (viewMode !== "diff" || isGenerating || diffLoading || versions.length < 2) return;
    if (diffContent) return;
    const sorted = [...versions].sort((a, b) => a.version - b.version);
    const latest = currentVersion ?? sorted[sorted.length - 1].version;
    const earlierVersions = sorted.filter((item) => item.version < latest);
    const previous = earlierVersions[earlierVersions.length - 1]?.version ?? sorted[sorted.length - 2].version;
    if (latest == null || previous == null) return;
    setDiffV1(previous);
    setDiffV2(latest);
    void loadDiff(previous, latest);
  }, [currentVersion, diffContent, diffLoading, isGenerating, loadDiff, versions, viewMode]);

  // ── Render ──

  if (!productId || !requirementId) {
    return (
      <div className="req-doc-page">
        <div className="req-doc-main"><p className="empty-state">无效的产品或需求 ID</p></div>
      </div>
    );
  }

  return (
    <div className="req-doc-page">
      {/* ── 左侧需求树侧边栏 ── */}
      <div className={`req-doc-sidebar${sidebarOpen ? "" : " req-doc-sidebar--collapsed"}`}>
        <div className="req-doc-sidebar-header">
          {sidebarOpen && <span className="req-doc-sidebar-title">需求树</span>}
          <button
            type="button"
            className="req-doc-sidebar-toggle"
            onClick={() => setSidebarOpen((v) => !v)}
            title={sidebarOpen ? "收起侧边栏" : "展开侧边栏"}
          >
            {sidebarOpen ? "«" : "»"}
          </button>
        </div>
        {sidebarOpen && (
          <div className="req-doc-sidebar-tree">
            {treeRequirements.length === 0 ? (
              <div className="req-doc-sidebar-empty">暂无需求</div>
            ) : (
              <ReqTreeSidebar
                requirements={treeRequirements}
                currentReqId={requirementId}
                collapsed={treeCollapsed}
                onToggle={toggleTreeCollapse}
                onSelect={handleTreeNavigate}
                onGenerateChildren={handleGenerateChildrenDocs}
                childGenParentId={childGenParentId}
                childGenEntries={childGenEntries}
                disableActions={isGenerating}
              />
            )}
          </div>
        )}
      </div>

      <div className="req-doc-main">
        {/* 固定头部区域 */}
        <div className="req-doc-sticky-header">
          <div className="req-doc-header">
            <button type="button" className="secondary xs" onClick={() => navigate(-1)}>
              &larr; 返回
            </button>
            {requirement && (
              <div className="req-doc-info card">
                <span className={`req-level-badge ${requirement.level}`}>{requirement.level}</span>
                <strong title={requirement.title}>{requirement.title}</strong>
                <span className="text-muted">状态: {requirement.status}</span>
                <span className="text-muted">优先级: {requirement.priority}</span>
              </div>
            )}
          </div>

          <div
            className={`req-doc-status-card req-doc-status-card--${statusInfo.tone}`}
            data-testid="doc-status-card"
            data-status={visibleStatus}
          >
            <div>
              <div className="req-doc-status-card__title">{statusInfo.title}</div>
              <div className="req-doc-status-card__desc">{statusInfo.description}</div>
            </div>
            <div className="req-doc-status-card__meta">
              {currentVersion != null && <span className="req-doc-status-pill">当前 v{currentVersion}</span>}
              {hasPersistedDoc && <span className="req-doc-status-pill">已有文档</span>}
              {hasReviewChanges && <span className="req-doc-status-pill">待审阅</span>}
              {isDirty && !hasReviewChanges && <span className="req-doc-status-pill">未保存</span>}
              {saveFeedback && !isDirty && <span className="req-doc-status-pill req-doc-status-pill--success">{saveFeedback}</span>}
            </div>
          </div>

          <div className="req-doc-toolbar">
            <div className="req-doc-view-mode">
              <button
                type="button"
                className={viewMode === "edit" ? "primary xs" : "secondary xs"}
                onClick={() => setViewMode("edit")}
                disabled={loading || isGenerating}
                data-testid="doc-action-edit"
              >
                编辑
              </button>
              <button
                type="button"
                className={viewMode === "preview" ? "primary xs" : "secondary xs"}
                onClick={() => setViewMode("preview")}
                disabled={!canEnterPreview}
              >
                预览
              </button>
              <button
                type="button"
                className={viewMode === "diff" ? "primary xs" : "secondary xs"}
                onClick={handleSwitchToDiff}
                disabled={!canSwitchToDiff}
              >
                变更
              </button>
              {hasReviewChanges && (
                <button
                  type="button"
                  className={viewMode === "review" ? "primary xs" : "secondary xs"}
                  onClick={() => setViewMode("review")}
                >
                  审阅变更
                </button>
              )}
            </div>
            <div className="req-doc-actions">
              {(isDirty || visibleStatus === "saved") && <span className="req-doc-dirty-badge">{isDirty ? "未保存" : saveFeedback ?? "已保存"}</span>}
              <button
                type="button"
                className="primary"
                onClick={handleSave}
                disabled={!canSave}
                title="Ctrl+S"
              >
                {saveButtonLabel}
              </button>
              {isGenerating ? (
                <button type="button" className="secondary" onClick={handleStopStream}>
                  停止
                </button>
              ) : (
                <button
                  type="button"
                  className="primary"
                  onClick={handleGenerateClick}
                  disabled={!canGenerate || hasBlockingLoadError}
                >
                  {primaryGenerateLabel}
                </button>
              )}
              {requirement && (requirement.level === "epic" || requirement.level === "story") && !isGenerating && (
                <button
                  type="button"
                  className="secondary"
                  onClick={() => { setSplitSuggestions(null); setShowSplitModal(true); }}
                  disabled={hasBlockingLoadError}
                >
                  拆分建议
                </button>
              )}
            </div>
          </div>

          <div className={`req-doc-status-banner req-doc-status-banner--${statusInfo.tone}`}>
            <div>
              <div className="req-doc-status-banner-title">{statusInfo.title}</div>
              <div className="req-doc-status-banner-description">{statusInfo.description}</div>
            </div>
            <div className="req-doc-status-banner-actions">
              {statusInfo.cta === "save" && (
                <button type="button" className="primary xs" onClick={handleSave} disabled={!canSave}>
                  保存当前草稿
                </button>
              )}
              {statusInfo.cta === "generate" && (
                <button type="button" className="primary xs" onClick={handleGenerateClick} disabled={!canGenerate || hasBlockingLoadError}>
                  {primaryGenerateLabel}
                </button>
              )}
              {statusInfo.cta === "retry_load" && (
                <button type="button" className="primary xs" onClick={() => { void loadDoc(); void loadVersions(); }}>
                  重试加载
                </button>
              )}
              {statusInfo.cta === "review" && hasReviewChanges && (
                <button type="button" className="primary xs" onClick={() => setViewMode("review")}>
                  打开审阅
                </button>
              )}
            </div>
          </div>

          {error && (
            <div className="result error" style={{ margin: 0 }}>
              {error}
              <button
                type="button"
                className="secondary xs"
                onClick={() => setError(null)}
                style={{ marginLeft: 8, padding: "2px 8px", fontSize: 11 }}
              >
                关闭
              </button>
            </div>
          )}

          {generationNotice && (
            <div className="req-doc-progress" data-testid="generation-notice">
              <span className="req-doc-progress-dot" />
              <span style={{ whiteSpace: "pre-line" }}>{generationNotice}</span>
              {hasGenerationFailure && (
                <button
                  type="button"
                  className="secondary xs"
                  onClick={() => {
                    setGenerationError(null);
                    setGenerationNotice("已退出失败态，当前保留草稿，可继续编辑或稍后重试。");
                  }}
                  style={{ marginLeft: 8 }}
                >
                  继续编辑
                </button>
              )}
            </div>
          )}
          {generateStreaming && generateStep && (
            <div className="req-doc-progress">
              <span className="req-doc-progress-dot" />
              {STEP_LABELS[generateStep] ?? generateStep}
            </div>
          )}
          {!generateStreaming && generationStatus === "running" && (
            <div className="req-doc-progress">
              <span className="req-doc-progress-dot" />
              文档生成中（后台运行）…
            </div>
          )}
          {(isGenerating || hasGenerationFailure || workflowSteps.some((step) => step.status !== "pending")) && (
            <div className="req-doc-state-panel card" data-testid="generation-steps-panel">
              <h3>生成进度</h3>
              <p>统一展示流式事件、后台轮询恢复和失败恢复口径。</p>
              <div className="req-doc-generation-steps">
                {workflowSteps.map((step) => (
                  <div key={step.key} className={`req-doc-generation-step req-doc-generation-step--${step.status}`}>
                    <span>{step.label}</span>
                    <span>{step.status === "done" ? "已完成" : step.status === "running" ? "进行中" : step.status === "failed" ? "失败" : "待执行"}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
          {currentRequirementChildGate && (
            <div
              className={`req-doc-state-panel card${currentRequirementChildGate.allowed ? "" : " req-doc-state-panel--warning"}`}
              data-testid="child-generation-gate-panel"
            >
              <h3>子文档生成门禁</h3>
              <p>{currentRequirementChildGate.allowed ? "当前节点已满足子文档生成条件。" : (currentRequirementChildGate.reason ?? "当前节点暂不允许生成子文档。")}</p>
              {currentRequirementChildGate.detail && <p>{currentRequirementChildGate.detail}</p>}
              <div className="req-doc-state-panel-actions">
                {currentRequirementChildGate.allowed ? (
                  <button
                    type="button"
                    className="primary"
                    onClick={() => handleGenerateChildrenDocs(requirementId)}
                    disabled={childGenParentId !== null || isGenerating}
                  >
                    生成子文档
                  </button>
                ) : (
                  <button type="button" className="secondary" disabled>
                    生成子文档
                  </button>
                )}
              </div>
            </div>
          )}
        </div>

        {/* 可滚动内容区域：编辑模式由 textarea 自带滚动，其余模式外层滚动 */}
        <div className={`req-doc-content-scroll${viewMode !== "edit" ? " req-doc-content-scroll--scrollable" : ""}`} ref={contentAreaRef}>
          {loading ? (
            <div className="loading-state">加载中...</div>
          ) : hasBlockingLoadError ? (
            <div className="req-doc-state-panel req-doc-state-panel--danger card">
              <h3>文档读取失败</h3>
              <p>{docLoadError ?? "当前无法读取文档内容，因此先不展示空编辑器，避免和“无文档”状态混淆。"}</p>
              <div className="req-doc-state-panel-actions">
                <button type="button" className="primary" onClick={() => { void loadDoc(); void loadVersions(); }}>
                  重试加载
                </button>
              </div>
            </div>
          ) : (
            <>
              {viewMode === "edit" && (
                <>
                  {visibleStatus === "empty" && (
                    <div className="req-doc-state-panel card">
                      <h3>当前还没有文档</h3>
                      <p>这是文档初始态，不是异常。你可以直接输入第一版内容，或点击上方“{primaryGenerateLabel}”。</p>
                    </div>
                  )}
                  <textarea
                    className="req-doc-editor"
                    value={content}
                    onChange={(e) => {
                      setContent(e.target.value);
                      if (pendingContent !== null) { setPendingContent(null); setPreChangeContent(""); }
                    }}
                    placeholder={visibleStatus === "empty" ? "从这里开始写第一版需求文档…" : "在此编辑 Markdown 文档…"}
                    spellCheck={false}
                  />
                </>
              )}
              {viewMode === "preview" && (
                <div className="req-doc-preview card">
                  <MarkdownRenderer content={content || "*暂无内容*"} />
                </div>
              )}
              {viewMode === "diff" && (
                <div className="req-doc-diff card">
                  <div className="req-doc-versions">
                    <div className="flex gap-8 flex-wrap" style={{ alignItems: "center" }}>
                      <label>
                        旧版本
                        <select
                          className="input-select"
                          value={diffV1 ?? ""}
                          onChange={(e) => setDiffV1(e.target.value ? Number(e.target.value) : null)}
                        >
                          <option value="">--</option>
                          {versions.map((v) => (
                            <option key={v.version} value={v.version}>
                              v{v.version} {v.generated_by ?? ""}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label>
                        新版本
                        <select
                          className="input-select"
                          value={diffV2 ?? ""}
                          onChange={(e) => setDiffV2(e.target.value ? Number(e.target.value) : null)}
                        >
                          <option value="">--</option>
                          {versions.map((v) => (
                            <option key={v.version} value={v.version}>
                              v{v.version} {v.generated_by ?? ""}
                            </option>
                          ))}
                        </select>
                      </label>
                      <button
                        type="button"
                        className="primary xs"
                        disabled={diffV1 == null || diffV2 == null || diffLoading}
                        onClick={() => {
                          if (diffV1 != null && diffV2 != null) {
                            void loadDiff(diffV1, diffV2);
                          }
                        }}
                      >
                        {diffLoading ? "对比中..." : "对比"}
                      </button>
                      {diffContent && (
                        <button
                          type="button"
                          className="secondary xs"
                          onClick={handleReviewCurrentDraft}
                        >
                          审阅当前稿
                        </button>
                      )}
                    </div>
                    <div className="text-muted" style={{ marginTop: 8 }}>
                      默认路径：先对比当前稿与上一版本，再决定是否进入逐块审阅并保存新版本。
                    </div>
                  </div>
                  {diffLoading ? (
                    <div className="req-doc-state-panel card">
                      <h3>正在加载版本差异</h3>
                      <p>正在准备“当前稿 vs 上一版本”的对比内容。</p>
                    </div>
                  ) : diffError ? (
                    <div className="req-doc-state-panel req-doc-state-panel--danger card">
                      <h3>版本差异加载失败</h3>
                      <p>{diffError}</p>
                      <div className="req-doc-state-panel-actions">
                        <button
                          type="button"
                          className="primary"
                          disabled={diffV1 == null || diffV2 == null}
                          onClick={() => {
                            if (diffV1 != null && diffV2 != null) {
                              void loadDiff(diffV1, diffV2);
                            }
                          }}
                        >
                          重试对比
                        </button>
                      </div>
                    </div>
                  ) : diffContent ? (
                    <MarkdownDiffRenderer
                      oldContent={diffContent.v1_content}
                      newContent={diffContent.v2_content}
                    />
                  ) : (
                    <div className="req-doc-state-panel card" data-testid="diff-empty-state">
                      <h3>还没有可展示的版本差异</h3>
                      <p>{hasComparableVersions ? "请选择两个版本后点击“对比”，或直接使用默认的当前稿 vs 上一版本路径。" : "至少保存两个版本后，才能查看历史差异。先保存当前草稿形成新版本，再回来审阅。"}</p>
                    </div>
                  )}
                </div>
              )}
              {viewMode === "review" && pendingContent !== null && (
                <MarkdownDiffReviewer
                  oldContent={preChangeContent}
                  newContent={pendingContent}
                  onApply={handleApplySelection}
                  onRejectAll={handleRejectChanges}
                  saving={saving}
                />
              )}
            </>
          )}
        </div>
      </div>

      {/* Epic 预生成引导弹窗 */}
      {showGenerateModal && (
        <div className="modal-overlay" onClick={() => { if (!preGenStreaming) { setShowGenerateModal(false); preGenAbortRef.current?.abort(); } }}>
          <div className="modal-content" style={{ minWidth: 560, maxWidth: 720, maxHeight: "80vh", display: "flex", flexDirection: "column" }} onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3 style={{ margin: 0 }}>AI 生成 Epic 文档</h3>
              <button type="button" className="modal-close" onClick={() => { if (!preGenStreaming) { setShowGenerateModal(false); preGenAbortRef.current?.abort(); } }}>&times;</button>
            </div>
            <div style={{ flex: 1, overflowY: "auto", marginBottom: 12 }}>
              {preGenChatHistory.map((msg, i) => (
                <div key={i} className={`req-doc-chat-msg req-doc-chat-${msg.role}`}>
                  <div className="req-doc-chat-role">{msg.role === "user" ? "你" : "AI 分析师"}</div>
                  <div className="req-doc-chat-body">
                    {msg.role === "assistant" ? (
                      <>
                        <MarkdownRenderer content={msg.content || (preGenStreaming && i === preGenChatHistory.length - 1 ? "..." : "")} />
                        {/* AI 消息的选项卡 */}
                        {msg.options && msg.options.length > 0 && !preGenStreaming && (
                          <div className="pre-gen-options" style={{ marginTop: 12 }}>
                            {msg.options.map((opt, j) => (
                              <button
                                key={j}
                                type="button"
                                className="pre-gen-option-chip"
                                onClick={() => handlePreGenSend(opt)}
                              >
                                {opt}
                              </button>
                            ))}
                            <button
                              type="button"
                              className="pre-gen-option-chip pre-gen-option-skip"
                              onClick={() => handlePreGenSend("跳过这个问题，继续下一步")}
                            >
                              Skip
                            </button>
                          </div>
                        )}
                      </>
                    ) : (
                      <span>{msg.content}</span>
                    )}
                  </div>
                </div>
              ))}
              {preGenStreaming && (
                <div className="req-doc-streaming-indicator">
                  <span className="req-doc-progress-dot" />
                  思考中
                </div>
              )}
              <div ref={preGenChatEndRef} />
            </div>
            {/* 手动输入框（始终显示） */}
            <div style={{ display: "flex", gap: 8 }}>
              <textarea
                className="req-doc-agent-input"
                value={preGenInput}
                onChange={(e) => setPreGenInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handlePreGenSend();
                  }
                }}
                placeholder="手动输入回复，或点击上方选项快速选择…"
                rows={2}
                disabled={preGenStreaming}
                style={{ flex: 1 }}
              />
            </div>
            <div style={{ display: "flex", gap: 8, marginTop: 12, justifyContent: "flex-end" }}>
              <button type="button" className="secondary" onClick={() => { setShowGenerateModal(false); preGenAbortRef.current?.abort(); }} disabled={preGenStreaming}>
                取消
              </button>
              <button type="button" className="primary" onClick={() => handlePreGenSend()} disabled={preGenStreaming || !preGenInput.trim()}>
                发送
              </button>
              <button type="button" className="primary" onClick={handleStartGenerateFromModal} disabled={preGenStreaming || preGenChatHistory.length < 2}>
                开始生成
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 拆分建议弹窗（Epic/Story 生成后展示，或手动打开） */}
      {requirement && (requirement.level === "epic" || requirement.level === "story") && (
        <SplitSuggestionsModal
          productId={productId}
          requirementId={requirementId}
          level={requirement.level}
          open={showSplitModal}
          onClose={() => setShowSplitModal(false)}
          onSaved={() => {}}
          initialSuggestions={splitSuggestions}
        />
      )}

    </div>
  );
}

// ── 侧边栏需求树组件 ──

function getTreeDocIndicator(req: ProductRequirement): { icon: string; label: string; tone: "none" | "pending" | "generating" | "failed" | "ready" } {
  const status = req.doc_status ?? (req.has_doc ? "ready" : "none");
  switch (status) {
    case "pending":
      return { icon: "◌", label: "文档排队中", tone: "pending" };
    case "generating":
      return { icon: "◔", label: "文档生成中", tone: "generating" };
    case "failed":
      return { icon: "✗", label: "文档生成失败", tone: "failed" };
    case "ready":
      return { icon: "●", label: "已有文档", tone: "ready" };
    default:
      return { icon: "○", label: "暂无文档", tone: "none" };
  }
}

function ReqTreeSidebar({
  requirements,
  currentReqId,
  collapsed,
  onToggle,
  onSelect,
  onGenerateChildren,
  childGenParentId,
  childGenEntries,
  disableActions,
}: {
  requirements: ProductRequirement[];
  currentReqId: number;
  collapsed: Set<number>;
  onToggle: (id: number) => void;
  onSelect: (id: number) => void;
  onGenerateChildren: (parentId: number) => void;
  childGenParentId: number | null;
  childGenEntries: ChildGenerationEntry[];
  disableActions: boolean;
}) {
  const epics = requirements.filter((r) => r.level === "epic");
  const stories = requirements.filter((r) => r.level === "story");
  const tasks = requirements.filter((r) => r.level === "task");

  const renderNode = (req: ProductRequirement, indent: number, children?: ProductRequirement[]) => {
    const hasChildren = children && children.length > 0;
    const isCollapsed = collapsed.has(req.id);
    const isCurrent = req.id === currentReqId;
    const childGate = deriveChildGenerationGate(req, requirements);
    const canGenChildren = req.level === "epic" || req.level === "story";
    const isGenerating = childGenParentId === req.id;
    const docIndicator = getTreeDocIndicator(req);

    return (
      <div key={req.id}>
        <div
          className={`req-sidebar-node${isCurrent ? " req-sidebar-node--active" : ""}`}
          style={{ paddingLeft: 8 + indent * 16 }}
        >
          {hasChildren ? (
            <span className="req-sidebar-arrow" onClick={() => onToggle(req.id)}>
              {isCollapsed ? "▸" : "▾"}
            </span>
          ) : (
            <span className="req-sidebar-arrow-placeholder" />
          )}
          <span
            className="req-sidebar-doc-dot"
            data-has-doc={req.has_doc ? "true" : undefined}
            data-doc-status={docIndicator.tone}
            title={docIndicator.label}
          >
            {docIndicator.icon}
          </span>
          <span className={`req-level-badge ${req.level}`} style={{ fontSize: 10, padding: "0 4px" }}>
            {req.level[0].toUpperCase()}
          </span>
          <span
            className="req-sidebar-title"
            onClick={() => onSelect(req.id)}
            title={req.title}
          >
            {req.title}
          </span>
          {canGenChildren && (
            <button
              type="button"
              className="req-sidebar-gen-btn"
              onClick={(e) => { e.stopPropagation(); onGenerateChildren(req.id); }}
              disabled={childGenParentId !== null || disableActions || !childGate.allowed}
              title={childGate.allowed ? "生成子级文档" : (childGate.reason ?? "当前不允许生成子级文档")}
            >
              {isGenerating ? "…" : childGate.allowed ? "⚡" : "🔒"}
            </button>
          )}
        </div>
        {hasChildren && !isCollapsed && children!.map((child) => {
          if (child.level === "story") {
            const childTasks = tasks.filter((t) => t.parent_id === child.id);
            return renderNode(child, indent + 1, childTasks);
          }
          return renderNode(child, indent + 1);
        })}
        {isGenerating && childGenEntries.length > 0 && !isCollapsed && (
          <div className="req-sidebar-gen-progress" style={{ paddingLeft: 8 + (indent + 1) * 16 }}>
            {childGenEntries.map((entry) => (
              <div key={entry.reqId} className={`req-sidebar-gen-entry ${entry.status}`}>
                <span className="req-sidebar-gen-icon">
                  {entry.status === "pending" && "○"}
                  {entry.status === "running" && "◌"}
                  {entry.status === "completed" && "✓"}
                  {entry.status === "failed" && "✗"}
                </span>
                <span className="req-sidebar-gen-title">
                  {entry.title}
                  {entry.detail ? ` · ${entry.detail}` : ""}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  };

  return (
    <>
      {epics.map((epic) => {
        const childStories = stories.filter((s) => s.parent_id === epic.id);
        return renderNode(epic, 0, childStories);
      })}
      {/* 无父级的 story */}
      {stories
        .filter((s) => !s.parent_id || !epics.some((e) => e.id === s.parent_id))
        .map((story) => {
          const childTasks = tasks.filter((t) => t.parent_id === story.id);
          return renderNode(story, 0, childTasks);
        })}
      {/* 无父级的 task */}
      {tasks
        .filter((t) => !t.parent_id || !stories.some((s) => s.id === t.parent_id))
        .map((task) => renderNode(task, 0))}
    </>
  );
}
