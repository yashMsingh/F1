"""ConstructorStanding model — World Constructors' Championship standings per round."""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.constructor import Constructor
    from app.db.models.season import Season


class ConstructorStanding(Base):
    __tablename__ = "constructor_standings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    season_year: Mapped[int] = mapped_column(ForeignKey("seasons.season_year"), nullable=False)
    round: Mapped[int] = mapped_column(Integer, nullable=False)
    constructor_id: Mapped[int] = mapped_column(ForeignKey("constructors.id"), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    points: Mapped[Decimal] = mapped_column(Numeric(7, 2), nullable=False)
    wins: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp(), nullable=False)

    __table_args__ = (
        UniqueConstraint("season_year", "round", "constructor_id", name="uq_constructor_standings_season_round_constructor"),
        Index("idx_constructor_standings_season", "season_year"),
    )

    # Relationships
    season: Mapped["Season"] = relationship("Season", back_populates="constructor_standings")
    constructor: Mapped["Constructor"] = relationship("Constructor", back_populates="constructor_standings")
