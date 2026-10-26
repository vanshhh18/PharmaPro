import { useEffect } from "react";
import { Link } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import { fetchDashboard, selectDashboard } from "../features/dashboard/dashboardSlice";
import { Loading, ErrorBox } from "../components/states";

const COUNT_LABELS = {
  investigations_total: "Investigations",
  investigations_open: "Open investigations",
  investigations_archived: "Archived investigations",
  cause_hypotheses: "Cause hypotheses",
  evidence_gaps: "Evidence gaps",
  evidence_gaps_unresolved: "Unresolved evidence gaps",
  rca_steps: "RCA steps",
  capa_actions: "CAPA actions",
  capa_open: "Open CAPA actions",
  audit_events: "Audit events",
};

export default function DashboardPage() {
  const dispatch = useDispatch();
  const { counts, loading, error } = useSelector(selectDashboard);

  useEffect(() => {
    dispatch(fetchDashboard());
  }, [dispatch]);

  return (
    <main className="page">
      <header className="page-header">
        <h1>Dashboard</h1>
        <nav className="actions">
          <Link className="btn" to="/investigations/new">
            New investigation
          </Link>
          <Link className="btn btn-secondary" to="/investigations">
            All investigations
          </Link>
        </nav>
      </header>

      <section className="card" aria-labelledby="counts-heading">
        <h2 id="counts-heading">Case overview (from database)</h2>
        {loading && <Loading label="Loading counts…" />}
        {error && <ErrorBox message={error} onRetry={() => dispatch(fetchDashboard())} />}
        {counts && !loading && (
          <>
            <dl className="counts-grid">
              {Object.entries(COUNT_LABELS).map(([key, label]) => (
                <div key={key} className="count-item">
                  <dt>{label}</dt>
                  <dd>{counts[key]}</dd>
                </div>
              ))}
            </dl>
            <p className="detail">
              Counts reflect real database content; a fresh system shows zeros — not placeholder
              statistics.
            </p>
          </>
        )}
      </section>
    </main>
  );
}
