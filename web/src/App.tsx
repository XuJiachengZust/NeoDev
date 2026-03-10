import { Routes, Route, Navigate } from "react-router-dom";
import { Layout } from "./components/Layout";
import { CockpitLayout } from "./components/CockpitLayout";
import { GraphBuildPage } from "./pages/GraphBuildPage";
import { MainWorkflowPage } from "./pages/MainWorkflowPage";
import { ImpactPage } from "./pages/ImpactPage";
import { RepoParsePage } from "./pages/RepoParsePage";
import { ProductsPage } from "./pages/ProductsPage";
import { ProductLayoutPage } from "./pages/product/ProductLayoutPage";
import { ProductDashboardPage } from "./pages/product/ProductDashboardPage";
import { ProductProjectsPage } from "./pages/product/ProductProjectsPage";
import { ProductProjectDetailPage } from "./pages/product/ProductProjectDetailPage";
import { ProductVersionsPage } from "./pages/product/ProductVersionsPage";
import { ProductVersionWorkspacePage } from "./pages/product/ProductVersionWorkspacePage";
import { ProductVersionOverviewPage } from "./pages/product/ProductVersionOverviewPage";
import { ProductRequirementsPage } from "./pages/product/ProductRequirementsPage";
import { ProductBugsPage } from "./pages/product/ProductBugsPage";
import "./App.css";

function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<ProductsPage />} />
        <Route path="/onboard" element={<Navigate to="/products" replace />} />
        <Route path="/graph-build" element={<GraphBuildPage />} />
        <Route path="/cockpit" element={<CockpitLayout />}>
          <Route index element={<Navigate to="requirements" replace />} />
          <Route path="requirements" element={<MainWorkflowPage />} />
          <Route path="impact" element={<ImpactPage />} />
        </Route>
        <Route path="/products" element={<ProductsPage />} />
        <Route path="/products/:productId" element={<ProductLayoutPage />}>
          <Route index element={<Navigate to="dashboard" replace />} />
          <Route path="dashboard" element={<ProductDashboardPage />} />
          <Route path="projects" element={<ProductProjectsPage />} />
          <Route path="projects/:projectId" element={<ProductProjectDetailPage />} />
          <Route path="versions" element={<ProductVersionsPage />} />
          <Route path="versions/:versionId" element={<ProductVersionWorkspacePage />}>
            <Route index element={<Navigate to="overview" replace />} />
            <Route path="overview" element={<ProductVersionOverviewPage />} />
            <Route path="requirements" element={<ProductRequirementsPage />} />
            <Route path="bugs" element={<ProductBugsPage />} />
          </Route>
        </Route>
        {/* 旧路由重定向 */}
        <Route path="/projects" element={<Navigate to="/products" replace />} />
        <Route path="/projects/*" element={<Navigate to="/products" replace />} />
        <Route path="/impact" element={<Navigate to="/cockpit/impact" replace />} />
        <Route path="/repos" element={<RepoParsePage />} />
      </Route>
    </Routes>
  );
}

export default App;
