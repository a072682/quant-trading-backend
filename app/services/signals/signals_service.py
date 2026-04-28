#region 引入套件
# date：取得今日日期（用於查詢和寫入 date 欄位）
from datetime import datetime, timezone, timedelta

# select、desc：建立 SQL 查詢與降冪排序
from sqlalchemy import select, desc

# AsyncSession：非同步資料庫連線物件類型
from sqlalchemy.ext.asyncio import AsyncSession

# Signal：每日評分訊號資料表的 ORM 模型
from app.core.models.signal_model import Signal
#endregion


#region 常數設定
# 台灣時區（UTC+8），用於計算台灣當地日期
TW_TZ = timezone(timedelta(hours=8))

# 推薦股票的總分門檻：低於此分數的股票不列入推薦
MIN_RECOMMEND_SCORE = 4
#endregion


#region 內部函式：_today — 取得台灣今日日期字串
# 輸出：格式為 "YYYY-MM-DD"（例如 "2026-04-29"）
def _today() -> str:
    """回傳台灣時區的今日日期字串（YYYY-MM-DD）"""
    return datetime.now(TW_TZ).strftime("%Y-%m-%d")
#endregion


#region 函式：save_signal — 將單支股票的評分結果寫入 signals 資料表
# 作用：若今日已有該股票的評分記錄則更新，否則新增一筆
# 輸入：
#   db（非同步資料庫連線）
#   stock_code（股票代號，字串）
#   stock_name（股票名稱，字串）
#   scores（分項分數字典，包含 institutional/ma/volume/yield/futures/total_score）
#   ai_result（AI 分析結果字典，包含 ai_action/ai_reason/confidence，可為 None）
# 輸出：Signal ORM 物件
async def save_signal(
    db: AsyncSession,
    stock_code: str,
    stock_name: str,
    scores: dict,
    ai_result: dict | None = None,
) -> Signal:
    """將單支股票的評分寫入資料庫，今日已有資料則更新，否則新增"""

    print(f"[評分寫入] 寫入 {stock_code} 評分...")

    # 取得台灣今日日期
    today = _today()

    # 查詢今日是否已有該股票的評分記錄
    result = await db.execute(
        select(Signal).where(
            # 日期欄位等於今日
            Signal.date == today,
            # 股票代號等於目標股票
            Signal.stock_code == stock_code,
        )
    )
    # scalar_one_or_none()：有資料回傳物件，無資料回傳 None
    signal = result.scalar_one_or_none()

    if signal:
        # 今日已有記錄：更新分項分數
        signal.stock_name = stock_name
        # 更新法人買賣超得分
        signal.institutional_score = scores.get("institutional_score", 0)
        # 更新均線位置得分
        signal.ma_score = scores.get("ma_score", 0)
        # 更新成交量量比得分
        signal.volume_score = scores.get("volume_score", 0)
        # 更新殖利率得分
        signal.yield_score = scores.get("yield_score", 0)
        # 更新大盤情緒得分
        signal.futures_score = scores.get("futures_score", 0)
        # 更新總分
        signal.total_score = scores.get("total_score", 0)
        # 更新最後修改時間
        signal.updated_at = datetime.now(timezone.utc)
    else:
        # 今日尚無記錄：新增一筆
        signal = Signal(
            # 記錄日期（台灣時區）
            date=today,
            # 股票代號
            stock_code=stock_code,
            # 股票名稱
            stock_name=stock_name,
            # 各分項分數
            institutional_score=scores.get("institutional_score", 0),
            ma_score=scores.get("ma_score", 0),
            volume_score=scores.get("volume_score", 0),
            yield_score=scores.get("yield_score", 0),
            futures_score=scores.get("futures_score", 0),
            total_score=scores.get("total_score", 0),
        )
        # 將新物件加入 Session（標記為待寫入）
        db.add(signal)

    # 若有 AI 分析結果，一併更新
    if ai_result:
        signal.ai_action = ai_result.get("ai_action")
        signal.ai_reason = ai_result.get("ai_reason")
        signal.confidence = ai_result.get("confidence")

    # 提交變更至資料庫
    await db.commit()
    # 重新載入物件，確保回傳的資料是資料庫最新狀態
    await db.refresh(signal)

    print(f"[評分寫入] {stock_code} 寫入完成 ✓")
    return signal
#endregion


#region 函式：get_today_signals — 查詢今日所有評分記錄
# 作用：取得今日所有股票的評分結果，依總分降冪排序
# 輸入：db（非同步資料庫連線）
# 輸出：Signal 物件清單（依 total_score 由高至低排序）
async def get_today_signals(db: AsyncSession) -> list[Signal]:
    """查詢今日所有評分記錄，依總分降冪排序"""

    print("[評分查詢] 查詢今日評分...")

    # 取得台灣今日日期
    today = _today()

    # 查詢今日所有評分，依總分降冪排序
    result = await db.execute(
        select(Signal)
        .where(Signal.date == today)
        # 總分高的排在前面
        .order_by(desc(Signal.total_score))
    )
    signals = result.scalars().all()

    print(f"[評分查詢] 取得 {len(signals)} 筆今日評分")
    return list(signals)
#endregion


#region 函式：get_top_signals — 查詢今日推薦股票
# 作用：取今日總分超過門檻的股票，依 confidence 降冪排序，回傳前 limit 筆
# 輸入：
#   db（非同步資料庫連線）
#   limit（回傳筆數上限，預設 3）
# 輸出：Signal 物件清單（依 confidence 由高至低，最多 limit 筆）
async def get_top_signals(db: AsyncSession, limit: int = 3) -> list[Signal]:
    """查詢今日推薦股票，總分須超過門檻且依信心值降冪排序"""

    print("[推薦查詢] 查詢今日推薦...")

    # 取得台灣今日日期
    today = _today()

    # 查詢條件：
    #   1. 今日的評分記錄
    #   2. 總分 > MIN_RECOMMEND_SCORE（過濾低分股票）
    #   3. 依 confidence 降冪排序（信心值高的排前面）
    #   4. 只取前 limit 筆
    result = await db.execute(
        select(Signal)
        .where(
            # 今日的記錄
            Signal.date == today,
            # 總分必須超過門檻才列入推薦
            Signal.total_score > MIN_RECOMMEND_SCORE,
        )
        # 信心值高的排在前面
        .order_by(desc(Signal.confidence))
        # 限制回傳筆數
        .limit(limit)
    )
    signals = result.scalars().all()

    print(f"[推薦查詢] 取得 {len(signals)} 筆推薦")
    return list(signals)
#endregion
