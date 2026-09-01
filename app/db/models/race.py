"""Race model — Grand Prix race events scheduled and held per season."""

from datetime import date, datetime, time
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, String, Text, Time, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.circuit import Circuit
    from app.db.models.lap_time import LapTime
    from app.db.models.pit_stop import PitStop
    from app.db.models.qualifying_result import QualifyingResult
    from app.db.models.race_result import RaceResult
    from app.db.models.season import Season
    from app.db.models.sprint_result import SprintResult


class Race(Base):
    __tablename__ = "races"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    season_year: Mapped[int] = mapped_column(ForeignKey("seasons.season_year"), nullable=False)
    round: Mapped[int] = mapped_column(Integer, nullable=False)
    race_name: Mapped[str] = mapped_column(String(255), nullable=False)
    circuit_id: Mapped[int] = mapped_column(ForeignKey("circuits.id"), nullable=False)
    race_date: Mapped[date] = mapped_column(Date, nullable=False)
    race_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("season_year", "round", name="uq_races_season_round"),
        Index("idx_races_season", "season_year"),
        Index("idx_races_circuit", "circuit_id"),
    )

    # Relationships
    season: Mapped["Season"] = relationship("Season", back_populates="races")
    circuit: Mapped["Circuit"] = relationship("Circuit", back_populates="races")
    race_results: Mapped[List["RaceResult"]] = relationship("RaceResult", back_populates="race")
    qualifying_results: Mapped[List["QualifyingResult"]] = relationship("QualifyingResult", back_populates="race")
    sprint_results: Mapped[List["SprintResult"]] = relationship("SprintResult", back_populates="race")
    pit_stops: Mapped[List["PitStop"]] = relationship("PitStop", back_populates="race")
    lap_times: Mapped[List["LapTime"]] = relationship("LapTime", back_populates="race")
