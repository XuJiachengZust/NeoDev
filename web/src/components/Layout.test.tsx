import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { Layout } from "./Layout";

function renderWithRouter(initialEntries: string[] = ["/"]) {
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<div data-testid="page-home">主流程页</div>} />
          <Route path="/projects" element={<div data-testid="page-projects">项目管理</div>} />
        </Route>
      </Routes>
    </MemoryRouter>
  );
}

describe("Layout", () => {
  it("renders shell and brand", () => {
    renderWithRouter();
    expect(screen.getByTestId("app-shell")).toBeInTheDocument();
    expect(screen.getByText("NeoDev")).toBeInTheDocument();
  });

  it("renders outlet for current route", () => {
    renderWithRouter(["/"]);
    expect(screen.getByTestId("page-home")).toHaveTextContent("主流程页");
  });
});
