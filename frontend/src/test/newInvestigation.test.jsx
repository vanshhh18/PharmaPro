import { render, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Provider } from "react-redux";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { makeStore } from "../app/store";
import { mockFetch } from "./mockFetch";
import NewInvestigationPage from "../pages/NewInvestigationPage";

function renderPage(store = makeStore()) {
  return render(
    <Provider store={store}>
      <MemoryRouter initialEntries={["/investigations/new"]}>
        <Routes>
          <Route path="/investigations/new" element={<NewInvestigationPage />} />
          <Route path="/investigations/:id" element={<div>DETAIL RENDERED</div>} />
        </Routes>
      </MemoryRouter>
    </Provider>
  );
}

const ANALYSIS_RESPONSE = {
  facts: [
    { statement: "Impurity 2.1% exceeded the limit", quote: "imurity found" },
  ],
  unknowns: [{ question_or_item: "Why no trends?", why_unclear: "not provided" }],
  evidence_gaps: [{ record_or_data: "Temperature trends", why_needed: "context" }],
  conflicts: [],
  hypotheses: [
    {
      statement: "Temperature excursion",
      rationale: "Fits history",
      supporting_evidence: ["made 20 Oct 2026"],
      evidence_status: "available",
    },
  ],
  investigation_prompts: [{ method: "5whys", question: "Why was the result OOS?" }],
  rca_steps: [
    {
      method: "5whys",
      question: "Why was the impurity 2.1% against the 1.0% limit?",
      answer: "The report states the result exceeded the specification limit.",
      status: "grounded",
      position: 1,
    },
    {
      method: "fishbone",
      question: "Which method factors could explain the result?",
      answer: "No test-condition data is available in the report.",
      status: "speculative",
      position: 2,
    },
  ],
  capa_recommendations: [
    { description: "Review batch record", type: "corrective", rationale: "Verify accuracy" },
  ],
  note: "AI-generated draft for review.",
};

it("runs AI analysis and displays separated results", async () => {
  const user = userEvent.setup();
  const fetchMock = mockFetch([
    { match: "/api/analysis", data: ANALYSIS_RESPONSE },
  ]);
  const view = renderPage();
  await user.type(view.getByLabelText(/paste the incident report/i), "batch API-102 impurity 2.1%");
  await user.click(view.getByRole("button", { name: /run ai analysis/i }));

  expect(await view.findByText(/possible causes \(unconfirmed drafts\)/i, { selector: "h3" })).toBeInTheDocument();
  expect(await view.findByText("proposed")).toBeInTheDocument();
  expect(await view.findByText(/AI-generated draft for review/i)).toBeInTheDocument();
  expect(await view.findByText(/evidence gaps/i, { selector: "h3" })).toBeInTheDocument();
  expect(fetchMock).toHaveBeenCalledTimes(1);
});

it("saves the investigation together with AI analysis results and navigates to detail", async () => {
  const user = userEvent.setup();
  const fetchMock = mockFetch([
    { match: "/api/analysis", data: ANALYSIS_RESPONSE },
    {
      match: (url, options) => url.includes("/api/investigations") && options.method === "POST",
      data: { id: 5, reference: "INV-5", title: "T", status: "open" },
    },
  ]);
  const view = renderPage();
  await user.type(view.getByLabelText(/title/i), "Impurity OOS");
  await user.type(view.getByLabelText(/reference/i), "INV-5");
  await user.type(
    view.getByLabelText(/paste the incident report/i),
    "batch API-102 impurity 2.1%"
  );
  await user.click(view.getByRole("button", { name: /run ai analysis/i }));
  await view.findByText(/possible causes \(unconfirmed drafts\)/i, { selector: "h3" });
  await user.click(view.getByRole("button", { name: /save investigation/i }));

  await waitFor(() => {
    expect(view.queryByText("DETAIL RENDERED")).toBeInTheDocument();
  });

  const [createCall] = fetchMock.mock.calls.filter(
    ([url, options]) => url.includes("/api/investigations") && options.method === "POST"
  );
  const body = JSON.parse(createCall[1].body);
  expect(body.title).toBe("Impurity OOS");
  expect(body.report_text).toContain("API-102");
  expect(body.cause_hypotheses[0].description).toBe("Temperature excursion");
  expect(body.evidence_gaps[0].description).toContain("Temperature trends");
  expect(body.capa_actions[0].status).toBe("proposed");
  expect(body.rca_steps[0].question).toBe("Why was the impurity 2.1% against the 1.0% limit?");
  expect(body.rca_steps[0].answer).toContain("exceeded the specification limit");
  expect(await view.findByText(/draft rca answers/i, { selector: "h3" })).toBeInTheDocument();
  expect(await view.findByText("grounded")).toBeInTheDocument();
  expect(await view.findByText("speculative")).toBeInTheDocument();
});

it("blocks saving without required fields", async () => {
  const view = renderPage();
  const addButton = view.getByRole("button", { name: /save investigation/i });
  expect(addButton).toBeDisabled();
});

it("shows backend validation errors, not silent failure", async () => {
  const user = userEvent.setup();
  mockFetch([
    {
      match: "/api/analysis",
      fail: true,
      status: 503,
      payload: { detail: "GROQ_API_KEY is not configured; AI analysis is unavailable." },
    },
  ]);
  const view = renderPage();
  await user.type(
    view.getByLabelText(/paste the incident report/i),
    "batch API-102 impurity 2.1%"
  );
  await user.click(view.getByRole("button", { name: /run ai analysis/i }));
  expect(await view.findByText(/GROQ_API_KEY is not configured/i)).toBeInTheDocument();
});



