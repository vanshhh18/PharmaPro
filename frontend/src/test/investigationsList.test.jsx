import { render } from "@testing-library/react";
import { Provider } from "react-redux";
import { MemoryRouter } from "react-router-dom";
import { makeStore } from "../app/store";
import { mockFetch } from "./mockFetch";
import InvestigationsListPage from "../pages/InvestigationsListPage";

function renderPage(route = "/investigations") {
  return render(
    <Provider store={makeStore()}>
      <MemoryRouter initialEntries={[route]}>
        <InvestigationsListPage />
      </MemoryRouter>
    </Provider>
  );
}

const ITEMS = [
  {
    id: 1,
    reference: "INV-1",
    title: "Impurity OOS",
    status: "open",
    updated_at: "2026-10-23T10:00:00Z",
    created_at: "2026-10-23T09:00:00Z",
    description: "",
  },
  {
    id: 2,
    reference: "INV-2",
    title: "Contamination",
    status: "archived",
    updated_at: "2026-10-22T08:00:00Z",
    created_at: "2026-10-22T07:00:00Z",
    description: "",
  },
];

it("lists saved investigations from the API", async () => {
  mockFetch([
    { match: (url, options) => url.includes("/api/investigations") && !url.includes("dashboard") && (options?.method ?? "GET") === "GET", data: ITEMS },
  ]);
  const { findByText, findAllByText } = renderPage();
  expect(await findByText("INV-1")).toBeInTheDocument();
  expect(await findByText("Impurity OOS")).toBeInTheDocument();
  expect(await findByText("Contamination")).toBeInTheDocument();
  expect((await findAllByText("Archived")).length).toBe(2);
});

it("shows empty state when no investigations exist", async () => {
  mockFetch([
    { match: "/api/investigations", data: [] },
  ]);
  const { findByText } = renderPage();
  expect(await findByText(/No investigations match this filter yet/i)).toBeInTheDocument();
});

