#region 引入資料庫相關工具
# AsyncSession：非同步資料庫連線型別
# select：建立 SQL SELECT 查詢
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
#endregion

#region 引入模型與型別工具
# SimulationTrade：模擬交易 ORM 模型
# date、datetime、timezone：日期時間工具
from app.core.models.simulation_model import SimulationTrade
from datetime import date, datetime, timezone
#endregion

#region 查詢函式：get_trades_by_status — 取得指定狀態的所有記錄
# 作用：查詢資料表中 status 符合指定值的所有交易記錄
# 輸入：db（資料庫連線）、status（"pending"/"holding"/"selling"/"sold"）
# 輸出：SimulationTrade 物件清單
async def get_trades_by_status(db: AsyncSession, status: str) -> list[SimulationTrade]:
    result = await db.execute(
        select(SimulationTrade).where(SimulationTrade.status == status)
    )
    return result.scalars().all()
#endregion

#region 查詢函式：get_active_stock_codes — 取得所有進行中的股票代號
# 作用：取得 pending + holding + selling 的所有股票代號
# 用途：after_signal_job 判斷推薦股票是否已在追蹤中
# 輸出：股票代號字串清單，例如 ["2330", "2317"]
async def get_active_stock_codes(db: AsyncSession) -> list[str]:
    result = await db.execute(
        select(SimulationTrade.stock_code).where(
            SimulationTrade.status.in_(["pending", "holding", "selling"])
        )
    )
    return [row[0] for row in result.all()]
#endregion

#region 查詢函式：get_active_count — 取得目前進行中的總數量
# 作用：取得 pending + holding + selling 的總筆數
# 用途：判斷是否已達到最多 3 檔的上限
# 輸出：整數（目前進行中的筆數）
async def get_active_count(db: AsyncSession) -> int:
    result = await db.execute(
        select(SimulationTrade).where(
            SimulationTrade.status.in_(["pending", "holding", "selling"])
        )
    )
    return len(result.scalars().all())
#endregion

#region 新增函式：create_trade — 新增一筆待買入記錄
# 作用：評分完成後，將推薦股票新增為 pending 狀態
# 輸入：db、stock_code（股票代號）、stock_name（股票名稱）、signal_date（推薦日期）
# 輸出：新增的 SimulationTrade 物件
async def create_trade(
    db: AsyncSession,
    stock_code: str,
    stock_name: str,
    signal_date: date,
) -> SimulationTrade:
    trade = SimulationTrade(
        stock_code=stock_code,
        stock_name=stock_name,
        status="pending",
        signal_date=signal_date,
    )
    db.add(trade)
    await db.commit()
    await db.refresh(trade)
    print(f"[模擬交易] 新增待買入記錄：{stock_code} {stock_name}")
    return trade
#endregion

#region 更新函式：update_to_holding — 將待買入改為持有中
# 作用：隔天開盤後，以開盤價買入，更新狀態為 holding
# 輸入：db、trade_id、buy_price（開盤價）、buy_date（買入日期）
async def update_to_holding(
    db: AsyncSession,
    trade_id: str,
    buy_price: float,
    buy_date: date,
) -> None:
    result = await db.execute(
        select(SimulationTrade).where(SimulationTrade.id == trade_id)
    )
    trade = result.scalar_one_or_none()
    if trade:
        trade.status = "holding"
        trade.buy_price = buy_price
        trade.current_price = buy_price
        trade.profit_pct = 0.0
        trade.buy_date = buy_date
        await db.commit()
        print(f"[模擬交易] {trade.stock_code} 買入成功，價格：{buy_price}")
#endregion

#region 更新函式：update_current_price — 更新現價與損益
# 作用：每天收盤後更新持倉的現價和損益百分比
# 輸入：db、trade_id、current_price（現在價格）
async def update_current_price(
    db: AsyncSession,
    trade_id: str,
    current_price: float,
) -> None:
    result = await db.execute(
        select(SimulationTrade).where(SimulationTrade.id == trade_id)
    )
    trade = result.scalar_one_or_none()
    if trade and trade.buy_price:
        # 計算損益百分比：(現價 - 買入價) / 買入價 * 100
        profit_pct = (current_price - trade.buy_price) / trade.buy_price * 100
        trade.current_price = current_price
        trade.profit_pct = round(profit_pct, 2)
        await db.commit()
#endregion

#region 更新函式：update_to_selling — 將持有中改為待賣出
# 作用：收盤後達到停利停損條件，標記為待賣出，等隔天開盤賣出
# 輸入：db、trade_id
async def update_to_selling(
    db: AsyncSession,
    trade_id: str,
) -> None:
    result = await db.execute(
        select(SimulationTrade).where(SimulationTrade.id == trade_id)
    )
    trade = result.scalar_one_or_none()
    if trade:
        trade.status = "selling"
        await db.commit()
        print(f"[模擬交易] {trade.stock_code} 達停利停損條件，等待隔天開盤賣出")
#endregion

#region 更新函式：close_trade — 完成賣出，結束交易
# 作用：以開盤價賣出，記錄最終損益，狀態改為 sold
# 輸入：db、trade_id、sell_price（賣出價格）、sell_reason（"停利"/"停損"）、sell_date
async def close_trade(
    db: AsyncSession,
    trade_id: str,
    sell_price: float,
    sell_reason: str,
    sell_date: date,
) -> None:
    result = await db.execute(
        select(SimulationTrade).where(SimulationTrade.id == trade_id)
    )
    trade = result.scalar_one_or_none()
    if trade and trade.buy_price:
        profit_pct = (sell_price - trade.buy_price) / trade.buy_price * 100
        trade.status = "sold"
        trade.sell_price = sell_price
        trade.sell_reason = sell_reason
        trade.sell_date = sell_date
        trade.current_price = sell_price
        trade.profit_pct = round(profit_pct, 2)
        await db.commit()
        print(f"[模擬交易] {trade.stock_code} {sell_reason}，價格：{sell_price}，損益：{round(profit_pct, 2)}%")
#endregion

#region 查詢函式：get_all_trades — 取得所有交易記錄
# 作用：取得所有交易記錄，依建立時間降序排列（最新的在最前面）
# 用途：歷史記錄頁面
async def get_all_trades(db: AsyncSession) -> list[SimulationTrade]:
    result = await db.execute(
        select(SimulationTrade).order_by(SimulationTrade.created_at.desc())
    )
    return result.scalars().all()
#endregion

#region 查詢函式：get_summary — 取得整體績效摘要
# 作用：計算所有已賣出交易的勝率與平均損益
# 輸出：包含統計數字的字典
async def get_summary(db: AsyncSession) -> dict:
    # 取得所有已賣出的記錄
    sold_trades = await get_trades_by_status(db, "sold")

    total = len(sold_trades)
    # 損益大於 0 為獲利
    wins = [t for t in sold_trades if t.profit_pct and t.profit_pct > 0]
    loses = [t for t in sold_trades if t.profit_pct and t.profit_pct <= 0]

    win_rate = round(len(wins) / total * 100, 2) if total > 0 else 0.0
    avg_profit = round(
        sum(t.profit_pct for t in sold_trades if t.profit_pct) / total, 2
    ) if total > 0 else 0.0

    # 取得目前進行中的筆數
    active_count = await get_active_count(db)

    return {
        "total_trades": total,
        "win_trades": len(wins),
        "lose_trades": len(loses),
        "win_rate": win_rate,
        "avg_profit_pct": avg_profit,
        "active_count": active_count,
    }
#endregion