from datetime import datetime, timezone
from sqlalchemy import String, Integer, Text, JSON, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Run(Base):
    __tablename__ = "runs"

    run_id: Mapped[str] = mapped_column(String, primary_key=True)
    client_id: Mapped[str] = mapped_column(String, index=True)
    nbr_pts: Mapped[int] = mapped_column(Integer)
    step: Mapped[int] = mapped_column(Integer)
    active_checkpoint: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="queued")
    checkpoints: Mapped[list] = mapped_column(JSON, default=list)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )
