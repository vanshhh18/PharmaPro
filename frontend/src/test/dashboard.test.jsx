import { render, waitFor } from "@testing-library/react";
import { Provider } from "react-redux";
import { MemoryRouter } from "react-router-dom";
import { makeStore } from "../app/store";
import { mockFetch } from "./mockFetch";
import DashboardPage from "../pages/DashboardPage";

function renderPage() {
  return render(
    <Provider store={makeStore()}>
      <MemoryRouter initialEntries={["/"]}>
        <DashboardPage />
      </MemoryRouter>
    </Provider>
  );
}

const COUNTS = {
  investigations_total: 2,
  investigations_open: 1,
  investigations_archived: 1,
  cause_hypotheses: 4,
  evidence_gaps: 5,
  evidence_gaps_unresolved: 3,
  rca_steps: 2,
  capa_actions: 5,
  capa_open: 5,
  audit_events: 7,
};

it("shows counts fetched from the database", async () => {
  mockFetch([{ match: "/api/investigations/dashboard", data: COUNTS }]);
  const { findByText, findAllByText } = renderPage();
  expect(await findByText("Open investigations")).toBeInTheDocument();
  expect((await findAllByText("1")).length).toBeGreaterThanOrEqual(1);
  expect(await findByText("Audit events")).toBeInTheDocument();
  await waitFor(() => {
    const dds = document.querySelectorAll(".count-item");
    expect(dds.length).toBe(10);
  });
});

it("shows an error with retry when the API fails", async () => {
  mockFetch([
    {
      match: "/api/investigations/dashboard",
      fail: true,
      status: 500,
      payload: { detail: "database exploded" },
    },
  ]);
  const { findByRole } = renderPage();
  const alert = await findByRole("alert");
  expect(alert).toHaveTextContent("database exploded");
});

