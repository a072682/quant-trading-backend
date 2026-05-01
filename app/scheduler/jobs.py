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

#region 引入模擬交易相關工具
# AsyncSessionLocal：直接建立資料庫連線
# 模擬交易 service 函式
from app.core.db.session import AsyncSessionLocal
from app.services.simulation.simulation_service import (
    get_trades_by_status,
    get_active_stock_codes,
    get_active_count,
    create_trade,
    update_to_holding,
    update_current_price,
    update_to_selling,
    close_trade,
)
from app.core.models.simulation_model import SimulationTrade
from datetime import date, datetime, timezone
#endregion

#region 引入 yfinance 取得股價
import yfinance as yf
#endregion

#region 引入評分資料查詢函式
from app.services.signals.signals_service import get_top_signals
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

#region 排程函式：after_signal_job — 每天 14:10 評分完成後處理新推薦
# 作用：取得今日前三名推薦，對尚未持有且未超過上限的股票新增 pending 記錄
async def after_signal_job() -> None:
    print("[排程] 開始處理今日推薦，新增待買入記錄")
    async with AsyncSessionLocal() as db:
        # 取得今日前三名推薦
        top_signals = await get_top_signals(db)

        if not top_signals:
            print("[排程] 今日無推薦股票，跳過")
            return

        # 取得目前所有進行中的股票代號
        active_codes = await get_active_stock_codes(db)

        # 取得目前進行中的總數量
        active_count = await get_active_count(db)

        # 今天的日期作為推薦日期
        today = date.today()

        for signal in top_signals:
            # 已達上限（3檔），停止新增
            if active_count >= 3:
                print(f"[排程] 持倉已達上限（3檔），忽略 {signal.stock_code}")
                break

            # 已持有這檔，忽略
            if signal.stock_code in active_codes:
                print(f"[排程] {signal.stock_code} 已在追蹤中，忽略")
                continue

            # 新增 pending 記錄
            await create_trade(db, signal.stock_code, signal.stock_name, today)
            active_count += 1

    print("[排程] 今日推薦處理完成")
#endregion

#region 排程函式：open_price_job — 每天 09:05 開盤後執行
# 作用：
# 1. 將 selling 記錄以開盤價賣出（改為 sold）
# 2. 將 pending 記錄以開盤價買入（改為 holding）
# 3. 判斷 holding 記錄的開盤價是否達停利停損
async def open_price_job() -> None:
    print("[排程] 開盤後處理開始")
    async with AsyncSessionLocal() as db:
        today = date.today()

        # 取得所有 selling 和 pending 記錄
        selling_trades = await get_trades_by_status(db, "selling")
        pending_trades = await get_trades_by_status(db, "pending")
        holding_trades = await get_trades_by_status(db, "holding")

        # 合併需要抓開盤價的股票代號
        all_trades = selling_trades + pending_trades + holding_trades
        if not all_trades:
            print("[排程] 目前無進行中的交易，跳過")
            return

        # 用 yfinance 抓取今天開盤價
        for trade in all_trades:
            try:
                # yfinance 台股代號格式：股票代號.TW
                ticker = yf.Ticker(f"{trade.stock_code}.TW")
                # 抓取今天的資料
                hist = ticker.history(period="1d")

                if hist.empty:
                    print(f"[排程] {trade.stock_code} 今日無資料，跳過")
                    continue

                # 取得開盤價
                open_price = round(float(hist["Open"].iloc[0]), 2)
                print(f"[排程] {trade.stock_code} 今日開盤價：{open_price}")

                if trade.status == "selling":
                    # 以開盤價完成賣出
                    profit_pct = (open_price - trade.buy_price) / trade.buy_price * 100
                    reason = "停利" if profit_pct >= 0 else "停損"
                    await close_trade(db, trade.id, open_price, reason, today)

                elif trade.status == "pending":
                    # 以開盤價買入
                    await update_to_holding(db, trade.id, open_price, today)

                elif trade.status == "holding":
                    # 判斷開盤價是否達停利停損
                    profit_pct = (open_price - trade.buy_price) / trade.buy_price * 100
                    if profit_pct >= 6.0:
                        await close_trade(db, trade.id, open_price, "停利", today)
                    elif profit_pct <= -3.0:
                        await close_trade(db, trade.id, open_price, "停損", today)

            except Exception as e:
                print(f"[排程] {trade.stock_code} 開盤價處理失敗：{e}")

    print("[排程] 開盤後處理完成")
#endregion

#region 排程函式：close_price_job — 每天 14:05 收盤後執行
# 作用：更新所有 holding 記錄的收盤價和損益，達停利停損則標記為 selling
async def close_price_job() -> None:
    print("[排程] 收盤後更新損益開始")
    async with AsyncSessionLocal() as db:
        # 取得所有持有中的記錄
        holding_trades = await get_trades_by_status(db, "holding")

        if not holding_trades:
            print("[排程] 目前無持有中的交易，跳過")
            return

        for trade in holding_trades:
            try:
                # 用 yfinance 抓取今天收盤價
                ticker = yf.Ticker(f"{trade.stock_code}.TW")
                hist = ticker.history(period="1d")

                if hist.empty:
                    print(f"[排程] {trade.stock_code} 今日無資料，跳過")
                    continue

                # 取得收盤價
                close_price = round(float(hist["Close"].iloc[0]), 2)

                # 計算損益百分比
                profit_pct = (close_price - trade.buy_price) / trade.buy_price * 100
                profit_pct = round(profit_pct, 2)

                print(f"[排程] {trade.stock_code} 收盤價：{close_price}，損益：{profit_pct}%")

                # 更新現價和損益
                await update_current_price(db, trade.id, close_price)

                # 達到停利停損條件，標記為待賣出
                if profit_pct >= 6.0:
                    print(f"[排程] {trade.stock_code} 達停利條件（{profit_pct}%），標記待賣出")
                    await update_to_selling(db, trade.id)
                elif profit_pct <= -3.0:
                    print(f"[排程] {trade.stock_code} 達停損條件（{profit_pct}%），標記待賣出")
                    await update_to_selling(db, trade.id)

            except Exception as e:
                print(f"[排程] {trade.stock_code} 收盤價更新失敗：{e}")

    print("[排程] 收盤後更新損益完成")
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

    # 每天 09:05 開盤後：處理待賣出和待買入
    scheduler.add_job(
        open_price_job,
        "cron",
        hour=9,
        minute=5,
        id="open_price",
        replace_existing=True,
    )

    # 每天 14:05 收盤後：更新損益、檢查停利停損
    scheduler.add_job(
        close_price_job,
        "cron",
        hour=14,
        minute=5,
        id="close_price",
        replace_existing=True,
    )

    # 每天 14:10 評分完成後：處理今日新推薦
    scheduler.add_job(
        after_signal_job,
        "cron",
        hour=14,
        minute=10,
        id="after_signal",
        replace_existing=True,
    )

    return scheduler
#endregion

