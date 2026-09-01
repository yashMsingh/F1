"""PitStop model — In-race pit stop data with duration and lap timing."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.driver import Driver
    from app.db.models.race import Race


class PitStop(Base):
    __tablename__ = "pit_stops"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    race_id: Mapped[int] = mapped_column(ForeignKey("races.id"), nullable=False)
    driver_id: Mapped[int] = mapped_column(ForeignKey("drivers.id"), nullable=False)
    stop_number: Mapped[int] = mapped_column(Integer, nullable=False)
    lap: Mapped[int] = mapped_column(Integer, nullable=False)
    time_of_day: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    duration_text: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    duration_millis: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp(), nullable=False)

    __table_args__ = (
        UniqueConstraint("race_id", "driver_id", "stop_number", name="uq_pit_stops_race_driver_stop"),
        Index("idx_pit_stops_race", "race_id"),
        Index("idx_pit_stops_driver", "driver_id"),
    )

    # Relationships
    race: Mapped["Race"] = relationship("Race", back_populates="pit_stops")
    driver: Mapped["Driver"] = relationship("Driver", back_populates="pit_stops")
