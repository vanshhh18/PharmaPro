import { render, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Provider } from "react-redux";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { makeStore } from "../app/store";
import { mockFetch } from "./mockFetch";
import InvestigationDetailPage from "../pages/InvestigationDetailPage";

const INVESTIGATION = {
  id: 1,
  reference: "INV-1",
  title: "Impurity OOS batch API-102",
  status: "open",
  description: "Release testing deviation",
  report_text: "Batch API-102 2.1% vs 1.0%",
  created_at: "2026-10-23T09:00:00Z",
  updated_at: "2026-10-23T09:30:00Z",
  cause_hypotheses: [
    { id: 11, description: "Process excursion", category: "process", status: "proposed" },
  ],
  evidence_gaps: [{ id: 21, description: "Temperature trends missing", resolved: false }],
  rca_steps: [{ id: 31, method: "5whys", question: "Why OOS?", answer: "", position: 1 }],
  capa_actions: [
    { id: 41, description: "Review chromatograms", type: "corrective", status: "proposed" },
  ],
  audit_events: [
    { id: 51, action: "created", detail: "created with: no related data", created_at: "2026-10-23T09:00:00Z" },
    { id: 52, action: "archived", detail: "status set to archived", created_at: "2026-10-23T10:00:00Z" },
  ],
};

function renderPage(store = makeStore()) {
  return render(
    <Provider store={store}>
      <MemoryRouter initialEntries={["/investigations/1"]}>
        <Routes>
          <Route path="/investigations/:id" element={<InvestigationDetailPage />} />
        </Routes>
      </MemoryRouter>
    </Provider>
  );
}

it("renders a saved investigation with its related data and audit history", async () => {
  mockFetch([{ match: "/api/investigations/1", data: INVESTIGATION }]);
  const view = renderPage();

  expect(await view.findByText("Impurity OOS batch API-102")).toBeInTheDocument();
  expect(await view.findByText("Open")).toBeInTheDocument();
  expect(await view.findByText(/original report text/i)).toBeInTheDocument();
  expect(await view.findByText("Process excursion")).toBeInTheDocument();
  expect(await view.findByText(/Temperature trends missing/i)).toBeInTheDocument();
  expect(await view.findByText(/created with: no related data/i)).toBeInTheDocument();
  expect(await view.findByText(/status set to archived/i)).toBeInTheDocument();
});

it("archives an open investigation through the API and shows the result", async () => {
  const user = userEvent.setup();
  const fetchMock = mockFetch([
    { match: "/api/investigations/1", data: INVESTIGATION },
    {
      match: (url, options) => url.includes("/archive") && options.method === "POST",
      data: { ...INVESTIGATION, status: "archived" },
    },
  ]);
  const view = renderPage();
  await view.findByText("Impurity OOS batch API-102");
  await user.click(view.getByRole("button", { name: /archive/i }));

  await waitFor(() => {
    expect(fetchMock.mock.calls.some(([url]) => url.includes("/archive"))).toBe(true);
  });
  expect(await view.findByText("Investigation archived.")).toBeInTheDocument();
});

it("loads edit mode with draft fields and saves via PATCH", async () => {
  const user = userEvent.setup();
  const fetchMock = mockFetch([
    { match: "/api/investigations/1", data: INVESTIGATION },
    {
      match: (url, options) => url.includes("/api/investigations/1") && options.method === "PATCH",
      data: {
        ...INVESTIGATION,
        title: "Updated title",
        capa_actions: [{ id: 41, description: "Amended action", type: "preventive", status: "accepted" }],
      },
    },
  ]);
  const view = renderPage();
  await view.findByText("Impurity OOS batch API-102");
  await user.click(view.getByRole("button", { name: /edit/i }));
  const titleInput = await view.findByLabelText("Title");
  await user.clear(titleInput);
  await user.type(titleInput, "Updated title");
  await user.click(view.getByRole("button", { name: /save changes/i }));

  const [patchCall] = fetchMock.mock.calls.filter(
    ([url, options]) => url.includes("/api/investigations/1") && options.method === "PATCH"
  );
  const patchBody = JSON.parse(patchCall[1].body);
  expect(patchBody.title).toBe("Updated title");
  expect(patchBody.related.cause_hypotheses).toHaveLength(1);
  expect(await view.findByText("Changes saved.")).toBeInTheDocument();
});

it("handles a 404 for an unknown investigation id", async () => {
  mockFetch([
    { match: "/api/investigations/1", fail: true, status: 404, payload: { detail: "Investigation not found" } },
  ]);
  const view = renderPage();
  expect(await view.findByRole("alert")).toHaveTextContent("Investigation not found");
});


it("groups RCA steps by method (5 Whys / Fishbone) in view mode", async () => {
  const withMethods = {
    ...INVESTIGATION,
    rca_steps: [
      { id: 31, method: "5whys", question: "Why was the result OOS?", answer: "Process drift", position: 1 },
      { id: 32, method: "fishbone", question: "Which category explains the drift?", answer: "", position: 2 },
    ],
  };
  mockFetch([{ match: "/api/investigations/1", data: withMethods }]);
  const view = renderPage();
  expect(await view.findByRole("heading", { name: "5 Whys" })).toBeInTheDocument();
  expect(await view.findByRole("heading", { name: "Fishbone" })).toBeInTheDocument();
  expect(await view.findByText("Which category explains the drift?")).toBeInTheDocument();
});

it("shows empty-list hints in edit mode for lists with no items", async () => {
  const empties = { ...INVESTIGATION, capa_actions: [] };
  mockFetch([{ match: "/api/investigations/1", data: empties }]);
  const user = userEvent.setup();
  const view = renderPage();
  await view.findByText("Impurity OOS batch API-102");
  await user.click(view.getByRole("button", { name: /^edit$/i }));
  expect(await view.findByText(/No CAPA actions yet/i)).toBeInTheDocument();
});

it("shows clear feedback when a save fails with a validation error", async () => {
  mockFetch([
    {
      match: (url, options) => url.includes("/api/investigations/1") && options.method === "PATCH",
      fail: true,
      status: 422,
      payload: { detail: [{ msg: "Ensure this field has no more than 2000 characters." }] },
    },
    { match: "/api/investigations/1", data: INVESTIGATION },
  ]);
  const user = userEvent.setup();
  const view = renderPage();
  await view.findByText("Impurity OOS batch API-102");
  await user.click(view.getByRole("button", { name: /^edit$/i }));
  await user.click(view.getByRole("button", { name: /save changes/i }));
  expect(
    await view.findByText(/Ensure this field has no more than 2000 characters/i)
  ).toBeInTheDocument();
});

it("exposes a working report-export link", async () => {
  mockFetch([{ match: "/api/investigations/1", data: INVESTIGATION }]);
  const view = renderPage();
  const link = await view.findByRole("link", { name: /export report/i });
  expect(link.getAttribute("href")).toContain("/api/investigations/1/export");
  expect(link.getAttribute("target")).toBe("_blank");
});
