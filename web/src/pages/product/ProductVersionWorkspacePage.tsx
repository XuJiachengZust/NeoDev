import { useEffect, useState, type ReactNode } from "react";
import { NavLink, Outlet, useOutletContext, useParams } from "react-router-dom";
import { useProductPageContext, type ProductPageContext } from "./ProductLayoutPage";
import { getProductVersion, type ProductVersion } from "../../api/client";

export interface VersionPageContext extends ProductPageContext {
  versionId: number;
  version: ProductVersion;
  reloadVersion: () => Promise<void>;
  setHeaderActions: (actions: ReactNode | null) => void;
}

export function useVersionPageContext(): VersionPageContext {
  return useOutletContext<VersionPageContext>();
}

export function ProductVersionWorkspacePage() {
  const ctx = useProductPageContext();
  const { productId, product } = ctx;
  const { versionId: vid } = useParams<{ versionId: string }>();
  const versionId = vid ? Number(vid) : NaN;

  const [version, setVersion] = useState<ProductVersion | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [headerActions, setHeaderActions] = useState<ReactNode | null>(null);

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
    void loadVersion();
  }, [productId, versionId]);

  if (!Number.isFinite(versionId)) return <div className="result error">无效版本</div>;
  if (loading) return <div className="loading-state">加载中...</div>;
  if (error || !version) return <div className="result error">{error ?? "版本不存在"}</div>;

  return (
    <div data-testid="page-version-workspace" className="version-workspace">
      <header className="version-workspace-header">
        <div className="version-workspace-header-main">
          <div className="version-workspace-breadcrumbs">
            <span>{product.name}</span>
            <span>/</span>
            <span>版本</span>
            <span>/</span>
            <span className="version-workspace-breadcrumbs-current">{version.version_name}</span>
          </div>
          {version.description && <div className="version-workspace-description">{version.description}</div>}
        </div>
        <div className="version-workspace-versionmeta">
          <span className="version-workspace-chip">状态 {version.status}</span>
        </div>
      </header>

      <div className="version-workspace-toolbar">
        <nav role="tablist" className="version-workspace-tabs" aria-label="版本导航">
          <NavLink to="overview" className={({ isActive }) => `version-workspace-tab ${isActive ? "active" : ""}`} role="tab">
            总览
          </NavLink>
          <NavLink to="requirements" className={({ isActive }) => `version-workspace-tab ${isActive ? "active" : ""}`} role="tab">
            需求
          </NavLink>
          <NavLink to="bugs" className={({ isActive }) => `version-workspace-tab ${isActive ? "active" : ""}`} role="tab">
            Bug
          </NavLink>
        </nav>
        <div className="version-workspace-toolbar-actions">{headerActions}</div>
      </div>

      <div className="version-workspace-content">
        <Outlet context={{ ...ctx, versionId, version, reloadVersion: loadVersion, setHeaderActions } satisfies VersionPageContext} />
      </div>
    </div>
  );
}
