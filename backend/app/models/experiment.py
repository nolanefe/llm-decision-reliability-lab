from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import JSON, CheckConstraint, String
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ExperimentStatus

if TYPE_CHECKING:
    from app.models.run import Run

_experiment_status_type = SqlEnum(
    ExperimentStatus,
    name="experiment_status",
    native_enum=False,
    values_callable=lambda enum_cls: [member.value for member in enum_cls],
)


class Experiment(Base):
    __tablename__ = "experiments"
    __table_args__ = (
        CheckConstraint(
            "repeat_count >= 1 AND repeat_count <= 10",
            name="ck_experiments_repeat_count_range",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[ExperimentStatus] = mapped_column(
        _experiment_status_type, default=ExperimentStatus.DRAFT, nullable=False
    )
    repeat_count: Mapped[int] = mapped_column(nullable=False)
    dataset_item_ids: Mapped[list[int]] = mapped_column(JSON, nullable=False)
    prompt_version_ids: Mapped[list[int]] = mapped_column(JSON, nullable=False)
    model_names: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc), nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    runs: Mapped[list["Run"]] = relationship(
        back_populates="experiment", cascade="all, delete-orphan"
    )
