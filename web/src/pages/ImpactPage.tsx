import { useState, useEffect } from "react";
import {
  listProjects,
  listImpactAnalyses,
  getImpactAnalysis,
  type Project,
  type ImpactAnalysis,
} from "../api/client";

export function ImpactPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectId, setProjectId] = useState<number | null>(null);
  const [analyses, setAnalyses] = useState<ImpactAnalysis[]>([]);
  const [detailId, setDetailId] = useState<number | null>(null);
  const [detail, setDetail] = useState<ImpactAnalysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    listProjects()
      .then((list) => {
        if (!cancelled) {
          setProjects(list);
          if (list.length > 0 && projectId === null) setProjectId(list[0].id);
        }
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : "加载失败");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!projectId) {
      setAnalyses([]);
      return;
    }
    let cancelled = false;
    setLoading(true);
    listImpactAnalyses(projectId)
      .then((list) => {
        if (!cancelled) setAnalyses(list);
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : "加载失败");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [projectId]);

  useEffect(() => {
    if (!projectId || detailId === null) {
      setDetail(null);
      return;
    }
    let cancelled = false;
    getImpactAnalysis(projectId, detailId)
      .then((a) => {
        if (!cancelled) setDetail(a);
      })
      .catch(() => {
        if (!cancelled) setDetail(null);
      });
    return () => {
      cancelled = true;
    };
  }, [projectId, detailId]);

  return (
    <div data-testid="page-impact">
      <h2 className="page-title" style={{ fontSize: "var(--text-h2)" }}>提交与影响面分析</h2>
      {error && <div className="result error" data-testid="impact-error">{error}</div>}
      <div className="form-row">
        <label htmlFor="impact-project">项目</label>
        <select
          id="impact-project"
          className="input-select"
          value={projectId ?? ""}
          onChange={(e) => setProjectId(e.target.value ? Number(e.target.value) : null)}
          data-testid="impact-project-select"
        >
          <option value="">请选择项目</option>
          {projects.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
      </div>
      {loading && <p data-testid="impact-loading">加载中...</p>}
      <ul data-testid="impact-list">
        {analyses.map((a) => (
          <li key={a.id} data-testid={`impact-item-${a.id}`}>
            <span>#{a.id}</span>
            <span> 状态: {a.status}</span>
            {a.triggered_at && <span> 触发: {new Date(a.triggered_at).toLocaleString()}</span>}
            <button type="button" className="secondary" onClick={() => setDetailId(a.id)} data-testid={`impact-detail-${a.id}`}>
              详情
            </button>
          </li>
        ))}
      </ul>
      {analyses.length === 0 && !loading && projectId && <p data-testid="impact-empty">暂无分析记录</p>}
      {detail && (
        <div className="card" data-testid="impact-detail-panel">
          <h3>分析详情 #{detail.id}</h3>
          <p>状态: {detail.status}</p>
          {detail.triggered_at && <p>触发时间: {new Date(detail.triggered_at).toLocaleString()}</p>}
          {detail.result_summary && <pre>{detail.result_summary}</pre>}
          <button type="button" className="secondary" onClick={() => setDetailId(null)}>
            关闭
          </button>
        </div>
      )}
    </div>
  );
}
