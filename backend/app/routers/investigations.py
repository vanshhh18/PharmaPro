from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import HTMLResponse
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import schemas
from ..db import get_db
from ..models import (
    AuditEvent,
    CapaAction,
    CauseHypothesis,
    EvidenceGap,
    Investigation,
    RcaStep,
)
from ..reports.export_html import build_report_html

router = APIRouter(prefix="/investigations", tags=["investigations"])

AUDIT_ACTIONS = {
    "created": "created",
    "updated": "updated",
    "archived": "archived",
    "reopened": "reopened",
}

RELATED_KEYS = (
    "cause_hypotheses",
    "evidence_gaps",
    "rca_steps",
    "capa_actions",
)


def get_investigation_or_404(investigation_id: int, session: Session) -> Investigation:
    investigation = session.get(Investigation, investigation_id)
    if investigation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Investigation not found"
        )
    return investigation


def replace_related_lists(
    session: Session,
    investigation: Investigation,
    cause_hypotheses: list[schemas.CauseHypothesisIn] | None,
    evidence_gaps: list[schemas.EvidenceGapIn] | None,
    rca_steps: list[schemas.RcaStepIn] | None,
    capa_actions: list[schemas.CapaActionIn] | None,
) -> list[str]:
    """Replace full related collections (exploiting cascade delete-orphan).

    Returns human-readable per-entity change summaries for the audit log.
    """
    summaries = []

    def swap(entity: str, incoming):
        if incoming is None:
            return
        before = len(getattr(investigation, entity))
        after = len(incoming)
        mapping = {
            "cause_hypotheses": (CauseHypothesis, schemas.CauseHypothesisIn),
            "evidence_gaps": (EvidenceGap, schemas.EvidenceGapIn),
            "rca_steps": (RcaStep, schemas.RcaStepIn),
            "capa_actions": (CapaAction, schemas.CapaActionIn),
        }
        model, _ = mapping[entity]
        setattr(investigation, entity, [model(**item.model_dump()) for item in incoming])
        if after == 0:
            change = "(cleared)"
        elif after > before:
            change = f"(+{after - before})"
        elif after < before:
            change = f"(-{before - after})"
        elif after > 0:
            change = "(rebuilt)"
        else:
            change = "(cleared)"
        summaries.append(f"{entity}: {before}->{after} {change}")

    swap("cause_hypotheses", cause_hypotheses)
    swap("evidence_gaps", evidence_gaps)
    swap("rca_steps", rca_steps)
    swap("capa_actions", capa_actions)
    return summaries


@router.post("", response_model=schemas.Investigation, status_code=status.HTTP_201_CREATED)
def create_investigation(payload: schemas.InvestigationCreate, session: Session = Depends(get_db)):
    investigation = Investigation(**payload.model_dump(exclude=RELATED_KEYS))
    session.add(investigation)
    try:
        session.flush()
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An investigation with this reference already exists",
        ) from None

    changed = replace_related_lists(
        session,
        investigation,
        payload.cause_hypotheses or None,
        payload.evidence_gaps or None,
        payload.rca_steps or None,
        payload.capa_actions or None,
    )
    detail = ", ".join(changed) if changed else "no related data"
    investigation.audit_events.append(
        AuditEvent(action="created", detail=f"created with: {detail}")
    )
    session.flush()
    return investigation


@router.get("", response_model=list[schemas.InvestigationSummary])
def list_investigations(
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_db),
):
    query = select(Investigation).order_by(Investigation.updated_at.desc())
    if status_filter is not None:
        if status_filter not in ("open", "archived"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid status filter"
            )
        query = query.where(Investigation.status == status_filter)
    return session.scalars(query.limit(limit).offset(offset)).all()


@router.get("/dashboard", response_model=schemas.DashboardCounts)
def dashboard_counts(session: Session = Depends(get_db)):
    def count(model, *filters):
        query = select(func.count()).select_from(model)
        if filters:
            query = query.where(*filters)
        return session.scalar(query) or 0

    return schemas.DashboardCounts(
        investigations_total=count(Investigation),
        investigations_open=count(Investigation, Investigation.status == "open"),
        investigations_archived=count(Investigation, Investigation.status == "archived"),
        cause_hypotheses=count(CauseHypothesis),
        evidence_gaps=count(EvidenceGap),
        evidence_gaps_unresolved=count(EvidenceGap, EvidenceGap.resolved.is_(False)),
        rca_steps=count(RcaStep),
        capa_actions=count(CapaAction),
        capa_open=count(CapaAction, CapaAction.status != "completed"),
        audit_events=count(AuditEvent),
    )


@router.get("/{investigation_id}", response_model=schemas.Investigation)
def get_investigation(investigation_id: int, session: Session = Depends(get_db)):
    return get_investigation_or_404(investigation_id, session)


@router.get("/{investigation_id}/audit", response_model=list[schemas.AuditEvent])
def list_audit_events(investigation_id: int, session: Session = Depends(get_db)):
    investigation = get_investigation_or_404(investigation_id, session)
    return investigation.audit_events


@router.get("/{investigation_id}/export")
def export_investigation_report(
    investigation_id: int, session: Session = Depends(get_db)
):
    """Printable HTML report built exclusively from persisted, escaped data."""
    investigation = get_investigation_or_404(investigation_id, session)
    filename = f"{investigation.reference}-report.html"
    return HTMLResponse(
        content=build_report_html(investigation),
        media_type="text/html",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@router.patch("/{investigation_id}", response_model=schemas.Investigation)
def update_investigation(
    investigation_id: int, payload: schemas.InvestigationUpdate, session: Session = Depends(get_db)
):
    investigation = get_investigation_or_404(investigation_id, session)

    changed_fields = []
    for field in ("title", "description", "report_text"):
        value = getattr(payload, field)
        if value is not None and value != getattr(investigation, field):
            setattr(investigation, field, value)
            changed_fields.append(field)

    changed_related = []
    if payload.related is not None:
        changed_related = replace_related_lists(
            session,
            investigation,
            payload.related.cause_hypotheses,
            payload.related.evidence_gaps,
            payload.related.rca_steps,
            payload.related.capa_actions,
        )
        try:
            session.flush()
        except IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Could not save related data"
            ) from None

    if changed_fields or changed_related:
        details = []
        if changed_fields:
            details.append(f"fields: {', '.join(changed_fields)}")
        if changed_related:
            details.append(f"related: {', '.join(changed_related)}")
        investigation.audit_events.append(
            AuditEvent(action="updated", detail="; ".join(details))
        )
        session.flush()
    return investigation


@router.post("/{investigation_id}/archive", response_model=schemas.Investigation)
def archive_investigation(investigation_id: int, session: Session = Depends(get_db)):
    investigation = get_investigation_or_404(investigation_id, session)
    if investigation.status != "open":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Only open investigations can be archived"
        )
    investigation.status = "archived"
    investigation.audit_events.append(AuditEvent(action="archived", detail="status set to archived"))
    session.flush()
    return investigation


@router.post("/{investigation_id}/reopen", response_model=schemas.Investigation)
def reopen_investigation(investigation_id: int, session: Session = Depends(get_db)):
    investigation = get_investigation_or_404(investigation_id, session)
    if investigation.status != "archived":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only archived investigations can be reopened",
        )
    investigation.status = "open"
    investigation.audit_events.append(AuditEvent(action="reopened", detail="status set to open"))
    session.flush()
    return investigation
