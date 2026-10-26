import { useEffect } from "react";
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import { loadHealth, selectHealth } from "./features/health/healthSlice";

function HealthBadge() {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const { data, error } = useSelector(selectHealth);

  useEffect(() => {
    dispatch(loadHealth());
  }, [dispatch, navigate]);

  const status = error ? "error" : data?.status ?? "unknown";
  const labels = { ok: "Backend + DB OK", degraded: "Backend degraded (DB unreachable)", unknown: "Backend status unknown", error: "Backend unreachable" };

  return (
    <button
      type="button"
      className={`badge badge-${status} badge-btn`}
      title="Click to retry health check"
      onClick={() => dispatch(loadHealth())}
    >
      {labels[status]}
    </button>
  );
}

export default function App() {
  return (
    <div className="app-shell">
      <header className="topbar">
        <nav className="nav">
          <Link to="/" className="brand">
            AIVOA
          </Link>
          <NavLink to="/" end>
            Dashboard
          </NavLink>
          <NavLink to="/investigations" end>
            Investigations
          </NavLink>
          <NavLink to="/investigations/new">New investigation</NavLink>
        </nav>
        <HealthBadge />
      </header>

      <p className="tagline">
        Deviation investigation decision support. AI output is a draft for review by a qualified
        quality professional. Not validated GMP software — no batch-release, recall, or
        disposition decisions are made here.
      </p>

      <Outlet />
    </div>
  );
}
