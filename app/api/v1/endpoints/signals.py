from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List
from pydantic import BaseModel

from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_current_user

from app.schemas.common import APIResponse
from app.schemas.signal import SignalOut

from app.services import signal_service
from app.scheduler.jobs import run_daily_signal_job


class RunStockBody(BaseModel):
    stock_code: str
    stock_name: str

router = APIRouter()


@router.get("/today", response_model=APIResponse[SignalOut])
async def get_today_signal(
    stock_code: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """取得指定股票的今日評分訊號"""
    signal = await signal_service.get_today_signal(stock_code, db)

    if not signal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="今日尚未產生評分，請等待排程執行",
        )

    return APIResponse(message="取得今日評分成功", data=signal)


@router.get("/history/{stock_code}", response_model=APIResponse[List[SignalOut]])
async def get_signal_history(
    stock_code: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """取得指定股票最近 30 筆歷史評分記錄"""
    records = await signal_service.get_signal_history(stock_code, db)
    return APIResponse(message="取得歷史評分成功", data=records)


@router.get("/stats", response_model=APIResponse[dict])
async def get_stats(
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """回傳系統統計資訊：評分總筆數與最後一次執行時間"""
    stats = await signal_service.get_stats(db)
    return APIResponse(message="取得統計資訊成功", data=stats)


@router.get("/by-date/{date}", response_model=APIResponse[List[SignalOut]])
async def get_signals_by_date(
    date: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """取得指定日期（YYYY-MM-DD）所有股票的評分紀錄"""
    records = await signal_service.get_signals_by_date(date, db)
    return APIResponse(message="取得指定日期評分成功", data=records)


@router.post("/run-stock", response_model=APIResponse[SignalOut])
async def run_stock(
    body: RunStockBody,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """對單一股票立即執行評分計算，適合前端新增股票後呼叫"""
    signal = await signal_service.create_today_signal(body.stock_code, body.stock_name, db)
    return APIResponse(message="評分計算完成", data=signal)


@router.post("/run-now", response_model=APIResponse[None])
async def run_signal_now(_=Depends(get_current_user)):
    """手動觸發今日所有監控股票的評分計算"""
    await run_daily_signal_job()
    return APIResponse(message="評分計算執行完成", data=None)


@router.get("/today-all", response_model=APIResponse[List[SignalOut]])
async def get_today_all(
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """取得今日所有股票評分，依總分降冪排列"""
    records = await signal_service.get_today_all_signals(db)
    return APIResponse(message="取得今日所有評分成功", data=records)


@router.get("/top", response_model=APIResponse[List[SignalOut]])
async def get_top_signals(
    limit: int = Query(default=5, ge=1, le=50),
    min_score: int = Query(default=6),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """取得今日高分股票，依總分降冪排列"""
    records = await signal_service.get_top_signals(db, limit=limit, min_score=min_score)
    return APIResponse(message=f"取得今日 Top{limit} 評分成功", data=records)
