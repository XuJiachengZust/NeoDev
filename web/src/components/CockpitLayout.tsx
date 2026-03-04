import { Outlet } from "react-router-dom";
import { CockpitTabs } from "./CockpitTabs";

export function CockpitLayout() {
  return (
    <div data-testid="cockpit-layout">
      <CockpitTabs />
      <Outlet />
    </div>
  );
}
