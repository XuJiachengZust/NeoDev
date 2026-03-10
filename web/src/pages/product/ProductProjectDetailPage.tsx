import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useProductPageContext } from "./ProductLayoutPage";
import {
  getProject,
  updateProject,
  listProjectBranches,
  listProductVersions,
  listVersionBranches,
  listVersions,
  listCommitsByVersion,
  syncCommitsForVersion,
  getPreprocessStatus,
  postPreprocess,
  type Project,
  type ProductVersion,
  type Version,
  type Commit,
  type PreprocessStatusItem,
} from "../../api/client";
import { FlowButton } from "../../components/FlowButton";

function isRepoUrl(path: string): boolean {
  const p = (path || "").trim();
  return p.startsWith("http://") || p.startsWith("https://") || p.startsWith("git@");
}

export function ProductProjectDetailPage() {
  const { productId, product } = useProductPageContext();
  const { projectId: pid } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const projectId = pid ? Number(pid) : NaN;

  const [project, setProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // 版本选择器
  const [productVersions, setProductVersions] = useState<ProductVersion[]>([]);
  const [selectedVersionId, setSelectedVersionId] = useState<number | null>(null);
  const [currentBranch, setCurrentBranch] = useState<string | null>(null);

  // 仓库配置
  const [repoPathInput, setRepoPathInput] = useState("");
  const [repoUsername, setRepoUsername] = useState("");
  const [repoPassword, setRepoPassword] = useState("");
  const [savingRepo, setSavingRepo] = useState(false);
  const [scanning, setScanning] = useState(false);

  // 同步&AI 分析
  const [syncing, setSyncing] = useState(false);
  const [preprocessStatus, setPreprocessStatus] = useState<PreprocessStatusItem | null>(null);
  const [preprocessLoading, setPreprocessLoading] = useState(false);

  // 提交列表
  const [commits, setCommits] = useState<Commit[]>([]);
  const [commitsLoading, setCommitsLoading] = useState(false);

  // 项目的内部 version（对应分支）
  const [projectVersion, setProjectVersion] = useState<Version | null>(null);

  const loadProject = useCallback(async () => {
    if (!Number.isFinite(projectId)) return;
    setLoading(true);
    setError(null);
    try {
      const [proj, pVersions] = await Promise.all([
        getProject(projectId),
        listProductVersions(productId),
      ]);
      setProject(proj);
      setRepoPathInput(proj.repo_path || "");
      setRepoUsername(proj.repo_username ?? "");
      setProductVersions(pVersions);

      // 默认选择第一个 developing 版本，或第一个版本
      if (pVersions.length > 0 && selectedVersionId == null) {
        const dev = pVersions.find((v) => v.status === "developing") || pVersions[0];
        setSelectedVersionId(dev.id);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载项目失败");
    } finally {
      setLoading(false);
    }
  }, [projectId, productId]);

  useEffect(() => {
    loadProject();
  }, [loadProject]);

  // 加载版本-分支映射 & 确定当前项目的分支
  useEffect(() => {
    if (!selectedVersionId || !Number.isFinite(projectId)) return;
    let cancelled = false;

    (async () => {
      try {
        const branches = await listVersionBranches(productId, selectedVersionId);
        if (cancelled) return;
        const match = branches.find((b) => b.project_id === projectId);
        setCurrentBranch(match?.branch ?? null);

        // 查找项目内部 version 对应这个分支
        if (match?.branch) {
          const projectVersions = await listVersions(projectId);
          const pv = projectVersions.find((v) => v.branch === match.branch);
          setProjectVersion(pv ?? null);

          if (pv) {
            // 加载提交
            setCommitsLoading(true);
            const [cmts, preprocessResp] = await Promise.all([
              listCommitsByVersion(projectId, pv.id),
              getPreprocessStatus(projectId, match.branch).catch(() => null),
            ]);
            if (!cancelled) {
              setCommits(cmts);
              if (preprocessResp && "status" in preprocessResp) {
                setPreprocessStatus(preprocessResp as PreprocessStatusItem);
              } else if (preprocessResp && "items" in preprocessResp) {
                const items = (preprocessResp as { items: PreprocessStatusItem[] }).items;
                setPreprocessStatus(items.find((i) => i.branch === match.branch) ?? null);
              }
              setCommitsLoading(false);
            }
          } else {
            setCommits([]);
            setPreprocessStatus(null);
          }
        } else {
          setProjectVersion(null);
          setCommits([]);
          setPreprocessStatus(null);
        }
      } catch {
        if (!cancelled) {
          setCurrentBranch(null);
          setProjectVersion(null);
          setCommits([]);
        }
      }
    })();

    return () => { cancelled = true; };
  }, [productId, projectId, selectedVersionId]);

  const handleSaveRepo = async () => {
    setSavingRepo(true);
    setError(null);
    setSuccess(null);
    try {
      const payload: Parameters<typeof updateProject>[1] = { repo_path: repoPathInput.trim() };
      if (isRepoUrl(repoPathInput)) {
        payload.repo_username = repoUsername.trim() || null;
        payload.repo_password = repoPassword || null;
      }
      await updateProject(projectId, payload);
      await loadProject();
      setSuccess("仓库配置已保存");
    } catch (e) {
      setError(e instanceof Error ? e.message : "保存仓库配置失败");
    } finally {
      setSavingRepo(false);
    }
  };

  const handleScanRepo = async () => {
    if (!repoPathInput.trim()) return;
    setScanning(true);
    setError(null);
    setSuccess(null);
    try {
      const payload: Parameters<typeof updateProject>[1] = { repo_path: repoPathInput.trim() };
      if (isRepoUrl(repoPathInput)) {
        payload.repo_username = repoUsername.trim() || null;
        payload.repo_password = repoPassword || null;
      }
      await updateProject(projectId, payload);
      // 拉取代码（远程自动 clone）并提取分支，持久化到 git_branches 表
      const branches = await listProjectBranches(projectId);
      await loadProject();
      setSuccess(`扫描完成，识别 ${branches.length} 个分支`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "扫描仓库失败");
    } finally {
      setScanning(false);
    }
  };

  const handleSync = async () => {
    if (!projectVersion) return;
    setSyncing(true);
    setError(null);
    try {
      await syncCommitsForVersion(projectId, projectVersion.id);
      // 刷新提交列表
      const cmts = await listCommitsByVersion(projectId, projectVersion.id);
      setCommits(cmts);
      setSuccess("同步完成");
    } catch (e) {
      setError(e instanceof Error ? e.message : "同步提交失败");
    } finally {
      setSyncing(false);
    }
  };

  const handlePreprocess = async () => {
    if (!currentBranch) return;
    setPreprocessLoading(true);
    setError(null);
    try {
      await postPreprocess(projectId, currentBranch, false);
      setSuccess("AI 分析已触发");
    } catch (e) {
      setError(e instanceof Error ? e.message : "触发 AI 分析失败");
    } finally {
      setPreprocessLoading(false);
    }
  };

  if (!Number.isFinite(projectId)) return <div className="result error">无效项目</div>;
  if (loading) return <div className="loading-state">加载中...</div>;
  if (!project) return <div className="result error">{error ?? "项目不存在"}</div>;

  return (
    <div data-testid="page-product-project-detail">
      {/* 面包屑 */}
      <div className="flex-center gap-8 mb-16">
        <button type="button" className="secondary" onClick={() => navigate(`/products/${productId}/projects`)}>
          {product.name}
        </button>
        <span className="text-muted">&gt;</span>
        <span className="text-bold">{project.name}</span>
      </div>

      {/* 版本选择器 */}
      {productVersions.length > 0 && (
        <div className="card mb-16">
          <div className="flex-center gap-12">
            <label className="text-bold">产品版本:</label>
            <select
              className="input-select"
              value={selectedVersionId ?? ""}
              onChange={(e) => setSelectedVersionId(e.target.value ? Number(e.target.value) : null)}
              style={{ minWidth: "10rem" }}
            >
              {productVersions.map((v) => (
                <option key={v.id} value={v.id}>{v.version_name}</option>
              ))}
            </select>
            {currentBranch ? (
              <span className="text-caption" style={{ color: "var(--color-primary)" }}>
                分支: {currentBranch}
              </span>
            ) : (
              <span className="text-caption text-muted">此版本未映射分支到本项目</span>
            )}
          </div>
        </div>
      )}

      {error && <div className="result error mb-16">{error}</div>}
      {success && <div className="result mb-16">{success}</div>}

      {/* 仓库配置 */}
      <div className="card mb-16">
        <h3>仓库配置</h3>
        <div className="form-row">
          <label>仓库 URL 或本地路径</label>
          <input
            className="glow-input"
            value={repoPathInput}
            onChange={(e) => setRepoPathInput(e.target.value)}
            placeholder="http://gitlab.example.com/group/repo.git 或 D:/repo"
          />
        </div>
        {isRepoUrl(repoPathInput) && (
          <>
            <div className="form-row">
              <label>Git 用户名（可选）</label>
              <input
                className="glow-input"
                type="text"
                value={repoUsername}
                onChange={(e) => setRepoUsername(e.target.value)}
                placeholder="用户名"
                autoComplete="username"
              />
            </div>
            <div className="form-row">
              <label>密码 / Token（可选）</label>
              <input
                className="glow-input"
                type="password"
                value={repoPassword}
                onChange={(e) => setRepoPassword(e.target.value)}
                placeholder="密码或 Token"
                autoComplete="current-password"
              />
            </div>
          </>
        )}
        <div style={{ display: "flex", gap: 12 }}>
          <button type="button" className="secondary" onClick={handleSaveRepo} disabled={savingRepo}>
            {savingRepo ? "保存中..." : "保存仓库配置"}
          </button>
          <FlowButton onClick={handleScanRepo} loading={scanning} disabled={!repoPathInput.trim()}>
            扫描分支
          </FlowButton>
        </div>
      </div>

      {/* 同步 & AI 分析（需要版本分支映射） */}
      {currentBranch && projectVersion && (
        <div className="card mb-16">
          <h3>版本同步 &amp; AI 分析</h3>
          <div className="flex-center gap-12 flex-wrap">
            <button type="button" className="secondary" onClick={handleSync} disabled={syncing}>
              {syncing ? "同步中..." : "同步提交"}
            </button>
            <button
              type="button"
              className="secondary"
              onClick={handlePreprocess}
              disabled={preprocessLoading || preprocessStatus?.status === "running"}
            >
              {preprocessLoading || preprocessStatus?.status === "running" ? "分析中..." : "AI 分析"}
            </button>
            {preprocessStatus && (
              <span className="text-caption text-muted">
                AI 分析状态: {preprocessStatus.status}
              </span>
            )}
          </div>
        </div>
      )}

      {/* 提交列表 */}
      {currentBranch && projectVersion && (
        <div className="card">
          <h3>提交列表（{currentBranch}）</h3>
          {commitsLoading ? (
            <div className="loading-state">加载中...</div>
          ) : commits.length === 0 ? (
            <div className="text-muted">暂无提交，请先同步</div>
          ) : (
            <ul style={{ listStyle: "none", padding: 0, margin: 0, maxHeight: 400, overflowY: "auto" }}>
              {commits.map((c) => (
                <li key={c.id} style={{ marginBottom: 8, display: "flex", alignItems: "center", gap: 8 }}>
                  <span className="mono" style={{ minWidth: 60 }}>{c.commit_sha.slice(0, 7)}</span>
                  <span className="flex-1">{c.message ?? ""}</span>
                  {c.author && <span className="text-caption text-muted">{c.author}</span>}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
