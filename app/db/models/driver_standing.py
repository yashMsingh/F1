"""DriverStanding model — World Drivers' Championship standings per round."""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.driver import Driver
    from app.db.models.season import Season


class DriverStanding(Base):
    __tablename__ = "driver_standings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    season_year: Mapped[int] = mapped_column(ForeignKey("seasons.season_year"), nullable=False)
    round: Mapped[int] = mapped_column(Integer, nullable=False)
    driver_id: Mapped[int] = mapped_column(ForeignKey("drivers.id"), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    points: Mapped[Decimal] = mapped_column(Numeric(7, 2), nullable=False)
    wins: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp(), nullable=False)

    __table_args__ = (
        UniqueConstraint("season_year", "round", "driver_id", name="uq_driver_standings_season_round_driver"),
        Index("idx_driver_standings_season", "season_year"),
    )

    # Relationships
    season: Mapped["Season"] = relationship("Season", back_populates="driver_standings")
    driver: Mapped["Driver"] = relationship("Driver", back_populates="driver_standings")
