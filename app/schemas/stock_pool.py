from datetime import datetime
from pydantic import BaseModel


class StockPoolItem(BaseModel):
    id: str
    stock_code: str
    stock_name: str
    yield_pct: float
    market_cap: float
    updated_at: datetime

    model_config = {"from_attributes": True}
