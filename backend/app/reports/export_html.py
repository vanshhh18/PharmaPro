"""Printable HTML investigation report built from persisted data only."""
import html
from datetime import datetime

from app.models import Investigation, utcnow

_DISCLAIMER = (
    "This summary was generated from data recorded in AIVOA. AI-assisted suggestions "
    "(for example cause hypotheses and CAPA drafts) are NOT verified conclusions and require "
    "review and approval by a qualified person before any disposition, release, recall, or "
    "other regulatory decision. No root cause has been confirmed solely by this report."
)

_METHOD_LABELS = {"5whys": "5 Whys", "fishbone": "Fishbone"}


def _esc(value) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def _section(title: str, items: list[str]) -> list[str]:
    parts = [f"<h2>{_esc(title)}</h2>"]
    if items:
        parts.append("<ul>")
        parts.extend(f"<li>{item}</li>" for item in items)
        parts.append("</ul>")
    else:
        parts.append("<p class='empty'>No records.</p>")
    return parts


def _row(label: str, value: str) -> str:
    return f"<tr><th scope='row'>{_esc(label)}</th><td>{value}</td></tr>"


def build_report_html(
    investigation: Investigation, generated_at: datetime | None = None
) -> str:
    inv = investigation
    generated = generated_at or utcnow()

    overview = "".join(
        [
            _row("Reference", _esc(inv.reference)),
            _row("Title", _esc(inv.title)),
            _row("Status", _esc(inv.status)),
            _row("Created", _esc(inv.created_at)),
            _row("Last updated", _esc(inv.updated_at)),
        ]
    )

    hypothesis_items = [
        f"{_esc(h.description)}; Status: {_esc(h.status)}"
        + (f"; Category: {_esc(h.category)}" if h.category else "")
        for h in inv.cause_hypotheses
    ]
    gap_items = [
        f"{_esc(g.description)} (resolved: {'yes' if g.resolved else 'no'})"
        for g in inv.evidence_gaps
    ]
    rca_items = [
        (
            f"<strong>{_esc(_METHOD_LABELS.get(s.method, s.method))}</strong>: {_esc(s.question)}"
            + (f" - Answer: {_esc(s.answer)}" if s.answer else " - Answer: not answered")
        )
        for s in sorted(inv.rca_steps, key=lambda x: x.position)
    ]
    capa_items = [
        f"{_esc(c.description)} (type: {_esc(c.type)}, status: {_esc(c.status)})"
        for c in inv.capa_actions
    ]
    audit_items = [
        f"{_esc(e.created_at)}: {_esc(e.action)} - {_esc(e.detail)}" for e in inv.audit_events
    ]

    parts = [
        "<!DOCTYPE html>",
        "<html lang='en'><head><meta charset='utf-8' />",
        f"<title>{_esc(inv.reference)} - {_esc(inv.title)}</title>",
        "<style>",
        "body{font-family:Georgia,'Times New Roman',serif;max-width:22.5cm;margin:2mm auto;"
        "padding:0 12mm;color:#111;}",
        "h1{font-size:20pt} h2{font-size:13pt;border-bottom:1px solid #666;padding-bottom:2px;"
        "margin-top:1.2em}",
        "table{border-collapse:collapse;width:100%} th,td{border:1px solid #999;"
        "padding:4px 8px;text-align:left;vertical-align:top} th{background:#eee;width:22%}",
        ".pre{white-space:pre-wrap;border:1px solid #ccc;padding:8px;background:#fafafa}",
        ".empty{color:#555;font-style:italic}",
        ".disclaimer{border:2px solid #333;padding:10px;background:#fff3cd;margin-top:1.5em}",
        ".meta{color:#555;font-size:9pt}",
        "@media print{@page{margin:12mm} h2{page-break-after:avoid}}",
        "</style>",
        "</head><body>",
        "<h1>Investigation summary</h1>",
        f"<p class='meta'>Generated {_esc(generated)} by AIVOA</p>",
        "<h2>Overview</h2><table>"
        + overview
        + "</table>",
        "<h2>Reported information / facts</h2>",
        f"<p class='pre'>{_esc(inv.description)}</p>",
        f"<p class='pre'>{_esc(inv.report_text)}</p>",
    ]
    parts.extend(_section("Cause hypotheses", hypothesis_items))
    parts.extend(_section("Evidence gaps", gap_items))
    parts.extend(_section("RCA steps", rca_items))
    parts.extend(_section("CAPA actions", capa_items))
    parts.extend(_section("Audit history", audit_items))
    parts.extend(
        [
            "<div class='disclaimer'><strong>Review notice and disclaimer.</strong> "
            + _esc(_DISCLAIMER)
            + "</div>",
            "</body></html>",
        ]
    )
    return "".join(parts)
