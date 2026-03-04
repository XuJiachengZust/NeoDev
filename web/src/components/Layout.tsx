import { useState } from "react";
import { Outlet } from "react-router-dom";
import { AgentPanel } from "./AgentPanel";

export function Layout() {
  const [agentCollapsed, setAgentCollapsed] = useState(false);
  return (
    <div className="app-shell" data-testid="app-shell">
      <header className="app-topbar">
        <div className="app-brand">NeoDev</div>
      </header>
      <div className="app-main-wrap">
        <main className="app-main">
          <Outlet />
        </main>
        <AgentPanel
          collapsed={agentCollapsed}
          onToggle={() => setAgentCollapsed((prev) => !prev)}
        />
      </div>
    </div>
  );
}
