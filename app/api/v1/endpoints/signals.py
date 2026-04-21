from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_current_user

from app.schemas.common import APIResponse
from app.schemas.signal import SignalOut

from app.services import signal_service
from app.scheduler.jobs import run_daily_signal_job

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


@router.post("/run-now", response_model=APIResponse[None])
async def run_signal_now(_=Depends(get_current_user)):
    """手動觸發今日所有監控股票的評分計算"""
    await run_daily_signal_job()
    return APIResponse(message="評分計算執行完成", data=None)
