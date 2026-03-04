import { describe, it, expect, beforeAll, afterEach, afterAll } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { setupServer } from "msw/node";
import { handlers } from "./test/mocks/handlers";
import App from "./App";

const server = setupServer(...handlers);

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe("App routes", () => {
  it("renders projects page at /", async () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <App />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(screen.getByTestId("page-projects")).toBeInTheDocument();
    });
  });

  it("renders impact page at /impact (redirects to cockpit/impact)", async () => {
    render(
      <MemoryRouter initialEntries={["/impact"]}>
        <App />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(screen.getByTestId("page-impact")).toBeInTheDocument();
    });
  });

  it("renders projects page at /projects", async () => {
    render(
      <MemoryRouter initialEntries={["/projects"]}>
        <App />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(screen.getByTestId("page-projects")).toBeInTheDocument();
    });
  });

});
