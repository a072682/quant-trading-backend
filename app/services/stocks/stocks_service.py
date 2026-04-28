#region 引入套件
# datetime、timezone：產生 UTC 時間，用於寫入 updated_at 欄位
from datetime import datetime, timezone

# select：建立 SQL SELECT 查詢
# delete：建立 SQL DELETE 查詢（清空資料表）
# desc：降冪排序，取最新一筆篩選狀態
from sqlalchemy import select, delete, desc

# AsyncSession：非同步資料庫連線物件類型
from sqlalchemy.ext.asyncio import AsyncSession

# StockPool：股票池資料表的 ORM 模型
# FilterStatus：篩選任務狀態資料表的 ORM 模型
from app.core.models.stock_pool_model import StockPool, FilterStatus
#endregion


#region 函式：save_stock_pool — 清空舊資料並寫入新的篩選結果
# 作用：先刪除 stock_pool 資料表所有舊資料，再批次寫入通過篩選的新股票
# 輸入：
#   stocks（通過篩選的股票清單，格式：[{"code": ..., "name": ..., "yield_pct": ..., "market_cap": ...}]）
#   db（非同步資料庫連線）
# 輸出：無（寫入資料庫後回傳）
async def save_stock_pool(stocks: list[dict], db: AsyncSession) -> None:
    """清空 stock_pool 舊資料，寫入新的篩選結果"""

    print("[股票池] 清空舊資料...")

    # 刪除 stock_pool 資料表中的所有現有資料
    await db.execute(delete(StockPool))

    print("[股票池] 清空舊資料完成")

    print(f"[股票池] 開始寫入 {len(stocks)} 筆資料...")

    # 取得當下 UTC 時間，作為所有新寫入資料的 updated_at
    now = datetime.now(timezone.utc)

    # 逐筆建立 StockPool ORM 物件並加入 Session
    for s in stocks:
        db.add(
            StockPool(
                # 股票代碼（如 "2330"）
                stock_code=s["code"],
                # 股票名稱（如 "台積電"）
                stock_name=s["name"],
                # 殖利率（百分比，如 4.07）
                yield_pct=s["yield_pct"],
                # 市值（億台幣，如 200.00）
                market_cap=s["market_cap"],
                # 寫入時間（UTC）
                updated_at=now,
            )
        )

    # 一次提交所有資料，減少資料庫往返次數
    await db.commit()

    print("[股票池] 寫入完成 ✓")
#endregion


#region 函式：get_stock_pool — 查詢 stock_pool 資料表所有股票
# 作用：取得股票池中目前所有通過篩選的股票
# 輸入：db（非同步資料庫連線）
# 輸出：StockPool 物件清單（可能為空清單）
async def get_stock_pool(db: AsyncSession) -> list[StockPool]:
    """查詢 stock_pool 資料表的所有股票，回傳 StockPool 物件清單"""

    print("[股票池] 查詢股票池...")

    # 建立 SELECT 查詢，取得 stock_pool 資料表所有資料
    result = await db.execute(select(StockPool))
    # scalars()：將查詢結果轉為 Python 物件（而非原始 Row）
    # all()：取出所有結果為清單
    stocks = result.scalars().all()

    print(f"[股票池] 取得 {len(stocks)} 支股票")
    # 回傳格式：[StockPool(...), StockPool(...), ...]
    return list(stocks)
#endregion


#region 函式：get_filter_status — 查詢最新一筆篩選任務的狀態
# 作用：供前端輪詢使用，取得目前或最近一次篩選任務的進度
# 輸入：db（非同步資料庫連線）
# 輸出：FilterStatus 物件（最新一筆），或 None（尚未有任何篩選紀錄）
async def get_filter_status(db: AsyncSession) -> FilterStatus | None:
    """查詢最新一筆篩選任務狀態，回傳 FilterStatus 物件或 None"""

    print("[篩選狀態] 查詢篩選狀態...")

    # 取最新一筆（依 started_at 降冪排序，取第一筆）
    result = await db.execute(
        select(FilterStatus).order_by(desc(FilterStatus.started_at)).limit(1)
    )
    # scalar_one_or_none()：有資料回傳物件，無資料回傳 None
    return result.scalar_one_or_none()
#endregion
