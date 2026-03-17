import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  getProductRequirement,
  getRequirementDoc,
  saveRequirementDoc,
  listDocVersions,
  getDocDiff,
  streamGenerateDoc,
  streamDocEditorChat,
  type ProductRequirement,
  type DocVersion,
} from "../api/client";
import { MarkdownRenderer } from "../components/MarkdownRenderer";
import { MarkdownDiffRenderer } from "../components/MarkdownDiffRenderer";

type ViewMode = "edit" | "preview" | "diff";

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
  const [, setVersion] = useState(0);
  const [viewMode, setViewMode] = useState<ViewMode>("edit");
  const [versions, setVersions] = useState<DocVersion[]>([]);
  const [diffV1, setDiffV1] = useState<number | null>(null);
  const [diffV2, setDiffV2] = useState<number | null>(null);
  const [diffContent, setDiffContent] = useState<{ v1_content: string; v2_content: string } | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [agentInput, setAgentInput] = useState("");
  const [agentReply, setAgentReply] = useState("");
  const [agentStreaming, setAgentStreaming] = useState(false);
  const [generateStreaming, setGenerateStreaming] = useState(false);
  const streamAbortRef = useRef<{ abort: () => void } | null>(null);

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
      setVersion(doc.version);
    } catch {
      setContent("");
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

  useEffect(() => {
    loadRequirement();
  }, [loadRequirement]);

  useEffect(() => {
    loadDoc();
    loadVersions();
  }, [loadDoc, loadVersions]);

  const handleSave = async () => {
    if (!productId || !requirementId) return;
    setSaving(true);
    setError(null);
    try {
      const doc = await saveRequirementDoc(productId, requirementId, content, "manual");
      setVersion(doc.version);
      loadVersions();
    } catch (e) {
      setError(e instanceof Error ? e.message : "保存失败");
    } finally {
      setSaving(false);
    }
  };

  const handleGenerate = () => {
    if (!productId || !requirementId) return;
    setGenerateStreaming(true);
    setError(null);
    streamAbortRef.current = streamGenerateDoc(productId, requirementId, {
      token: (data: unknown) => {
        const text = typeof data === "string" ? data : (data as { content?: string })?.content ?? "";
        setContent((prev) => prev + text);
      },
      workflow_done: () => {
        setGenerateStreaming(false);
        loadDoc();
        loadVersions();
        streamAbortRef.current = null;
      },
      workflow_step: (data: unknown) => {
        if ((data as { status?: string })?.status === "failed") {
          setGenerateStreaming(false);
          streamAbortRef.current = null;
        }
      },
    });
  };

  const loadDiff = useCallback(async (v1: number, v2: number) => {
    if (!productId || !requirementId) return;
    try {
      const d = await getDocDiff(productId, requirementId, v1, v2);
      setDiffContent(d);
      setViewMode("diff");
    } catch {
      setDiffContent(null);
    }
  }, [productId, requirementId]);

  const handleAgentSend = () => {
    const msg = agentInput.trim();
    if (!msg || !productId || !requirementId || agentStreaming) return;
    setAgentInput("");
    setAgentReply("");
    setAgentStreaming(true);
    streamAbortRef.current = streamDocEditorChat(productId, requirementId, msg, {
      token: (data: unknown) => {
        const text = typeof data === "string" ? data : "";
        setAgentReply((prev) => prev + text);
      },
      done: (data: unknown) => {
        const d = data as { content?: string };
        if (d?.content) setAgentReply(d.content);
        setAgentStreaming(false);
        streamAbortRef.current = null;
      },
      error: (data: unknown) => {
        setError((data as { message?: string })?.message ?? "Agent 错误");
        setAgentStreaming(false);
        streamAbortRef.current = null;
      },
    });
  };

  const handleApplyAgentReply = async () => {
    if (!agentReply.trim() || !productId || !requirementId) return;
    setContent(agentReply);
    setSaving(true);
    setError(null);
    try {
      await saveRequirementDoc(productId, requirementId, agentReply, "agent");
      const doc = await getRequirementDoc(productId, requirementId);
      setVersion(doc.version);
      loadVersions();
      setViewMode("diff");
      setDiffContent({ v1_content: content, v2_content: agentReply });
    } catch (e) {
      setError(e instanceof Error ? e.message : "应用失败");
    } finally {
      setSaving(false);
    }
  };

  useEffect(() => {
    return () => {
      streamAbortRef.current?.abort();
    };
  }, []);

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
        <div className="req-doc-header">
          <button type="button" className="secondary xs" onClick={() => navigate(-1)}>
            ← 返回
          </button>
          {requirement && (
            <div className="req-doc-info card">
              <span className={`req-level-badge ${requirement.level}`}>{requirement.level}</span>
              <strong>{requirement.title}</strong>
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
              onClick={() => {
                setViewMode("diff");
                if (diffV1 != null && diffV2 != null) loadDiff(diffV1, diffV2);
              }}
            >
              变更
            </button>
          </div>
          <div className="req-doc-actions">
            <button
              type="button"
              className="primary"
              onClick={handleSave}
              disabled={saving || loading}
            >
              {saving ? "保存中…" : "保存"}
            </button>
            <button
              type="button"
              className="primary"
              onClick={handleGenerate}
              disabled={generateStreaming || loading}
            >
              {generateStreaming ? "生成中…" : "AI 生成"}
            </button>
          </div>
        </div>

        {error && <div className="result error">{error}</div>}

        {loading ? (
          <div className="loading-state">加载中...</div>
        ) : (
          <>
            {viewMode === "edit" && (
              <textarea
                className="req-doc-editor"
                value={content}
                onChange={(e) => setContent(e.target.value)}
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
                {diffContent ? (
                  <MarkdownDiffRenderer
                    oldContent={diffContent.v1_content}
                    newContent={diffContent.v2_content}
                  />
                ) : (
                  <div className="req-doc-versions">
                    <p className="text-muted">选择两个版本对比：</p>
                    <div className="flex gap-8 flex-wrap">
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
                        onClick={() => diffV1 != null && diffV2 != null && loadDiff(diffV1, diffV2)}
                      >
                        对比
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </div>

      <aside className="req-doc-agent-panel">
        <div className="req-doc-agent-header">文档助手</div>
        <div className="req-doc-agent-messages">
          {agentReply ? (
            <div className="req-doc-agent-reply">
              <MarkdownRenderer content={agentReply} />
            </div>
          ) : (
            <p className="text-muted text-caption">输入指令让 AI 修改或补充文档，然后点击「应用到文档」写回并保存。</p>
          )}
        </div>
        <div className="req-doc-agent-input-wrap">
          <textarea
            className="req-doc-agent-input"
            value={agentInput}
            onChange={(e) => setAgentInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleAgentSend();
              }
            }}
            placeholder="例如：把验收标准增加性能相关条目"
            rows={2}
            disabled={agentStreaming}
          />
          <button
            type="button"
            className="primary"
            onClick={handleAgentSend}
            disabled={agentStreaming || !agentInput.trim()}
          >
            {agentStreaming ? "生成中…" : "发送"}
          </button>
          <button
            type="button"
            className="secondary"
            onClick={handleApplyAgentReply}
            disabled={!agentReply.trim() || saving}
          >
            应用到文档
          </button>
        </div>
      </aside>
    </div>
  );
}
