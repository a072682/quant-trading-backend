#region 引入 FastAPI 相關套件
# APIRouter：定義這個模組的路由群組
# BackgroundTasks：FastAPI 內建背景任務，讓 API 立即回傳後繼續執行耗時工作
# Depends：FastAPI 依賴注入
# HTTPException：拋出 HTTP 錯誤
# status：HTTP 狀態碼常數
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
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
# StockPool：股票池資料表的 ORM 模型，用於取得待評分的股票清單
from app.core.models.stock_pool_model import StockPool

# Signal：每日評分訊號資料表的 ORM 模型，用於更新 AI 分析結果
from app.core.models.signal_model import Signal
#endregion


#region 引入 API 回應格式
# APIResponse：統一的 API 回傳格式
from app.core.schemas.common import APIResponse

# SignalOut：評分資料的回應格式（含所有分項分數與 AI 結果）
from app.core.schemas.signal_schema import SignalOut
#endregion


#region 引入評分計算模組
# calculate_total_score：呼叫所有分項評分函式並加總
# fetch_market_score：抓取大盤評分（所有股票共用，只抓一次）
from app.core.signals.calculator import calculate_total_score, fetch_market_score
#endregion


#region 引入 AI 分析模組
# analyze_signal：將評分資料送給 Claude AI 分析，回傳買進建議
from app.core.signals.ai_analyzer import analyze_signal
#endregion


#region 引入評分 Service
# save_signal：將評分結果寫入資料庫（upsert：更新或新增）
# get_today_signals：查詢今日所有評分記錄
# get_top_signals：查詢今日推薦股票（總分超過門檻）
from app.services.signals.signals_service import save_signal, get_today_signals, get_top_signals
#endregion


#region 建立路由器
# 此模組的所有路由都會掛在這個 router 下
# 由 router.py 負責決定 prefix（/signals）
router = APIRouter()
#endregion


#region 模組層級旗標：防止評分任務重複執行
# _is_running：True 代表目前有評分任務在執行中，拒絕新任務觸發
# 注意：此旗標只在單一 process 中有效
#       若 FastAPI 使用多個 worker（uvicorn --workers N），需改用 Redis 等分散式鎖
_is_running: bool = False
#endregion


#region 內部函式：_run_scoring_task — 背景執行完整評分流程
# 作用：依序完成大盤評分 → 逐支股票評分 → AI 分析 → 寫入資料庫
# 輸入：無（背景任務不接收參數，所需資料由函式內部自行取得）
# 注意：此函式為非同步函式，由 FastAPI BackgroundTasks 在背景執行
#       需自行建立獨立的資料庫 Session（不能重用 request 的 Session）
async def _run_scoring_task() -> None:
    """背景執行完整評分流程：大盤 → 個股評分 → AI 分析 → 寫入資料庫"""

    # 宣告使用模組層級的旗標變數
    global _is_running

    # 在背景任務中需要自行建立獨立的資料庫 Session
    from app.core.db.session import AsyncSessionLocal

    try:
        # 標記任務開始執行
        _is_running = True

        async with AsyncSessionLocal() as db:
            # === 第一步：取得大盤評分（所有股票共用，只抓一次） ===
            market_score = await fetch_market_score()

            # === 第二步：從 StockPool 讀取所有待評分的股票 ===
            result = await db.execute(select(StockPool))
            stocks = result.scalars().all()

            print(f"[評分任務] 開始執行，共 {len(stocks)} 支股票...")

            # === 第三步：逐一對每支股票計算評分並寫入資料庫 ===
            for idx, stock in enumerate(stocks, start=1):
                # 計算該股票的所有分項分數與總分
                scores = await calculate_total_score(
                    stock.stock_code,
                    stock.stock_name,
                    market_score,
                )
                # 寫入資料庫（不含 AI 結果，後續再更新）
                await save_signal(db, stock.stock_code, stock.stock_name, scores)

                # 每完成 10 支輸出一次進度
                if idx % 10 == 0 or idx == len(stocks):
                    print(f"[評分任務] 進度：{idx}/{len(stocks)} 完成")

        print("[評分任務] 數字評分完成，開始 AI 分析...")

        # === 第四步：取今日高分股票進行 AI 分析 ===
        # 建立新的 Session 進行 AI 分析和更新
        async with AsyncSessionLocal() as db:
            # 取今日總分 > 門檻的前幾名股票
            top_signals = await get_top_signals(db)

            for signal in top_signals:
                # 呼叫 Claude AI 分析這支股票
                ai_result = await analyze_signal(
                    signal.stock_code,
                    signal.stock_name,
                    {
                        "institutional_score": signal.institutional_score,
                        "ma_score": signal.ma_score,
                        "volume_score": signal.volume_score,
                        "yield_score": signal.yield_score,
                        "futures_score": signal.futures_score,
                        "total_score": signal.total_score,
                    },
                )

                # === 第五步：更新 Signal 資料表的 AI 分析結果 ===
                # 重新查詢該筆 Signal，確保拿到最新狀態
                result = await db.execute(
                    select(Signal).where(Signal.id == signal.id)
                )
                sig = result.scalar_one_or_none()
                if sig:
                    # 更新 AI 建議動作（buy / watch / sell）
                    sig.ai_action = ai_result.get("ai_action")
                    # 更新 AI 說明文字
                    sig.ai_reason = ai_result.get("ai_reason")
                    # 更新 AI 信心值（0 到 100）
                    sig.confidence = ai_result.get("confidence")

            # 提交所有 AI 分析結果
            await db.commit()

        print("[評分任務] 全部完成 ✓")

    except Exception as e:
        print(f"[評分任務] 執行失敗：{e}")

    finally:
        # 無論成功或失敗，都要重置旗標，允許下次觸發
        _is_running = False
#endregion


#region 路由：POST /run — 手動觸發評分（背景執行）
# 作用：立即回傳 202 Accepted，在背景執行完整評分流程
# 輸入：
#   background_tasks（FastAPI 背景任務管理器）
#   current_user（依賴注入，驗證 token 確認已登入）
# 輸出：APIResponse（含任務已啟動的訊息），HTTP 202
# 防重複：若已有任務在執行中，回傳 400 Bad Request
@router.post("/run", response_model=APIResponse, status_code=202)
async def run_scoring(
    # BackgroundTasks：FastAPI 提供的背景任務管理器
    background_tasks: BackgroundTasks,
    # get_current_user：驗證 token，確認使用者已登入
    current_user: str = Depends(get_current_user),
):
    """手動觸發評分任務，立即回傳 202，評分在背景執行"""

    print(f"[評分 API] 使用者 {current_user} 觸發評分")

    # 防止重複執行：若旗標為 True 代表任務仍在執行
    if _is_running:
        print("[評分 API] 評分任務執行中，拒絕重複觸發")
        raise HTTPException(
            # 400 Bad Request：請求不合法（重複觸發）
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="評分任務執行中，請稍後再試",
        )

    # 將完整評分流程加入背景任務佇列
    # FastAPI 會在回傳 response 後自動執行
    background_tasks.add_task(_run_scoring_task)

    print("[評分 API] 背景評分任務已啟動")

    # 立即回傳 202 Accepted，前端可透過 GET /today 輪詢結果
    return APIResponse(message="評分任務已啟動，請稍後透過 GET /today 查詢結果")
#endregion


#region 路由：GET /today — 取得今日所有評分
# 作用：回傳今日所有股票的評分記錄，依總分降冪排序
# 輸入：
#   current_user（依賴注入，驗證 token 確認已登入）
#   db（資料庫連線）
# 輸出：APIResponse[list[SignalOut]]
@router.get("/today", response_model=APIResponse[list[SignalOut]])
async def get_today(
    # get_current_user：驗證 token，確認使用者已登入
    current_user: str = Depends(get_current_user),
    # get_db：依賴注入，自動借出並歸還資料庫連線
    db: AsyncSession = Depends(get_db),
):
    """取得今日所有股票評分記錄，依總分降冪排序"""

    print(f"[評分 API] 使用者 {current_user} 查詢今日評分")

    # 呼叫 service 查詢今日所有評分記錄
    signals = await get_today_signals(db)

    # 將 ORM 物件清單轉換為 Pydantic Schema 清單
    items = [SignalOut.model_validate(s) for s in signals]

    return APIResponse(
        message=f"取得今日 {len(items)} 筆評分",
        data=items,
    )
#endregion


#region 路由：GET /top — 取得今日推薦股票
# 作用：回傳今日推薦的前三名股票（總分 > 門檻，依信心值排序）
# 輸入：
#   current_user（依賴注入，驗證 token 確認已登入）
#   db（資料庫連線）
# 輸出：APIResponse[list[SignalOut]]
@router.get("/top", response_model=APIResponse[list[SignalOut]])
async def get_top(
    # get_current_user：驗證 token，確認使用者已登入
    current_user: str = Depends(get_current_user),
    # get_db：依賴注入，自動借出並歸還資料庫連線
    db: AsyncSession = Depends(get_db),
):
    """取得今日推薦股票（總分超過門檻，依信心值排序）"""

    print(f"[評分 API] 使用者 {current_user} 查詢今日推薦")

    # 呼叫 service 查詢今日推薦股票（預設前 3 名）
    signals = await get_top_signals(db)

    # 將 ORM 物件清單轉換為 Pydantic Schema 清單
    items = [SignalOut.model_validate(s) for s in signals]

    return APIResponse(
        message=f"取得今日 {len(items)} 筆推薦",
        data=items,
    )
#endregion
