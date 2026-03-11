import { useEffect, useState } from "react";
import { useVersionPageContext } from "./ProductVersionWorkspacePage";
import {
  listProductRequirementsTree,
  createProductRequirement,
  updateProductRequirement,
  deleteProductRequirement,
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
                  onStatusChange={handleStatusChange}
                  onDelete={handleDelete}
                  onCreateChild={openInlineCreate}
                  hasChildren={childStories.length > 0}
                  isCollapsed={isEpicCollapsed}
                  onToggleCollapse={() => toggleCollapse(epic.id)}
                />
                {!isEpicCollapsed && (
                  <>
                    {renderInlineForm(epic.id, "story")}
                    {childStories.map((story) => {
                      const childTasks = tasks.filter((t) => t.parent_id === story.id);
                      const isStoryCollapsed = collapsed.has(story.id);
                      return (
                        <div key={story.id}>
                          <RequirementRow
                            req={story}
                            onStatusChange={handleStatusChange}
                            onDelete={handleDelete}
                            onCreateChild={openInlineCreate}
                            hasChildren={childTasks.length > 0}
                            isCollapsed={isStoryCollapsed}
                            onToggleCollapse={() => toggleCollapse(story.id)}
                          />
                          {!isStoryCollapsed && (
                            <>
                              {renderInlineForm(story.id, "task")}
                              {childTasks.map((task) => (
                                <RequirementRow
                                  key={task.id}
                                  req={task}
                                  onStatusChange={handleStatusChange}
                                  onDelete={handleDelete}
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
                    onStatusChange={handleStatusChange}
                    onDelete={handleDelete}
                    onCreateChild={openInlineCreate}
                    hasChildren={childTasks.length > 0}
                    isCollapsed={isStoryCollapsed}
                    onToggleCollapse={() => toggleCollapse(story.id)}
                  />
                  {!isStoryCollapsed && (
                    <>
                      {renderInlineForm(story.id, "task")}
                      {childTasks.map((task) => (
                        <RequirementRow
                          key={task.id}
                          req={task}
                          onStatusChange={handleStatusChange}
                          onDelete={handleDelete}
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
                onStatusChange={handleStatusChange}
                onDelete={handleDelete}
              />
            ))}
        </div>
      )}
    </div>
  );
}

function RequirementRow({
  req,
  onStatusChange,
  onDelete,
  onCreateChild,
  hasChildren,
  isCollapsed,
  onToggleCollapse,
}: {
  req: ProductRequirement;
  onStatusChange: (id: number, status: string) => void;
  onDelete: (id: number) => void;
  onCreateChild?: (parentId: number, level: string) => void;
  hasChildren?: boolean;
  isCollapsed?: boolean;
  onToggleCollapse?: () => void;
}) {
  const childLevel = CHILD_LEVEL[req.level];
  const childLabel = CHILD_LABEL[req.level];

  return (
    <div className={`req-tree-item ${req.level}`}>
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
      <span className={`req-level-badge ${req.level}`}>{req.level}</span>
      <span className="flex-1">{req.title}</span>
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
