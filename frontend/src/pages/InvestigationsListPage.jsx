import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import {
  fetchInvestigations,
  selectInvestigations,
} from "../features/investigations/investigationsSlice";
import { Loading, ErrorBox, EmptyBox, StatusBadge } from "../components/states";

export default function InvestigationsListPage() {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const { list, listLoading, listError } = useSelector(selectInvestigations);
  const [statusFilter, setStatusFilter] = useState("");

  useEffect(() => {
    dispatch(fetchInvestigations({ status: statusFilter || undefined }));
  }, [dispatch, statusFilter]);

  return (
    <main className="page">
      <header className="page-header">
        <h1>Investigations</h1>
        <nav className="actions">
          <Link className="btn" to="/investigations/new">
            New investigation
          </Link>
        </nav>
      </header>

      <section className="card">
        <div className="filter-row">
          <label htmlFor="status-filter">Status</label>
          <select
            id="status-filter"
            value={statusFilter}
            onChange={(event) => setStatusFilter(event.target.value)}
          >
            <option value="">All</option>
            <option value="open">Open</option>
            <option value="archived">Archived</option>
          </select>
        </div>

        {listLoading && <Loading label="Loading investigations…" />}
        {listError && (
          <ErrorBox message={listError} onRetry={() => dispatch(fetchInvestigations({ status: statusFilter || undefined }))} />
        )}

        {!listLoading && !listError && list.length === 0 && (
          <EmptyBox message="No investigations match this filter yet.">
            <Link className="btn" to="/investigations/new">
              Create the first investigation
            </Link>
          </EmptyBox>
        )}

        {!listLoading && !listError && list.length > 0 && (
          <table className="table">
            <thead>
              <tr>
                <th>Reference</th>
                <th>Title</th>
                <th>Status</th>
                <th>Updated</th>
              </tr>
            </thead>
            <tbody>
              {list.map((item) => (
                <tr
                  key={item.id}
                  className="row-link"
                  tabIndex={0}
                  onClick={() => navigate(`/investigations/${item.id}`)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter") navigate(`/investigations/${item.id}`);
                  }}
                >
                  <td>{item.reference}</td>
                  <td>{item.title}</td>
                  <td>
                    <StatusBadge status={item.status} />
                  </td>
                  <td>{new Date(item.updated_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </main>
  );
}
