import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import {
  listProjects,
  createProject,
  updateProject,
  deleteProject,
  type Project,
} from "../api/client";

export function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<Project | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [formName, setFormName] = useState("");
  const [formRepoPath, setFormRepoPath] = useState("");
  const [formWatchEnabled, setFormWatchEnabled] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [deleteConfirmId, setDeleteConfirmId] = useState<number | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const list = await listProjects();
      setProjects(list);
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const openCreate = () => {
    setEditing(null);
    setFormName("");
    setFormRepoPath("");
    setFormWatchEnabled(false);
    setFormOpen(true);
  };

  const openEdit = (p: Project) => {
    setEditing(p);
    setFormName(p.name);
    setFormRepoPath(p.repo_path);
    setFormWatchEnabled(p.watch_enabled ?? false);
    setFormOpen(true);
  };

  const closeForm = () => {
    setFormOpen(false);
    setEditing(null);
  };

  const submitForm = async () => {
    if (!formName.trim()) return;
    setSubmitting(true);
    try {
      if (editing) {
        await updateProject(editing.id, {
          name: formName.trim(),
          repo_path: formRepoPath.trim() || "",
          watch_enabled: formWatchEnabled,
        });
      } else {
        await createProject({
          name: formName.trim(),
          repo_path: formRepoPath.trim() || "",
          watch_enabled: formWatchEnabled,
        });
      }
      closeForm();
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "保存失败");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await deleteProject(id);
      setDeleteConfirmId(null);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "删除失败");
    }
  };

  if (loading) return <div data-testid="projects-loading">加载中...</div>;
  if (error) return <div data-testid="projects-error" className="result error">{error}</div>;

  return (
    <div data-testid="page-projects">
      <h2>项目管理</h2>
      <button type="button" onClick={openCreate} data-testid="projects-new-btn">
        新建项目
      </button>
      {projects.length === 0 ? (
        <p data-testid="projects-empty">暂无项目</p>
      ) : (
        <ul data-testid="projects-list">
          {projects.map((p) => (
            <li key={p.id} data-testid={`project-${p.id}`}>
              <span>{p.name}</span>
              {p.repo_path ? <span className="hint"> {p.repo_path}</span> : null}
              <Link to={`/projects/${p.id}`} data-testid={`project-versions-${p.id}`}>进入项目</Link>
              <button type="button" className="secondary" onClick={() => openEdit(p)} data-testid={`project-edit-${p.id}`}>
                编辑
              </button>
              {deleteConfirmId === p.id ? (
                <>
                  <span>确认删除？</span>
                  <button type="button" onClick={() => handleDelete(p.id)} data-testid={`project-delete-confirm-${p.id}`}>
                    确认
                  </button>
                  <button type="button" className="secondary" onClick={() => setDeleteConfirmId(null)}>
                    取消
                  </button>
                </>
              ) : (
                <button type="button" className="secondary" onClick={() => setDeleteConfirmId(p.id)} data-testid={`project-delete-${p.id}`}>
                  删除
                </button>
              )}
            </li>
          ))}
        </ul>
      )}

      {formOpen && (
        <div className="card" data-testid="project-form">
          <h3>{editing ? "编辑项目" : "新建项目"}</h3>
          <div className="form-row">
            <label htmlFor="project-name">名称</label>
            <input
              id="project-name"
              value={formName}
              onChange={(e) => setFormName(e.target.value)}
              placeholder="项目名称"
            />
          </div>
          <div className="form-row">
            <label htmlFor="project-repo">仓库路径</label>
            <input
              id="project-repo"
              value={formRepoPath}
              onChange={(e) => setFormRepoPath(e.target.value)}
              placeholder=""
            />
          </div>
          <div className="form-row">
            <label>
              <input
                type="checkbox"
                checked={formWatchEnabled}
                onChange={(e) => setFormWatchEnabled(e.target.checked)}
              />
              启用监听
            </label>
          </div>
          <button type="button" onClick={submitForm} disabled={submitting || !formName.trim()} data-testid="project-form-submit">
            {submitting ? "保存中..." : "保存"}
          </button>
          <button type="button" className="secondary" onClick={closeForm}>
            取消
          </button>
        </div>
      )}
    </div>
  );
}
