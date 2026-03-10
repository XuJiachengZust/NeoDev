import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { AgentSessionProvider } from "../contexts/AgentSessionContext";
import { AgentPanel } from "./AgentPanel";

export function Layout() {
  const [agentCollapsed, setAgentCollapsed] = useState(false);
  return (
    <AgentSessionProvider>
      <div className="app-shell" data-testid="app-shell">
        <header className="app-topbar">
          <NavLink to="/" className="app-brand" style={{ textDecoration: "none" }}>NeoDev</NavLink>
          <nav className="app-topbar-nav">
            <NavLink to="/products" className={({ isActive }) => `topbar-link ${isActive ? "active" : ""}`}>
              产品
            </NavLink>
          </nav>
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
    </AgentSessionProvider>
  );
}
