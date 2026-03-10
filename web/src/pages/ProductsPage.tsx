import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  listProducts,
  createProduct,
  deleteProduct,
  type Product,
} from "../api/client";

export function ProductsPage() {
  const navigate = useNavigate();
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ name: "", code: "", description: "" });

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      setProducts(await listProducts());
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleCreate = async () => {
    if (!form.name.trim()) return;
    try {
      await createProduct({
        name: form.name.trim(),
        code: form.code.trim() || undefined,
        description: form.description.trim() || undefined,
      });
      setForm({ name: "", code: "", description: "" });
      setShowCreate(false);
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "创建失败");
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("确定删除该产品？")) return;
    try {
      await deleteProduct(id);
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "删除失败");
    }
  };

  return (
    <div data-testid="page-products">
      <div className="page-toolbar mb-24">
        <h1 className="page-title" style={{ margin: 0 }}>产品管理</h1>
        <button type="button" className="primary" onClick={() => setShowCreate(!showCreate)}>
          {showCreate ? "取消" : "新建产品"}
        </button>
      </div>

      {showCreate && (
        <div className="card mb-24">
          <h3>新建产品</h3>
          <div className="form-row">
            <label>产品名称 *</label>
            <input
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="如：NeoDev 平台"
            />
          </div>
          <div className="form-row">
            <label>产品编码</label>
            <input
              value={form.code}
              onChange={(e) => setForm({ ...form, code: e.target.value })}
              placeholder="如：NEODEV"
            />
          </div>
          <div className="form-row">
            <label>描述</label>
            <input
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              placeholder="产品简要描述"
            />
          </div>
          <button type="button" className="primary" onClick={handleCreate} disabled={!form.name.trim()}>
            创建
          </button>
        </div>
      )}

      {error && <div className="result error">{error}</div>}
      {loading && <div className="loading-state">加载中...</div>}

      {!loading && products.length === 0 && (
        <div className="empty-state">暂无产品，请创建第一个产品。</div>
      )}

      <div className="list-col">
        {products.map((p) => (
          <div
            key={p.id}
            className="card flex-center gap-16"
            style={{ cursor: "pointer" }}
            onClick={() => navigate(`/products/${p.id}`)}
          >
            <div className="flex-1">
              <div className="text-bold">
                {p.name}
                {p.code && (
                  <span className="text-caption text-muted" style={{ marginLeft: 8 }}>
                    [{p.code}]
                  </span>
                )}
              </div>
              {p.description && (
                <div className="text-caption text-muted mt-4">{p.description}</div>
              )}
            </div>
            <span className="agent-context-badge" style={{ fontSize: 11 }}>{p.status}</span>
            <button
              type="button"
              className="secondary sm"
              onClick={(e) => {
                e.stopPropagation();
                handleDelete(p.id);
              }}
            >
              删除
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
