export function Loading({ label = "Loading…" }) {
  return <p className="state state-loading">{label}</p>;
}

export function ErrorBox({ message, onRetry, retryLabel = "Retry" }) {
  return (
    <div className="state state-error" role="alert">
      <p>{message}</p>
      {onRetry && (
        <button type="button" onClick={onRetry}>
          {retryLabel}
        </button>
      )}
    </div>
  );
}

export function EmptyBox({ message, children }) {
  return (
    <div className="state state-empty">
      <p>{message}</p>
      {children}
    </div>
  );
}

export function StatusBadge({ status }) {
  const labels = { open: "Open", archived: "Archived" };
  return <span className={`badge badge-${status || "unknown"}`}>{labels[status] || status}</span>;
}

export function SuccessNotice({ message, onDismiss }) {
  if (!message) return null;
  return (
    <div className="notice" role="status">
      <span>{message}</span>
      {onDismiss && (
        <button type="button" className="notice-dismiss" onClick={onDismiss} aria-label="Dismiss">
          ×
        </button>
      )}
    </div>
  );
}
