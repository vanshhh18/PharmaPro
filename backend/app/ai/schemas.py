from pydantic import BaseModel, Field, field_validator

HYPOTHESIS_STATUSES = ("proposed",)


class FactStatement(BaseModel):
    statement: str = Field(min_length=1, max_length=500)
    quote: str = Field(min_length=1, max_length=800)


class UnknownItem(BaseModel):
    question_or_item: str = Field(min_length=1, max_length=500)
    why_unclear: str = Field(default="", max_length=800)


class EvidenceGap(BaseModel):
    record_or_data: str = Field(min_length=1, max_length=500)
    why_needed: str = Field(default="", max_length=800)


class ConflictItem(BaseModel):
    description: str = Field(min_length=1, max_length=500)
    quotes: list[str] = Field(default_factory=list, max_length=10)


class CauseHypothesis(BaseModel):
    statement: str = Field(min_length=1, max_length=500)
    rationale: str = Field(min_length=1, max_length=1500)
    supporting_evidence: list[str] = Field(default_factory=list, max_length=10)
    evidence_status: str = "available"

    model_config = {"json_schema_extra": {"examples": []}}

    @property
    def is_unavailable_evidence(self) -> bool:
        return self.evidence_status == "unavailable"


class InvestigationPrompt(BaseModel):
    method: str = Field(min_length=1, max_length=40)
    question: str = Field(min_length=1, max_length=800)


RCA_METHODS = ("5whys", "fishbone", "other")
RCA_STATUSES = ("grounded", "speculative")


class RcaStepDraft(BaseModel):
    method: str
    question: str = Field(min_length=1, max_length=2000)
    answer: str = Field(default="", max_length=2000)
    status: str = "speculative"
    position: int = Field(default=0, ge=0)

    @field_validator("method")
    @classmethod
    def valid_method(cls, value: str) -> str:
        if value not in RCA_METHODS:
            raise ValueError(f"method must be one of {RCA_METHODS}")
        return value

    @field_validator("status")
    @classmethod
    def valid_status(cls, value: str) -> str:
        if value not in RCA_STATUSES:
            raise ValueError(f"status must be one of {RCA_STATUSES}")
        return value


class CapaRecommendation(BaseModel):
    description: str = Field(min_length=1, max_length=800)
    type: str
    rationale: str = Field(default="", max_length=1000)


CAPA_TYPES = ("corrective", "preventive")


class AnalysisResult(BaseModel):
    facts: list[FactStatement] = Field(default_factory=list, max_length=50)
    unknowns: list[UnknownItem] = Field(default_factory=list, max_length=30)
    evidence_gaps: list[EvidenceGap] = Field(default_factory=list, max_length=30)
    conflicts: list[ConflictItem] = Field(default_factory=list, max_length=20)
    hypotheses: list[CauseHypothesis] = Field(default_factory=list, max_length=10)
    investigation_prompts: list[InvestigationPrompt] = Field(default_factory=list, max_length=20)
    rca_steps: list[RcaStepDraft] = Field(default_factory=list, max_length=20)
    capa_recommendations: list[CapaRecommendation] = Field(default_factory=list, max_length=20)

    note: str = (
        "AI-generated draft for review by a qualified quality professional. "
        "Hypotheses are unconfirmed. This app does not make batch-release, "
        "recall, or disposition decisions."
    )
