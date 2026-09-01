"""Constructor model — Formula 1 teams and constructors."""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.constructor_standing import ConstructorStanding
    from app.db.models.qualifying_result import QualifyingResult
    from app.db.models.race_result import RaceResult
    from app.db.models.sprint_result import SprintResult


class Constructor(Base):
    __tablename__ = "constructors"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    constructor_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    nationality: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp(), nullable=False
    )

    # Relationships
    race_results: Mapped[List["RaceResult"]] = relationship("RaceResult", back_populates="constructor")
    qualifying_results: Mapped[List["QualifyingResult"]] = relationship("QualifyingResult", back_populates="constructor")
    sprint_results: Mapped[List["SprintResult"]] = relationship("SprintResult", back_populates="constructor")
    constructor_standings: Mapped[List["ConstructorStanding"]] = relationship("ConstructorStanding", back_populates="constructor")
