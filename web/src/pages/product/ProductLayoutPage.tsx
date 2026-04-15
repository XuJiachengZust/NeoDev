import { useEffect, useState } from "react";
import { NavLink, Outlet, useOutletContext, useParams } from "react-router-dom";
import { getProduct, type Product } from "../../api/client";

export interface ProductPageContext {
  productId: number;
  product: Product;
  reloadProduct: () => Promise<void>;
}

export function useProductPageContext(): ProductPageContext {
  return useOutletContext<ProductPageContext>();
}

export function ProductLayoutPage() {
  const { productId: pid } = useParams<{ productId: string }>();
  const productId = pid ? Number(pid) : NaN;
  const [product, setProduct] = useState<Product | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  const loadProduct = async () => {
    if (!Number.isFinite(productId)) return;
    setLoading(true);
    setError(null);
    try {
      const row = await getProduct(productId);
      setProduct(row);
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载产品失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadProduct();
  }, [productId]);

  if (!Number.isFinite(productId)) return <div className="result error">无效产品</div>;
  if (loading) return <div className="loading-state">加载中...</div>;
  if (error || !product) return <div className="result error">{error ?? "产品不存在"}</div>;

  return (
    <div data-testid="page-product-layout" className="product-shell">
      <aside className={`product-shell-sidebar${sidebarCollapsed ? " is-collapsed" : ""}`}>
        <div className="product-shell-sidebar-head">
          <div className="product-shell-brand">
            <span className="product-shell-kicker">Product</span>
            {!sidebarCollapsed && (
              <>
                <span className="product-shell-title" title={product.name}>{product.name}</span>
                {product.code && <span className="product-shell-code">{product.code}</span>}
              </>
            )}
          </div>
          <button
            type="button"
            className="product-shell-collapse"
            onClick={() => setSidebarCollapsed((value) => !value)}
            aria-label={sidebarCollapsed ? "展开产品导航" : "收起产品导航"}
            title={sidebarCollapsed ? "展开产品导航" : "收起产品导航"}
          >
            {sidebarCollapsed ? "»" : "«"}
          </button>
        </div>

        <nav className="product-shell-nav" aria-label="产品导航">
          <NavLink to="dashboard" className={({ isActive }) => `product-shell-link ${isActive ? "active" : ""}`}>
            <span className="product-shell-link-mark">D</span>
            {!sidebarCollapsed && <span>仪表盘</span>}
          </NavLink>
          <NavLink to="projects" className={({ isActive }) => `product-shell-link ${isActive ? "active" : ""}`}>
            <span className="product-shell-link-mark">P</span>
            {!sidebarCollapsed && <span>项目</span>}
          </NavLink>
          <NavLink to="versions" className={({ isActive }) => `product-shell-link ${isActive ? "active" : ""}`}>
            <span className="product-shell-link-mark">V</span>
            {!sidebarCollapsed && <span>版本</span>}
          </NavLink>
          <NavLink to="reports" className={({ isActive }) => `product-shell-link ${isActive ? "active" : ""}`}>
            <span className="product-shell-link-mark">R</span>
            {!sidebarCollapsed && <span>报告</span>}
          </NavLink>
        </nav>
      </aside>

      <div className="product-shell-main">
        <div className="product-shell-main-scroll">
          <Outlet context={{ productId, product, reloadProduct: loadProduct }} />
        </div>
      </div>
    </div>
  );
}
