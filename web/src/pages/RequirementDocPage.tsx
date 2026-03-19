import { useCallback, useEffect, useRef, useState } from "react";
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
  type ProductRequirement,
  type DocVersion,
} from "../api/client";
import { MarkdownRenderer } from "../components/MarkdownRenderer";
import { MarkdownDiffRenderer } from "../components/MarkdownDiffRenderer";
import { MarkdownDiffReviewer } from "../components/MarkdownDiffReviewer";
import { useAgentSession } from "../contexts/AgentSessionContext";

type ViewMode = "edit" | "preview" | "diff" | "review";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
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
  const [, setVersion] = useState(0);
  const [viewMode, setViewMode] = useState<ViewMode>("edit");
  const [versions, setVersions] = useState<DocVersion[]>([]);
  const [diffV1, setDiffV1] = useState<number | null>(null);
  const [diffV2, setDiffV2] = useState<number | null>(null);
  const [diffContent, setDiffContent] = useState<{ v1_content: string; v2_content: string } | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Review mode (agent → direct edit)
  const [pendingContent, setPendingContent] = useState<string | null>(null);
  const [preChangeContent, setPreChangeContent] = useState<string>("");

  // Generation
  const [generateStreaming, setGenerateStreaming] = useState(false);
  const [generateStep, setGenerateStep] = useState<string | null>(null);
  const [splitSuggestions, setSplitSuggestions] = useState<string | null>(null);

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

  const isDirty = content !== savedContent;

  // ── Data loading ──

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
    setError(null);
    try {
      const doc = await getRequirementDoc(productId, requirementId);
      setContent(doc.content);
      setSavedContent(doc.content);
      setVersion(doc.version);
    } catch {
      setContent("");
      setSavedContent("");
      setVersion(0);
    } finally {
      setLoading(false);
    }
  }, [productId, requirementId]);

  const loadVersions = useCallback(async () => {
    if (!productId || !requirementId) return;
    try {
      const list = await listDocVersions(productId, requirementId);
      setVersions(list);
    } catch {
      setVersions([]);
    }
  }, [productId, requirementId]);

  useEffect(() => { loadRequirement(); }, [loadRequirement]);
  useEffect(() => { loadDoc(); loadVersions(); }, [loadDoc, loadVersions]);

  // ── Unsaved changes warning ──

  useEffect(() => {
    const handler = (e: BeforeUnloadEvent) => {
      if (isDirty) { e.preventDefault(); }
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [isDirty]);

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
      if (st.generation_status === "completed") {
        if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
        setGenerationStatus(null);
        loadDoc();
        loadVersions();
      } else if (st.generation_status === "failed") {
        if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
        setGenerationStatus(null);
        setError(st.generation_error || "生成失败");
      }
    } catch { /* ignore */ }
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
    try {
      const doc = await saveRequirementDoc(productId, requirementId, content, "manual");
      setVersion(doc.version);
      setSavedContent(content);
      loadVersions();
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
    setGenerateStreaming(true);
    setGenerateStep(null);
    setError(null);
    setContent("");
    setSplitSuggestions(null);
    setViewMode("edit");
    setShowGenerateModal(false);
    streamAbortRef.current = streamGenerateDoc(productId, requirementId, {
      token: (data: unknown) => {
        const text = typeof data === "string" ? data : (data as { text?: string; content?: string })?.text ?? (data as { content?: string })?.content ?? "";
        if (text) setContent((prev) => prev + text);
      },
      workflow_step: (data: unknown) => {
        const d = data as { step?: string; status?: string };
        if (d?.status === "running" && d?.step) {
          setGenerateStep(d.step);
        }
        if (d?.status === "failed") {
          setGenerateStreaming(false);
          setGenerateStep(null);
          setError("生成失败");
          streamAbortRef.current = null;
        }
      },
      split_suggestions: (data: unknown) => {
        const d = data as { content?: string };
        if (d?.content) setSplitSuggestions(d.content);
      },
      workflow_done: (data: unknown) => {
        setGenerateStreaming(false);
        setGenerateStep(null);
        streamAbortRef.current = null;
        const d = data as { status?: string; error?: string };
        if (d?.status === "failed" && d?.error) {
          setError(d.error);
        } else {
          loadDoc();
          loadVersions();
        }
      },
    }, userOverview);
  };

  const handleStopStream = () => {
    streamAbortRef.current?.abort();
    streamAbortRef.current = null;
    if (generateStreaming) {
      setGenerateStreaming(false);
      setGenerateStep(null);
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
        setPreGenStreaming(false);
        preGenAbortRef.current = null;
      },
      error: () => {
        setPreGenStreaming(false);
        preGenAbortRef.current = null;
      },
    });
  };

  const handlePreGenSend = () => {
    const msg = preGenInput.trim();
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
    try {
      const d = await getDocDiff(productId, requirementId, v1, v2);
      setDiffContent(d);
    } catch {
      setDiffContent(null);
    }
  }, [productId, requirementId]);

  const handleSwitchToDiff = () => {
    setViewMode("diff");
    // 自动选择最新两个版本
    if (versions.length >= 2 && diffV1 == null && diffV2 == null) {
      const sorted = [...versions].sort((a, b) => a.version - b.version);
      const v1 = sorted[sorted.length - 2].version;
      const v2 = sorted[sorted.length - 1].version;
      setDiffV1(v1);
      setDiffV2(v2);
      loadDiff(v1, v2);
    } else if (diffV1 != null && diffV2 != null) {
      loadDiff(diffV1, diffV2);
    }
  };

  const handleApplySelection = async (rebuiltContent: string) => {
    if (!productId || !requirementId) return;
    setSaving(true);
    setError(null);
    try {
      const doc = await saveRequirementDoc(productId, requirementId, rebuiltContent, "agent");
      setContent(rebuiltContent);
      setSavedContent(rebuiltContent);
      setVersion(doc.version);
      loadVersions();
      setPendingContent(null);
      setPreChangeContent("");
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
    setViewMode("edit");
  };

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

          <div className="req-doc-toolbar">
            <div className="req-doc-view-mode">
              <button
                type="button"
                className={viewMode === "edit" ? "primary xs" : "secondary xs"}
                onClick={() => setViewMode("edit")}
              >
                编辑
              </button>
              <button
                type="button"
                className={viewMode === "preview" ? "primary xs" : "secondary xs"}
                onClick={() => setViewMode("preview")}
              >
                预览
              </button>
              <button
                type="button"
                className={viewMode === "diff" ? "primary xs" : "secondary xs"}
                onClick={handleSwitchToDiff}
              >
                变更
              </button>
              {pendingContent !== null && (
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
              {isDirty && <span className="req-doc-dirty-badge">未保存</span>}
              <button
                type="button"
                className="primary"
                onClick={handleSave}
                disabled={saving || loading || !isDirty}
                title="Ctrl+S"
              >
                {saving ? "保存中…" : "保存"}
              </button>
              {generateStreaming ? (
                <button type="button" className="secondary" onClick={handleStopStream}>
                  停止
                </button>
              ) : (
                <button
                  type="button"
                  className="primary"
                  onClick={handleGenerateClick}
                  disabled={loading || generationStatus === "running"}
                >
                  {generationStatus === "running" ? "生成中…" : "AI 生成"}
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
        </div>

        {/* 可滚动内容区域：编辑模式由 textarea 自带滚动，其余模式外层滚动 */}
        <div className={`req-doc-content-scroll${viewMode !== "edit" ? " req-doc-content-scroll--scrollable" : ""}`} ref={contentAreaRef}>
          {loading ? (
            <div className="loading-state">加载中...</div>
          ) : (
            <>
              {viewMode === "edit" && (
                <textarea
                  className="req-doc-editor"
                  value={content}
                  onChange={(e) => {
                    setContent(e.target.value);
                    if (pendingContent !== null) { setPendingContent(null); setPreChangeContent(""); }
                  }}
                  placeholder="在此编辑 Markdown 文档…"
                  spellCheck={false}
                />
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
                        disabled={diffV1 == null || diffV2 == null}
                        onClick={() => {
                          if (diffV1 != null && diffV2 != null) {
                            loadDiff(diffV1, diffV2);
                          }
                        }}
                      >
                        对比
                      </button>
                    </div>
                  </div>
                  {diffContent && (
                    <MarkdownDiffRenderer
                      oldContent={diffContent.v1_content}
                      newContent={diffContent.v2_content}
                    />
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
                      <MarkdownRenderer content={msg.content || (preGenStreaming && i === preGenChatHistory.length - 1 ? "..." : "")} />
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
                placeholder="回复 AI 的问题…"
                rows={2}
                disabled={preGenStreaming}
                style={{ flex: 1 }}
              />
            </div>
            <div style={{ display: "flex", gap: 8, marginTop: 12, justifyContent: "flex-end" }}>
              <button type="button" className="secondary" onClick={() => { setShowGenerateModal(false); preGenAbortRef.current?.abort(); }} disabled={preGenStreaming}>
                取消
              </button>
              <button type="button" className="primary" onClick={handlePreGenSend} disabled={preGenStreaming || !preGenInput.trim()}>
                发送
              </button>
              <button type="button" className="primary" onClick={handleStartGenerateFromModal} disabled={preGenStreaming || preGenChatHistory.length < 2}>
                开始生成
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 拆分建议面板（Epic/Story 生成后展示） */}
      {splitSuggestions && (
        <div className="req-doc-split-suggestions card">
          <div className="req-doc-split-suggestions-header">
            <span>{requirement?.level === "epic" ? "Story 拆分建议" : "Task 拆分建议"}</span>
            <button type="button" className="secondary xs" onClick={() => setSplitSuggestions(null)}>关闭</button>
          </div>
          <MarkdownRenderer content={splitSuggestions} />
        </div>
      )}

    </div>
  );
}
