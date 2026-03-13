import { useEffect, useState } from "react";
import { NavLink, Outlet, useNavigate, useOutletContext, useParams } from "react-router-dom";
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
  const navigate = useNavigate();
  const productId = pid ? Number(pid) : NaN;
  const [product, setProduct] = useState<Product | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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
    loadProduct();
  }, [productId]);

  if (!Number.isFinite(productId)) return <div className="result error">无效产品</div>;
  if (loading) return <div className="loading-state">加载中...</div>;
  if (error || !product) return <div className="result error">{error ?? "产品不存在"}</div>;

  return (
    <div data-testid="page-product-layout" style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <div style={{ flexShrink: 0 }}>
        <button type="button" className="secondary" onClick={() => navigate("/products")}>
          返回产品列表
        </button>
        <h2 className="page-title mt-16">
          {product.name}
          {product.code && (
            <span className="text-caption text-muted" style={{ marginLeft: 8 }}>
              [{product.code}]
            </span>
          )}
        </h2>

        <nav role="tablist" className="cockpit-tabs mb-16">
          <NavLink to="dashboard" className={({ isActive }) => `cockpit-tab ${isActive ? "active" : ""}`} role="tab">
            仪表盘
          </NavLink>
          <NavLink to="projects" className={({ isActive }) => `cockpit-tab ${isActive ? "active" : ""}`} role="tab">
            项目
          </NavLink>
          <NavLink to="versions" className={({ isActive }) => `cockpit-tab ${isActive ? "active" : ""}`} role="tab">
            版本
          </NavLink>
          <NavLink to="reports" className={({ isActive }) => `cockpit-tab ${isActive ? "active" : ""}`} role="tab">
            报告
          </NavLink>
        </nav>
      </div>

      <div style={{ flex: 1, minHeight: 0, overflow: "auto" }}>
        <Outlet context={{ productId, product, reloadProduct: loadProduct }} />
      </div>
    </div>
  );
}
