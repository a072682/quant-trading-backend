from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List, Optional
from pydantic import BaseModel

from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_current_user

from app.schemas.common import APIResponse
from app.schemas.signal import SignalOut

from sqlalchemy import select as sa_select
from app.models.simulation import SimulationTrade
from app.models.stock_pool import StockPool
from app.services import signal_service
from app.services.signal_service import create_today_signal
from app.scheduler.jobs import WATCH_LIST


class RunStockBody(BaseModel):
    stock_code: str
    stock_name: str


class StockItem(BaseModel):
    code: str
    name: str


class RunNowBody(BaseModel):
    stocks: Optional[List[StockItem]] = None


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


@router.post("/run-now", response_model=APIResponse[List[SignalOut]])
async def run_signal_now(
    body: RunNowBody = RunNowBody(),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """手動觸發評分計算（含 AI 分析）。
    傳入 stocks 則只計算指定清單；不傳則從 stock_pool 讀取完整清單，pool 為空才退回 WATCH_LIST。
    """
    if body.stocks:
        targets = [{"code": s.code, "name": s.name} for s in body.stocks]
    else:
        pool_result = await db.execute(
            sa_select(StockPool.stock_code, StockPool.stock_name)
        )
        pool_rows = pool_result.all()
        targets = (
            [{"code": row[0], "name": row[1]} for row in pool_rows]
            if pool_rows
            else WATCH_LIST
        )

    results = []
    for stock in targets:
        try:
            signal = await create_today_signal(
                stock_code=stock["code"],
                stock_name=stock["name"],
                db=db,
                skip_ai=False,
            )
            results.append(signal)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"{stock['code']} 評分失敗: {exc}",
            )

    return APIResponse(message=f"評分計算完成，共 {len(results)} 檔", data=results)


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
    limit: int = Query(default=3, ge=1, le=50),
    min_score: int = Query(default=6),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """取得今日高分股票，排除已有模擬持倉的股票，依總分降冪排列"""
    open_result = await db.execute(
        sa_select(SimulationTrade.stock_code).distinct().where(
            SimulationTrade.status == "open",
            SimulationTrade.action == "buy",
        )
    )
    exclude_codes = [row[0] for row in open_result.all()]
    print(f"[top] exclude_codes: {exclude_codes}")
    print(f"[top] min_score: {min_score}, limit: {limit}")

    records = await signal_service.get_top_signals(
        db, limit=limit, min_score=min_score, exclude_codes=exclude_codes
    )
    return APIResponse(message=f"取得今日 Top{limit} 推薦成功", data=records)
