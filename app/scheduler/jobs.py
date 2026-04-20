from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.db.session import AsyncSessionLocal
from app.services.signal_service import create_today_signal

WATCH_LIST = [
    {"code": "0050", "name": "元大台灣50"},
    {"code": "0056", "name": "元大高股息"},
    {"code": "2886", "name": "兆豐金"},
    {"code": "2412", "name": "中華電"},
    {"code": "5880", "name": "合庫金"},
]


async def run_daily_signal_job():
    """每日排程任務：收盤後自動計算所有監控股票的評分"""
    print("開始執行每日評分計算任務...")

    async with AsyncSessionLocal() as db:
        for stock in WATCH_LIST:
            try:
                signal = await create_today_signal(
                    stock_code=stock["code"],
                    stock_name=stock["name"],
                    db=db,
                )
                print(f"  {stock['name']} 評分完成：{signal.total_score} 分")
            except Exception as e:
                print(f"  {stock['name']} 評分失敗：{e}")

    print("每日評分計算任務完成")


def create_scheduler() -> AsyncIOScheduler:
    """建立並設定排程器（台灣時間週一至週五 14:00 執行）"""
    scheduler = AsyncIOScheduler(timezone="Asia/Taipei")

    scheduler.add_job(
        run_daily_signal_job,
        trigger="cron",
        day_of_week="mon-fri",
        hour=14,
        minute=0,
        id="daily_signal",
    )

    return scheduler
