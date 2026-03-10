import { useEffect, useState } from "react";
import { useVersionPageContext } from "./ProductVersionWorkspacePage";
import {
  listProductRequirementsTree,
  createProductRequirement,
  updateProductRequirement,
  deleteProductRequirement,
  type ProductRequirement,
} from "../../api/client";

const LEVEL_OPTIONS = ["epic", "story", "task"];
const STATUS_OPTIONS = ["open", "in_progress", "done", "closed"];
const PRIORITY_OPTIONS = ["low", "medium", "high", "critical"];

export function ProductRequirementsPage() {
  const { productId, versionId } = useVersionPageContext();
  const [requirements, setRequirements] = useState<ProductRequirement[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [createForm, setCreateForm] = useState({
    title: "",
    level: "story" as string,
    parent_id: undefined as number | undefined,
    description: "",
    priority: "medium",
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

  const handleCreate = async () => {
    if (!createForm.title.trim()) return;
    try {
      await createProductRequirement(productId, {
        title: createForm.title.trim(),
        level: createForm.level,
        parent_id: createForm.parent_id || undefined,
        description: createForm.description.trim() || undefined,
        priority: createForm.priority,
        version_id: versionId,
      });
      setCreateForm({ title: "", level: "story", parent_id: undefined, description: "", priority: "medium" });
      setShowCreate(false);
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "创建失败");
    }
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

  // parent 选项（创建 story 时选 epic，创建 task 时选 story）
  const parentOptions = createForm.level === "story" ? epics : createForm.level === "task" ? stories : [];

  if (loading) return <div className="loading-state">加载中...</div>;

  return (
    <div data-testid="page-product-requirements">
      <div className="page-toolbar">
        <h3>需求管理</h3>
        <button type="button" className="primary" onClick={() => setShowCreate(!showCreate)}>
          {showCreate ? "取消" : "新建需求"}
        </button>
      </div>

      {error && <div className="result error">{error}</div>}

      {showCreate && (
        <div className="card mb-16">
          <div className="flex gap-12 flex-wrap">
            <div className="form-row flex-1" style={{ minWidth: 200 }}>
              <label>标题 *</label>
              <input
                value={createForm.title}
                onChange={(e) => setCreateForm({ ...createForm, title: e.target.value })}
                placeholder="需求标题"
              />
            </div>
            <div className="form-row">
              <label>层级</label>
              <select
                className="input-select"
                value={createForm.level}
                onChange={(e) => setCreateForm({ ...createForm, level: e.target.value, parent_id: undefined })}
              >
                {LEVEL_OPTIONS.map((l) => (
                  <option key={l} value={l}>{l.toUpperCase()}</option>
                ))}
              </select>
            </div>
            {parentOptions.length > 0 && (
              <div className="form-row">
                <label>父需求</label>
                <select
                  className="input-select"
                  value={createForm.parent_id ?? ""}
                  onChange={(e) => setCreateForm({ ...createForm, parent_id: e.target.value ? Number(e.target.value) : undefined })}
                >
                  <option value="">无</option>
                  {parentOptions.map((p) => (
                    <option key={p.id} value={p.id}>{p.title}</option>
                  ))}
                </select>
              </div>
            )}
            <div className="form-row">
              <label>优先级</label>
              <select
                className="input-select"
                value={createForm.priority}
                onChange={(e) => setCreateForm({ ...createForm, priority: e.target.value })}
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
              value={createForm.description}
              onChange={(e) => setCreateForm({ ...createForm, description: e.target.value })}
              placeholder="需求描述"
            />
          </div>
          <button type="button" className="primary" onClick={handleCreate} disabled={!createForm.title.trim()}>
            创建
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
          {epics.map((epic) => (
            <div key={epic.id}>
              <RequirementRow
                req={epic}
                onStatusChange={handleStatusChange}
                onDelete={handleDelete}
              />
              {stories
                .filter((s) => s.parent_id === epic.id)
                .map((story) => (
                  <div key={story.id}>
                    <RequirementRow
                      req={story}
                      onStatusChange={handleStatusChange}
                      onDelete={handleDelete}
                    />
                    {tasks
                      .filter((t) => t.parent_id === story.id)
                      .map((task) => (
                        <RequirementRow
                          key={task.id}
                          req={task}
                          onStatusChange={handleStatusChange}
                          onDelete={handleDelete}
                        />
                      ))}
                  </div>
                ))}
            </div>
          ))}
          {/* 无父级的 story 和 task */}
          {stories
            .filter((s) => !s.parent_id || !epics.some((e) => e.id === s.parent_id))
            .map((story) => (
              <div key={story.id}>
                <RequirementRow
                  req={story}
                  onStatusChange={handleStatusChange}
                  onDelete={handleDelete}
                />
                {tasks
                  .filter((t) => t.parent_id === story.id)
                  .map((task) => (
                    <RequirementRow
                      key={task.id}
                      req={task}
                      onStatusChange={handleStatusChange}
                      onDelete={handleDelete}
                    />
                  ))}
              </div>
            ))}
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
}: {
  req: ProductRequirement;
  onStatusChange: (id: number, status: string) => void;
  onDelete: (id: number) => void;
}) {
  return (
    <div className={`req-tree-item ${req.level}`}>
      <span className={`req-level-badge ${req.level}`}>{req.level}</span>
      <span className="flex-1">{req.title}</span>
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
