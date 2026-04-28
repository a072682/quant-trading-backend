from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class StockPoolItem(BaseModel):
    id: str
    stock_code: str
    stock_name: str
    yield_pct: float
    market_cap: float
    updated_at: datetime

    model_config = {"from_attributes": True}


class FilterStatusOut(BaseModel):
    id: str
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    stock_count: Optional[int] = None
    error_message: Optional[str] = None

    model_config = {"from_attributes": True}
