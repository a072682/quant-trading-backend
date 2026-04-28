import asyncio
from asyncio import get_event_loop
from datetime import datetime, timezone
from typing import List

import yfinance as yf
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.db.session import AsyncSessionLocal
from app.core.models.stock_pool_model import FilterStatus, StockPool
from app.core.schemas.common import APIResponse
from app.core.schemas.stock import KLineItem
from app.core.schemas.stock_pool import FilterStatusOut, StockPoolItem
from app.services.signal_service import _thread_pool
from app.services.stock_filter_service import filter_stock_pool, save_stock_pool

router = APIRouter()

# 持有背景任務的強參考，防止被 GC 提早回收
_background_tasks: set[asyncio.Task] = set()


# ── K 線 ─────────────────────────────────────────────────────────────────────

def _fetch_kline(ticker_symbol: str) -> list:
    ticker = yf.Ticker(ticker_symbol)
    hist = ticker.history(period="3mo")
    if hist.empty:
        return []
    return [
        {
            "time": dt.strftime("%Y-%m-%d"),
            "open": round(float(row["Open"]), 2),
            "high": round(float(row["High"]), 2),
            "low": round(float(row["Low"]), 2),
            "close": round(float(row["Close"]), 2),
            "volume": int(row["Volume"]),
        }
        for dt, row in hist.iterrows()
    ]


@router.get("/kline/{stock_code}", response_model=APIResponse[List[KLineItem]])
async def get_kline(
    stock_code: str,
    _=Depends(get_current_user),
):
    """取得指定股票最近 3 個月的日K線數據"""
    loop = get_event_loop()
    data = await loop.run_in_executor(_thread_pool, _fetch_kline, f"{stock_code}.TW")
    return APIResponse(message="取得K線數據成功", data=data)


# ── 股票池 ────────────────────────────────────────────────────────────────────

@router.get("/pool", response_model=APIResponse[List[StockPoolItem]])
async def get_stock_pool(
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """取得目前股票池清單"""
    result = await db.execute(select(StockPool).order_by(StockPool.stock_code))
    return APIResponse(message="取得股票池成功", data=result.scalars().all())


# ── 篩選狀態 ──────────────────────────────────────────────────────────────────

async def _get_latest_status(db: AsyncSession) -> FilterStatus | None:
    result = await db.execute(
        select(FilterStatus).order_by(FilterStatus.started_at.desc()).limit(1)
    )
    return result.scalars().first()


@router.get("/status", response_model=APIResponse[FilterStatusOut])
async def get_filter_status(
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """取得最新一次篩選任務的狀態（前端用此輪詢）"""
    status = await _get_latest_status(db)
    if status is None:
        return APIResponse(message="尚無篩選紀錄", data=None)
    return APIResponse(message="取得狀態成功", data=status)


# ── 背景篩選任務 ───────────────────────────────────────────────────────────────

async def _update_filter_status(
    status_id: str,
    *,
    status: str,
    stock_count: int | None = None,
    error_message: str | None = None,
) -> None:
    """以獨立 session 更新 FilterStatus，確保不受其他 session 狀態影響"""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(FilterStatus).where(FilterStatus.id == status_id)
        )
        fs = result.scalars().first()
        if fs:
            fs.status = status
            fs.completed_at = datetime.now(timezone.utc)
            if stock_count is not None:
                fs.stock_count = stock_count
            if error_message is not None:
                fs.error_message = error_message[:500]
        await db.commit()
        print(f"[篩選狀態] status_id={status_id} 已更新為 {status}，股票數={stock_count}")


async def _run_filter_background(status_id: str) -> None:
    """背景執行篩選：各步驟使用獨立 session，避免 session 狀態交叉污染"""
    print(f"[股票池篩選] 開始執行背景篩選，status_id={status_id}")
    try:
        # Step 1: 執行篩選
        stocks = await filter_stock_pool()
        print(f"[股票池篩選] TWSE 取得 {len(stocks)} 檔股票（已通過篩選條件）")

        # Step 2: 存入 stock_pool（獨立 session）
        async with AsyncSessionLocal() as db:
            print(f"[股票池篩選] 開始寫入股票池資料表，共 {len(stocks)} 筆...")
            await save_stock_pool(stocks, db)
            print(f"[股票池篩選] 篩選完成，共 {len(stocks)} 檔成功寫入資料庫")

        # Step 3: 更新 FilterStatus（再另一個獨立 session）
        await _update_filter_status(
            status_id, status="completed", stock_count=len(stocks)
        )

    except Exception as exc:
        print(f"[股票池篩選] 篩選任務失敗：{exc}")
        try:
            await _update_filter_status(
                status_id, status="failed", error_message=str(exc)
            )
        except Exception as inner:
            print(f"[股票池篩選] 更新失敗狀態時亦發生例外：{inner}")


@router.post("/filter", response_model=APIResponse)
async def run_stock_filter(
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """啟動背景股票篩選任務（若已有任務進行中則拒絕）"""
    latest = await _get_latest_status(db)
    if latest and latest.status == "running":
        raise HTTPException(status_code=400, detail="已有篩選任務進行中，請稍後再試")

    fs = FilterStatus(
        status="running",
        started_at=datetime.now(timezone.utc),
    )
    db.add(fs)
    await db.commit()
    await db.refresh(fs)

    task = asyncio.create_task(_run_filter_background(fs.id))
    # 持有強參考防止 GC，任務完成後自動移除
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)

    return APIResponse(message="篩選已開始，請透過 GET /stocks/status 輪詢進度")
