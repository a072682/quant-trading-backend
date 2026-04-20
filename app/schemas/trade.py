from pydantic import BaseModel
from typing import Optional


class TradeBuyIn(BaseModel):
    """買進請求的輸入格式（前端送來）"""
    stock_code: str
    stock_name: str
    shares: int
    price: float
    reason: str


class TradeSellIn(BaseModel):
    """賣出請求的輸入格式（前端送來）"""
    stock_code: str
    shares: int
    price: float
    reason: str


class TradeOut(BaseModel):
    """交易紀錄的回應格式（回傳給前端）"""
    id: str
    date: str
    stock_code: str
    stock_name: str
    action: str
    price: float
    shares: int
    total_amount: float
    profit: float
    reason: Optional[str] = None
    order_id: Optional[str] = None

    model_config = {"from_attributes": True}


class MonthlyStatsOut(BaseModel):
    """月度統計的回應格式"""
    month: str
    total_profit: float
    win_count: int
    loss_count: int
    total_count: int
    win_rate: float
