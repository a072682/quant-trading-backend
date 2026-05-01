#region 引入排程器套件
# APScheduler：Python 排程套件，負責定時觸發指定函式
# AsyncIOScheduler：支援 asyncio 的非同步排程器
from apscheduler.schedulers.asyncio import AsyncIOScheduler
#endregion

#region 引入評分與篩選的背景任務函式
# 這兩個函式是實際執行業務邏輯的地方
# 排程器只負責計時，時間到就呼叫這兩個函式
from app.services.signals.signals_service import run_signals_job
from app.services.stocks.stocks_service import run_filter_job
#endregion

#region 建立排程器並設定定時任務
# 作用：建立一個 APScheduler 實例，設定兩個定時任務後回傳
# 輸出：設定完成的 AsyncIOScheduler 實例（尚未啟動）
def create_scheduler() -> AsyncIOScheduler:
    # 建立排程器，指定時區為台北時間
    # 所有 cron 設定的時間都會以 Asia/Taipei 為準
    scheduler = AsyncIOScheduler(timezone="Asia/Taipei")

    # 每天 14:00 自動執行全量評分
    # 台股收盤時間為 13:30，14:00 確保當日資料已更新完成
    scheduler.add_job(
        run_signals_job,        # 要執行的函式
        "cron",                 # 觸發方式：固定時間
        hour=14,                # 每天 14 時
        minute=0,               # 0 分
        id="daily_signals",     # 任務唯一識別碼
        replace_existing=True,  # 重複啟動時覆蓋舊任務，避免重複
    )

    # 每週一 08:00 自動執行股票池篩選
    # 週一開盤前更新股票池，確保本週評分範圍是最新的
    scheduler.add_job(
        run_filter_job,         # 要執行的函式
        "cron",                 # 觸發方式：固定時間
        day_of_week="mon",      # 每週一
        hour=8,                 # 8 時
        minute=0,               # 0 分
        id="weekly_filter",     # 任務唯一識別碼
        replace_existing=True,  # 重複啟動時覆蓋舊任務，避免重複
    )

    return scheduler
#endregion
