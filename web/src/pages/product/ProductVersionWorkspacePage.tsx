import { useEffect, useState } from "react";
import { NavLink, Outlet, useNavigate, useOutletContext, useParams } from "react-router-dom";
import { useProductPageContext, type ProductPageContext } from "./ProductLayoutPage";
import { getProductVersion, type ProductVersion } from "../../api/client";

export interface VersionPageContext extends ProductPageContext {
  versionId: number;
  version: ProductVersion;
  reloadVersion: () => Promise<void>;
}

export function useVersionPageContext(): VersionPageContext {
  return useOutletContext<VersionPageContext>();
}

export function ProductVersionWorkspacePage() {
  const ctx = useProductPageContext();
  const { productId } = ctx;
  const { versionId: vid } = useParams<{ versionId: string }>();
  const navigate = useNavigate();
  const versionId = vid ? Number(vid) : NaN;

  const [version, setVersion] = useState<ProductVersion | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadVersion = async () => {
    if (!Number.isFinite(versionId)) return;
    setLoading(true);
    setError(null);
    try {
      setVersion(await getProductVersion(productId, versionId));
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载版本失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadVersion();
  }, [productId, versionId]);

  if (!Number.isFinite(versionId)) return <div className="result error">无效版本</div>;
  if (loading) return <div className="loading-state">加载中...</div>;
  if (error || !version) return <div className="result error">{error ?? "版本不存在"}</div>;

  return (
    <div data-testid="page-version-workspace">
      <button type="button" className="secondary" onClick={() => navigate(`/products/${productId}/versions`)}>
        返回版本列表
      </button>

      <div className="mt-16 mb-16">
        <h3 style={{ margin: 0 }}>{version.version_name}</h3>
        {version.description && (
          <p className="text-muted mt-4">{version.description}</p>
        )}
      </div>

      <nav role="tablist" className="cockpit-tabs mb-16">
        <NavLink to="overview" className={({ isActive }) => `cockpit-tab ${isActive ? "active" : ""}`} role="tab">
          总览
        </NavLink>
        <NavLink to="requirements" className={({ isActive }) => `cockpit-tab ${isActive ? "active" : ""}`} role="tab">
          需求
        </NavLink>
        <NavLink to="bugs" className={({ isActive }) => `cockpit-tab ${isActive ? "active" : ""}`} role="tab">
          Bug
        </NavLink>
      </nav>

      <Outlet context={{ ...ctx, versionId, version, reloadVersion: loadVersion } satisfies VersionPageContext} />
    </div>
  );
}
