import { useLocation } from "react-router-dom";

export type AgentState = "welcome" | "parsing" | "suggestion" | "alert" | "default";

interface AgentPanelProps {
  collapsed: boolean;
  onToggle: () => void;
  /** 可选：由父级传入的上下文话术，覆盖基于路由的占位 */
  message?: string;
  state?: AgentState;
}

const routePlaceholders: Record<string, { text: string; state: AgentState }> = {
  "/": {
    text: "欢迎使用 NeoDev。从左侧选择「项目与仓库初始化」开始接入资产，或进入「版本驾驶舱」查看需求与影响面。",
    state: "welcome",
  },
  "/onboard": {
    text: "填写项目名称与 Git 仓库地址并点击「校验并接入资产」。接入成功后我会输出迎新话术。",
    state: "welcome",
  },
  "/graph-build": {
    text: "选择分支后点击「启动图谱重构」。解析过程中我会流式播报进度。",
    state: "parsing",
  },
  "/cockpit/requirements": {
    text: "在需求树中选中需求可查看详情与关联提交。点击「+ 关联提交」可绑定 Commit，我会根据需求状态给出智能建议。",
    state: "suggestion",
  },
  "/cockpit/impact": {
    text: "在时间轴中选择提交可查看动态影响面拓扑图与业务归属。我会输出根因与风险提示。",
    state: "alert",
  },
  "/projects": {
    text: "管理项目列表。可新建、编辑、删除项目，或进入项目详情管理版本与解析。",
    state: "default",
  },
};

function getPlaceholder(pathname: string): { text: string; state: AgentState } {
  if (routePlaceholders[pathname]) return routePlaceholders[pathname];
  if (pathname.startsWith("/cockpit/")) {
    if (pathname.includes("impact")) return routePlaceholders["/cockpit/impact"];
    return routePlaceholders["/cockpit/requirements"];
  }
  if (pathname.startsWith("/projects/")) return { text: "项目详情与版本管理。", state: "default" };
  if (pathname === "/repos") return { text: "仓库解析与分支拉取。", state: "default" };
  return routePlaceholders["/"];
}

export function AgentPanel({ collapsed, onToggle, message, state: stateOverride }: AgentPanelProps) {
  const location = useLocation();
  const { text: defaultText, state: routeState } = getPlaceholder(location.pathname);
  const state = stateOverride ?? routeState;
  const displayText = message ?? defaultText;

  return (
    <div className={`app-agent-wrap ${collapsed ? "collapsed" : ""}`} data-testid="agent-panel">
      <button
        type="button"
        className="app-agent-toggle"
        onClick={onToggle}
        aria-label={collapsed ? "展开 Agent" : "收起 Agent"}
        data-testid="agent-toggle"
      >
        {collapsed ? "◀" : "▶"}
      </button>
      {!collapsed && (
        <div className="app-agent-panel">
          <div className="agent-message insight" style={{ marginBottom: 8 }}>
            NeoDev Agent
          </div>
          <p className={`agent-message ${state === "alert" ? "alert" : state === "suggestion" ? "insight" : ""}`}>
            {displayText}
          </p>
        </div>
      )}
    </div>
  );
}
