import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  createImpactAnalysis,
  listCommitsByVersion,
  listNodesByVersion,
  listVersions,
  type Commit,
  type GraphNode,
  type Version,
} from "../../api/client";
import { FlowButton } from "../../components/FlowButton";
import { useProjectPageContext } from "./ProjectLayoutPage";

export function ProjectCommitsPage() {
  const { projectId } = useProjectPageContext();
  const navigate = useNavigate();
  const { versionId } = useParams<{ versionId: string }>();
  const selectedVersionId = versionId ? Number(versionId) : NaN;
  const [versions, setVersions] = useState<Version[]>([]);
  const [commits, setCommits] = useState<Commit[]>([]);
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [nodeTypes, setNodeTypes] = useState<string[]>([]);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [selectedCommitIds, setSelectedCommitIds] = useState<number[]>([]);
  const [loading, setLoading] = useState(true);
  const [impactLoading, setImpactLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [nodeNameFilter, setNodeNameFilter] = useState("");
  const [nodeTypeFilter, setNodeTypeFilter] = useState("");
  const [commitMessageFilter, setCommitMessageFilter] = useState("");
  const [commitFrom, setCommitFrom] = useState("");
  const [commitTo, setCommitTo] = useState("");
  const [commitIdFilter, setCommitIdFilter] = useState("");
  const [commitShaFilter, setCommitShaFilter] = useState("");

  const nodeTypeOptions = useMemo(
    () => ["", ...nodeTypes.filter((x) => x.trim() !== "")],
    [nodeTypes]
  );

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
      setNodes([]);
      setSelectedNode(null);
      return;
    }
    let cancelled = false;
    listNodesByVersion(projectId, selectedVersionId, {
      name: nodeNameFilter.trim() || undefined,
      type: nodeTypeFilter.trim() || undefined,
    }).then((list) => {
      if (cancelled) return;
      setNodes(list);
      setSelectedNode((prev) => {
        if (!prev) return list[0] ?? null;
        return list.find((n) => n.id === prev.id) ?? (list[0] ?? null);
      });
    }).catch(() => {
      if (cancelled) return;
      setNodes([]);
      setSelectedNode(null);
    });
    return () => { cancelled = true; };
  }, [projectId, selectedVersionId, nodeNameFilter, nodeTypeFilter]);

  useEffect(() => {
    if (!Number.isFinite(selectedVersionId)) {
      setNodeTypes([]);
      return;
    }
    let cancelled = false;
    listNodesByVersion(projectId, selectedVersionId).then((list) => {
      if (cancelled) return;
      const allTypes = Array.from(new Set(list.map((n) => n.label).filter(Boolean))).sort(
        (a, b) => a.localeCompare(b)
      );
      setNodeTypes(allTypes);
    }).catch(() => {
      if (!cancelled) setNodeTypes([]);
    });
    return () => { cancelled = true; };
  }, [projectId, selectedVersionId]);

  useEffect(() => {
    if (!Number.isFinite(selectedVersionId)) {
      setCommits([]);
      return;
    }
    let cancelled = false;
    setError(null);
    const commitIdNum = commitIdFilter.trim() ? Number(commitIdFilter.trim()) : undefined;
    listCommitsByVersion(projectId, selectedVersionId, {
      message: commitMessageFilter.trim() || undefined,
      committed_at_from: commitFrom.trim() || undefined,
      committed_at_to: commitTo.trim() || undefined,
      id: commitIdNum !== undefined && !Number.isNaN(commitIdNum) ? commitIdNum : undefined,
      sha: commitShaFilter.trim() || undefined,
    }).then((list) => {
      if (!cancelled) setCommits(list);
    }).catch((e) => {
      if (!cancelled) setError(e instanceof Error ? e.message : "加载提交失败");
    });
    return () => { cancelled = true; };
  }, [projectId, selectedVersionId, commitMessageFilter, commitFrom, commitTo, commitIdFilter, commitShaFilter]);

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

  const formatNodeValue = (value: unknown): string => {
    if (value == null) return "-";
    if (typeof value === "string") return value;
    if (typeof value === "number" || typeof value === "boolean") return String(value);
    try {
      return JSON.stringify(value);
    } catch {
      return String(value);
    }
  };

  return (
    <div className="card" data-testid="project-commits-page">
      <h3>版本详情</h3>
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
                setNodeNameFilter("");
                setNodeTypeFilter("");
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

          <div style={{ marginTop: 20, display: "grid", gridTemplateColumns: "1fr 1.4fr", gap: 16 }}>
            <section
              style={{
                border: "1px solid var(--border-color, #2a2a2a)",
                borderRadius: 8,
                padding: 12,
                minHeight: 420,
              }}
            >
              <h4 style={{ margin: "0 0 10px" }}>节点列表</h4>
              <div className="form-row" style={{ flexWrap: "wrap", gap: 8, marginBottom: 10 }}>
                <input
                  type="text"
                  className="input"
                  placeholder="节点名称"
                  value={nodeNameFilter}
                  onChange={(e) => setNodeNameFilter(e.target.value)}
                  style={{ width: 180 }}
                />
                <select
                  className="input-select"
                  value={nodeTypeFilter}
                  onChange={(e) => setNodeTypeFilter(e.target.value)}
                  style={{ width: 180 }}
                >
                  {nodeTypeOptions.map((opt) => (
                    <option key={opt || "all"} value={opt}>{opt || "全部类型"}</option>
                  ))}
                </select>
              </div>
              {nodes.length === 0 ? (
                <p className="hint">暂无节点或未配置图数据</p>
              ) : (
                <ul style={{ listStyle: "none", margin: 0, padding: 0, maxHeight: 320, overflowY: "auto" }}>
                  {nodes.map((n) => {
                    const active = selectedNode?.id === n.id;
                    return (
                      <li key={n.id} style={{ marginBottom: 6 }}>
                        <button
                          type="button"
                          className="secondary"
                          style={{
                            width: "100%",
                            textAlign: "left",
                            borderColor: active ? "var(--color-primary, #2ea8ff)" : undefined,
                            background: active ? "rgba(46,168,255,0.08)" : undefined,
                          }}
                          onClick={() => setSelectedNode(n)}
                        >
                          <span style={{ marginRight: 8 }}>{n.name || n.id}</span>
                          {n.label ? <span className="hint">[{n.label}]</span> : null}
                        </button>
                      </li>
                    );
                  })}
                </ul>
              )}
              {selectedNode ? (
                <div
                  style={{
                    marginTop: 10,
                    borderTop: "1px solid var(--border-color, #2a2a2a)",
                    paddingTop: 10,
                    fontSize: "0.92em",
                  }}
                >
                  <div style={{ marginBottom: 6, fontWeight: 600 }}>节点详情</div>
                  <div><span className="hint">名称:</span> {selectedNode.name || "-"}</div>
                  <div><span className="hint">类型:</span> {selectedNode.label || "-"}</div>
                  <div><span className="hint">ID:</span> <span className="mono">{selectedNode.id}</span></div>
                  {selectedNode.properties ? (
                    <ul style={{ margin: "8px 0 0", paddingLeft: 18 }}>
                      {Object.entries(selectedNode.properties).map(([k, v]) => (
                        <li key={k}>
                          <span className="hint">{k}:</span> {formatNodeValue(v)}
                        </li>
                      ))}
                    </ul>
                  ) : null}
                </div>
              ) : null}
            </section>

            <section
              style={{
                border: "1px solid var(--border-color, #2a2a2a)",
                borderRadius: 8,
                padding: 12,
                minHeight: 420,
              }}
            >
              <h4 style={{ margin: "0 0 10px" }}>提交列表</h4>
              <div className="form-row" style={{ flexWrap: "wrap", gap: 8, marginBottom: 10 }}>
                <input
                  type="text"
                  className="input"
                  placeholder="提交消息"
                  value={commitMessageFilter}
                  onChange={(e) => setCommitMessageFilter(e.target.value)}
                  style={{ width: 170 }}
                />
                <input
                  type="datetime-local"
                  className="input"
                  value={commitFrom}
                  onChange={(e) => setCommitFrom(e.target.value)}
                  style={{ width: 180 }}
                />
                <input
                  type="datetime-local"
                  className="input"
                  value={commitTo}
                  onChange={(e) => setCommitTo(e.target.value)}
                  style={{ width: 180 }}
                />
                <input
                  type="text"
                  className="input"
                  placeholder="ID"
                  value={commitIdFilter}
                  onChange={(e) => setCommitIdFilter(e.target.value)}
                  style={{ width: 90 }}
                />
                <input
                  type="text"
                  className="input"
                  placeholder="SHA 前缀"
                  value={commitShaFilter}
                  onChange={(e) => setCommitShaFilter(e.target.value)}
                  style={{ width: 110 }}
                />
              </div>

              <div style={{ marginBottom: 10 }}>
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
            </section>
          </div>
        </>
      )}
      {error && <div className="result error">{error}</div>}
    </div>
  );
}
