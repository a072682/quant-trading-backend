from pydantic import BaseModel
from typing import Optional


class SignalOut(BaseModel):
    """評分訊號的回應格式（回傳給前端）"""
    id: str
    date: str
    stock_code: str
    stock_name: str
    institutional_score: int
    ma_score: int
    volume_score: int
    yield_score: int = 0
    total_score: int
    ai_action: Optional[str] = None
    ai_reason: Optional[str] = None

    model_config = {"from_attributes": True}
