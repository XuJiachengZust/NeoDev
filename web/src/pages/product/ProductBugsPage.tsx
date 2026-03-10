import { useEffect, useState } from "react";
import { useVersionPageContext } from "./ProductVersionWorkspacePage";
import {
  listProductBugs,
  createProductBug,
  updateProductBug,
  deleteProductBug,
  type ProductBug,
} from "../../api/client";

const STATUS_OPTIONS = ["open", "confirmed", "fixing", "resolved", "closed"];
const SEVERITY_OPTIONS = ["blocker", "critical", "major", "minor", "trivial"];
const PRIORITY_OPTIONS = ["low", "medium", "high", "critical"];

export function ProductBugsPage() {
  const { productId, versionId } = useVersionPageContext();
  const [bugs, setBugs] = useState<ProductBug[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterStatus, setFilterStatus] = useState<string | undefined>();
  const [filterSeverity, setFilterSeverity] = useState<string | undefined>();
  const [showCreate, setShowCreate] = useState(false);
  const [createForm, setCreateForm] = useState({
    title: "",
    description: "",
    severity: "minor",
    priority: "medium",
  });

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const bgs = await listProductBugs(productId, {
        status: filterStatus,
        severity: filterSeverity,
        version_id: versionId,
      });
      setBugs(bgs);
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [productId, versionId, filterStatus, filterSeverity]);

  const handleCreate = async () => {
    if (!createForm.title.trim()) return;
    try {
      await createProductBug(productId, {
        title: createForm.title.trim(),
        description: createForm.description.trim() || undefined,
        severity: createForm.severity,
        priority: createForm.priority,
        version_id: versionId,
      });
      setCreateForm({ title: "", description: "", severity: "minor", priority: "medium" });
      setShowCreate(false);
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "创建失败");
    }
  };

  const handleStatusChange = async (id: number, status: string) => {
    try {
      await updateProductBug(productId, id, { status });
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "更新失败");
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("确定删除该 Bug？")) return;
    try {
      await deleteProductBug(productId, id);
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "删除失败");
    }
  };

  if (loading) return <div className="loading-state">加载中...</div>;

  return (
    <div data-testid="page-product-bugs">
      <div className="page-toolbar">
        <h3>Bug 管理</h3>
        <select
          className="input-select"
          value={filterStatus ?? ""}
          onChange={(e) => setFilterStatus(e.target.value || undefined)}
          style={{ minWidth: "7rem" }}
        >
          <option value="">全部状态</option>
          {STATUS_OPTIONS.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
        <select
          className="input-select"
          value={filterSeverity ?? ""}
          onChange={(e) => setFilterSeverity(e.target.value || undefined)}
          style={{ minWidth: "7rem" }}
        >
          <option value="">全部严重度</option>
          {SEVERITY_OPTIONS.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
        <button type="button" className="primary" onClick={() => setShowCreate(!showCreate)}>
          {showCreate ? "取消" : "新建 Bug"}
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
                placeholder="Bug 标题"
              />
            </div>
            <div className="form-row">
              <label>严重度</label>
              <select
                className="input-select"
                value={createForm.severity}
                onChange={(e) => setCreateForm({ ...createForm, severity: e.target.value })}
              >
                {SEVERITY_OPTIONS.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>
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
              placeholder="Bug 描述"
            />
          </div>
          <button type="button" className="primary" onClick={handleCreate} disabled={!createForm.title.trim()}>
            创建
          </button>
        </div>
      )}

      <div className="stats mb-16">
        <div className="stat">总计: {bugs.length}</div>
        <div className="stat">待处理: {bugs.filter((b) => ["open", "confirmed", "fixing"].includes(b.status)).length}</div>
        <div className="stat">已解决: {bugs.filter((b) => ["resolved", "closed"].includes(b.status)).length}</div>
      </div>

      {bugs.length === 0 ? (
        <div className="empty-state">暂无 Bug</div>
      ) : (
        <div className="list-col">
          {bugs.map((bug) => (
            <div
              key={bug.id}
              className="card flex-center gap-12"
              style={{ padding: "10px 16px" }}
            >
              <span className={`severity-badge ${bug.severity}`}>{bug.severity}</span>
              <span className="flex-1">{bug.title}</span>
              <select
                className="input-select"
                value={bug.status}
                onChange={(e) => handleStatusChange(bug.id, e.target.value)}
                style={{ minWidth: "6rem", padding: "2px 8px", fontSize: 12 }}
              >
                {STATUS_OPTIONS.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
              <span className={`status-badge ${bug.status}`}>{bug.status}</span>
              {bug.assignee && (
                <span className="text-caption text-muted" style={{ fontSize: 11 }}>{bug.assignee}</span>
              )}
              <button
                type="button"
                className="secondary xs"
                onClick={() => handleDelete(bug.id)}
              >
                删除
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
