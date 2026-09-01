"""QualifyingResult model — Official qualifying session classifications."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.constructor import Constructor
    from app.db.models.driver import Driver
    from app.db.models.race import Race


class QualifyingResult(Base):
    __tablename__ = "qualifying_results"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    race_id: Mapped[int] = mapped_column(ForeignKey("races.id"), nullable=False)
    driver_id: Mapped[int] = mapped_column(ForeignKey("drivers.id"), nullable=False)
    constructor_id: Mapped[int] = mapped_column(ForeignKey("constructors.id"), nullable=False)
    car_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    q1_time: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    q1_time_millis: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    q2_time: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    q2_time_millis: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    q3_time: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    q3_time_millis: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp(), nullable=False)

    __table_args__ = (
        UniqueConstraint("race_id", "driver_id", name="uq_qualifying_results_race_driver"),
        Index("idx_qualifying_race", "race_id"),
        Index("idx_qualifying_driver", "driver_id"),
    )

    # Relationships
    race: Mapped["Race"] = relationship("Race", back_populates="qualifying_results")
    driver: Mapped["Driver"] = relationship("Driver", back_populates="qualifying_results")
    constructor: Mapped["Constructor"] = relationship("Constructor", back_populates="qualifying_results")
