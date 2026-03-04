import { describe, it, expect, beforeAll, afterEach, afterAll } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { handlers } from "../test/mocks/handlers";
import { setupServer } from "msw/node";
import { ImpactPage } from "./ImpactPage";

const server = setupServer(...handlers);

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function renderPage() {
  return render(
    <MemoryRouter>
      <ImpactPage />
    </MemoryRouter>
  );
}

describe("ImpactPage", () => {
  it("loads projects and shows impact list for selected project", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByRole("option", { name: "P1" })).toBeInTheDocument();
    });
    expect(screen.getByTestId("impact-list")).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByTestId("impact-item-1")).toHaveTextContent("pending");
    });
  });

  it("shows detail when 详情 clicked", async () => {
    const user = userEvent.setup();
    renderPage();
    await waitFor(() => screen.getByTestId("impact-detail-1"));
    await user.click(screen.getByTestId("impact-detail-1"));
    await waitFor(() => {
      expect(screen.getByTestId("impact-detail-panel")).toHaveTextContent("分析详情");
      expect(screen.getByTestId("impact-detail-panel")).toHaveTextContent("pending");
    });
  });
});
