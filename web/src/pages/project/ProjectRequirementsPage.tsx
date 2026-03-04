import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  bindRequirementCommits,
  createRequirement,
  listCommitsByVersion,
  listRequirements,
  listVersions,
  type Commit,
  type Requirement,
  type Version,
} from "../../api/client";
import { useProjectPageContext } from "./ProjectLayoutPage";

export function ProjectRequirementsPage() {
  const { projectId } = useProjectPageContext();
  const navigate = useNavigate();
  const { versionId } = useParams<{ versionId: string }>();
  const selectedVersionId = versionId ? Number(versionId) : NaN;
  const [versions, setVersions] = useState<Version[]>([]);
  const [requirements, setRequirements] = useState<Requirement[]>([]);
  const [commits, setCommits] = useState<Commit[]>([]);
  const [selectedCommitIds, setSelectedCommitIds] = useState<number[]>([]);
  const [newReqTitle, setNewReqTitle] = useState("");
  const [createReqLoading, setCreateReqLoading] = useState(false);
  const [bindReqId, setBindReqId] = useState<number | null>(null);
  const [bindLoading, setBindLoading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    Promise.all([listVersions(projectId), listRequirements(projectId)]).then(([vList, rList]) => {
      if (cancelled) return;
      setVersions(vList);
      setRequirements(rList);
      if (vList.length > 0 && !vList.some((v) => v.id === selectedVersionId)) {
        navigate(`/projects/${projectId}/versions/${vList[0].id}/requirements`, { replace: true });
      }
      setLoading(false);
    }).catch((e) => {
      if (cancelled) return;
      setError(e instanceof Error ? e.message : "加载需求失败");
      setLoading(false);
    });
    return () => { cancelled = true; };
  }, [projectId, selectedVersionId, navigate]);

  useEffect(() => {
    if (!Number.isFinite(selectedVersionId)) {
      setCommits([]);
      return;
    }
    let cancelled = false;
    listCommitsByVersion(projectId, selectedVersionId).then((list) => {
      if (!cancelled) setCommits(list);
    }).catch((e) => {
      if (!cancelled) setError(e instanceof Error ? e.message : "加载版本提交失败");
    });
    return () => { cancelled = true; };
  }, [projectId, selectedVersionId]);

  const versionRequirements = useMemo(() => {
    if (!Number.isFinite(selectedVersionId)) return [];
    const key = `version:${selectedVersionId}`;
    return requirements.filter((r) => r.external_id === key);
  }, [requirements, selectedVersionId]);

  const toggleCommit = (commitId: number) => {
    setSelectedCommitIds((prev) =>
      prev.includes(commitId) ? prev.filter((id) => id !== commitId) : [...prev, commitId]
    );
  };

  const handleCreateRequirement = async () => {
    if (!Number.isFinite(selectedVersionId) || !newReqTitle.trim()) return;
    setCreateReqLoading(true);
    setError(null);
    try {
      await createRequirement(projectId, {
        title: newReqTitle.trim(),
        external_id: `version:${selectedVersionId}`,
      });
      setNewReqTitle("");
      setRequirements(await listRequirements(projectId));
    } catch (e) {
      setError(e instanceof Error ? e.message : "创建需求失败");
    } finally {
      setCreateReqLoading(false);
    }
  };

  const handleBindRequirement = async (requirementId: number) => {
    if (selectedCommitIds.length === 0) return;
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

  return (
    <div className="card" data-testid="project-requirements-page">
      <h3>需求</h3>
      {loading ? (
        <p>加载中...</p>
      ) : versions.length === 0 ? (
        <p className="hint">暂无版本，请先在版本页创建或扫描版本</p>
      ) : (
        <>
          <div className="form-row">
            <label htmlFor="project-requirement-version">选择版本</label>
            <select
              id="project-requirement-version"
              className="input-select"
              value={Number.isFinite(selectedVersionId) ? selectedVersionId : ""}
              onChange={(e) => {
                if (!e.target.value) return;
                navigate(`/projects/${projectId}/versions/${Number(e.target.value)}/requirements`);
                setSelectedCommitIds([]);
                setBindReqId(null);
              }}
            >
              {versions.map((v) => (
                <option key={v.id} value={v.id}>
                  {v.version_name?.trim() || v.branch?.trim() || `版本 #${v.id}`}
                  {v.branch ? ` (${v.branch})` : ""}
                </option>
              ))}
            </select>
          </div>

          <div style={{ display: "flex", gap: 8, alignItems: "flex-end", marginBottom: 16 }}>
            <input
              value={newReqTitle}
              onChange={(e) => setNewReqTitle(e.target.value)}
              placeholder="新需求标题"
              className="glow-input"
              style={{ width: 260 }}
            />
            <button
              type="button"
              onClick={handleCreateRequirement}
                disabled={createReqLoading || !Number.isFinite(selectedVersionId) || !newReqTitle.trim()}
            >
              {createReqLoading ? "创建中..." : "新建需求"}
            </button>
          </div>

          <h4 className="card-subtitle">当前版本提交（用于绑定）</h4>
          {commits.length === 0 ? (
            <p className="hint">暂无提交，请先在版本页同步提交</p>
          ) : (
            <ul style={{ listStyle: "none", padding: 0, margin: "0 0 16px" }}>
              {commits.map((c) => (
                <li key={c.id} style={{ marginBottom: 6 }}>
                  <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer" }}>
                    <input
                      type="checkbox"
                      checked={selectedCommitIds.includes(c.id)}
                      onChange={() => toggleCommit(c.id)}
                    />
                    <span className="mono">{c.commit_sha.slice(0, 7)}</span>
                    <span>{c.message ?? ""}</span>
                  </label>
                </li>
              ))}
            </ul>
          )}

          <h4 className="card-subtitle">当前版本需求</h4>
          {versionRequirements.length === 0 ? (
            <p className="hint">暂无需求</p>
          ) : (
            <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
              {versionRequirements.map((r) => (
                <li key={r.id} style={{ marginBottom: 8, display: "flex", alignItems: "center", gap: 8 }}>
                  <span>{r.title}</span>
                  {bindReqId === r.id ? (
                    <>
                      <button
                        type="button"
                        onClick={() => handleBindRequirement(r.id)}
                        disabled={bindLoading || selectedCommitIds.length === 0}
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
                    >
                      绑定选中提交
                    </button>
                  )}
                </li>
              ))}
            </ul>
          )}
        </>
      )}
      {error && <div className="result error">{error}</div>}
    </div>
  );
}
