import { describe, it, expect, beforeAll, afterEach, afterAll } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { handlers } from "../test/mocks/handlers";
import { setupServer } from "msw/node";
import { ProjectDetailPage } from "./ProjectDetailPage";

const server = setupServer(...handlers);

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function renderPage(projectId: string) {
  return render(
    <MemoryRouter initialEntries={[`/projects/${projectId}`]}>
      <Routes>
        <Route path="/projects/:id" element={<ProjectDetailPage />} />
      </Routes>
    </MemoryRouter>
  );
}

describe("ProjectDetailPage", () => {
  it("loads project and versions", async () => {
    renderPage("1");
    await waitFor(() => {
      expect(screen.getByTestId("page-project-detail")).toBeInTheDocument();
    });
    expect(screen.getByRole("heading", { level: 2 })).toHaveTextContent("P1");
    expect(screen.getByTestId("project-detail-versions")).toHaveTextContent("main");
  });

  it("shows watch status", async () => {
    renderPage("1");
    await waitFor(() => {
      expect(screen.getByTestId("project-detail-watch")).toBeInTheDocument();
    });
    expect(screen.getByTestId("project-detail-watch")).toHaveTextContent("未启用");
  });

  it("submits new version form", async () => {
    const user = userEvent.setup();
    renderPage("1");
    await waitFor(() => screen.getByTestId("project-detail-version-submit"));
    const branchInput = screen.getByPlaceholderText("绑定分支（可选）");
    await user.type(branchInput, "develop");
    await user.click(screen.getByTestId("project-detail-version-submit"));
    await waitFor(() => {
      expect(screen.getByPlaceholderText("绑定分支（可选）")).toHaveValue("");
    });
  });

  it("sync commits button exists", async () => {
    renderPage("1");
    await waitFor(() => screen.getByTestId("project-detail-sync"));
    expect(screen.getByTestId("project-detail-sync")).toHaveTextContent("同步全部");
  });
});
