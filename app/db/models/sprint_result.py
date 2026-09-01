"""SprintResult model — Official classifications for Sprint race sessions."""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.constructor import Constructor
    from app.db.models.driver import Driver
    from app.db.models.race import Race


class SprintResult(Base):
    __tablename__ = "sprint_results"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    race_id: Mapped[int] = mapped_column(ForeignKey("races.id"), nullable=False)
    driver_id: Mapped[int] = mapped_column(ForeignKey("drivers.id"), nullable=False)
    constructor_id: Mapped[int] = mapped_column(ForeignKey("constructors.id"), nullable=False)
    car_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    grid_position: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    source_position: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    position_text: Mapped[str] = mapped_column(String(10), nullable=False)
    points: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0.0"), server_default="0", nullable=False)
    laps_completed: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    status: Mapped[str] = mapped_column(String(100), nullable=False)
    time_millis: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    time_text: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    fastest_lap_rank: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    fastest_lap_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    fastest_lap_time: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    fastest_lap_time_millis: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp(), nullable=False)

    __table_args__ = (
        UniqueConstraint("race_id", "driver_id", name="uq_sprint_results_race_driver"),
        Index("idx_sprint_race", "race_id"),
    )

    # Relationships
    race: Mapped["Race"] = relationship("Race", back_populates="sprint_results")
    driver: Mapped["Driver"] = relationship("Driver", back_populates="sprint_results")
    constructor: Mapped["Constructor"] = relationship("Constructor", back_populates="sprint_results")
