import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  createVersion,
  deleteVersion,
  getPreprocessStatus,
  getWatchStatus,
  listProjectBranches,
  listVersions,
  postPreprocess,
  syncCommits,
  syncCommitsForVersion,
  type PreprocessStatusItem,
  type Version,
  type WatchStatus,
} from "../../api/client";
import { useProjectPageContext } from "./ProjectLayoutPage";

export function ProjectVersionsPage() {
  const { projectId } = useProjectPageContext();
  const [versions, setVersions] = useState<Version[]>([]);
  const [watchStatus, setWatchStatus] = useState<WatchStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [modalVersionName, setModalVersionName] = useState("");
  const [modalBranch, setModalBranch] = useState("");
  const [branches, setBranches] = useState<string[]>([]);
  const [branchesLoading, setBranchesLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [syncingVersionId, setSyncingVersionId] = useState<number | null>(null);
  const [deleteConfirmId, setDeleteConfirmId] = useState<number | null>(null);
  const [preprocessByBranch, setPreprocessByBranch] = useState<Record<string, PreprocessStatusItem>>({});
  const [preprocessLoadingBranch, setPreprocessLoadingBranch] = useState<string | null>(null);
  const [expandedLogsBranch, setExpandedLogsBranch] = useState<string | null>(null);

  /** 列表只展示版本：有版本名用版本名，否则用 版本 #id（不展示分支名） */
  const versionDisplayName = (v: Version) =>
    v.version_name?.trim() || `版本 #${v.id}`;

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [vList, status, preprocessResp] = await Promise.all([
        listVersions(projectId),
        getWatchStatus(projectId),
        getPreprocessStatus(projectId).catch(() => null),
      ]);
      setVersions(vList);
      setWatchStatus(status);
      const items =
        preprocessResp && typeof preprocessResp === "object" && "items" in preprocessResp
          ? (preprocessResp as { items: PreprocessStatusItem[] }).items
          : [];
      const map: Record<string, PreprocessStatusItem> = {};
      for (const it of items) {
        if (it && typeof it === "object" && "branch" in it) map[it.branch] = it;
      }
      setPreprocessByBranch(map);
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载版本失败");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    load();
  }, [load]);

  const openCreateModal = useCallback(() => {
    setModalVersionName("");
    setModalBranch("");
    setModalOpen(true);
    setBranches([]);
    setBranchesLoading(true);
    listProjectBranches(projectId)
      .then((list) => setBranches(Array.isArray(list) ? list : []))
      .catch(() => setBranches([]))
      .finally(() => setBranchesLoading(false));
  }, [projectId]);

  const handleCreateVersion = async () => {
    const versionName = modalVersionName.trim() || null;
    const branch = modalBranch.trim() || null;
    if (!versionName && !branch) return;
    setSubmitting(true);
    setError(null);
    try {
      await createVersion(projectId, {
        version_name: versionName,
        branch: branch || undefined,
      });
      setModalOpen(false);
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

  const handleSyncVersion = async (versionId: number) => {
    setSyncingVersionId(versionId);
    setError(null);
    try {
      await syncCommitsForVersion(projectId, versionId);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "同步提交失败");
    } finally {
      setSyncingVersionId(null);
    }
  };

  const handleTriggerPreprocess = async (branch: string) => {
    const key = branch || "main";
    setPreprocessLoadingBranch(key);
    setError(null);
    try {
      await postPreprocess(projectId, key, false);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "触发 AI 分析失败");
    } finally {
      setPreprocessLoadingBranch(null);
    }
  };

  const formatPreprocessTime = (item: PreprocessStatusItem) => {
    const t = item.finished_at || item.started_at;
    if (!t) return null;
    try {
      const d = new Date(t);
      return d.toLocaleString(undefined, { dateStyle: "short", timeStyle: "short" });
    } catch {
      return t;
    }
  };

  const formatLogAt = (at: string) => {
    try {
      const d = new Date(at);
      return d.toLocaleTimeString(undefined, { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" });
    } catch {
      return at;
    }
  };

  return (
    <div className="card" data-testid="project-versions-page">
      <h3>版本管理</h3>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center", marginBottom: 12 }}>
        <button type="button" onClick={openCreateModal}>
          新建版本
        </button>
        <button type="button" className="secondary" onClick={handleSync} disabled={syncing || versions.length === 0}>
          {syncing ? "同步中..." : "同步全部"}
        </button>
      </div>

      {modalOpen && (
        <div
          className="modal-overlay"
          role="dialog"
          aria-modal="true"
          aria-labelledby="create-version-title"
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.5)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
          }}
          onClick={(e) => e.target === e.currentTarget && setModalOpen(false)}
        >
          <div
            className="card"
            style={{ minWidth: 320, maxWidth: "90vw" }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 id="create-version-title">新建版本</h3>
            <div style={{ display: "flex", flexDirection: "column", gap: 12, marginTop: 12 }}>
              <label>
                <span style={{ display: "block", marginBottom: 4 }}>版本名</span>
                <input
                  value={modalVersionName}
                  onChange={(e) => setModalVersionName(e.target.value)}
                  placeholder="输入版本名称"
                  className="glow-input"
                  style={{ width: "100%", boxSizing: "border-box" }}
                />
              </label>
              <label>
                <span style={{ display: "block", marginBottom: 4 }}>绑定分支（可选）</span>
                <select
                  value={modalBranch}
                  onChange={(e) => setModalBranch(e.target.value)}
                  className="glow-input"
                  style={{ width: "100%", boxSizing: "border-box" }}
                  disabled={branchesLoading}
                >
                  <option value="">不绑定</option>
                  {branches.map((b) => (
                    <option key={b} value={b}>
                      {b}
                    </option>
                  ))}
                </select>
                {branchesLoading && <span className="hint">加载分支中...</span>}
              </label>
            </div>
            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 16 }}>
              <button type="button" className="secondary" onClick={() => setModalOpen(false)}>
                取消
              </button>
              <button
                type="button"
                onClick={handleCreateVersion}
                disabled={submitting || (!modalVersionName.trim() && !modalBranch.trim())}
              >
                {submitting ? "创建中..." : "创建"}
              </button>
            </div>
          </div>
        </div>
      )}

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
        <ul style={{ marginTop: 12, listStyle: "none", padding: 0 }}>
          {versions.map((v) => {
            const branchKey = v.branch ?? "main";
            const preprocessStatus = preprocessByBranch[branchKey];
            const isPreprocessLoading = preprocessLoadingBranch === branchKey;
            const processLogs = preprocessStatus?.extra?.logs;
            const hasLogs = Array.isArray(processLogs) && processLogs.length > 0;
            const logsExpanded = expandedLogsBranch === branchKey;
            return (
              <li key={v.id} style={{ marginBottom: 10 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                  <span style={{ minWidth: 100 }}>{versionDisplayName(v)}</span>
                  {v.branch ? <span className="hint">分支: {v.branch}</span> : null}
                  {v.last_parsed_commit ? <span className="hint">最后解析: {v.last_parsed_commit.slice(0, 7)}</span> : null}
                  <span className="hint" style={{ minWidth: 120 }}>
                    AI 分析: {preprocessStatus ? (preprocessStatus.status === "running" ? "进行中" : preprocessStatus.status === "completed" ? "已完成" : preprocessStatus.status === "failed" ? "失败" : preprocessStatus.status) : "—"}
                    {preprocessStatus && formatPreprocessTime(preprocessStatus) ? ` (${formatPreprocessTime(preprocessStatus)})` : ""}
                  </span>
                  <button
                    type="button"
                    className="secondary"
                    onClick={() => handleTriggerPreprocess(branchKey)}
                    disabled={isPreprocessLoading || preprocessStatus?.status === "running"}
                    title="对当前分支触发 AI 预处理分析"
                  >
                    {isPreprocessLoading || preprocessStatus?.status === "running" ? "分析中..." : "AI 分析"}
                  </button>
                  {hasLogs ? (
                    <button
                      type="button"
                      className="secondary"
                      onClick={() => setExpandedLogsBranch(logsExpanded ? null : branchKey)}
                      title="查看过程日志"
                    >
                      {logsExpanded ? "收起日志" : `过程日志 (${processLogs.length})`}
                    </button>
                  ) : null}
                  <button
                    type="button"
                    className="secondary"
                    onClick={() => handleSyncVersion(v.id)}
                    disabled={syncingVersionId !== null}
                  >
                    {syncingVersionId === v.id ? "同步中..." : "同步提交"}
                  </button>
                  <Link to={`/projects/${projectId}/versions/${v.id}/commits`} className="secondary" style={{ textDecoration: "none" }}>
                    进入版本
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
                </div>
                {hasLogs && logsExpanded ? (
                  <div className="hint" style={{ marginTop: 6, padding: "8px 12px", background: "var(--bg-secondary, #1a1a1a)", borderRadius: 6, fontSize: "0.9em", maxHeight: 200, overflowY: "auto" }}>
                    <div style={{ marginBottom: 4, fontWeight: 600 }}>AI 分析过程日志</div>
                    <ul style={{ margin: 0, paddingLeft: 20, listStyle: "disc" }}>
                      {processLogs.map((entry, i) => (
                        <li key={i} style={{ marginBottom: 2 }}>
                          <span style={{ opacity: 0.85 }}>{formatLogAt(entry.at)}</span> {entry.message}
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}
              </li>
            );
          })}
        </ul>
      )}
      {error && <div className="result error">{error}</div>}
    </div>
  );
}
