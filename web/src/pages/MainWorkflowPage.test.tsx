import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { MainWorkflowPage } from "./MainWorkflowPage";

function renderPage() {
  return render(
    <MemoryRouter>
      <MainWorkflowPage />
    </MemoryRouter>
  );
}

describe("MainWorkflowPage", () => {
  it("renders page title", () => {
    renderPage();
    expect(screen.getByTestId("page-main-workflow")).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 2 })).toHaveTextContent("需求流转矩阵");
  });
});
