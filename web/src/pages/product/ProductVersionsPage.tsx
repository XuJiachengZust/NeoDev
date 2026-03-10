import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useProductPageContext } from "./ProductLayoutPage";
import {
  listProductVersions,
  createProductVersion,
  deleteProductVersion,
  type ProductVersion,
} from "../../api/client";

const STATUS_LABELS: Record<string, string> = {
  planning: "规划中",
  developing: "开发中",
  testing: "测试中",
  released: "已发布",
};

export function ProductVersionsPage() {
  const { productId } = useProductPageContext();
  const navigate = useNavigate();
  const [versions, setVersions] = useState<ProductVersion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ version_name: "", description: "", status: "planning" });

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      setVersions(await listProductVersions(productId));
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [productId]);

  const handleCreate = async () => {
    if (!form.version_name.trim()) return;
    try {
      await createProductVersion(productId, {
        version_name: form.version_name.trim(),
        description: form.description.trim() || undefined,
        status: form.status,
      });
      setForm({ version_name: "", description: "", status: "planning" });
      setShowCreate(false);
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "创建失败");
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("确定删除该版本？")) return;
    try {
      await deleteProductVersion(productId, id);
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "删除失败");
    }
  };

  if (loading) return <div className="loading-state">加载中...</div>;

  return (
    <div data-testid="page-product-versions">
      <div className="page-toolbar">
        <h3>产品版本</h3>
        <button type="button" className="primary" onClick={() => setShowCreate(!showCreate)}>
          {showCreate ? "取消" : "新建版本"}
        </button>
      </div>

      {error && <div className="result error">{error}</div>}

      {showCreate && (
        <div className="card mb-16">
          <div className="form-row">
            <label>版本名称 *</label>
            <input
              value={form.version_name}
              onChange={(e) => setForm({ ...form, version_name: e.target.value })}
              placeholder="如：v1.0.0"
            />
          </div>
          <div className="form-row">
            <label>描述</label>
            <input
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              placeholder="版本描述"
            />
          </div>
          <div className="form-row">
            <label>状态</label>
            <select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>
              <option value="planning">规划中</option>
              <option value="developing">开发中</option>
              <option value="testing">测试中</option>
              <option value="released">已发布</option>
            </select>
          </div>
          <button type="button" className="primary" onClick={handleCreate} disabled={!form.version_name.trim()}>
            创建
          </button>
        </div>
      )}

      {versions.length === 0 ? (
        <div className="empty-state">暂无版本</div>
      ) : (
        <div className="list-col">
          {versions.map((v) => (
            <div
              key={v.id}
              className="card flex-center gap-16"
              style={{ cursor: "pointer" }}
              onClick={() => navigate(`${v.id}`)}
            >
              <div className="flex-1">
                <div className="text-bold">{v.version_name}</div>
                {v.description && (
                  <div className="text-caption text-muted mt-4">{v.description}</div>
                )}
              </div>
              <span className="agent-context-badge">{STATUS_LABELS[v.status] ?? v.status}</span>
              {v.release_date && (
                <span className="text-caption text-muted">{v.release_date}</span>
              )}
              <button
                type="button"
                className="secondary sm"
                onClick={(e) => {
                  e.stopPropagation();
                  handleDelete(v.id);
                }}
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
