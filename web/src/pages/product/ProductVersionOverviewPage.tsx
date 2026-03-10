import { useEffect, useState } from "react";
import { useVersionPageContext } from "./ProductVersionWorkspacePage";
import {
  updateProductVersion,
  listVersionBranches,
  listProductProjects,
  listProjectBranches,
  setVersionBranch,
  listProductRequirements,
  listProductBugs,
  type VersionBranch,
  type Project,
} from "../../api/client";

const STATUS_OPTIONS = ["planning", "developing", "testing", "released"];
const STATUS_LABELS: Record<string, string> = {
  planning: "规划中",
  developing: "开发中",
  testing: "测试中",
  released: "已发布",
};

export function ProductVersionOverviewPage() {
  const { productId, versionId, version, reloadVersion } = useVersionPageContext();

  const [branches, setBranches] = useState<VersionBranch[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [reqCount, setReqCount] = useState(0);
  const [bugCount, setBugCount] = useState(0);

  // 分支设置表单
  const [branchForm, setBranchForm] = useState({ projectId: 0, branch: "" });
  const [projectBranches, setProjectBranches] = useState<string[]>([]);

  const load = async () => {
    try {
      const [brs, projs, reqs, bugs] = await Promise.all([
        listVersionBranches(productId, versionId),
        listProductProjects(productId),
        listProductRequirements(productId, { version_id: versionId }),
        listProductBugs(productId, { version_id: versionId }),
      ]);
      setBranches(brs);
      setProjects(projs);
      setReqCount(reqs.length);
      setBugCount(bugs.length);
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
    }
  };

  useEffect(() => {
    load();
  }, [productId, versionId]);

  // 选择项目后加载分支列表
  useEffect(() => {
    if (branchForm.projectId) {
      listProjectBranches(branchForm.projectId)
        .then(setProjectBranches)
        .catch(() => setProjectBranches([]));
    }
  }, [branchForm.projectId]);

  const handleStatusChange = async (status: string) => {
    try {
      await updateProductVersion(productId, versionId, { status });
      reloadVersion();
    } catch (e) {
      setError(e instanceof Error ? e.message : "更新失败");
    }
  };

  const handleSetBranch = async () => {
    if (!branchForm.projectId || !branchForm.branch) return;
    try {
      await setVersionBranch(productId, versionId, branchForm.projectId, branchForm.branch);
      setBranchForm({ projectId: 0, branch: "" });
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "设置分支失败");
    }
  };

  const mappedProjectIds = new Set(branches.map((b) => b.project_id));
  const unmappedProjects = projects.filter((p) => !mappedProjectIds.has(p.id));

  return (
    <div data-testid="page-version-overview">
      <div className="flex-center gap-16 mb-24">
        <span>状态:</span>
        <select
          className="input-select"
          value={version.status}
          onChange={(e) => handleStatusChange(e.target.value)}
        >
          {STATUS_OPTIONS.map((s) => (
            <option key={s} value={s}>{STATUS_LABELS[s]}</option>
          ))}
        </select>
      </div>

      {error && <div className="result error">{error}</div>}

      <div className="stats mb-16">
        <div className="stat">需求数: {reqCount}</div>
        <div className="stat">Bug 数: {bugCount}</div>
      </div>

      <div className="card mb-16">
        <h3>项目分支映射</h3>
        {branches.length === 0 ? (
          <div className="text-muted">暂无分支映射</div>
        ) : (
          <div className="list-col">
            {branches.map((b) => (
              <div key={b.id} className="flex-center gap-12">
                <span className="text-bold">{b.project_name ?? `项目#${b.project_id}`}</span>
                <span style={{ color: "var(--color-primary)" }}>{b.branch}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {unmappedProjects.length > 0 && (
        <div className="card">
          <h3>设置分支</h3>
          <div className="flex gap-12 flex-wrap" style={{ alignItems: "flex-end" }}>
            <div className="form-row" style={{ marginBottom: 0 }}>
              <label>项目</label>
              <select
                className="input-select"
                value={branchForm.projectId || ""}
                onChange={(e) => setBranchForm({ ...branchForm, projectId: Number(e.target.value), branch: "" })}
              >
                <option value="">选择项目</option>
                {unmappedProjects.map((p) => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
            </div>
            <div className="form-row" style={{ marginBottom: 0 }}>
              <label>分支</label>
              {projectBranches.length > 0 ? (
                <select
                  className="input-select"
                  value={branchForm.branch}
                  onChange={(e) => setBranchForm({ ...branchForm, branch: e.target.value })}
                >
                  <option value="">选择分支</option>
                  {projectBranches.map((b) => (
                    <option key={b} value={b}>{b}</option>
                  ))}
                </select>
              ) : (
                <input
                  value={branchForm.branch}
                  onChange={(e) => setBranchForm({ ...branchForm, branch: e.target.value })}
                  placeholder="分支名称"
                />
              )}
            </div>
            <button
              type="button"
              className="primary"
              onClick={handleSetBranch}
              disabled={!branchForm.projectId || !branchForm.branch}
            >
              设置
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
