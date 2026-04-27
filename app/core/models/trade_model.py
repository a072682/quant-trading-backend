import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Float, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import Base


class Trade(Base):
    """交易紀錄資料表：儲存每一筆買進與賣出紀錄"""
    __tablename__ = "trades"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    date: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    stock_code: Mapped[str] = mapped_column(String(10), nullable=False)
    stock_name: Mapped[str] = mapped_column(String(50), nullable=False)

    action: Mapped[str] = mapped_column(String(10), nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    shares: Mapped[int] = mapped_column(Integer, nullable=False)
    total_amount: Mapped[float] = mapped_column(Float, nullable=False)
    profit: Mapped[float] = mapped_column(Float, default=0.0)

    reason: Mapped[str] = mapped_column(Text, nullable=True)
    order_id: Mapped[str] = mapped_column(String(100), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
