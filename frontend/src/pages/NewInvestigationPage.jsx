import { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useNavigate } from "react-router-dom";
import {
  clearNotice,
  createInvestigation,
  selectInvestigations,
} from "../features/investigations/investigationsSlice";
import {
  clearResults,
  intakeFile,
  intakeText,
  runAnalysis,
  selectAnalysis,
} from "../features/analysis/analysisSlice";
import AnalysisResultPanel from "../components/AnalysisResultPanel";
import { Loading, ErrorBox, SuccessNotice } from "../components/states";

function rcaFromAnalysis(analysis) {
  if (analysis.rca_steps?.length) {
    return analysis.rca_steps.map((s) => ({
      method: s.method,
      question: s.question,
      answer: s.answer ?? "",
      position: s.position ?? 0,
    }));
  }
  return (analysis.investigation_prompts ?? []).map((p, i) => ({
    method: p.method,
    question: p.question,
    answer: "",
    position: i + 1,
  }));
}

function analysisToRelated(analysis) {
  if (!analysis) return null;
  return {
    cause_hypotheses: (analysis.hypotheses ?? []).map((h) => ({
      description: h.statement,
      category: "",
      status: "proposed",
    })),
    evidence_gaps: (analysis.evidence_gaps ?? []).map((g) => ({
      description: [g.record_or_data, g.why_needed].filter(Boolean).join(" — "),
      resolved: false,
    })),
    rca_steps: rcaFromAnalysis(analysis),
    capa_actions: (analysis.capa_recommendations ?? []).map((c) => ({
      description: c.description,
      type: c.type,
      status: "proposed",
    })),
  };
}

export default function NewInvestigationPage() {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const { lastSaved, saving, saveError, notice } = useSelector(selectInvestigations);
  const { intake, analysis, loading, error } = useSelector(selectAnalysis);

  const [form, setForm] = useState({ title: "", reference: "", description: "" });
  const [reportText, setReportText] = useState("");
  const [fileName, setFileName] = useState("");

  useEffect(() => {
    if (lastSaved) {
      navigate(`/investigations/${lastSaved.id}`);
    }
  }, [lastSaved, navigate]);

  const setField = (field) => (event) =>
    setForm((prev) => ({ ...prev, [field]: event.target.value }));

  const hasAnalysis = Boolean(analysis);
  const related = analysisToRelated(analysis);

  const onSave = (event) => {
    event.preventDefault();
    dispatch(
      createInvestigation({
        ...form,
        report_text: reportText,
        ...(related ?? {}),
      })
    );
  };

  const onSaveDisableReason =
    !form.title.trim() || !form.reference.trim() || saving || loading;

  return (
    <main className="page">
      <header className="page-header">
        <h1>New investigation</h1>
      </header>

      <SuccessNotice message={notice} onDismiss={() => dispatch(clearNotice())} />
      {saveError && <ErrorBox message={saveError} />}

      <form className="card" onSubmit={onSave}>
        <h2>Investigation details</h2>
        <div className="form-row">
          <label htmlFor="title">Title *</label>
          <input
            id="title"
            value={form.title}
            onChange={setField("title")}
            placeholder="e.g. Impurity OOS on batch API-102"
            required
          />
        </div>
        <div className="form-row">
          <label htmlFor="reference">Reference *</label>
          <input
            id="reference"
            value={form.reference}
            onChange={setField("reference")}
            placeholder="e.g. INV-2026-001 (letters, digits, . _ -)"
            required
          />
        </div>
        <div className="form-row">
          <label htmlFor="description">Description</label>
          <textarea
            id="description"
            rows={3}
            value={form.description}
            onChange={setField("description")}
            placeholder="Short summary of the deviation"
          />
        </div>

        <h2>Report text</h2>
        <div className="form-row">
          <label htmlFor="report">Paste the incident report</label>
          <textarea
            id="report"
            rows={7}
            value={reportText}
            onChange={(event) => setReportText(event.target.value)}
            placeholder="Paste deviation/incident report text here…"
          />
        </div>

        <div className="actions">
          <button
            type="button"
            className="btn btn-secondary"
            disabled={!reportText.trim() || loading}
            onClick={() => dispatch(intakeText(reportText))}
          >
            Extract facts (rule-based)
          </button>
          <button
            type="button"
            className="btn"
            disabled={!reportText.trim() || loading}
            onClick={() => dispatch(runAnalysis(reportText))}
          >
            Run AI analysis
          </button>
        </div>
        <p className="detail">
          File upload: PDF, TXT, MD or EML up to 10 MB. Uploaded files are analyzed with the
          rule-based extractor (facts only); paste the text to also get the full AI RCA draft.
        </p>
        <div className="form-row">
          <label htmlFor="file">Or upload a report file</label>
          <input
            id="file"
            type="file"
            accept=".pdf,.txt,.md,.eml"
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (!file) return;
              setFileName(file.name);
              dispatch(
                intakeFile(file)
              );
              event.target.value = "";
            }}
          />
          {fileName && <span className="detail">File sent: {fileName}</span>}
        </div>
      </form>

      <section className="card" aria-label="Extraction and analysis results">
        <h2>Extraction and analysis results</h2>
        {loading && <Loading label="Contacting the backend…" />}
        {error && <ErrorBox message={error} />}
        {!loading && !error && (
          <AnalysisResultPanel intake={intake} analysis={hasAnalysis ? analysis : null} />
        )}
      </section>

      <form className="card save-card" onSubmit={onSave}>
        <h2>Save case</h2>
        <p className="detail">
          {related
            ? "Saving will attach the AI draft hypotheses, evidence gaps, RCA prompts and CAPA actions to the investigation as proposed items for human review."
            : "Running the AI analysis is optional; you can also save the case with just the report text."}
        </p>
        <div className="actions">
          <button className="btn" type="submit" disabled={Boolean(onSaveDisableReason)}>
            {saving ? "Saving…" : "Save investigation"}
          </button>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => {
              dispatch(clearResults());
              setFileName("");
            }}
          >
            Clear results
          </button>
        </div>
      </form>
    </main>
  );
}
