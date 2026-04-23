from datetime import datetime

from pydantic import BaseModel


class SimulationTradeOut(BaseModel):
    id: str
    date: str
    stock_code: str
    stock_name: str
    action: str
    price: float
    shares: int
    total_amount: float
    signal_score: int
    status: str
    buy_price: float | None = None
    profit: float
    profit_pct: float
    created_at: datetime

    model_config = {"from_attributes": True}


class SimulationSummaryOut(BaseModel):
    total_profit: float
    win_count: int
    loss_count: int
    total_count: int
    win_rate: float
    open_positions: int
