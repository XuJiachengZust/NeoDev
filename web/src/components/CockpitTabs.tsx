import { Link, useLocation } from "react-router-dom";

export function CockpitTabs() {
  const location = useLocation();
  const base = "/cockpit";

  return (
    <nav role="tablist" className="cockpit-tabs" data-testid="cockpit-tabs">
      <Link
        to={`${base}/requirements`}
        className={`cockpit-tab ${location.pathname === `${base}/requirements` ? "active" : ""}`}
        role="tab"
      >
        需求流转矩阵
      </Link>
      <Link
        to={`${base}/impact`}
        className={`cockpit-tab ${location.pathname === `${base}/impact` ? "active" : ""}`}
        role="tab"
      >
        提交与影响面分析
      </Link>
    </nav>
  );
}
