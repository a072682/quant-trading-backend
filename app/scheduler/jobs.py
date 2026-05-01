#region 設定定時排程器的函式內容
# APScheduler：Python 排程套件，負責定時觸發指定函式
# AsyncIOScheduler：支援 asyncio 的非同步排程器
from apscheduler.schedulers.asyncio import AsyncIOScheduler
#endregion

#region 引入評分背景任務函式
# _run_scoring_task：對股票進行評分的函式
from app.api.signals.signals import _run_scoring_task
#endregion

#region 引入篩選所需的資料庫工具
# AsyncSessionLocal：借出連線通道的函式
# FilterStatus：任務確認狀態資料表
# _run_filter_task:篩選股票的函式
# datetime:產生現在時間
# timezone：確認時區
from app.core.db.session import AsyncSessionLocal
from app.core.models.stock_pool_model import FilterStatus
from app.api.stocks.stocks import _run_filter_task
from datetime import datetime, timezone
#endregion

#region 包裝函式：scheduled_filter_job 
# 作用：排程器無法使用 FastAPI 的 BackgroundTasks 和依賴注入
#       所以需要手動建立 FilterStatus 記錄，再呼叫 _run_filter_task
async def scheduled_filter_job() -> None:
    
    # 借出一條資料庫連線並新建一份資料表資料並寫入FilterStatus資料表
    # 借出一條資料庫連線稱為db
    async with AsyncSessionLocal() as db:
        # 建立一筆新的 FilterStatus 資料表資料，狀態設為 running
        fs = FilterStatus(
            status="running",
            started_at=datetime.now(timezone.utc),
        )
        # 將資料加入待執行名單
        db.add(fs)
        # 執行待執行指令
        await db.commit()
        # 重新從資料庫讀取，取得資料庫自動產生的 id
        await db.refresh(fs)

    # 用取得的 id 呼叫實際的篩選函式
    await _run_filter_task(fs.id)
#endregion

#region 建立排程器並設定定時任務
# 作用：建立一個 APScheduler 實例，設定兩個定時任務後回傳
# 輸出：設定完成的 AsyncIOScheduler 實例（尚未啟動）
def create_scheduler() -> AsyncIOScheduler:
    # 建立排程器，指定時區為台北時間
    scheduler = AsyncIOScheduler(timezone="Asia/Taipei")

    # 每天 14:00 自動執行全量評分
    # 台股收盤時間為 13:30，14:00 確保當日資料已更新完成
    scheduler.add_job(
        _run_scoring_task,      # 直接呼叫，不需要包裝
        "cron",
        hour=14,
        minute=0,
        id="daily_signals",
        replace_existing=True,
    )

    # 每週一 08:00 自動執行股票池篩選
    # 週一開盤前更新股票池，確保本週評分範圍是最新的
    scheduler.add_job(
        scheduled_filter_job,   # 透過包裝函式呼叫
        "cron",
        day_of_week="mon",
        hour=8,
        minute=0,
        id="weekly_filter",
        replace_existing=True,
    )

    return scheduler
#endregion