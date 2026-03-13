import { useCallback, useEffect, useRef, useState } from "react";
import { useProductPageContext } from "./ProductLayoutPage";
import { listProductReports, getImpactAnalysis, type ImpactAnalysis } from "../../api/client";
import { MarkdownRenderer } from "../../components/MarkdownRenderer";

export function ProductReportsPage() {
  const { productId } = useProductPageContext();
  const [reports, setReports] = useState<ImpactAnalysis[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<ImpactAnalysis | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const load = useCallback(async () => {
    try {
      const data = await listProductReports(productId);
      setReports(data);
      return data;
    } catch {
      return [];
    }
  }, [productId]);

  // 初始加载
  useEffect(() => {
    setLoading(true);
    load().finally(() => setLoading(false));
  }, [load]);

  // 有 running 状态时自动轮询
  useEffect(() => {
    const hasRunning = reports.some((r) => r.status === "running");
    if (hasRunning && !pollRef.current) {
      pollRef.current = setInterval(() => { load(); }, 4000);
    }
    if (!hasRunning && pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    return () => {
      if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
    };
  }, [reports, load]);

  const handleRowClick = async (r: ImpactAnalysis) => {
    if (r.status !== "done") return;
    if (r.result_summary) { setSelected(r); return; }
    setDetailLoading(true);
    try {
      const full = await getImpactAnalysis(r.project_id, r.id);
      setSelected(full);
    } catch { /* ignore */ }
    finally { setDetailLoading(false); }
  };

  const statusBadge = (s: string) => {
    const map: Record<string, { color: string; label: string }> = {
      done: { color: "#00C853", label: "完成" },
      failed: { color: "#FF0055", label: "失败" },
      running: { color: "#FFB300", label: "生成中..." },
      pending: { color: "#8A8A9A", label: "等待中" },
    };
    const { color, label } = map[s] || { color: "#8A8A9A", label: s };
    return (
      <span style={{
        display: "inline-flex", alignItems: "center", gap: 6,
        padding: "2px 10px", borderRadius: 4, fontSize: 12,
        background: `${color}22`, color, border: `1px solid ${color}44`,
      }}>
        {s === "running" && <span className="status-dot-pulse" style={{
          width: 6, height: 6, borderRadius: "50%", background: color,
          animation: "pulse 1.2s ease-in-out infinite",
        }} />}
        {label}
      </span>
    );
  };

  if (loading) return <div className="loading-state">加载中...</div>;

  return (
    <div data-testid="page-product-reports">
      <style>{`@keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.3; } }`}</style>
      <div className="flex-between mb-16">
        <h3 style={{ margin: 0 }}>影响面分析报告</h3>
        {reports.some((r) => r.status === "running") && (
          <span className="text-caption" style={{ color: "#FFB300" }}>有任务正在生成中...</span>
        )}
      </div>

      {reports.length === 0 ? (
        <div className="empty-state" style={{ textAlign: "center", padding: "48px 0" }}>
          <p className="text-muted">暂无报告</p>
          <p className="text-caption text-muted">在项目提交列表中选择提交后点击「影响面分析」生成报告</p>
        </div>
      ) : (
        <div className="card" style={{ overflow: "auto" }}>
          {detailLoading && <div className="text-caption text-muted" style={{ marginBottom: 8 }}>加载报告详情...</div>}
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: "1px solid var(--color-border)" }}>
                <th style={thStyle}>报告名称</th>
                <th style={thStyle}>项目</th>
                <th style={thStyle}>版本</th>
                <th style={{ ...thStyle, textAlign: "center" }}>状态</th>
                <th style={{ ...thStyle, textAlign: "center" }}>提交数</th>
                <th style={thStyle}>创建时间</th>
              </tr>
            </thead>
            <tbody>
              {reports.map((r) => (
                <tr
                  key={r.id}
                  onClick={() => handleRowClick(r)}
                  style={{
                    borderBottom: "1px solid rgba(255,255,255,0.04)",
                    cursor: r.status === "done" ? "pointer" : "default",
                    transition: "background 0.15s",
                  }}
                  onMouseEnter={(e) => { if (r.status === "done") e.currentTarget.style.background = "rgba(0,240,255,0.04)"; }}
                  onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; }}
                >
                  <td style={tdStyle}>{r.title || (r.status === "running" ? "生成中..." : `报告 #${r.id}`)}</td>
                  <td style={tdStyle} className="text-muted">{r.project_name || "-"}</td>
                  <td style={tdStyle} className="text-muted">{r.version_name || "-"}</td>
                  <td style={{ ...tdStyle, textAlign: "center" }}>{statusBadge(r.status)}</td>
                  <td style={{ ...tdStyle, textAlign: "center" }}>{r.commit_count ?? "-"}</td>
                  <td style={tdStyle} className="text-caption text-muted">
                    {r.triggered_at ? r.triggered_at.slice(0, 16).replace("T", " ") : "-"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {selected?.result_summary && (
        <div className="modal-overlay" onClick={() => setSelected(null)}>
          <div
            className="modal-content"
            onClick={(e) => e.stopPropagation()}
            style={{ minWidth: "60vw", maxWidth: "85vw", maxHeight: "90vh", overflow: "hidden", display: "flex", flexDirection: "column" }}
          >
            <div className="modal-header">
              <h3 style={{ margin: 0 }}>{selected.title || "影响面分析报告"}</h3>
              <button type="button" className="modal-close" onClick={() => setSelected(null)}>&times;</button>
            </div>
            <div style={{ flex: 1, overflowY: "auto", minHeight: 0 }}>
              <MarkdownRenderer content={selected.result_summary} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

const thStyle: React.CSSProperties = { textAlign: "left", padding: "8px 6px", fontWeight: 500 };
const tdStyle: React.CSSProperties = { padding: "8px 6px" };
