import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useProductPageContext } from "./ProductLayoutPage";
import {
  listProductProjects,
  createProjectInProduct,
  deleteProject,
  type Project,
} from "../../api/client";

export function ProductProjectsPage() {
  const { productId } = useProductPageContext();
  const navigate = useNavigate();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ name: "", repo_path: "", repo_username: "", repo_password: "" });

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      setProjects(await listProductProjects(productId));
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
    if (!form.name.trim() || !form.repo_path.trim()) return;
    try {
      await createProjectInProduct(productId, {
        name: form.name.trim(),
        repo_path: form.repo_path.trim(),
        repo_username: form.repo_username.trim() || undefined,
        repo_password: form.repo_password.trim() || undefined,
      });
      setForm({ name: "", repo_path: "", repo_username: "", repo_password: "" });
      setShowCreate(false);
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "创建失败");
    }
  };

  const handleDelete = async (projectId: number) => {
    if (!confirm("确定删除该项目？")) return;
    try {
      await deleteProject(projectId);
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "删除失败");
    }
  };

  if (loading) return <div className="loading-state">加载中...</div>;

  return (
    <div data-testid="page-product-projects">
      <div className="page-toolbar">
        <h3>项目管理</h3>
        <button type="button" className="primary" onClick={() => setShowCreate(!showCreate)}>
          {showCreate ? "取消" : "创建项目"}
        </button>
      </div>

      {error && <div className="result error">{error}</div>}

      {showCreate && (
        <div className="card mb-16">
          <h3>创建项目</h3>
          <div className="form-row">
            <label>项目名称 *</label>
            <input
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="如：my-service"
            />
          </div>
          <div className="form-row">
            <label>仓库地址 *</label>
            <input
              value={form.repo_path}
              onChange={(e) => setForm({ ...form, repo_path: e.target.value })}
              placeholder="Git 仓库 URL 或本地路径"
            />
          </div>
          <div className="form-row">
            <label>用户名（可选）</label>
            <input
              value={form.repo_username}
              onChange={(e) => setForm({ ...form, repo_username: e.target.value })}
              placeholder="仓库认证用户名"
            />
          </div>
          <div className="form-row">
            <label>Token / 密码（可选）</label>
            <input
              type="password"
              value={form.repo_password}
              onChange={(e) => setForm({ ...form, repo_password: e.target.value })}
              placeholder="仓库认证 Token"
            />
          </div>
          <button
            type="button"
            className="primary"
            onClick={handleCreate}
            disabled={!form.name.trim() || !form.repo_path.trim()}
          >
            创建
          </button>
        </div>
      )}

      {projects.length === 0 ? (
        <div className="empty-state">暂无项目，请创建第一个项目</div>
      ) : (
        <div className="list-col">
          {projects.map((p) => (
            <div
              key={p.id}
              className="card flex-center gap-16"
              style={{ cursor: "pointer" }}
              onClick={() => navigate(`${p.id}`)}
            >
              <div className="flex-1">
                <div className="text-bold">{p.name}</div>
                <div className="text-caption text-muted">{p.repo_path}</div>
              </div>
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
      )}
    </div>
  );
}
