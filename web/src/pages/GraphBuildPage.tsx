import { useState, useEffect } from "react";
import {
  listProjects,
  listVersions,
  runParse,
  type Project,
  type Version,
} from "../api/client";
import { FlowButton } from "../components/FlowButton";

export function GraphBuildPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectId, setProjectId] = useState<number | null>(null);
  const [versions, setVersions] = useState<Version[]>([]);
  const [versionId, setVersionId] = useState<number | null>(null);
  const [versionTag, setVersionTag] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadList, setLoadList] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState<{ phase: string; done: boolean } | null>(null);
  const [parseResult, setParseResult] = useState<{ node_count: number; relationship_count: number; file_count: number } | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoadList(true);
    listProjects()
      .then((list) => {
        if (!cancelled) setProjects(list);
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : "加载失败");
      })
      .finally(() => {
        if (!cancelled) setLoadList(false);
      });
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    if (!projectId) {
      setVersions([]);
      setVersionId(null);
      return;
    }
    let cancelled = false;
    listVersions(projectId)
      .then((list) => {
        if (!cancelled) {
          setVersions(list);
          setVersionId(list[0]?.id ?? null);
        }
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : "加载版本失败");
      });
    return () => { cancelled = true; };
  }, [projectId]);

  const project = projects.find((p) => p.id === projectId);
  const repoPath = project?.repo_path ?? "";

  const handleStartBuild = async () => {
    if (!projectId || !versionId || !repoPath) return;
    const ver = versions.find((v) => v.id === versionId);
    setError(null);
    setParseResult(null);
    setProgress({ phase: "启动解析…", done: false });
    setLoading(true);
    try {
      const r = await runParse(repoPath, true, ver?.branch ?? undefined);
      setProgress({ phase: "图谱构建完毕", done: true });
      setParseResult({
        node_count: r.node_count,
        relationship_count: r.relationship_count,
        file_count: r.file_count,
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "图谱构建失败");
      setProgress(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div data-testid="page-graph-build">
      <h1 className="page-title">版本基线与图谱构建</h1>

      <div className="card" style={{ maxWidth: 560 }}>
        <div className="form-row">
          <label htmlFor="gb-project">项目</label>
          <select
            id="gb-project"
            className="input-select"
            value={projectId ?? ""}
            onChange={(e) => setProjectId(e.target.value ? Number(e.target.value) : null)}
            disabled={loadList}
            data-testid="graph-build-project"
          >
            <option value="">请选择项目</option>
            {projects.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
        </div>
        <div className="form-row">
          <label htmlFor="gb-version">分支（版本）</label>
          <select
            id="gb-version"
            className="input-select"
            value={versionId ?? ""}
            onChange={(e) => setVersionId(e.target.value ? Number(e.target.value) : null)}
            disabled={!projectId || versions.length === 0}
            data-testid="graph-build-version"
          >
            <option value="">请选择分支</option>
            {versions.map((v) => (
              <option key={v.id} value={v.id}>
                {v.version_name?.trim() || v.branch?.trim() || `版本 #${v.id}`}
                {v.branch ? ` (${v.branch})` : ""}
              </option>
            ))}
          </select>
        </div>
        <div className="form-row">
          <label htmlFor="gb-tag">版本号/标签（可选）</label>
          <input
            id="gb-tag"
            className="glow-input"
            value={versionTag}
            onChange={(e) => setVersionTag(e.target.value)}
            placeholder="例如 v1.0"
            disabled={loading}
          />
        </div>
        {error && <div className="result error" data-testid="graph-build-error">{error}</div>}
        {progress && (
          <div className="result" data-testid="graph-build-progress">
            {progress.phase}
          </div>
        )}
        {parseResult && (
          <div className="stats" data-testid="graph-build-result">
            <span className="stat">节点: {parseResult.node_count}</span>
            <span className="stat">关系: {parseResult.relationship_count}</span>
            <span className="stat">文件: {parseResult.file_count}</span>
          </div>
        )}
        <FlowButton
          onClick={handleStartBuild}
          loading={loading}
          disabled={!projectId || !versionId || !repoPath}
          data-testid="graph-build-submit"
        >
          启动图谱重构
        </FlowButton>
      </div>
    </div>
  );
}
