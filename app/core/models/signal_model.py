import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Float, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import Base


class Signal(Base):
    """每日評分訊號資料表：儲存每天每檔股票的評分結果"""
    __tablename__ = "signals"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    date: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    stock_code: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    stock_name: Mapped[str] = mapped_column(String(50), nullable=False)

    institutional_score: Mapped[int] = mapped_column(Integer, default=0)
    ma_score: Mapped[int] = mapped_column(Integer, default=0)
    volume_score: Mapped[int] = mapped_column(Integer, default=0)
    yield_score: Mapped[int] = mapped_column(Integer, default=0)
    futures_score: Mapped[int] = mapped_column(Integer, default=0)
    total_score: Mapped[int] = mapped_column(Integer, default=0)

    ai_action: Mapped[str] = mapped_column(String(10), nullable=True)
    ai_reason: Mapped[str] = mapped_column(Text, nullable=True)
    confidence: Mapped[int] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
