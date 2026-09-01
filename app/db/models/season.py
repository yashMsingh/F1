"""Season model — Formula 1 championship seasons."""

from sqlalchemy import Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Season(Base):
    __tablename__ = "seasons"

    season_year: Mapped[int] = mapped_column(Integer, primary_key=True)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    races = relationship("Race", back_populates="season")
    driver_standings = relationship("DriverStanding", back_populates="season")
    constructor_standings = relationship("ConstructorStanding", back_populates="season")
