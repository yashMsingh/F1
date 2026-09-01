"""LapTime model — Individual lap-by-lap timing and positional tracking."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.driver import Driver
    from app.db.models.race import Race


class LapTime(Base):
    __tablename__ = "lap_times"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    race_id: Mapped[int] = mapped_column(ForeignKey("races.id"), nullable=False)
    driver_id: Mapped[int] = mapped_column(ForeignKey("drivers.id"), nullable=False)
    lap_number: Mapped[int] = mapped_column(Integer, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    time: Mapped[str] = mapped_column(String(20), nullable=False)
    time_millis: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp(), nullable=False)

    __table_args__ = (
        UniqueConstraint("race_id", "driver_id", "lap_number", name="uq_lap_times_race_driver_lap"),
        Index("idx_lap_times_race", "race_id"),
        Index("idx_lap_times_driver", "driver_id"),
        Index("idx_lap_times_race_lap", "race_id", "lap_number"),
    )

    # Relationships
    race: Mapped["Race"] = relationship("Race", back_populates="lap_times")
    driver: Mapped["Driver"] = relationship("Driver", back_populates="lap_times")
