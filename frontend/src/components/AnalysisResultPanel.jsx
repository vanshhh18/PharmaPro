import { EmptyBox } from "./states";

function List({ items, render }) {
  return <ul className="result-list">{items.map((item, i) => <li key={i}>{render(item)}</li>)}</ul>;
}

function Section({ title, count, children }) {
  if (!count) return null;
  return (
    <section className="result-section">
      <h3>
        {title} <span className="count">({count})</span>
      </h3>
      {children}
    </section>
  );
}

const PROPOSED_FIELDS = ["batch_id", "reported_result", "spec_limit", "event_date", "detection_context"];

function AnalysisResultPanel({ intake, analysis }) {
  const hasAny =
    (analysis && (
      analysis.facts?.length ||
      analysis.unknowns?.length ||
      analysis.evidence_gaps?.length ||
      analysis.conflicts?.length ||
      analysis.hypotheses?.length ||
      analysis.investigation_prompts?.length ||
      analysis.rca_steps?.length ||
      analysis.capa_recommendations?.length
    )) ||
    (intake && (intake.facts?.length || intake.missing_information_statements?.length));

  if (!hasAny) {
    return (
      <EmptyBox message="No facts or analysis results yet. Paste report text or upload a document, then run extraction or AI analysis." />
    );
  }

  const facts = analysis?.facts ?? intake?.facts ?? [];
  const missingFields = intake?.missing ?? [];
  const missingStatements = intake?.missing_information_statements ?? [];

  return (
    <div className="analysis-panel">
      <Section title="Facts explicitly stated in the report" count={facts.length}>
        <List
          items={facts}
          render={(fact) => (
            <div className="fact">
              <strong>{fact.statement}</strong>
              {fact.quote && <blockquote>“{fact.quote}”</blockquote>}
            </div>
          )}
        />
      </Section>

      {missingFields.length > 0 && (
        <Section title="Missing fields (not stated in the report)" count={missingFields.length}>
          <ul className="chip-list">
            {missingFields.map((field) => (
              <li key={field} className="chip chip-missing">
                {field}
              </li>
            ))}
          </ul>
        </Section>
      )}

      <Section
        title="Statements about missing records"
        count={missingStatements.length}
      >
        <List items={missingStatements} render={(s) => <em>“{s}”</em>} />
      </Section>

      <Section title="Unknowns / unclear points" count={analysis?.unknowns?.length}>
        <List
          items={analysis?.unknowns ?? []}
          render={(item) => (
            <div>
              <strong>{item.question_or_item}</strong>
              {item.why_unclear && <p className="detail">{item.why_unclear}</p>}
            </div>
          )}
        />
      </Section>

      <Section title="Evidence gaps" count={analysis?.evidence_gaps?.length}>
        <List
          items={analysis?.evidence_gaps ?? []}
          render={(item) => (
            <div>
              <strong>{item.record_or_data}</strong>
              {item.why_needed && <p className="detail">{item.why_needed}</p>}
            </div>
          )}
        />
      </Section>

      <Section title="Conflicting info" count={analysis?.conflicts?.length ?? intake?.conflicts?.length}>
        <List
          items={analysis?.conflicts ?? intake?.conflicts ?? []}
          render={(item) => (
            <div>
              <strong>{item.description}</strong>
              {item.quotes?.length > 0 && <p className="detail">{item.quotes.join(" | ")}</p>}
            </div>
          )}
        />
      </Section>

      <Section title="Possible causes (unconfirmed drafts)" count={analysis?.hypotheses?.length}>
        <List
          items={analysis?.hypotheses ?? []}
          render={(h) => (
            <div className="hypothesis">
              <span className="count chip">proposed</span>
              <strong>{h.statement}</strong>
              <p className="detail">{h.rationale}</p>
              {h.supporting_evidence?.length > 0 ? (
                <p className="detail">Evidence: {h.supporting_evidence.join("; ")}</p>
              ) : (
                <p className="detail">Evidence: unavailable in report</p>
              )}
            </div>
          )}
        />
      </Section>

      <Section title="Investigation prompts" count={analysis?.investigation_prompts?.length}>
        <List
          items={analysis?.investigation_prompts ?? []}
          render={(p) => (
            <div>
              <span className="chip">{p.method}</span> {p.question}
            </div>
          )}
        />
      </Section>

      <Section title="Draft RCA answers (5 Whys / Fishbone, unconfirmed)" count={analysis?.rca_steps?.length}>
        <List
          items={analysis?.rca_steps ?? []}
          render={(s) => (
            <div>
              <span className="chip">{s.method}</span>{" "}
              <span className={`chip chip-${s.status === "grounded" ? "resolved" : "missing"}`}>
                {s.status}
              </span>{" "}
              <strong>{s.question}</strong>
              {s.answer && <p className="detail">→ {s.answer}</p>}
            </div>
          )}
        />
      </Section>

      <Section title="Draft CAPA actions (for review)" count={analysis?.capa_recommendations?.length}>
        <List
          items={analysis?.capa_recommendations ?? []}
          render={(c) => (
            <div>
              <span className={`chip chip-${c.type}`}>{c.type}</span> <strong>{c.description}</strong>
              {c.rationale && <p className="detail">{c.rationale}</p>}
            </div>
          )}
        />
      </Section>

      {analysis?.note && <p className="detail">{analysis.note}</p>}
      {intake?.note && <p className="detail">{intake.note}</p>}
    </div>
  );
}

export default AnalysisResultPanel;
