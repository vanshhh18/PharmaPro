import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import {
  archiveInvestigation,
  clearNotice,
  fetchInvestigation,
  reopenInvestigation,
  selectInvestigations,
  updateInvestigation,
} from "../features/investigations/investigationsSlice";
import { Loading, ErrorBox, EmptyBox, SuccessNotice, StatusBadge } from "../components/states";
import { API_BASE as apiBaseUrl } from "../api/client";

const EMPTY_RELATED = {
  cause_hypotheses: [],
  evidence_gaps: [],
  rca_steps: [],
  capa_actions: [],
};

export default function InvestigationDetailPage() {
  const { id } = useParams();
  const dispatch = useDispatch();
  const { current, currentLoading, currentError, saving, saveError, notice } =
    useSelector(selectInvestigations);

  const [editing, setEditing] = useState(false);
  const [draftTitle, setDraftTitle] = useState("");
  const [draftDescription, setDraftDescription] = useState("");
  const [draftRelated, setDraftRelated] = useState(EMPTY_RELATED);

  useEffect(() => {
    dispatch(fetchInvestigation(id));
  }, [dispatch, id]);

  useEffect(() => {
    if (current) {
      setEditing(false);
    }
  }, [current?.id]);

  const startEditing = () => {
    if (!current) return;
    setDraftTitle(current.title);
    setDraftDescription(current.description);
    setDraftRelated({
      cause_hypotheses: current.cause_hypotheses ?? [],
      evidence_gaps: current.evidence_gaps ?? [],
      rca_steps: current.rca_steps ?? [],
      capa_actions: current.capa_actions ?? [],
    });
    setEditing(true);
  };

  const onSave = (event) => {
    event.preventDefault();
    if (!current) return;
    dispatch(
      updateInvestigation({
        id: current.id,
        title: draftTitle,
        description: draftDescription,
        related: draftRelated,
      })
    );
  };

  const setRelatedList = (listName) => (updater) =>
    setDraftRelated((prev) => ({ ...prev, [listName]: updater(prev[listName]) }));

  const updateRelatedItem = (listName, index, field) => (event) =>
    setRelatedList(listName)((items) =>
      items.map((item, i) =>
        i === index
          ? {
              ...item,
              [field]:
                event.target.type === "checkbox" ? event.target.checked : event.target.value,
            }
          : item
      )
    );

  const removeRelatedItem = (listName, index) => () =>
    setRelatedList(listName)((items) => items.filter((_, i) => i !== index));

  const addRelatedItem = (listName) => () => {
    const templates = {
      cause_hypotheses: { description: "", category: "", status: "proposed" },
      evidence_gaps: { description: "", resolved: false },
      rca_steps: { method: "5whys", question: "", answer: "", position: 0 },
      capa_actions: { description: "", type: "corrective", status: "proposed" },
    };
    setRelatedList(listName)((items) => [...items, templates[listName]]);
  };

  if (currentLoading) {
    return (
      <main className="page">
        <Loading label="Loading investigation…" />
      </main>
    );
  }
  if (currentError) {
    return (
      <main className="page">
        <ErrorBox message={currentError} onRetry={() => dispatch(fetchInvestigation(id))} />
        <Link to="/investigations">← Back to list</Link>
      </main>
    );
  }
  if (!current) {
    return (
      <main className="page">
        <EmptyBox message="Investigation not found." />
        <Link to="/investigations">← Back to list</Link>
      </main>
    );
  }

  const inv = current;

  return (
    <main className="page">
      <header className="page-header">
        <div>
          <h1>{inv.title}</h1>
          <p className="detail">
            <span className="chip">{inv.reference}</span> <StatusBadge status={inv.status} />{" "}
            Updated {new Date(inv.updated_at).toLocaleString()}
          </p>
        </div>
        <nav className="actions">
          {!editing && (
            <button type="button" className="btn" onClick={startEditing}>
              Edit
            </button>
          )}
          {!editing && (
            <a
              className="btn"
              href={`${apiBaseUrl}/api/investigations/${inv.id}/export`}
              target="_blank"
              rel="noreferrer"
            >
              Export report
            </a>
          )}
          {inv.status === "open" ? (
            <button
              type="button"
              className="btn btn-secondary"
              disabled={saving}
              onClick={() => dispatch(archiveInvestigation(inv.id))}
            >
              Archive
            </button>
          ) : (
            <button
              type="button"
              className="btn btn-secondary"
              disabled={saving}
              onClick={() => dispatch(reopenInvestigation(inv.id))}
            >
              Reopen
            </button>
          )}
        </nav>
      </header>

      <SuccessNotice message={notice} onDismiss={() => dispatch(clearNotice())} />
      {saveError && <ErrorBox message={saveError} />}
      {saving && <Loading label="Saving…" />}

      {editing ? (
        <form onSubmit={onSave}>
          <section className="card">
            <h2>Case details</h2>
            <div className="form-row">
              <label htmlFor="edit-title">Title</label>
              <input id="edit-title" value={draftTitle} onChange={(e) => setDraftTitle(e.target.value)} />
            </div>
            <div className="form-row">
              <label htmlFor="edit-description">Description</label>
              <textarea
                id="edit-description"
                rows={3}
                value={draftDescription}
                onChange={(e) => setDraftDescription(e.target.value)}
              />
            </div>
          </section>

          <section className="card">
            <h2>Cause hypotheses (drafts)</h2>
            {draftRelated.cause_hypotheses.map((h, i) => (
              <div className="edit-row" key={i}>
                <div className="form-row">
                  <label>Description</label>
                  <textarea rows={2} value={h.description} onChange={updateRelatedItem("cause_hypotheses", i, "description")} />
                </div>
                <div className="form-row inline">
                  <input
                    className="short"
                    placeholder="category"
                    value={h.category}
                    onChange={updateRelatedItem("cause_hypotheses", i, "category")}
                  />
                  <span className="chip">proposed</span>
                  <button type="button" className="btn btn-danger" onClick={removeRelatedItem("cause_hypotheses", i)}>
                    Remove
                  </button>
                </div>
              </div>
            ))}
            {draftRelated.cause_hypotheses.length === 0 && (
              <p className="detail">No hypotheses yet - add one below.</p>
            )}
            <button type="button" className="btn btn-secondary" onClick={addRelatedItem("cause_hypotheses")}>
              Add hypothesis
            </button>
          </section>

          <section className="card">
            <h2>Evidence gaps</h2>
            {draftRelated.evidence_gaps.map((gap, i) => (
              <div className="edit-row" key={i}>
                <div className="form-row">
                  <label>Description</label>
                  <textarea rows={2} value={gap.description} onChange={updateRelatedItem("evidence_gaps", i, "description")} />
                </div>
                <div className="form-row inline">
                  <label>
                    <input type="checkbox" checked={gap.resolved} onChange={updateRelatedItem("evidence_gaps", i, "resolved")} />{" "}
                    Resolved
                  </label>
                  <button type="button" className="btn btn-danger" onClick={removeRelatedItem("evidence_gaps", i)}>
                    Remove
                  </button>
                </div>
              </div>
            ))}
            {draftRelated.evidence_gaps.length === 0 && (
              <p className="detail">No evidence gaps yet - add one below.</p>
            )}
            <button type="button" className="btn btn-secondary" onClick={addRelatedItem("evidence_gaps")}>
              Add evidence gap
            </button>
          </section>

          <section className="card">
            <h2>RCA steps</h2>
            {draftRelated.rca_steps.map((step, i) => (
              <div className="edit-row" key={i}>
                <div className="form-row">
                  <label htmlFor={`rca-q-${i}`}>Question</label>
                  <input id={`rca-q-${i}`} value={step.question} onChange={updateRelatedItem("rca_steps", i, "question")} />
                </div>
                <div className="form-row">
                  <label htmlFor={`rca-a-${i}`}>Answer</label>
                  <textarea id={`rca-a-${i}`} rows={2} value={step.answer} onChange={updateRelatedItem("rca_steps", i, "answer")} />
                </div>
                <div className="form-row inline">
                  <label htmlFor={`rca-m-${i}`}>Method</label>
                  <select id={`rca-m-${i}`} value={step.method} onChange={updateRelatedItem("rca_steps", i, "method")}>
                    <option value="5whys">5 Whys</option>
                    <option value="fishbone">Fishbone</option>
                    <option value="other">Other</option>
                  </select>
                  <button type="button" className="btn btn-danger" onClick={removeRelatedItem("rca_steps", i)}>
                    Remove
                  </button>
                </div>
              </div>
            ))}
            {draftRelated.rca_steps.length === 0 && (
              <p className="detail">No RCA steps yet - add one below.</p>
            )}
            <button type="button" className="btn btn-secondary" onClick={addRelatedItem("rca_steps")}>
              Add RCA step
            </button>
          </section>

          <section className="card">
            <h2>CAPA actions (drafts)</h2>
            {draftRelated.capa_actions.map((action, i) => (
              <div className="edit-row" key={i}>
                <div className="form-row">
                  <label htmlFor={`capa-d-${i}`}>Description</label>
                  <textarea id={`capa-d-${i}`} rows={2} value={action.description} onChange={updateRelatedItem("capa_actions", i, "description")} />
                </div>
                <div className="form-row inline">
                  <label htmlFor={`capa-t-${i}`}>Type</label>
                  <select id={`capa-t-${i}`} value={action.type} onChange={updateRelatedItem("capa_actions", i, "type")}>
                    <option value="corrective">Corrective</option>
                    <option value="preventive">Preventive</option>
                  </select>
                  <label htmlFor={`capa-s-${i}`}>Status</label>
                  <select id={`capa-s-${i}`} value={action.status} onChange={updateRelatedItem("capa_actions", i, "status")}>
                    <option value="proposed">Proposed</option>
                    <option value="accepted">Accepted</option>
                    <option value="completed">Completed</option>
                    <option value="rejected">Rejected</option>
                  </select>
                  <button type="button" className="btn btn-danger" onClick={removeRelatedItem("capa_actions", i)}>
                    Remove
                  </button>
                </div>
              </div>
            ))}
            {draftRelated.capa_actions.length === 0 && (
              <p className="detail">No CAPA actions yet - add one below.</p>
            )}
            <button type="button" className="btn btn-secondary" onClick={addRelatedItem("capa_actions")}>
              Add CAPA action
            </button>
          </section>

          <div className="actions">
            <button className="btn" type="submit" disabled={saving}>
              Save changes
            </button>
            <button type="button" className="btn btn-secondary" onClick={() => setEditing(false)} disabled={saving}>
              Cancel
            </button>
          </div>
        </form>
      ) : (
        <>
          <section className="card">
            <h2>Description</h2>
            <p>{inv.description || <em>No description provided.</em>}</p>
            {inv.report_text && (
              <details>
                <summary>Original report text</summary>
                <pre className="report-text">{inv.report_text}</pre>
              </details>
            )}
          </section>

          <section className="card">
            <h2>Cause hypotheses (drafts for review)</h2>
            {inv.cause_hypotheses.length === 0 ? (
              <p className="detail">No cause hypotheses saved.</p>
            ) : (
              <ul className="result-list">
                {inv.cause_hypotheses.map((h) => (
                  <li key={h.id}>
                    <span className="chip">proposed</span> <strong>{h.description}</strong>
                    {h.category && <span className="detail"> ({h.category})</span>}
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="card">
            <h2>Evidence gaps</h2>
            {inv.evidence_gaps.length === 0 ? (
              <p className="detail">No evidence gaps saved.</p>
            ) : (
              <ul className="result-list">
                {inv.evidence_gaps.map((gap) => (
                  <li key={gap.id}>
                    <span className={`chip chip-${gap.resolved ? "resolved" : "missing"}`}>
                      {gap.resolved ? "resolved" : "open"}
                    </span>{" "}
                    {gap.description}
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="card">
            <h2>RCA steps</h2>
            {inv.rca_steps.length === 0 ? (
              <p className="detail">No RCA steps saved.</p>
            ) : (
              (() => {
                const labels = { "5whys": "5 Whys", fishbone: "Fishbone", other: "Other methods" };
                const groups = [];
                for (const step of inv.rca_steps) {
                  const existing = groups.find((g) => g.method === step.method);
                  if (existing) existing.steps.push(step);
                  else groups.push({ method: step.method, steps: [step] });
                }
                return groups.map((group) => (
                  <div key={group.method} className="rca-group">
                    <h3>{labels[group.method] ?? group.method}</h3>
                    <ol className="result-list">
                      {group.steps.map((step) => (
                        <li key={step.id}>
                          {step.question}
                          {step.answer && <p className="detail">→ {step.answer}</p>}
                        </li>
                      ))}
                    </ol>
                  </div>
                ));
              })()
            )}
          </section>

          <section className="card">
            <h2>CAPA actions (drafts for review)</h2>
            {inv.capa_actions.length === 0 ? (
              <p className="detail">No CAPA actions saved.</p>
            ) : (
              <ul className="result-list">
                {inv.capa_actions.map((action) => (
                  <li key={action.id}>
                    <span className={`chip chip-${action.type}`}>{action.type}</span>{" "}
                    <span className={`chip`}>{action.status}</span> <strong>{action.description}</strong>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="card">
            <h2>Audit history</h2>
            <ul className="result-list">
              {inv.audit_events.map((event) => (
                <li key={event.id}>
                  <strong>{event.action}</strong> — {event.detail}{" "}
                  <span className="detail">{new Date(event.created_at).toLocaleString()}</span>
                </li>
              ))}
            </ul>
          </section>
        </>
      )}
    </main>
  );
}
