import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useVersionPageContext } from "./ProductVersionWorkspacePage";
import {
  updateProductVersion,
  listVersionBranches,
  listProductProjects,
  listProjectBranches,
  setVersionBranch,
  listProductRequirements,
  listProductBugs,
  getPreprocessStatus,
  type VersionBranch,
  type Project,
  type PreprocessStatusItem,
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
  const navigate = useNavigate();

  const [branches, setBranches] = useState<VersionBranch[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [reqCount, setReqCount] = useState(0);
  const [bugCount, setBugCount] = useState(0);

  // 分支 AI 分析状态: key = "projectId:branch"
  const [branchAiStatus, setBranchAiStatus] = useState<Record<string, PreprocessStatusItem>>({});

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

      // 加载每个分支的 AI 分析状态
      const statusMap: Record<string, PreprocessStatusItem> = {};
      await Promise.all(
        brs.map(async (b) => {
          try {
            const resp = await getPreprocessStatus(b.project_id, b.branch);
            if (resp && "status" in resp) {
              statusMap[`${b.project_id}:${b.branch}`] = resp as PreprocessStatusItem;
            }
          } catch {
            // 没有预处理记录，忽略
          }
        })
      );
      setBranchAiStatus(statusMap);
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
            {branches.map((b) => {
              const aiStatus = branchAiStatus[`${b.project_id}:${b.branch}`];
              return (
                <div
                  key={b.id}
                  className="flex-center gap-12"
                  style={{
                    cursor: "pointer",
                    padding: "6px 8px",
                    borderRadius: 4,
                    transition: "background 0.15s",
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(0, 240, 255, 0.08)")}
                  onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                  onClick={() => navigate(`/products/${productId}/projects/${b.project_id}?versionId=${versionId}`)}
                >
                  <span className="text-bold">{b.project_name ?? `项目#${b.project_id}`}</span>
                  <span style={{ color: "var(--color-primary)" }}>{b.branch}</span>
                  <AiStatusBadge status={aiStatus} />
                  <span className="flex-1" />
                  <span className="text-muted">→</span>
                </div>
              );
            })}
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

const AI_STATUS_STYLES: Record<string, { bg: string; color: string; label: string }> = {
  pending: { bg: "rgba(255, 200, 0, 0.12)", color: "#ffc800", label: "AI 待分析" },
  running: { bg: "rgba(0, 240, 255, 0.12)", color: "var(--color-primary)", label: "AI 分析中" },
  completed: { bg: "rgba(0, 255, 128, 0.12)", color: "#00ff80", label: "AI 已完成" },
  failed: { bg: "rgba(255, 0, 85, 0.12)", color: "var(--color-alert)", label: "AI 失败" },
};

function AiStatusBadge({ status }: { status?: PreprocessStatusItem }) {
  if (!status) {
    return (
      <span
        style={{
          fontSize: 11,
          padding: "1px 6px",
          borderRadius: "var(--radius-pill)",
          background: "rgba(74, 74, 85, 0.3)",
          color: "var(--color-text-muted)",
        }}
      >
        未分析
      </span>
    );
  }
  const s = AI_STATUS_STYLES[status.status] ?? AI_STATUS_STYLES.pending;
  return (
    <span
      style={{
        fontSize: 11,
        padding: "1px 6px",
        borderRadius: "var(--radius-pill)",
        background: s.bg,
        color: s.color,
        ...(status.status === "running" ? { animation: "pulse 1s ease-in-out infinite" } : {}),
      }}
      title={status.error_message || undefined}
    >
      {s.label}
    </span>
  );
}
