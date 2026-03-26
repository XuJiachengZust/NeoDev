import { describe, it, expect, beforeAll, afterEach, afterAll } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
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
  it("shows explicit version feedback after saving and refreshes diff path", async () => {
    let docVersions = [{ version: 1 }, { version: 2 }];
    let currentDoc = {
      content: "# draft\n\nupdated",
      version: 2,
      generated_by: "manual",
      updated_at: "2026-03-27T00:00:00Z",
    };

    server.use(
      http.get(`${API_BASE}/products/1/requirements/1/doc`, () => HttpResponse.json(currentDoc)),
      http.get(`${API_BASE}/products/1/requirements/1/doc/versions`, () => HttpResponse.json(docVersions)),
      http.put(`${API_BASE}/products/1/requirements/1/doc`, async () => {
        currentDoc = {
          ...currentDoc,
          content: "# draft\n\nupdated again",
          version: 3,
          updated_at: "2026-03-27T00:05:00Z",
        };
        docVersions = [{ version: 1 }, { version: 2 }, { version: 3 }];
        return HttpResponse.json(currentDoc);
      }),
    );

    renderPage();

    const editor = await screen.findByRole("textbox");
    fireEvent.change(editor, { target: { value: "# draft\n\nupdated again" } });

    await waitFor(() => {
      expect(screen.getAllByText("未保存").length).toBeGreaterThan(0);
    });

    fireEvent.click(screen.getByRole("button", { name: "保存" }));

    await waitFor(() => {
      expect(screen.getAllByText("保存完成 · 已生成 v3").length).toBeGreaterThan(0);
    });

    expect(screen.getAllByText("已保存为 v3").length).toBeGreaterThan(0);
    expect(screen.getByText("当前 v3")).toBeInTheDocument();
  });

  it("disables diff entry when there are not enough versions and keeps guidance visible", async () => {
    server.use(
      http.get(`${API_BASE}/products/1/requirements/1/doc`, () => HttpResponse.json({
        content: "# only one version",
        version: 1,
        generated_by: "manual",
        updated_at: "2026-03-27T00:00:00Z",
      })),
      http.get(`${API_BASE}/products/1/requirements/1/doc/versions`, () => HttpResponse.json([{ version: 1 }])),
    );

    renderPage();

    await screen.findByDisplayValue("# only one version");
    expect(screen.getByRole("button", { name: "变更" })).toBeDisabled();
    expect(screen.getAllByText("当前版本为 v1，建议先看“当前稿 vs 上一版本”差异，再决定是否继续编辑。").length).toBeGreaterThan(0);
  });

  it("shows empty-doc initial state when doc endpoint returns 404", async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getAllByText("当前还没有需求文档").length).toBeGreaterThan(0);
    });

    expect(screen.getAllByRole("button", { name: "生成文档" }).length).toBeGreaterThan(0);
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
    expect(screen.getAllByRole("button", { name: "重试加载" }).length).toBeGreaterThan(0);
  });

  it("restores running generation state after refresh and surfaces progress panel", async () => {
    server.use(
      http.get(`${API_BASE}/products/1/requirements/1/doc/generation-status`, () => HttpResponse.json({ generation_status: "running", generation_error: null })),
    );

    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("doc-status-card")).toHaveAttribute("data-status", "generating");
    });

    expect(screen.getByTestId("generation-notice")).toHaveTextContent("页面已恢复后台生成状态");
    expect(screen.getByTestId("generation-steps-panel")).toBeInTheDocument();
    expect(screen.getByText("文档生成中（后台运行）…")).toBeInTheDocument();
  });
});
