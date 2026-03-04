import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { createImpactAnalysis, listCommitsByVersion, listVersions, type Commit, type Version } from "../../api/client";
import { FlowButton } from "../../components/FlowButton";
import { useProjectPageContext } from "./ProjectLayoutPage";

export function ProjectCommitsPage() {
  const { projectId } = useProjectPageContext();
  const navigate = useNavigate();
  const { versionId } = useParams<{ versionId: string }>();
  const selectedVersionId = versionId ? Number(versionId) : NaN;
  const [versions, setVersions] = useState<Version[]>([]);
  const [commits, setCommits] = useState<Commit[]>([]);
  const [selectedCommitIds, setSelectedCommitIds] = useState<number[]>([]);
  const [loading, setLoading] = useState(true);
  const [impactLoading, setImpactLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    listVersions(projectId).then((vList) => {
      if (cancelled) return;
      setVersions(vList);
      if (vList.length > 0 && !vList.some((v) => v.id === selectedVersionId)) {
        navigate(`/projects/${projectId}/versions/${vList[0].id}/commits`, { replace: true });
      }
      setLoading(false);
    }).catch((e) => {
      if (cancelled) return;
      setError(e instanceof Error ? e.message : "加载版本失败");
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
    setError(null);
    listCommitsByVersion(projectId, selectedVersionId).then((list) => {
      if (!cancelled) setCommits(list);
    }).catch((e) => {
      if (!cancelled) setError(e instanceof Error ? e.message : "加载提交失败");
    });
    return () => { cancelled = true; };
  }, [projectId, selectedVersionId]);

  const toggleCommit = (commitId: number) => {
    setSelectedCommitIds((prev) =>
      prev.includes(commitId) ? prev.filter((id) => id !== commitId) : [...prev, commitId]
    );
  };

  const handleImpactAnalysis = async () => {
    if (selectedCommitIds.length === 0) return;
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

  return (
    <div className="card" data-testid="project-commits-page">
      <h3>提交</h3>
      {loading ? (
        <p>加载中...</p>
      ) : versions.length === 0 ? (
        <p className="hint">暂无版本，请先在版本页创建或扫描版本</p>
      ) : (
        <>
          <div className="form-row">
            <label htmlFor="project-commits-version">选择版本</label>
            <select
              id="project-commits-version"
              className="input-select"
              value={Number.isFinite(selectedVersionId) ? selectedVersionId : ""}
              onChange={(e) => {
                if (!e.target.value) return;
                navigate(`/projects/${projectId}/versions/${Number(e.target.value)}/commits`);
                setSelectedCommitIds([]);
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

          <div style={{ marginBottom: 12 }}>
            <FlowButton onClick={handleImpactAnalysis} loading={impactLoading} disabled={selectedCommitIds.length === 0}>
              影响面分析
            </FlowButton>
            <span className="hint" style={{ marginLeft: 8 }}>已选 {selectedCommitIds.length} 个提交</span>
          </div>

          {commits.length === 0 ? (
            <p className="hint">暂无提交，请先点击“版本”页中的“同步提交”</p>
          ) : (
            <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
              {commits.map((c) => (
                <li key={c.id} style={{ marginBottom: 8 }}>
                  <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer" }}>
                    <input
                      type="checkbox"
                      checked={selectedCommitIds.includes(c.id)}
                      onChange={() => toggleCommit(c.id)}
                    />
                    <span className="mono">{c.commit_sha.slice(0, 7)}</span>
                    <span>{c.message ?? ""}</span>
                    {c.author ? <span className="hint">{c.author}</span> : null}
                  </label>
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
