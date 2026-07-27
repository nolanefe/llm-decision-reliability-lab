from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.run import Run


class DatasetItem(Base):
    __tablename__ = "dataset_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    input_text: Mapped[str] = mapped_column(Text, nullable=False)
    expected_category: Mapped[str] = mapped_column(String(50), nullable=False)
    expected_priority: Mapped[str] = mapped_column(String(50), nullable=False)
    reference_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    reference_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc), nullable=False
    )

    runs: Mapped[list["Run"]] = relationship(back_populates="dataset_item")
