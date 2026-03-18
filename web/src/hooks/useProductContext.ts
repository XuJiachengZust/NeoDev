import { useMatch, useSearchParams } from "react-router-dom";

/**
 * 从当前路由解析产品上下文（产品 ID、版本 ID 和路由 hint）。
 * 在产品页面下使用，用于 Agent 会话解析。
 *
 * 版本 ID 优先从路由路径提取（版本子路由），其次从 URL 查询参数 ?versionId= 提取
 * （用于项目详情页等通过下拉框选择版本的场景）。
 */
export function useProductContext(): {
  productId: number | null;
  versionId: number | null;
  routeHint: string;
  requirementId: number | null;
} {
  const [searchParams] = useSearchParams();
  const dashMatch = useMatch("/products/:productId/dashboard");
  const projMatch = useMatch("/products/:productId/projects");
  const projDetailMatch = useMatch("/products/:productId/projects/:projectId");
  const verMatch = useMatch("/products/:productId/versions");
  const verOverviewMatch = useMatch("/products/:productId/versions/:versionId/overview");
  const verReqMatch = useMatch("/products/:productId/versions/:versionId/requirements");
  const verBugMatch = useMatch("/products/:productId/versions/:versionId/bugs");
  const verDetailMatch = useMatch("/products/:productId/versions/:versionId");
  const docMatch = useMatch("/products/:productId/requirements/:requirementId/doc");
  const baseMatch = useMatch("/products/:productId");

  const match = dashMatch || projMatch || projDetailMatch || verMatch || verOverviewMatch || verReqMatch || verBugMatch || verDetailMatch || docMatch || baseMatch;
  if (!match) return { productId: null, versionId: null, routeHint: "default", requirementId: null };

  const productId = match.params.productId ? Number(match.params.productId) : null;

  // 从版本子路由提取 versionId
  const versionMatch = verOverviewMatch || verReqMatch || verBugMatch || verDetailMatch;
  const versionId = versionMatch?.params.versionId ? Number(versionMatch.params.versionId) : null;

  // 从 URL 查询参数提取 versionId（用于项目详情页版本下拉框）
  const queryVersionId = searchParams.get("versionId");
  const queryVerId = queryVersionId ? Number(queryVersionId) : null;

  if (docMatch) {
    const reqId = docMatch.params.requirementId ? Number(docMatch.params.requirementId) : null;
    return { productId, versionId: queryVerId, routeHint: "product_requirement_doc", requirementId: reqId };
  }
  if (dashMatch) return { productId, versionId: null, routeHint: "product_dashboard", requirementId: null };
  if (projMatch || projDetailMatch) return { productId, versionId: queryVerId, routeHint: "product_projects", requirementId: null };
  if (verOverviewMatch || verMatch || verDetailMatch) return { productId, versionId, routeHint: "product_versions", requirementId: null };
  if (verReqMatch) return { productId, versionId, routeHint: "product_requirements", requirementId: null };
  if (verBugMatch) return { productId, versionId, routeHint: "product_bugs", requirementId: null };

  return { productId, versionId: null, routeHint: "product_dashboard", requirementId: null };
}
