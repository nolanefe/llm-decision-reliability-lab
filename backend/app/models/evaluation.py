from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Text
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import FailureCategory

if TYPE_CHECKING:
    from app.models.run import Run

_failure_category_type = SqlEnum(
    FailureCategory,
    name="failure_category",
    native_enum=False,
    values_callable=lambda enum_cls: [member.value for member in enum_cls],
)


class Evaluation(Base):
    __tablename__ = "evaluations"
    __table_args__ = (
        CheckConstraint(
            "quality_score IS NULL OR (quality_score >= 0.0 AND quality_score <= 1.0)",
            name="ck_evaluations_quality_score_range",
        ),
        CheckConstraint(
            "consistency_score IS NULL OR (consistency_score >= 0.0 AND consistency_score <= 1.0)",
            name="ck_evaluations_consistency_score_range",
        ),
        CheckConstraint(
            "reliability_score IS NULL OR (reliability_score >= 0.0 AND reliability_score <= 100.0)",
            name="ck_evaluations_reliability_score_range",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(
        ForeignKey("runs.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    schema_valid: Mapped[bool] = mapped_column(nullable=False)
    category_correct: Mapped[bool | None] = mapped_column(nullable=True)
    priority_correct: Mapped[bool | None] = mapped_column(nullable=True)
    quality_score: Mapped[float | None] = mapped_column(nullable=True)
    consistency_score: Mapped[float | None] = mapped_column(nullable=True)
    failure_category: Mapped[FailureCategory | None] = mapped_column(
        _failure_category_type, nullable=True
    )
    reliability_score: Mapped[float | None] = mapped_column(nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc), nullable=False
    )

    run: Mapped["Run"] = relationship(back_populates="evaluation")
