from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

INVESTIGATION_STATUSES = ("open", "archived")
HYPOTHESIS_STATUSES = ("proposed", "rejected")
CAPA_TYPES = ("corrective", "preventive")
CAPA_STATUSES = ("proposed", "accepted", "completed", "rejected")
RCA_METHODS = ("5whys", "fishbone", "other")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        server_default=func.now(),
        onupdate=utcnow,
        nullable=False,
    )


class Investigation(TimestampMixin, Base):
    __tablename__ = "investigations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    reference: Mapped[str] = mapped_column(String(60), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    report_text: Mapped[str] = mapped_column(Text, default="", nullable=False)

    cause_hypotheses: Mapped[list["CauseHypothesis"]] = relationship(
        back_populates="investigation", cascade="all, delete-orphan", order_by="CauseHypothesis.id"
    )
    evidence_gaps: Mapped[list["EvidenceGap"]] = relationship(
        back_populates="investigation", cascade="all, delete-orphan", order_by="EvidenceGap.id"
    )
    rca_steps: Mapped[list["RcaStep"]] = relationship(
        back_populates="investigation", cascade="all, delete-orphan", order_by="RcaStep.position"
    )
    capa_actions: Mapped[list["CapaAction"]] = relationship(
        back_populates="investigation", cascade="all, delete-orphan", order_by="CapaAction.id"
    )
    audit_events: Mapped[list["AuditEvent"]] = relationship(
        back_populates="investigation", cascade="all, delete-orphan", order_by="AuditEvent.id"
    )


class CauseHypothesis(Base):
    __tablename__ = "cause_hypotheses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    investigation_id: Mapped[int] = mapped_column(
        ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(60), default="", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="proposed", nullable=False)

    investigation: Mapped[Investigation] = relationship(back_populates="cause_hypotheses")


class EvidenceGap(Base):
    __tablename__ = "evidence_gaps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    investigation_id: Mapped[int] = mapped_column(
        ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    resolved: Mapped[bool] = mapped_column(default=False, nullable=False)

    investigation: Mapped[Investigation] = relationship(back_populates="evidence_gaps")


class RcaStep(Base):
    __tablename__ = "rca_steps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    investigation_id: Mapped[int] = mapped_column(
        ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False
    )
    method: Mapped[str] = mapped_column(String(20), default="5whys", nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, default="", nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    investigation: Mapped[Investigation] = relationship(back_populates="rca_steps")


class CapaAction(Base):
    __tablename__ = "capa_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    investigation_id: Mapped[int] = mapped_column(
        ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(String(20), default="corrective", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="proposed", nullable=False)

    investigation: Mapped[Investigation] = relationship(back_populates="capa_actions")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    investigation_id: Mapped[int] = mapped_column(
        ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False
    )
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    detail: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now(), nullable=False
    )

    investigation: Mapped[Investigation] = relationship(back_populates="audit_events")
