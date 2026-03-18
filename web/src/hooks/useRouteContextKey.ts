import { useLocation } from "react-router-dom";

/**
 * 根据当前路由返回 route_context_key 和 project_id。
 * 与后端 agent_profiles.py 中的 ROUTE_CONTEXT_MAP 对应。
 */
export function useRouteContextKey(): {
  routeContextKey: string;
  projectId: number | null;
} {
  const location = useLocation();
  const pathname = location.pathname;

  // 产品内项目详情
  const productProjectMatch = pathname.match(/^\/products\/\d+\/projects\/(\d+)/);
  if (productProjectMatch) {
    return { routeContextKey: "product_projects", projectId: Number(productProjectMatch[1]) };
  }

  // 需求文档编辑
  if (pathname.match(/^\/products\/\d+\/requirements\/\d+\/doc/)) {
    return { routeContextKey: "product_requirement_doc", projectId: null };
  }

  // 产品内版本级需求
  if (pathname.match(/^\/products\/\d+\/versions\/\d+\/requirements/)) {
    return { routeContextKey: "product_requirements", projectId: null };
  }

  // 产品内版本级 Bug
  if (pathname.match(/^\/products\/\d+\/versions\/\d+\/bugs/)) {
    return { routeContextKey: "product_bugs", projectId: null };
  }

  // 产品内版本总览
  if (pathname.match(/^\/products\/\d+\/versions\/\d+/)) {
    return { routeContextKey: "product_versions", projectId: null };
  }

  // 产品内版本列表
  if (pathname.match(/^\/products\/\d+\/versions/)) {
    return { routeContextKey: "product_versions", projectId: null };
  }

  // 产品内项目列表
  if (pathname.match(/^\/products\/\d+\/projects/)) {
    return { routeContextKey: "product_projects", projectId: null };
  }

  // 产品仪表盘
  if (pathname.match(/^\/products\/\d+\/dashboard/)) {
    return { routeContextKey: "product_dashboard", projectId: null };
  }

  // 产品根
  if (pathname.match(/^\/products\/\d+/)) {
    return { routeContextKey: "product_dashboard", projectId: null };
  }

  // 驾驶舱
  if (pathname.startsWith("/cockpit/impact")) {
    return { routeContextKey: "cockpit_impact", projectId: null };
  }
  if (pathname.startsWith("/cockpit")) {
    return { routeContextKey: "cockpit_requirements", projectId: null };
  }

  // 顶层页面
  if (pathname === "/onboard") {
    return { routeContextKey: "onboard", projectId: null };
  }
  if (pathname === "/graph-build") {
    return { routeContextKey: "graph_build", projectId: null };
  }

  return { routeContextKey: "default", projectId: null };
}
