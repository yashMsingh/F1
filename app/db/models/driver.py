"""Driver model — Formula 1 racing drivers."""

from datetime import date, datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Date, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.driver_standing import DriverStanding
    from app.db.models.lap_time import LapTime
    from app.db.models.pit_stop import PitStop
    from app.db.models.qualifying_result import QualifyingResult
    from app.db.models.race_result import RaceResult
    from app.db.models.sprint_result import SprintResult


class Driver(Base):
    __tablename__ = "drivers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    driver_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    permanent_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    code: Mapped[Optional[str]] = mapped_column(String(3), nullable=True)
    given_name: Mapped[str] = mapped_column(String(255), nullable=False)
    family_name: Mapped[str] = mapped_column(String(255), nullable=False)
    date_of_birth: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    nationality: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp(), nullable=False
    )

    # Relationships
    race_results: Mapped[List["RaceResult"]] = relationship("RaceResult", back_populates="driver")
    qualifying_results: Mapped[List["QualifyingResult"]] = relationship("QualifyingResult", back_populates="driver")
    sprint_results: Mapped[List["SprintResult"]] = relationship("SprintResult", back_populates="driver")
    pit_stops: Mapped[List["PitStop"]] = relationship("PitStop", back_populates="driver")
    lap_times: Mapped[List["LapTime"]] = relationship("LapTime", back_populates="driver")
    driver_standings: Mapped[List["DriverStanding"]] = relationship("DriverStanding", back_populates="driver")
