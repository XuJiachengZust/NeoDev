import { Link } from "react-router-dom";

export function HomePage() {
  return (
    <div data-testid="page-home">
      <h1 className="page-title">NeoDev 工作台</h1>
      <div className="card" style={{ maxWidth: 560 }}>
        <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
          <li style={{ marginBottom: 16 }}>
            <Link to="/onboard" style={{ color: "var(--color-primary)" }}>
              创建项目并添加仓库
            </Link>
          </li>
          <li style={{ marginBottom: 16 }}>
            <Link to="/projects" style={{ color: "var(--color-primary)" }}>
              项目管理
            </Link>
          </li>
          <li style={{ marginBottom: 16 }}>
            <Link to="/graph-build" style={{ color: "var(--color-primary)" }}>
              版本基线与图谱构建
            </Link>
          </li>
          <li>
            <Link to="/cockpit/impact" style={{ color: "var(--color-primary)" }}>
              影响面结果
            </Link>
          </li>
        </ul>
      </div>
    </div>
  );
}
