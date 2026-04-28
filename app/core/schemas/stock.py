from pydantic import BaseModel


class KLineItem(BaseModel):
    time: str
    open: float
    high: float
    low: float
    close: float
    volume: int
