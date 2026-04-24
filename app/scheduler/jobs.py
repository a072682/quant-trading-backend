from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.stock_pool import StockPool
from app.services.signal_service import create_today_signal
from app.services.simulation_service import check_and_close_positions
from app.services.stock_filter_service import filter_stock_pool, save_stock_pool

WATCH_LIST = [
    {"code": "0050", "name": "元大台灣50"},
    {"code": "0056", "name": "元大高股息"},
    {"code": "2886", "name": "兆豐金"},
    {"code": "2412", "name": "中華電"},
    {"code": "5880", "name": "合庫金"},
]


async def _get_scan_targets(db) -> list[dict]:
    """從 stock_pool 讀取掃描清單，若為空則退回 WATCH_LIST"""
    result = await db.execute(select(StockPool))
    pool = result.scalars().all()
    if pool:
        return [{"code": s.stock_code, "name": s.stock_name} for s in pool]
    print("stock_pool 為空，退回使用預設 WATCH_LIST")
    return WATCH_LIST


async def run_daily_signal_job():
    print("開始執行每日訊號任務")

    async with AsyncSessionLocal() as db:
        targets = await _get_scan_targets(db)
        print(f"本次掃描股票數：{len(targets)} 檔")

        success, failed = 0, 0
        for stock in targets:
            try:
                signal = await create_today_signal(
                    stock_code=stock["code"],
                    stock_name=stock["name"],
                    db=db,
                )
                print(f"[signal] {stock['code']} 完成，總分: {signal.total_score}")
                success += 1
            except Exception as exc:
                print(f"[signal] {stock['code']} 失敗: {exc}")
                failed += 1

        closed_positions = await check_and_close_positions(db)
        print(f"平倉筆數: {len(closed_positions)}")

    print(f"每日訊號任務完成：成功 {success} 檔，失敗 {failed} 檔，共掃描 {len(targets)} 檔")


async def run_weekly_stock_filter_job():
    print("開始執行每週股票池篩選任務")
    try:
        stocks = await filter_stock_pool()
        async with AsyncSessionLocal() as db:
            await save_stock_pool(stocks, db)
        print(f"股票池篩選完成，共 {len(stocks)} 檔入池")
    except Exception as exc:
        print(f"股票池篩選任務失敗: {exc}")


def create_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="Asia/Taipei")

    scheduler.add_job(
        run_daily_signal_job,
        trigger="cron",
        day_of_week="mon-fri",
        hour=14,
        minute=0,
        id="daily_signal",
    )

    scheduler.add_job(
        run_weekly_stock_filter_job,
        trigger="cron",
        day_of_week="mon",
        hour=8,
        minute=0,
        id="weekly_stock_filter",
    )

    return scheduler
