#region 引入 FastAPI 相關套件
# APIRouter：定義這個模組的路由群組
# BackgroundTasks：FastAPI 內建背景任務，讓 API 立即回傳後繼續執行耗時工作
# Depends：FastAPI 依賴注入
# HTTPException：拋出 HTTP 錯誤
# status：HTTP 狀態碼常數
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
#endregion


#region 引入時間工具
# datetime、timezone：產生 UTC 時間，用於記錄篩選開始 / 完成時間
from datetime import datetime, timezone
#endregion


#region 引入資料庫連線依賴
# AsyncSession：非同步資料庫連線物件類型
from sqlalchemy.ext.asyncio import AsyncSession

# select：建立 SQL SELECT 查詢
from sqlalchemy import select

# get_db：FastAPI 依賴注入函式，負責借出並歸還資料庫連線
from app.core.db.session import get_db
#endregion


#region 引入安全模組
# get_current_user：驗證 JWT Token，回傳目前登入的使用者 id
from app.core.auth.security import get_current_user
#endregion


#region 引入 ORM 模型
# 引入FilterStatus資料表，負責記錄篩選任務是否執行中
from app.core.models.stock_pool_model import FilterStatus
#endregion


#region 引入 API 回應格式
# APIResponse：統一的 API 回傳格式
from app.core.schemas.common import APIResponse

# StockPoolItem：股票池清單的回應格式
# FilterStatusOut：篩選任務狀態的回應格式
from app.core.schemas.stock_pool import StockPoolItem, FilterStatusOut
#endregion


#region 引入 TWSE 與 yfinance 客戶端
# fetch_twse_stocks：從 TWSE 官網抓取所有上市股票清單
from app.core.stocks.twse_client import fetch_twse_stocks

# filter_by_yfinance：逐批用 yfinance 篩選符合條件的股票
from app.core.stocks.yfinance_client import filter_by_yfinance
#endregion


#region 引入股票池 Service
# save_stock_pool：清空舊資料並寫入新篩選結果
# get_stock_pool：查詢股票池所有股票
# get_filter_status：查詢最新一筆篩選任務狀態
from app.services.stocks.stocks_service import save_stock_pool, get_stock_pool, get_filter_status
#endregion


#region 建立路由器
# 此模組的所有路由都會掛在這個 router 下
# 由 router.py 負責決定 prefix（/stocks）
router = APIRouter()
#endregion


#region 內部函式：_run_filter_task — 背景執行完整的股票池篩選流程
# 作用：依序執行 fetch_twse_stocks → filter_by_yfinance → save_stock_pool
#       並在過程中更新 FilterStatus 狀態（running → completed / failed）
# 輸入：filter_status_id（本次任務的 FilterStatus 資料表 id）
# 注意：此函式為同步函式，由 FastAPI BackgroundTasks 在背景執行
#       需自行建立新的資料庫 Session（不能重用 request 的 Session）
async def _run_filter_task(filter_status_id: str) -> None:
    """背景執行完整篩選流程，並同步更新 FilterStatus 狀態"""

    # 引入借出資料庫請求通道函式
    from app.core.db.session import AsyncSessionLocal

    # 將AsyncSessionLocal命名為db
    async with AsyncSessionLocal() as db:
        try:
            # 第一步：抓取所有上市股票清單
            raw_stocks = await fetch_twse_stocks()

            # 第二步：使用yfinance查詢篩選符合條件的股票
            passed_stocks = await filter_by_yfinance(raw_stocks)

            # 第三步：清空舊股票池，寫入新篩選結果
            await save_stock_pool(passed_stocks, db)

            # 篩選成功：更新 FilterStatus 為 completed
            result = await db.execute(
                select(FilterStatus).where(FilterStatus.id == filter_status_id)
            )
            fs = result.scalar_one_or_none()
            if fs:
                # 記錄完成時間與通過數量
                fs.status = "completed"
                fs.completed_at = datetime.now(timezone.utc)
                fs.stock_count = len(passed_stocks)
                await db.commit()

            print(f"[篩選任務] 完成，共通過 {len(passed_stocks)} 支股票")

        except Exception as e:
            # 篩選失敗：更新 FilterStatus 為 failed，記錄錯誤原因
            print(f"[篩選任務] 執行失敗：{e}")
            try:
                async with AsyncSessionLocal() as err_db:
                    result = await err_db.execute(
                        select(FilterStatus).where(FilterStatus.id == filter_status_id)
                    )
                    fs = result.scalar_one_or_none()
                    if fs:
                        fs.status = "failed"
                        fs.completed_at = datetime.now(timezone.utc)
                        # 將錯誤原因截斷至 500 字，避免超出欄位長度
                        fs.error_message = str(e)[:500]
                        await err_db.commit()
            except Exception as inner_e:
                print(f"[篩選任務] 更新失敗狀態時發生錯誤：{inner_e}")
#endregion


#region 路由：POST /filter — 手動觸發股票池篩選（背景執行）
# 輸入：
#   background_tasks（FastAPI 背景任務管理器）
#   current_user（依賴注入，驗證 token 確認已登入）
#   db（資料庫連線，用於建立 FilterStatus 紀錄與防止重複執行）
# 輸出：APIResponse（含任務已啟動的訊息），HTTP 202
# 防重複：若已有 running 狀態的任務，回傳 400 Bad Request
@router.post("/filter", response_model=APIResponse, status_code=202)
async def trigger_filter(
    # BackgroundTasks：FastAPI 提供的背景任務管理器，固定寫法不能變更
    background_tasks: BackgroundTasks,
    # get_current_user：驗證 token，確認使用者已登入
    current_user: str = Depends(get_current_user),
    # get_db：依賴注入，自動借出並歸還資料庫連線
    db: AsyncSession = Depends(get_db),
):
    """手動觸發股票池篩選，立即回傳 202，篩選在背景執行"""
    
    # 印出篩選訊息
    print(f"[篩選 API] 使用者 {current_user} 觸發篩選")

    # 防止重複執行：查詢是否已有 running 狀態的任務
    # 先搜尋FilterStatus這個資料表確認欄位status是否有等於running並將結果傳回result
    # 但result目前並不能讀取(會是一團記憶體位置)
    result = await db.execute(
        select(FilterStatus).where(FilterStatus.status == "running")
    )
    # scalar_one_or_none代表從查詢結果裡取出第一筆資料的第一個欄位，如果沒有就回傳 None
    # 可能會是以下格式內容:
    # running.id           # "abc-123-def-456"
    # running.status       # "running"
    # running.started_at   # 2026-05-01 14:00:00
    # running.stock_count  # None（還在跑，還不知道）
    # running.error_message # None
    # 或是
    # running  # None
    running = result.scalar_one_or_none()

    # 如果running有資料則執行
    if running:
        # 印出訊息
        print("[篩選 API] 已有篩選任務在執行中，拒絕重複觸發")

        # raise代表輸出錯誤訊息並停止函式執行
        # HTTPException代表錯誤訊息的格式
        raise HTTPException(
            # 400 Bad Request：錯誤訊息內容
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="篩選任務執行中，請稍後再試",
        )

    # FilterStatus 寫入新資料，設定status欄位資料為 running以及時間
    fs = FilterStatus(
        status="running",
        # 記錄任務開始時間（UTC）
        started_at=datetime.now(timezone.utc),
    )
    # add代表先將資料放入像是購物車的空間
    db.add(fs)
    # 執行放入購物車的檔案
    await db.commit()
    # 重新從資料表讀取資料
    # 會像是這樣
    # fs.id             # "abc-123-def-456"  ← 資料庫自動產生
    # fs.status         # "running"
    # fs.started_at     # 2026-05-01 14:00:00
    # fs.completed_at   # None（還沒完成）
    # fs.stock_count    # None（還沒跑完）
    # fs.error_message  # None（沒有錯誤）
    await db.refresh(fs)

    # 將完整篩選流程加入背景任務佇列
    # FastAPI 會在回傳 response 後自動執行
    # background_tasks 代表先把 API 回應送給前端，然後再在背景執行耗時的工作
    # add_task() 代表工作加入背景任務清單，格式是：.add_task(要執行的函式, 參數1, 參數2, ...)
    background_tasks.add_task(_run_filter_task, fs.id)

    # 印出訊息
    print(f"[篩選 API] 背景任務已啟動，FilterStatus id：{fs.id}")

    # 立即回傳APIResponse設定的格式資料，讓前端知道任務已接受
    return APIResponse(message="篩選任務已啟動，請稍後透過 GET /status 查詢進度")
#endregion


#region 路由：GET /pool — 取得股票池清單
# 作用：回傳 stock_pool 資料表所有股票
# 輸入：
#   current_user（依賴注入，驗證 token 確認已登入）
#   db（資料庫連線）
# 輸出：APIResponse[list[StockPoolItem]]
@router.get("/pool", response_model=APIResponse[list[StockPoolItem]])
async def get_pool(
    # get_current_user：驗證 token，確認使用者已登入
    current_user: str = Depends(get_current_user),
    # get_db：依賴注入，自動借出並歸還資料庫連線
    db: AsyncSession = Depends(get_db),
):
    """
        取得股票池清單，回傳所有通過篩選的股票
        前端股票池管理的"上次篩選時間"和"目前股票池數量"資料由此API提供
    """

    # 印出資訊
    print(f"[股票池 API] 使用者 {current_user} 查詢股票池")

    # 呼叫 service 查詢股票池所有股票
    stocks = await get_stock_pool(db)

    # 將 ORM 物件清單轉換為 Pydantic Schema 清單
    # model_validate()：從 ORM 物件建立 Pydantic 物件（需設定 from_attributes=True）
    stock_items = [StockPoolItem.model_validate(s) for s in stocks]

    # 回傳統一格式的成功回應
    return APIResponse(
        message=f"取得 {len(stock_items)} 支股票",
        data=stock_items,
    )
#endregion


#region 路由：GET /status — 查詢篩選任務狀態
# 作用：前端輪詢用，查詢目前篩選任務的進度（running / completed / failed）
# 輸入：
#   current_user（依賴注入，驗證 token 確認已登入）
#   db（資料庫連線）
# 輸出：APIResponse[FilterStatusOut]（含狀態、時間、股票數量、錯誤原因）
@router.get("/status", response_model=APIResponse[FilterStatusOut])
async def get_status(
    # get_current_user：驗證 token，確認使用者已登入
    current_user: str = Depends(get_current_user),
    # get_db：依賴注入，自動借出並歸還資料庫連線
    db: AsyncSession = Depends(get_db),
):
    """查詢最新一筆篩選任務狀態，前端可輪詢此端點追蹤進度"""

    print(f"[狀態 API] 使用者 {current_user} 查詢篩選狀態")

    # 呼叫 service 查詢最新一筆篩選狀態
    fs = await get_filter_status(db)

    if fs is None:
        # 尚未有任何篩選紀錄
        raise HTTPException(
            # 404 Not Found：尚未有篩選紀錄
            status_code=status.HTTP_404_NOT_FOUND,
            detail="尚未有篩選紀錄",
        )

    # 將 ORM 物件轉換為 Pydantic Schema
    return APIResponse(
        message="查詢成功",
        data=FilterStatusOut.model_validate(fs),
    )
#endregion
