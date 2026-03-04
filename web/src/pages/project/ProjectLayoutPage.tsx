import { useEffect, useState } from "react";
import { NavLink, Outlet, useNavigate, useOutletContext, useParams } from "react-router-dom";
import { getProject, type Project } from "../../api/client";

export interface ProjectPageContext {
  projectId: number;
  project: Project;
  reloadProject: () => Promise<void>;
}

export function useProjectPageContext(): ProjectPageContext {
  return useOutletContext<ProjectPageContext>();
}

export function ProjectLayoutPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const projectId = id ? Number(id) : NaN;
  const [project, setProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadProject = async () => {
    if (!Number.isFinite(projectId)) return;
    setLoading(true);
    setError(null);
    try {
      const row = await getProject(projectId);
      setProject(row);
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载项目失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProject();
  }, [projectId]);

  if (!Number.isFinite(projectId)) return <div className="result error">无效项目</div>;
  if (loading) return <div data-testid="project-layout-loading">加载中...</div>;
  if (error || !project) return <div className="result error">{error ?? "项目不存在"}</div>;

  return (
    <div data-testid="page-project-layout">
      <button type="button" className="secondary" onClick={() => navigate("/projects")}>
        返回列表
      </button>
      <h2 className="page-title" style={{ fontSize: "var(--text-h2)", marginTop: 16 }}>
        {project.name}
      </h2>

      <nav role="tablist" className="cockpit-tabs" style={{ marginBottom: 16 }}>
        <NavLink to="repo" className={({ isActive }) => `cockpit-tab ${isActive ? "active" : ""}`} role="tab">
          仓库配置
        </NavLink>
        <NavLink to="versions" className={({ isActive }) => `cockpit-tab ${isActive ? "active" : ""}`} role="tab">
          版本
        </NavLink>
      </nav>

      <Outlet context={{ projectId, project, reloadProject: loadProject }} />
    </div>
  );
}
