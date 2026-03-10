import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useProductPageContext } from "./ProductLayoutPage";
import {
  listProductProjects,
  listProductVersions,
  listProductRequirements,
  listProductBugs,
  type Project,
  type ProductVersion,
} from "../../api/client";

export function ProductDashboardPage() {
  const { productId, product } = useProductPageContext();
  const navigate = useNavigate();
  const [projects, setProjects] = useState<Project[]>([]);
  const [versions, setVersions] = useState<ProductVersion[]>([]);
  const [reqCount, setReqCount] = useState({ total: 0, open: 0, done: 0 });
  const [bugCount, setBugCount] = useState({ total: 0, open: 0, resolved: 0 });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const [projs, vers, reqs, bugs] = await Promise.all([
          listProductProjects(productId),
          listProductVersions(productId),
          listProductRequirements(productId),
          listProductBugs(productId),
        ]);
        setProjects(projs);
        setVersions(vers);
        setReqCount({
          total: reqs.length,
          open: reqs.filter((r) => r.status === "open" || r.status === "in_progress").length,
          done: reqs.filter((r) => r.status === "done" || r.status === "closed").length,
        });
        setBugCount({
          total: bugs.length,
          open: bugs.filter((b) => b.status === "open" || b.status === "confirmed" || b.status === "fixing").length,
          resolved: bugs.filter((b) => b.status === "resolved" || b.status === "closed").length,
        });
      } catch {
        // 静默处理
      } finally {
        setLoading(false);
      }
    })();
  }, [productId]);

  if (loading) return <div className="loading-state">加载中...</div>;

  const activeVersion = versions.find((v) => v.status === "developing") || versions[0];

  return (
    <div data-testid="page-product-dashboard">
      {product.description && (
        <p className="page-subtitle">{product.description}</p>
      )}

      <div className="stats mb-24">
        <div className="stat">项目数: {projects.length}</div>
        <div className="stat">版本数: {versions.length}</div>
        <div className="stat">
          需求: {reqCount.total} (进行中 {reqCount.open} / 完成 {reqCount.done})
        </div>
        <div className="stat">
          Bug: {bugCount.total} (待处理 {bugCount.open} / 已解决 {bugCount.resolved})
        </div>
      </div>

      {activeVersion && (
        <div
          className="card mb-16"
          style={{ cursor: "pointer" }}
          onClick={() => navigate(`/products/${productId}/versions/${activeVersion.id}/overview`)}
        >
          <h3>当前版本</h3>
          <div className="flex-center gap-16">
            <span className="text-bold">{activeVersion.version_name}</span>
            <span className="agent-context-badge">{activeVersion.status}</span>
            {activeVersion.release_date && (
              <span className="text-caption text-muted">
                发布日期: {activeVersion.release_date}
              </span>
            )}
          </div>
        </div>
      )}

      <div className="card">
        <h3>关联项目</h3>
        {projects.length === 0 ? (
          <div className="text-muted">暂无项目</div>
        ) : (
          <div className="list-col">
            {projects.map((p) => (
              <div
                key={p.id}
                className="flex-center gap-12"
                style={{ cursor: "pointer" }}
                onClick={() => navigate(`/products/${productId}/projects/${p.id}`)}
              >
                <span className="text-bold">{p.name}</span>
                <span className="text-caption text-muted">{p.repo_path}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
