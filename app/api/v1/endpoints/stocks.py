from fastapi import APIRouter, Depends
from typing import List
from asyncio import get_event_loop

import yfinance as yf

from app.api.deps import get_current_user
from app.schemas.common import APIResponse
from app.schemas.stock import KLineItem
from app.services.signal_service import _thread_pool

router = APIRouter()


def _fetch_kline(ticker_symbol: str) -> list:
    ticker = yf.Ticker(ticker_symbol)
    hist = ticker.history(period="3mo")

    if hist.empty:
        return []

    result = []
    for dt, row in hist.iterrows():
        result.append({
            "time": dt.strftime("%Y-%m-%d"),
            "open": round(float(row["Open"]), 2),
            "high": round(float(row["High"]), 2),
            "low": round(float(row["Low"]), 2),
            "close": round(float(row["Close"]), 2),
            "volume": int(row["Volume"]),
        })
    return result


@router.get("/kline/{stock_code}", response_model=APIResponse[List[KLineItem]])
async def get_kline(
    stock_code: str,
    _=Depends(get_current_user),
):
    """取得指定股票最近 3 個月的日K線數據"""
    ticker_symbol = f"{stock_code}.TW"
    loop = get_event_loop()
    data = await loop.run_in_executor(_thread_pool, _fetch_kline, ticker_symbol)
    return APIResponse(message="取得K線數據成功", data=data)
