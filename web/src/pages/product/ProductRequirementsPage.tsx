import { useEffect, useRef, useState } from "react";
import { useVersionPageContext } from "./ProductVersionWorkspacePage";
import {
  listProductRequirementsTree,
  createProductRequirement,
  updateProductRequirement,
  deleteProductRequirement,
  canGenerateChildren,
  streamGenerateChildrenDocs,
  type ProductRequirement,
} from "../../api/client";

const STATUS_OPTIONS = ["open", "in_progress", "done", "closed"];
const PRIORITY_OPTIONS = ["low", "medium", "high", "critical"];

const CHILD_LEVEL: Record<string, string> = {
  epic: "story",
  story: "task",
};

const CHILD_LABEL: Record<string, string> = {
  epic: "+Story",
  story: "+Task",
};

const STEP_LABELS: Record<string, string> = {
  collect_context: "收集上下文",
  code_search:     "代码检索",
  graph_search:    "图谱检索",
  synthesize:      "合并结果",
  generate_doc:    "生成文档",
  save_draft:      "保存草稿",
};

type ChildGenStatus = "pending" | "running" | "completed" | "failed";

interface ChildProgressEntry {
  reqId: number;
  title: string;
  isNew: boolean;
  status: ChildGenStatus;
  currentStep?: string | null;
  error?: string;
}

function ChildrenProgressPanel({
  entries,
  onAbort,
}: {
  entries: ChildProgressEntry[];
  onAbort: () => void;
}) {
  const completed = entries.filter((e) => e.status === "completed").length;
  const failed    = entries.filter((e) => e.status === "failed").length;
  const total     = entries.length;

  return (
    <div className="children-gen-panel">
      <div className="children-gen-header">
        <span>
          批量生成子级文档 · {completed}/{total} 完成
          {failed > 0 && <span className="children-gen-failed-count"> · {failed} 失败</span>}
        </span>
        <button type="button" className="secondary xs" onClick={onAbort}>中止</button>
      </div>
      <div className="children-gen-list">
        {entries.map((entry) => (
          <div key={entry.reqId} className={`children-gen-item ${entry.status}`}>
            <span className="children-gen-icon">
              {entry.status === "pending"   && <span className="children-gen-dot">○</span>}
              {entry.status === "running"   && <span className="req-doc-progress-dot" />}
              {entry.status === "completed" && <span className="children-gen-dot ok">✓</span>}
              {entry.status === "failed"    && <span className="children-gen-dot err">✗</span>}
            </span>
            <span className="children-gen-title">{entry.title}</span>
            {entry.isNew && <span className="children-gen-new-badge">新建</span>}
            {entry.status === "running" && entry.currentStep && (
              <span className="children-gen-step">
                {STEP_LABELS[entry.currentStep] ?? entry.currentStep}
              </span>
            )}
            {entry.status === "failed" && entry.error && (
              <span className="children-gen-error">{entry.error}</span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export function ProductRequirementsPage() {
  const { productId, versionId } = useVersionPageContext();
  const [requirements, setRequirements] = useState<ProductRequirement[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 顶层 Epic 创建
  const [showCreate, setShowCreate] = useState(false);
  const [epicForm, setEpicForm] = useState({ title: "", description: "", priority: "medium" });

  // 内联子需求创建（同一时间仅一个）
  const [inlineCreate, setInlineCreate] = useState<{ parentId: number; level: string } | null>(null);
  const [inlineForm, setInlineForm] = useState({ title: "", priority: "medium" });

  // 折叠状态
  const [collapsed, setCollapsed] = useState<Set<number>>(new Set());

  // 批量生成子级文档状态
  const [generatingParentId, setGeneratingParentId] = useState<number | null>(null);
  const [childrenProgress, setChildrenProgress] = useState<ChildProgressEntry[]>([]);
  const generateChildrenAbortRef = useRef<{ abort: () => void } | null>(null);

  const toggleCollapse = (id: number) =>
    setCollapsed((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const reqs = await listProductRequirementsTree(productId, versionId);
      setRequirements(reqs);
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
    } finally {
      setLoading(false);
    }
  };

  // 静默刷新需求树（has_doc 更新），不触发 loading spinner
  const silentLoad = async () => {
    try {
      const reqs = await listProductRequirementsTree(productId, versionId);
      setRequirements(reqs);
    } catch { /* ignore */ }
  };

  useEffect(() => {
    load();
  }, [productId, versionId]);

  const handleCreateEpic = async () => {
    if (!epicForm.title.trim()) return;
    try {
      await createProductRequirement(productId, {
        title: epicForm.title.trim(),
        level: "epic",
        description: epicForm.description.trim() || undefined,
        priority: epicForm.priority,
        version_id: versionId,
      });
      setEpicForm({ title: "", description: "", priority: "medium" });
      setShowCreate(false);
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "创建失败");
    }
  };

  const handleCreateChild = async () => {
    if (!inlineCreate || !inlineForm.title.trim()) return;
    try {
      await createProductRequirement(productId, {
        title: inlineForm.title.trim(),
        level: inlineCreate.level,
        parent_id: inlineCreate.parentId,
        priority: inlineForm.priority,
        version_id: versionId,
      });
      setInlineCreate(null);
      setInlineForm({ title: "", priority: "medium" });
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "创建失败");
    }
  };

  const openInlineCreate = (parentId: number, level: string) => {
    setInlineCreate({ parentId, level });
    setInlineForm({ title: "", priority: "medium" });
  };

  const handleStatusChange = async (id: number, status: string) => {
    try {
      await updateProductRequirement(productId, id, { status });
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "更新失败");
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("确定删除？子需求也会被删除。")) return;
    try {
      await deleteProductRequirement(productId, id);
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "删除失败");
    }
  };

  const handleGenerateChildren = async (parentId: number) => {
    if (generatingParentId !== null) return;  // 全局互锁
    try {
      const { can_generate_children } = await canGenerateChildren(productId, parentId);
      if (!can_generate_children) {
        setError("请先完成当前需求文档后再生成子级文档");
        return;
      }
      setGeneratingParentId(parentId);
      setChildrenProgress([]);
      setError(null);
      // 自动展开父节点，确保进度面板可见
      setCollapsed((prev) => { const n = new Set(prev); n.delete(parentId); return n; });

      generateChildrenAbortRef.current = streamGenerateChildrenDocs(productId, parentId, {
        decompose_done: (data) => {
          const d = data as { children: { requirement_id: number; title: string; is_new: boolean }[] };
          setChildrenProgress(
            d.children.map((c) => ({
              reqId: c.requirement_id,
              title: c.title ?? `需求 #${c.requirement_id}`,
              isNew: c.is_new,
              status: "pending",
            }))
          );
        },
        child_start: (data) => {
          const { requirement_id } = data as { requirement_id: number };
          setChildrenProgress((prev) =>
            prev.map((c) => c.reqId === requirement_id ? { ...c, status: "running", currentStep: null } : c)
          );
        },
        child_progress: (data) => {
          const d = data as { requirement_id: number; step?: string; status?: string };
          if (d.status === "running" && d.step) {
            setChildrenProgress((prev) =>
              prev.map((c) => c.reqId === d.requirement_id ? { ...c, currentStep: d.step! } : c)
            );
          }
        },
        child_done: (data) => {
          const { requirement_id, status, error } = data as {
            requirement_id: number; status: string; error?: string;
          };
          setChildrenProgress((prev) =>
            prev.map((c) =>
              c.reqId === requirement_id
                ? { ...c, status: status === "completed" ? "completed" : "failed", currentStep: null, error }
                : c
            )
          );
          silentLoad();  // 每个子文档完成后立即更新需求树 has_doc 状态
        },
        workflow_done: () => {
          setGeneratingParentId(null);
          setChildrenProgress([]);
          generateChildrenAbortRef.current = null;
          load();  // 全部完成后完整刷新
        },
      });
    } catch (e) {
      setGeneratingParentId(null);
      setError(e instanceof Error ? e.message : "校验失败");
    }
  };

  const abortGeneration = () => {
    generateChildrenAbortRef.current?.abort();
    setGeneratingParentId(null);
    setChildrenProgress([]);
    generateChildrenAbortRef.current = null;
  };

  // 构建树
  const epics = requirements.filter((r) => r.level === "epic");
  const stories = requirements.filter((r) => r.level === "story");
  const tasks = requirements.filter((r) => r.level === "task");

  if (loading) return <div className="loading-state">加载中...</div>;

  // 内联创建表单渲染
  const renderInlineForm = (parentId: number, level: string) => {
    if (!inlineCreate || inlineCreate.parentId !== parentId || inlineCreate.level !== level) return null;
    const indent = level === "story" ? 24 : 48;
    return (
      <div
        style={{
          marginLeft: indent,
          padding: "8px 12px",
          border: "1px dashed var(--color-primary)",
          borderRadius: "var(--radius-input)",
          background: "rgba(0, 240, 255, 0.04)",
          display: "flex",
          alignItems: "center",
          gap: 8,
        }}
      >
        <span className={`req-level-badge ${level}`}>{level}</span>
        <input
          style={{ flex: 1, padding: "4px 8px", fontSize: 13 }}
          value={inlineForm.title}
          onChange={(e) => setInlineForm({ ...inlineForm, title: e.target.value })}
          placeholder={`${level === "story" ? "Story" : "Task"} 标题`}
          autoFocus
          onKeyDown={(e) => { if (e.key === "Enter") handleCreateChild(); if (e.key === "Escape") setInlineCreate(null); }}
        />
        <select
          className="input-select"
          value={inlineForm.priority}
          onChange={(e) => setInlineForm({ ...inlineForm, priority: e.target.value })}
          style={{ minWidth: "5rem", padding: "2px 8px", fontSize: 12 }}
        >
          {PRIORITY_OPTIONS.map((p) => (
            <option key={p} value={p}>{p}</option>
          ))}
        </select>
        <button type="button" className="primary xs" onClick={handleCreateChild} disabled={!inlineForm.title.trim()}>
          创建
        </button>
        <button type="button" className="secondary xs" onClick={() => setInlineCreate(null)}>
          取消
        </button>
      </div>
    );
  };

  return (
    <div data-testid="page-product-requirements">
      <div className="page-toolbar">
        <h3>需求管理</h3>
        <button type="button" className="primary" onClick={() => setShowCreate(!showCreate)}>
          {showCreate ? "取消" : "新建 Epic"}
        </button>
      </div>

      {error && <div className="result error">{error}</div>}

      {showCreate && (
        <div className="card mb-16">
          <div className="flex gap-12 flex-wrap">
            <div className="form-row flex-1" style={{ minWidth: 200 }}>
              <label>标题 *</label>
              <input
                value={epicForm.title}
                onChange={(e) => setEpicForm({ ...epicForm, title: e.target.value })}
                placeholder="Epic 标题"
                onKeyDown={(e) => { if (e.key === "Enter") handleCreateEpic(); }}
              />
            </div>
            <div className="form-row">
              <label>优先级</label>
              <select
                className="input-select"
                value={epicForm.priority}
                onChange={(e) => setEpicForm({ ...epicForm, priority: e.target.value })}
              >
                {PRIORITY_OPTIONS.map((p) => (
                  <option key={p} value={p}>{p}</option>
                ))}
              </select>
            </div>
          </div>
          <div className="form-row">
            <label>描述</label>
            <input
              value={epicForm.description}
              onChange={(e) => setEpicForm({ ...epicForm, description: e.target.value })}
              placeholder="Epic 描述"
            />
          </div>
          <button type="button" className="primary" onClick={handleCreateEpic} disabled={!epicForm.title.trim()}>
            创建 Epic
          </button>
        </div>
      )}

      <div className="stats mb-16">
        <div className="stat">Epic: {epics.length}</div>
        <div className="stat">Story: {stories.length}</div>
        <div className="stat">Task: {tasks.length}</div>
      </div>

      {requirements.length === 0 ? (
        <div className="empty-state">暂无需求</div>
      ) : (
        <div className="req-tree">
          {epics.map((epic) => {
            const childStories = stories.filter((s) => s.parent_id === epic.id);
            const isEpicCollapsed = collapsed.has(epic.id);
            return (
              <div key={epic.id}>
                <RequirementRow
                  req={epic}
                  productId={productId}
                  onStatusChange={handleStatusChange}
                  onDelete={handleDelete}
                  onCreateChild={openInlineCreate}
                  onGenerateChildren={handleGenerateChildren}
                  hasChildren={childStories.length > 0}
                  isCollapsed={isEpicCollapsed}
                  onToggleCollapse={() => toggleCollapse(epic.id)}
                  generatingParentId={generatingParentId}
                />
                {!isEpicCollapsed && (
                  <>
                    {generatingParentId === epic.id && childrenProgress.length > 0 && (
                      <ChildrenProgressPanel
                        entries={childrenProgress}
                        onAbort={abortGeneration}
                      />
                    )}
                    {renderInlineForm(epic.id, "story")}
                    {childStories.map((story) => {
                      const childTasks = tasks.filter((t) => t.parent_id === story.id);
                      const isStoryCollapsed = collapsed.has(story.id);
                      return (
                        <div key={story.id}>
                          <RequirementRow
                            req={story}
                            productId={productId}
                            onStatusChange={handleStatusChange}
                            onDelete={handleDelete}
                            onCreateChild={openInlineCreate}
                            onGenerateChildren={handleGenerateChildren}
                            hasChildren={childTasks.length > 0}
                            isCollapsed={isStoryCollapsed}
                            onToggleCollapse={() => toggleCollapse(story.id)}
                            generatingParentId={generatingParentId}
                          />
                          {!isStoryCollapsed && (
                            <>
                              {generatingParentId === story.id && childrenProgress.length > 0 && (
                                <ChildrenProgressPanel
                                  entries={childrenProgress}
                                  onAbort={abortGeneration}
                                />
                              )}
                              {renderInlineForm(story.id, "task")}
                              {childTasks.map((task) => (
                                <RequirementRow
                                  key={task.id}
                                  req={task}
                                  productId={productId}
                                  onStatusChange={handleStatusChange}
                                  onDelete={handleDelete}
                                  generatingParentId={generatingParentId}
                                />
                              ))}
                            </>
                          )}
                        </div>
                      );
                    })}
                  </>
                )}
              </div>
            );
          })}
          {/* 无父级的 story 和 task */}
          {stories
            .filter((s) => !s.parent_id || !epics.some((e) => e.id === s.parent_id))
            .map((story) => {
              const childTasks = tasks.filter((t) => t.parent_id === story.id);
              const isStoryCollapsed = collapsed.has(story.id);
              return (
                <div key={story.id}>
                  <RequirementRow
                    req={story}
                    productId={productId}
                    onStatusChange={handleStatusChange}
                    onDelete={handleDelete}
                    onCreateChild={openInlineCreate}
                    onGenerateChildren={handleGenerateChildren}
                    hasChildren={childTasks.length > 0}
                    isCollapsed={isStoryCollapsed}
                    onToggleCollapse={() => toggleCollapse(story.id)}
                    generatingParentId={generatingParentId}
                  />
                  {!isStoryCollapsed && (
                    <>
                      {generatingParentId === story.id && childrenProgress.length > 0 && (
                        <ChildrenProgressPanel
                          entries={childrenProgress}
                          onAbort={abortGeneration}
                        />
                      )}
                      {renderInlineForm(story.id, "task")}
                      {childTasks.map((task) => (
                        <RequirementRow
                          key={task.id}
                          req={task}
                          productId={productId}
                          onStatusChange={handleStatusChange}
                          onDelete={handleDelete}
                          generatingParentId={generatingParentId}
                        />
                      ))}
                    </>
                  )}
                </div>
              );
            })}
          {tasks
            .filter((t) => !t.parent_id || !stories.some((s) => s.id === t.parent_id))
            .map((task) => (
              <RequirementRow
                key={task.id}
                req={task}
                productId={productId}
                onStatusChange={handleStatusChange}
                onDelete={handleDelete}
                generatingParentId={generatingParentId}
              />
            ))}
        </div>
      )}
    </div>
  );
}

function RequirementRow({
  req,
  productId,
  onStatusChange,
  onDelete,
  onCreateChild,
  onGenerateChildren,
  hasChildren,
  isCollapsed,
  onToggleCollapse,
  generatingParentId,
}: {
  req: ProductRequirement;
  productId: number;
  onStatusChange: (id: number, status: string) => void;
  onDelete: (id: number) => void;
  onCreateChild?: (parentId: number, level: string) => void;
  onGenerateChildren?: (parentId: number) => void;
  hasChildren?: boolean;
  isCollapsed?: boolean;
  onToggleCollapse?: () => void;
  generatingParentId?: number | null;
}) {
  const childLevel = CHILD_LEVEL[req.level];
  const childLabel = CHILD_LABEL[req.level];
  const docUrl = `/products/${productId}/requirements/${req.id}/doc`;
  const isGenerating = generatingParentId === req.id;
  const isAnyGenerating = generatingParentId !== null;

  return (
    <div className={`req-tree-item ${req.level}`} data-has-doc={req.has_doc ? "true" : undefined}>
      {hasChildren && onToggleCollapse ? (
        <span
          onClick={onToggleCollapse}
          style={{ cursor: "pointer", userSelect: "none", fontSize: 11, width: 16, textAlign: "center", flexShrink: 0 }}
        >
          {isCollapsed ? "+" : "-"}
        </span>
      ) : req.level !== "task" ? (
        <span style={{ width: 16, flexShrink: 0 }} />
      ) : null}
      <span
        className="req-doc-status"
        title={req.has_doc ? "有文档" : "无文档"}
        aria-hidden
      >
        {req.has_doc ? "●" : "○"}
      </span>
      <span className={`req-level-badge ${req.level}`}>{req.level}</span>
      <span className="flex-1">{req.title}</span>
      <a
        href={docUrl}
        target="_blank"
        rel="noopener noreferrer"
        className="secondary xs"
        style={{ textDecoration: "none" }}
      >
        文档
      </a>
      {childLevel && onCreateChild && (
        <button
          type="button"
          className="secondary xs"
          onClick={() => onCreateChild(req.id, childLevel)}
          style={{ color: "var(--color-primary)", borderColor: "var(--color-primary)" }}
        >
          {childLabel}
        </button>
      )}
      {childLevel && onGenerateChildren && (req.level === "epic" || req.level === "story") && (
        <button
          type="button"
          className="secondary xs"
          onClick={() => onGenerateChildren(req.id)}
          disabled={isAnyGenerating}
          title="批量生成子级需求文档"
        >
          {isGenerating ? "生成中…" : "生成子级文档"}
        </button>
      )}
      <select
        className="input-select"
        value={req.status}
        onChange={(e) => onStatusChange(req.id, e.target.value)}
        style={{ minWidth: "6rem", padding: "2px 8px", fontSize: 12 }}
        onClick={(e) => e.stopPropagation()}
      >
        {STATUS_OPTIONS.map((s) => (
          <option key={s} value={s}>{s}</option>
        ))}
      </select>
      <span className={`status-badge ${req.status}`}>{req.priority}</span>
      {req.assignee && (
        <span className="text-caption text-muted" style={{ fontSize: 11 }}>{req.assignee}</span>
      )}
      <button
        type="button"
        className="secondary xs"
        onClick={() => onDelete(req.id)}
      >
        删除
      </button>
    </div>
  );
}
