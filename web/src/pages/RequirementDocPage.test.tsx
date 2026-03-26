import { describe, it, expect, beforeAll, afterEach, afterAll } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { AgentSessionProvider } from "../contexts/AgentSessionContext";
import { RequirementDocPage } from "./RequirementDocPage";

const API_BASE = "/api";

const requirement = {
  id: 1,
  product_id: 1,
  parent_id: null,
  level: "story",
  title: "用户登录",
  description: null,
  external_id: null,
  status: "draft",
  priority: "high",
  assignee: null,
  version_id: 1,
  sort_order: 1,
  has_doc: false,
};

const server = setupServer(
  http.get(`${API_BASE}/products/1/requirements/1`, () => HttpResponse.json(requirement)),
  http.get(`${API_BASE}/products/1/requirements/tree`, () => HttpResponse.json([requirement])),
  http.get(`${API_BASE}/products/1/requirements/1/doc/versions`, () => HttpResponse.json([])),
  http.get(`${API_BASE}/products/1/requirements/1/doc/generation-status`, () => HttpResponse.json({ generation_status: null, generation_error: null })),
  http.get(`${API_BASE}/products/1/requirements/1/doc`, () => HttpResponse.json({ detail: "Not found" }, { status: 404 })),
);

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function renderPage() {
  return render(
    <AgentSessionProvider>
      <MemoryRouter initialEntries={["/products/1/requirements/1/doc"]}>
        <Routes>
          <Route path="/products/:productId/requirements/:requirementId/doc" element={<RequirementDocPage />} />
        </Routes>
      </MemoryRouter>
    </AgentSessionProvider>
  );
}

describe("RequirementDocPage", () => {
  it("shows empty-doc initial state when doc endpoint returns 404", async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getAllByText("当前还没有需求文档").length).toBeGreaterThan(0);
    });

    expect(screen.getByRole("button", { name: "生成文档" })).toBeInTheDocument();
    expect(screen.getByPlaceholderText("从这里开始写第一版需求文档…")).toBeInTheDocument();
  });

  it("shows load failure state instead of empty editor when doc endpoint errors", async () => {
    server.use(
      http.get(`${API_BASE}/products/1/requirements/1/doc`, () => HttpResponse.json({ detail: "boom" }, { status: 500 })),
    );

    renderPage();

    await waitFor(() => {
      expect(screen.getAllByText("文档加载失败").length).toBeGreaterThan(0);
    });

    expect(screen.getByText("文档读取失败")).toBeInTheDocument();
    expect(screen.queryByPlaceholderText("从这里开始写第一版需求文档…")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "重试加载" })).toBeInTheDocument();
  });
});
