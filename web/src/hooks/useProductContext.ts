import { useMatch } from "react-router-dom";

/**
 * 从当前路由解析产品上下文（产品 ID 和路由 hint）。
 * 在产品页面下使用，用于 Agent 会话解析。
 */
export function useProductContext(): {
  productId: number | null;
  routeHint: string;
} {
  const dashMatch = useMatch("/products/:productId/dashboard");
  const projMatch = useMatch("/products/:productId/projects");
  const projDetailMatch = useMatch("/products/:productId/projects/:projectId");
  const verMatch = useMatch("/products/:productId/versions");
  const verOverviewMatch = useMatch("/products/:productId/versions/:versionId/overview");
  const verReqMatch = useMatch("/products/:productId/versions/:versionId/requirements");
  const verBugMatch = useMatch("/products/:productId/versions/:versionId/bugs");
  const verDetailMatch = useMatch("/products/:productId/versions/:versionId");
  const baseMatch = useMatch("/products/:productId");

  const match = dashMatch || projMatch || projDetailMatch || verMatch || verOverviewMatch || verReqMatch || verBugMatch || verDetailMatch || baseMatch;
  if (!match) return { productId: null, routeHint: "default" };

  const productId = match.params.productId ? Number(match.params.productId) : null;

  if (dashMatch) return { productId, routeHint: "product_dashboard" };
  if (projMatch || projDetailMatch) return { productId, routeHint: "product_projects" };
  if (verOverviewMatch || verMatch || verDetailMatch) return { productId, routeHint: "product_versions" };
  if (verReqMatch) return { productId, routeHint: "product_requirements" };
  if (verBugMatch) return { productId, routeHint: "product_bugs" };

  return { productId, routeHint: "product_dashboard" };
}
