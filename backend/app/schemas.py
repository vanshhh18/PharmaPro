from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .models import (
    CAPA_STATUSES,
    CAPA_TYPES,
    HYPOTHESIS_STATUSES,
    INVESTIGATION_STATUSES,
    RCA_METHODS,
)


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CauseHypothesisIn(BaseModel):
    description: str = Field(min_length=1, max_length=2000)
    category: str = Field(default="", max_length=60)
    status: str = "proposed"

    @field_validator("status")
    @classmethod
    def valid_status(cls, value: str) -> str:
        if value not in HYPOTHESIS_STATUSES:
            raise ValueError(f"status must be one of {HYPOTHESIS_STATUSES}")
        return value


class EvidenceGapIn(BaseModel):
    description: str = Field(min_length=1, max_length=2000)
    resolved: bool = False


class RcaStepIn(BaseModel):
    method: str = "5whys"
    question: str = Field(min_length=1, max_length=2000)
    answer: str = Field(default="", max_length=2000)
    position: int = Field(default=0, ge=0)

    @field_validator("method")
    @classmethod
    def valid_method(cls, value: str) -> str:
        if value not in RCA_METHODS:
            raise ValueError(f"method must be one of {RCA_METHODS}")
        return value


class CapaActionIn(BaseModel):
    description: str = Field(min_length=1, max_length=2000)
    type: str = "corrective"
    status: str = "proposed"

    @field_validator("type")
    @classmethod
    def valid_type(cls, value: str) -> str:
        if value not in CAPA_TYPES:
            raise ValueError(f"type must be one of {CAPA_TYPES}")
        return value

    @field_validator("status")
    @classmethod
    def valid_status(cls, value: str) -> str:
        if value not in CAPA_STATUSES:
            raise ValueError(f"status must be one of {CAPA_STATUSES}")
        return value


class InvestigationCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    reference: str = Field(min_length=1, max_length=60, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    description: str = Field(default="", max_length=5000)
    report_text: str = Field(default="", max_length=200000)

    cause_hypotheses: list[CauseHypothesisIn] = Field(default_factory=list)
    evidence_gaps: list[EvidenceGapIn] = Field(default_factory=list)
    rca_steps: list[RcaStepIn] = Field(default_factory=list)
    capa_actions: list[CapaActionIn] = Field(default_factory=list)


class RelatedListsUpdate(BaseModel):
    """Replace the full lists of related rows on an investigation."""

    cause_hypotheses: list[CauseHypothesisIn] | None = None
    evidence_gaps: list[EvidenceGapIn] | None = None
    rca_steps: list[RcaStepIn] | None = None
    capa_actions: list[CapaActionIn] | None = None


class InvestigationUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    report_text: str | None = Field(default=None, max_length=200000)
    related: RelatedListsUpdate | None = None


class DashboardCounts(BaseModel):
    investigations_total: int
    investigations_open: int
    investigations_archived: int
    cause_hypotheses: int
    evidence_gaps: int
    evidence_gaps_unresolved: int
    rca_steps: int
    capa_actions: int
    capa_open: int
    audit_events: int


class CauseHypothesis(ORMModel):
    id: int
    description: str
    category: str
    status: str


class EvidenceGap(ORMModel):
    id: int
    description: str
    resolved: bool


class RcaStep(ORMModel):
    id: int
    method: str
    question: str
    answer: str
    position: int


class CapaAction(ORMModel):
    id: int
    description: str
    type: str
    status: str


class AuditEvent(ORMModel):
    id: int
    action: str
    detail: str
    created_at: datetime


class InvestigationSummary(ORMModel):
    id: int
    reference: str
    title: str
    status: str
    description: str
    created_at: datetime
    updated_at: datetime


class Investigation(ORMModel):
    id: int
    reference: str
    title: str
    status: str
    description: str
    report_text: str
    created_at: datetime
    updated_at: datetime
    cause_hypotheses: list[CauseHypothesis]
    evidence_gaps: list[EvidenceGap]
    rca_steps: list[RcaStep]
    capa_actions: list[CapaAction]
    audit_events: list[AuditEvent]


class ReportTextInput(BaseModel):
    text: str = Field(min_length=1, max_length=200000)


class FactOut(BaseModel):
    field: str
    value: str
    quote: str
    iso_date: str | None = None


class ConflictOut(BaseModel):
    field: str
    values: list[str]


class ReportSourceOut(BaseModel):
    kind: str
    name: str
    size_bytes: int
    file_type: str | None = None


class DocumentStatsOut(BaseModel):
    char_count: int
    word_count: int


class IntakeResult(BaseModel):
    source: ReportSourceOut
    document: DocumentStatsOut
    facts: list[FactOut]
    missing: list[str]
    conflicts: list[ConflictOut]
    missing_information_statements: list[str]
    note: str = (
        "Rule-based draft extraction for review by a qualified quality professional. "
        "Facts contain only wording explicitly present in the report."
    )
