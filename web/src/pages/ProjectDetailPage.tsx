import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  getProject,
  updateProject,
  listVersions,
  createVersion,
  deleteVersion,
  getWatchStatus,
  syncCommits,
  syncCommitsForVersion,
  listProjectBranches,
  listCommitsByVersion,
  listRequirements,
  createRequirement,
  createImpactAnalysis,
  bindRequirementCommits,
  type Project,
  type Version,
  type WatchStatus,
  type Commit,
  type Requirement,
} from "../api/client";
import { FlowButton } from "../components/FlowButton";

function isRepoUrl(path: string): boolean {
  const p = (path || "").trim();
  return p.startsWith("http://") || p.startsWith("https://") || p.startsWith("git@");
}

export function ProjectDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const projectId = id ? parseInt(id, 10) : NaN;
  const [project, setProject] = useState<Project | null>(null);
  const [versions, setVersions] = useState<Version[]>([]);
  const [watchStatus, setWatchStatus] = useState<WatchStatus | null>(null);
  const [repoPathInput, setRepoPathInput] = useState("");
  const [repoUsername, setRepoUsername] = useState("");
  const [repoPassword, setRepoPassword] = useState("");
  const [savingRepo, setSavingRepo] = useState(false);
  const [selectedVersionId, setSelectedVersionId] = useState<number | null>(null);
  const [commits, setCommits] = useState<Commit[]>([]);
  const [requirements, setRequirements] = useState<Requirement[]>([]);
  const [selectedCommitIds, setSelectedCommitIds] = useState<number[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [formVersionName, setFormVersionName] = useState("");
  const [formBranch, setFormBranch] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const versionDisplayName = (v: Version) =>
    v.version_name?.trim() || v.branch?.trim() || `版本 #${v.id}`;
  const [scanning, setScanning] = useState(false);
  const [deleteConfirmId, setDeleteConfirmId] = useState<number | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [syncingVersionId, setSyncingVersionId] = useState<number | null>(null);
  const [impactLoading, setImpactLoading] = useState(false);
  const [bindReqId, setBindReqId] = useState<number | null>(null);
  const [bindLoading, setBindLoading] = useState(false);
  const [newReqTitle, setNewReqTitle] = useState("");
  const [createReqLoading, setCreateReqLoading] = useState(false);

  const load = async () => {
    if (!Number.isFinite(projectId)) return;
    setLoading(true);
    setError(null);
    try {
      const [proj, vList, status] = await Promise.all([
        getProject(projectId),
        listVersions(projectId),
        getWatchStatus(projectId),
      ]);
      setProject(proj);
      setRepoPathInput(proj.repo_path || "");
      setVersions(vList);
      setWatchStatus(status);
      setSelectedVersionId((prev) => (vList.length > 0 && !prev ? vList[0].id : prev));
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [projectId]);

  useEffect(() => {
    if (!Number.isFinite(projectId) || !selectedVersionId) {
      setCommits([]);
      return;
    }
    let cancelled = false;
    listCommitsByVersion(projectId, selectedVersionId).then((list) => {
      if (!cancelled) setCommits(list);
    }).catch(() => {
      if (!cancelled) setCommits([]);
    });
    return () => { cancelled = true; };
  }, [projectId, selectedVersionId]);

  useEffect(() => {
    setSelectedCommitIds([]);
    setBindReqId(null);
  }, [selectedVersionId]);

  useEffect(() => {
    if (!Number.isFinite(projectId)) {
      setRequirements([]);
      return;
    }
    let cancelled = false;
    listRequirements(projectId).then((list) => {
      if (!cancelled) setRequirements(list);
    }).catch(() => {
      if (!cancelled) setRequirements([]);
    });
    return () => { cancelled = true; };
  }, [projectId]);

  const handleSaveRepo = async () => {
    if (!Number.isFinite(projectId) || !project) return;
    setSavingRepo(true);
    setError(null);
    try {
      const updated = await updateProject(projectId, { repo_path: repoPathInput.trim() });
      setProject(updated);
      setRepoPathInput(updated.repo_path || "");
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
    try {
      const payload: Parameters<typeof updateProject>[1] = {
        repo_path: repoPathInput.trim(),
      };
      if (isRepoUrl(repoPathInput)) {
        payload.repo_username = repoUsername.trim() || null;
        payload.repo_password = repoPassword || null;
      }
      await updateProject(projectId, payload);

      const branches = await listProjectBranches(projectId);
      const existing = new Set(versions.map((v) => v.branch).filter((b): b is string => !!b));
      for (const branch of branches) {
        if (existing.has(branch)) continue;
        await createVersion(projectId, { branch, version_name: null });
        existing.add(branch);
      }
      await load();
      const vList = await listVersions(projectId);
      if (vList.length > 0) setSelectedVersionId(vList[0].id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "扫描仓库失败");
    } finally {
      setScanning(false);
    }
  };

  const handleCreateVersion = async () => {
    const versionName = formVersionName.trim() || null;
    const branch = formBranch.trim() || null;
    if ((!versionName && !branch) || !Number.isFinite(projectId)) return;
    setSubmitting(true);
    try {
      await createVersion(projectId, {
        version_name: versionName,
        branch,
      });
      setFormVersionName("");
      setFormBranch("");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "创建失败");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteVersion = async (versionId: number) => {
    if (!Number.isFinite(projectId)) return;
    try {
      await deleteVersion(projectId, versionId);
      setDeleteConfirmId(null);
      if (selectedVersionId === versionId) setSelectedVersionId(versions.find((v) => v.id !== versionId)?.id ?? null);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "删除失败");
    }
  };

  const handleSync = async () => {
    if (!Number.isFinite(projectId)) return;
    setSyncing(true);
    try {
      await syncCommits(projectId);
      await load();
      if (selectedVersionId) {
        const list = await listCommitsByVersion(projectId, selectedVersionId);
        setCommits(list);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "同步失败");
    } finally {
      setSyncing(false);
    }
  };

  const handleSyncVersion = async (versionId: number) => {
    if (!Number.isFinite(projectId)) return;
    setSyncingVersionId(versionId);
    setError(null);
    try {
      await syncCommitsForVersion(projectId, versionId);
      await load();
      if (selectedVersionId === versionId) {
        const list = await listCommitsByVersion(projectId, selectedVersionId);
        setCommits(list);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "同步失败");
    } finally {
      setSyncingVersionId(null);
    }
  };

  const toggleCommit = (commitId: number) => {
    setSelectedCommitIds((prev) =>
      prev.includes(commitId) ? prev.filter((id) => id !== commitId) : [...prev, commitId]
    );
  };

  const handleImpactAnalysis = async () => {
    if (!Number.isFinite(projectId) || selectedCommitIds.length === 0) return;
    setImpactLoading(true);
    setError(null);
    try {
      await createImpactAnalysis(projectId, { commit_ids: selectedCommitIds });
      setSelectedCommitIds([]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "触发影响面分析失败");
    } finally {
      setImpactLoading(false);
    }
  };

  const handleCreateRequirement = async () => {
    if (!Number.isFinite(projectId) || !selectedVersionId || !newReqTitle.trim()) return;
    setCreateReqLoading(true);
    setError(null);
    try {
      await createRequirement(projectId, {
        title: newReqTitle.trim(),
        external_id: `version:${selectedVersionId}`,
      });
      setNewReqTitle("");
      const list = await listRequirements(projectId);
      setRequirements(list);
    } catch (e) {
      setError(e instanceof Error ? e.message : "创建需求失败");
    } finally {
      setCreateReqLoading(false);
    }
  };

  const handleBindRequirement = async (requirementId: number) => {
    if (!Number.isFinite(projectId) || selectedCommitIds.length === 0) return;
    setBindLoading(true);
    setError(null);
    try {
      await bindRequirementCommits(projectId, requirementId, selectedCommitIds);
      setBindReqId(null);
      setSelectedCommitIds([]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "绑定需求失败");
    } finally {
      setBindLoading(false);
    }
  };

  if (!Number.isFinite(projectId)) {
    return <div data-testid="project-detail-invalid">无效项目</div>;
  }
  if (loading) return <div data-testid="project-detail-loading">加载中...</div>;
  if (error && !project) return <div className="result error" data-testid="project-detail-error">{error}</div>;
  if (!project) return null;

  const versionKey = selectedVersionId ? `version:${selectedVersionId}` : "";
  const versionRequirements = requirements.filter((r) => r.external_id === versionKey);

  return (
    <div data-testid="page-project-detail">
      <button type="button" className="secondary" onClick={() => navigate("/projects")} data-testid="project-detail-back">
        返回列表
      </button>
      <h2 className="page-title" style={{ fontSize: "var(--text-h2)" }}>{project.name}</h2>

      {error && <div className="result error" data-testid="project-detail-error-msg">{error}</div>}

      <div className="card" style={{ marginTop: 24 }}>
        <h3>仓库配置</h3>
        <div className="form-row">
          <label htmlFor="project-repo-config">仓库 URL 或本地路径</label>
          <input
            id="project-repo-config"
            className="glow-input"
            value={repoPathInput}
            onChange={(e) => setRepoPathInput(e.target.value)}
            placeholder="https://gitlab.example.com/group/repo.git 或 /path/to/repo"
          />
        </div>
        {isRepoUrl(repoPathInput) && (
          <>
            <div className="form-row">
              <label htmlFor="project-repo-username">Git 用户名（可选，私有仓库必填）</label>
              <input
                id="project-repo-username"
                className="glow-input"
                type="text"
                value={repoUsername}
                onChange={(e) => setRepoUsername(e.target.value)}
                placeholder="GitLab 用户名或 Access Token 用户名"
                autoComplete="username"
              />
            </div>
            <div className="form-row">
              <label htmlFor="project-repo-password">密码 / Token（可选）</label>
              <input
                id="project-repo-password"
                className="glow-input"
                type="password"
                value={repoPassword}
                onChange={(e) => setRepoPassword(e.target.value)}
                placeholder="密码或 Personal Access Token"
                autoComplete="current-password"
              />
            </div>
          </>
        )}
        <button
          type="button"
          className="secondary"
          onClick={handleSaveRepo}
          disabled={savingRepo}
          data-testid="project-detail-save-repo"
        >
          {savingRepo ? "保存中..." : "保存仓库配置"}
        </button>
      </div>

      <div className="card" style={{ marginTop: 24 }}>
        <h3>版本</h3>
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 16 }}>
          <FlowButton
            onClick={handleScanRepo}
            loading={scanning}
            disabled={!repoPathInput.trim()}
            data-testid="project-detail-scan"
          >
            扫描仓库
          </FlowButton>
          <button type="button" onClick={handleSync} disabled={syncing || versions.length === 0} className="secondary" data-testid="project-detail-sync">
            {syncing ? "同步中..." : "同步全部"}
          </button>
        </div>
        {watchStatus && versions.length > 0 && (
          <p data-testid="project-detail-watch" className="hint">
            监听: {watchStatus.watch_enabled ? "已启用" : "未启用"}
          </p>
        )}

        <div className="form-row" style={{ marginTop: 16 }}>
          <label>手动添加版本</label>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "flex-end" }}>
            <input
              value={formVersionName}
              onChange={(e) => setFormVersionName(e.target.value)}
              placeholder="版本名"
              className="glow-input"
              style={{ width: 140 }}
            />
            <input
              value={formBranch}
              onChange={(e) => setFormBranch(e.target.value)}
              placeholder="绑定分支（可选）"
              className="glow-input"
              style={{ width: 140 }}
            />
            <button
              type="button"
              onClick={handleCreateVersion}
              disabled={submitting || (!formVersionName.trim() && !formBranch.trim())}
              data-testid="project-detail-version-submit"
            >
              {submitting ? "创建中..." : "新建版本"}
            </button>
          </div>
        </div>

        {versions.length > 0 && (
          <>
            <div className="form-row">
              <label htmlFor="project-detail-version">选择版本</label>
              <select
                id="project-detail-version"
                className="input-select"
                value={selectedVersionId ?? ""}
                onChange={(e) => setSelectedVersionId(e.target.value ? Number(e.target.value) : null)}
                data-testid="project-detail-version-select"
              >
                {versions.map((v) => (
                  <option key={v.id} value={v.id}>
                    {versionDisplayName(v)}{v.branch ? ` (${v.branch})` : ""}
                  </option>
                ))}
              </select>
            </div>
            <ul data-testid="project-detail-versions" className="hint" style={{ marginTop: 8 }}>
              {versions.map((v) => (
                <li key={v.id} data-testid={`version-${v.id}`} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                  {versionDisplayName(v)}
                  {v.branch ? <span className="hint">绑定分支: {v.branch}</span> : null}
                  {v.last_parsed_commit != null && <span>最后解析: {v.last_parsed_commit.slice(0, 7)}</span>}
                  <button
                    type="button"
                    className="secondary"
                    onClick={() => handleSyncVersion(v.id)}
                    disabled={syncingVersionId !== null}
                    data-testid={`version-sync-${v.id}`}
                  >
                    {syncingVersionId === v.id ? "同步中..." : "同步提交"}
                  </button>
                  {deleteConfirmId === v.id ? (
                    <>
                      <span>确认删除？</span>
                      <button type="button" onClick={() => handleDeleteVersion(v.id)} data-testid={`version-delete-confirm-${v.id}`}>确认</button>
                      <button type="button" className="secondary" onClick={() => setDeleteConfirmId(null)}>取消</button>
                    </>
                  ) : (
                    <button type="button" className="secondary" onClick={() => setDeleteConfirmId(v.id)} data-testid={`version-delete-${v.id}`}>删除</button>
                  )}
                </li>
              ))}
            </ul>
          </>
        )}
      </div>

      {selectedVersionId && (
        <>
          <div className="card" style={{ marginTop: 24 }}>
            <h3>提交</h3>
            {commits.length === 0 ? (
              <p className="hint" data-testid="project-detail-commits-empty">暂无提交</p>
            ) : (
              <>
                <div style={{ marginBottom: 12 }}>
                  <FlowButton
                    onClick={handleImpactAnalysis}
                    loading={impactLoading}
                    disabled={selectedCommitIds.length === 0}
                    data-testid="project-detail-impact-btn"
                  >
                    影响面分析
                  </FlowButton>
                  <span className="hint" style={{ marginLeft: 8 }}>已选 {selectedCommitIds.length} 个提交</span>
                </div>
                <ul data-testid="project-detail-commits" style={{ listStyle: "none", padding: 0, margin: 0 }}>
                  {commits.map((c) => (
                    <li key={c.id} data-testid={`commit-${c.id}`} style={{ marginBottom: 8 }}>
                      <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer" }}>
                        <input
                          type="checkbox"
                          checked={selectedCommitIds.includes(c.id)}
                          onChange={() => toggleCommit(c.id)}
                          data-testid={`commit-checkbox-${c.id}`}
                        />
                        <span className="mono">{c.commit_sha.slice(0, 7)}</span>
                        <span>{c.message ?? ""}</span>
                        {c.author && <span className="hint">{c.author}</span>}
                      </label>
                    </li>
                  ))}
                </ul>
              </>
            )}
          </div>

          <div className="card" style={{ marginTop: 24 }}>
            <h3>需求</h3>
            <div style={{ display: "flex", gap: 8, alignItems: "flex-end", marginBottom: 16 }}>
              <input
                value={newReqTitle}
                onChange={(e) => setNewReqTitle(e.target.value)}
                placeholder="新需求标题"
                className="glow-input"
                style={{ width: 240 }}
                data-testid="project-detail-new-req-input"
              />
              <button
                type="button"
                onClick={handleCreateRequirement}
                disabled={createReqLoading || !selectedVersionId || !newReqTitle.trim()}
                data-testid="project-detail-new-req-btn"
              >
                {createReqLoading ? "创建中..." : "新建需求"}
              </button>
            </div>
            {versionRequirements.length === 0 ? (
              <p className="hint" data-testid="project-detail-requirements-empty">暂无需求</p>
            ) : (
              <ul data-testid="project-detail-requirements" style={{ listStyle: "none", padding: 0, margin: 0 }}>
                {versionRequirements.map((r) => (
                  <li key={r.id} data-testid={`requirement-${r.id}`} style={{ marginBottom: 8, display: "flex", alignItems: "center", gap: 8 }}>
                    <span>{r.title}</span>
                    {bindReqId === r.id ? (
                      <>
                        <button
                          type="button"
                          onClick={() => handleBindRequirement(r.id)}
                          disabled={bindLoading || selectedCommitIds.length === 0}
                          data-testid={`requirement-bind-confirm-${r.id}`}
                        >
                          {bindLoading ? "绑定中..." : "确认绑定选中提交"}
                        </button>
                        <button type="button" className="secondary" onClick={() => setBindReqId(null)}>取消</button>
                      </>
                    ) : (
                      <button
                        type="button"
                        className="secondary"
                        onClick={() => setBindReqId(r.id)}
                        disabled={selectedCommitIds.length === 0}
                        data-testid={`requirement-bind-${r.id}`}
                      >
                        绑定选中提交
                      </button>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </>
      )}
    </div>
  );
}
