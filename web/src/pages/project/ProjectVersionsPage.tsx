import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { createVersion, deleteVersion, getWatchStatus, listVersions, syncCommits, type Version, type WatchStatus } from "../../api/client";
import { useProjectPageContext } from "./ProjectLayoutPage";

export function ProjectVersionsPage() {
  const { projectId } = useProjectPageContext();
  const [versions, setVersions] = useState<Version[]>([]);
  const [watchStatus, setWatchStatus] = useState<WatchStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [formVersionName, setFormVersionName] = useState("");
  const [formBranch, setFormBranch] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [deleteConfirmId, setDeleteConfirmId] = useState<number | null>(null);

  /** 版本展示名：版本名 > 绑定分支 > 版本 #id */
  const versionDisplayName = (v: Version) =>
    v.version_name?.trim() || v.branch?.trim() || `版本 #${v.id}`;

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const [vList, status] = await Promise.all([listVersions(projectId), getWatchStatus(projectId)]);
      setVersions(vList);
      setWatchStatus(status);
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载版本失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [projectId]);

  const handleCreateVersion = async () => {
    const versionName = formVersionName.trim() || null;
    const branch = formBranch.trim() || null;
    if (!versionName && !branch) return;
    setSubmitting(true);
    setError(null);
    try {
      await createVersion(projectId, {
        version_name: versionName,
        branch,
      });
      setFormVersionName("");
      setFormBranch("");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "创建版本失败");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteVersion = async (versionId: number) => {
    setError(null);
    try {
      await deleteVersion(projectId, versionId);
      setDeleteConfirmId(null);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "删除版本失败");
    }
  };

  const handleSync = async () => {
    setSyncing(true);
    setError(null);
    try {
      await syncCommits(projectId);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "同步提交失败");
    } finally {
      setSyncing(false);
    }
  };

  return (
    <div className="card" data-testid="project-versions-page">
      <h3>版本管理</h3>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "flex-end" }}>
        <input
          value={formVersionName}
          onChange={(e) => setFormVersionName(e.target.value)}
          placeholder="版本名"
          className="glow-input"
          style={{ width: 160 }}
        />
        <input
          value={formBranch}
          onChange={(e) => setFormBranch(e.target.value)}
          placeholder="绑定分支（可选）"
          className="glow-input"
          style={{ width: 160 }}
        />
        <button
          type="button"
          onClick={handleCreateVersion}
          disabled={submitting || (!formVersionName.trim() && !formBranch.trim())}
        >
          {submitting ? "创建中..." : "新建版本"}
        </button>
        <button type="button" className="secondary" onClick={handleSync} disabled={syncing || versions.length === 0}>
          {syncing ? "同步中..." : "同步提交"}
        </button>
      </div>

      {watchStatus && versions.length > 0 && (
        <p className="hint" style={{ marginTop: 12 }}>
          监听: {watchStatus.watch_enabled ? "已启用" : "未启用"}
        </p>
      )}

      {loading ? (
        <p>加载中...</p>
      ) : versions.length === 0 ? (
        <p className="hint">暂无版本</p>
      ) : (
        <ul style={{ marginTop: 12 }}>
          {versions.map((v) => (
            <li key={v.id} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
              <span>{versionDisplayName(v)}</span>
              {v.branch ? <span className="hint">绑定分支: {v.branch}</span> : null}
              {v.last_parsed_commit ? <span className="hint">最后解析: {v.last_parsed_commit.slice(0, 7)}</span> : null}
              <Link to={`/projects/${projectId}/versions/${v.id}/commits`} className="secondary" style={{ textDecoration: "none" }}>
                进入提交
              </Link>
              <Link to={`/projects/${projectId}/versions/${v.id}/requirements`} className="secondary" style={{ textDecoration: "none" }}>
                进入需求
              </Link>
              {deleteConfirmId === v.id ? (
                <>
                  <span>确认删除？</span>
                  <button type="button" onClick={() => handleDeleteVersion(v.id)}>确认</button>
                  <button type="button" className="secondary" onClick={() => setDeleteConfirmId(null)}>取消</button>
                </>
              ) : (
                <button type="button" className="secondary" onClick={() => setDeleteConfirmId(v.id)}>删除</button>
              )}
            </li>
          ))}
        </ul>
      )}
      {error && <div className="result error">{error}</div>}
    </div>
  );
}
