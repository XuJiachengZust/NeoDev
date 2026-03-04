import { Routes, Route, Navigate } from "react-router-dom";
import { Layout } from "./components/Layout";
import { CockpitLayout } from "./components/CockpitLayout";
import { OnboardPage } from "./pages/OnboardPage";
import { GraphBuildPage } from "./pages/GraphBuildPage";
import { MainWorkflowPage } from "./pages/MainWorkflowPage";
import { ProjectsPage } from "./pages/ProjectsPage";
import { ImpactPage } from "./pages/ImpactPage";
import { RepoParsePage } from "./pages/RepoParsePage";
import { ProjectLayoutPage } from "./pages/project/ProjectLayoutPage";
import { ProjectRepoPage } from "./pages/project/ProjectRepoPage";
import { ProjectVersionsPage } from "./pages/project/ProjectVersionsPage";
import { ProjectCommitsPage } from "./pages/project/ProjectCommitsPage";
import { ProjectRequirementsPage } from "./pages/project/ProjectRequirementsPage";
import "./App.css";

function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<ProjectsPage />} />
        <Route path="/onboard" element={<OnboardPage />} />
        <Route path="/graph-build" element={<GraphBuildPage />} />
        <Route path="/cockpit" element={<CockpitLayout />}>
          <Route index element={<Navigate to="requirements" replace />} />
          <Route path="requirements" element={<MainWorkflowPage />} />
          <Route path="impact" element={<ImpactPage />} />
        </Route>
        <Route path="/projects" element={<ProjectsPage />} />
        <Route path="/projects/:id" element={<ProjectLayoutPage />}>
          <Route index element={<Navigate to="repo" replace />} />
          <Route path="repo" element={<ProjectRepoPage />} />
          <Route path="versions" element={<ProjectVersionsPage />} />
          <Route path="versions/:versionId/commits" element={<ProjectCommitsPage />} />
          <Route path="versions/:versionId/requirements" element={<ProjectRequirementsPage />} />
        </Route>
        <Route path="/impact" element={<Navigate to="/cockpit/impact" replace />} />
        <Route path="/repos" element={<RepoParsePage />} />
      </Route>
    </Routes>
  );
}

export default App;
