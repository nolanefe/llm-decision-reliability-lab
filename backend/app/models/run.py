from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import RunStatus

if TYPE_CHECKING:
    from app.models.dataset_item import DatasetItem
    from app.models.evaluation import Evaluation
    from app.models.experiment import Experiment
    from app.models.prompt_version import PromptVersion

_run_status_type = SqlEnum(
    RunStatus,
    name="run_status",
    native_enum=False,
    values_callable=lambda enum_cls: [member.value for member in enum_cls],
)


class Run(Base):
    __tablename__ = "runs"
    __table_args__ = (
        UniqueConstraint(
            "experiment_id",
            "dataset_item_id",
            "prompt_version_id",
            "model_name",
            "repetition_index",
            name="uq_runs_experiment_item_prompt_model_repetition",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    experiment_id: Mapped[int] = mapped_column(
        ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False
    )
    dataset_item_id: Mapped[int] = mapped_column(
        ForeignKey("dataset_items.id"), nullable=False
    )
    prompt_version_id: Mapped[int] = mapped_column(
        ForeignKey("prompt_versions.id"), nullable=False
    )
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    repetition_index: Mapped[int] = mapped_column(nullable=False)
    status: Mapped[RunStatus] = mapped_column(
        _run_status_type, default=RunStatus.PENDING, nullable=False
    )
    raw_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    parsed_output: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(nullable=True)
    prompt_tokens: Mapped[int | None] = mapped_column(nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(nullable=True)
    estimated_cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    experiment: Mapped["Experiment"] = relationship(back_populates="runs")
    dataset_item: Mapped["DatasetItem"] = relationship(back_populates="runs")
    prompt_version: Mapped["PromptVersion"] = relationship(back_populates="runs")
    evaluation: Mapped["Evaluation | None"] = relationship(
        back_populates="run", cascade="all, delete-orphan", uselist=False
    )
