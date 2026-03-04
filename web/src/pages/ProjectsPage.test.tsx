import { describe, it, expect, beforeAll, afterEach, afterAll } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { ProjectsPage } from "./ProjectsPage";

const API_BASE = "/api";

const defaultProject = {
  id: 1,
  name: "P1",
  repo_path: "/path/to/repo",
  created_at: "",
  watch_enabled: false,
  neo4j_database: null,
  neo4j_identifier: null,
};

let getProjectsResponse: unknown[] = [];

const server = setupServer(
  http.get(`${API_BASE}/projects`, () => HttpResponse.json(getProjectsResponse)),
  http.post(`${API_BASE}/projects`, async ({ request }) => {
    const body = (await request.json()) as { name: string; repo_path: string };
    return HttpResponse.json(
      { id: 1, ...body, created_at: "2024-01-01T00:00:00Z", watch_enabled: false, neo4j_database: null, neo4j_identifier: null },
      { status: 201 }
    );
  }),
  http.patch(`${API_BASE}/projects/:id`, async ({ request, params }) => {
    const body = (await request.json()) as { name?: string };
    return HttpResponse.json({ id: Number(params.id), name: body.name ?? "P1", repo_path: "/path", created_at: "", watch_enabled: false, neo4j_database: null, neo4j_identifier: null });
  }),
  http.delete(`${API_BASE}/projects/:id`, () => new HttpResponse(null, { status: 204 }))
);

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => {
  server.resetHandlers();
  getProjectsResponse = [];
});
afterAll(() => server.close());

function renderPage() {
  return render(
    <MemoryRouter>
      <ProjectsPage />
    </MemoryRouter>
  );
}

describe("ProjectsPage", () => {
  it("shows 暂无项目 when list is empty", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId("projects-empty")).toHaveTextContent("暂无项目");
    });
  });

  it("shows list and 新建项目 button when list has items", async () => {
    getProjectsResponse = [defaultProject];
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId("projects-list")).toBeInTheDocument();
    });
    expect(screen.getByTestId("project-1")).toHaveTextContent("P1");
    expect(screen.getByTestId("project-1")).toHaveTextContent("/path/to/repo");
    expect(screen.getByTestId("projects-new-btn")).toHaveTextContent("新建项目");
  });

  it("opens form on 新建项目 and POSTs on submit", async () => {
    const user = userEvent.setup();
    renderPage();
    await waitFor(() => screen.getByTestId("projects-new-btn"));
    await user.click(screen.getByTestId("projects-new-btn"));
    expect(screen.getByTestId("project-form")).toBeInTheDocument();
    await user.type(screen.getByLabelText("名称"), "NewProj");
    await user.type(screen.getByLabelText("仓库路径"), "/repo/path");
    await user.click(screen.getByTestId("project-form-submit"));
    await waitFor(() => {
      expect(screen.queryByTestId("project-form")).not.toBeInTheDocument();
    });
  });

  it("opens edit form and PATCHes on submit", async () => {
    const user = userEvent.setup();
    getProjectsResponse = [{ ...defaultProject, repo_path: "/path" }];
    renderPage();
    await waitFor(() => screen.getByTestId("project-edit-1"));
    await user.click(screen.getByTestId("project-edit-1"));
    expect(screen.getByTestId("project-form")).toBeInTheDocument();
    expect(screen.getByLabelText("名称")).toHaveValue("P1");
    await user.clear(screen.getByLabelText("名称"));
    await user.type(screen.getByLabelText("名称"), "P1-renamed");
    await user.click(screen.getByTestId("project-form-submit"));
    await waitFor(() => {
      expect(screen.queryByTestId("project-form")).not.toBeInTheDocument();
    });
  });

  it("delete confirm and DELETE removes item", async () => {
    const user = userEvent.setup();
    getProjectsResponse = [{ ...defaultProject, repo_path: "/path" }];
    renderPage();
    await waitFor(() => screen.getByTestId("project-delete-1"));
    await user.click(screen.getByTestId("project-delete-1"));
    expect(screen.getByTestId("project-delete-confirm-1")).toBeInTheDocument();
    getProjectsResponse = [];
    await user.click(screen.getByTestId("project-delete-confirm-1"));
    await waitFor(() => {
      expect(screen.getByTestId("projects-empty")).toHaveTextContent("暂无项目");
    });
  });
});
