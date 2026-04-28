from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.models.trade_model import Trade
from app.services.fugle_service import fugle_service
from app.core.schemas.trade import TradeBuyIn, TradeSellIn

from datetime import date


async def execute_buy(data: TradeBuyIn, db: AsyncSession) -> Trade:
    """
    執行買進流程：
    1. 呼叫富果 API 送出委託單
    2. 將交易紀錄存入資料庫
    """
    order_result = await fugle_service.place_buy_order(
        stock_code=data.stock_code,
        shares=data.shares,
        price=data.price,
    )

    total_amount = data.shares * data.price

    trade = Trade(
        date=date.today().strftime("%Y-%m-%d"),
        stock_code=data.stock_code,
        stock_name=data.stock_name,
        action="buy",
        price=data.price,
        shares=data.shares,
        total_amount=total_amount,
        profit=0.0,
        reason=data.reason,
        order_id=order_result.get("orderId", ""),
    )

    db.add(trade)
    await db.commit()
    await db.refresh(trade)

    return trade


async def execute_sell(data: TradeSellIn, db: AsyncSession) -> Trade:
    """
    執行賣出流程：
    1. 查詢買進成本
    2. 呼叫富果 API 送出委託單
    3. 計算損益並存入資料庫
    """
    result = await db.execute(
        select(Trade).where(
            Trade.stock_code == data.stock_code,
            Trade.action == "buy",
        ).order_by(Trade.created_at.desc()).limit(1)
    )
    buy_trade = result.scalar_one_or_none()

    sell_amount = data.shares * data.price
    buy_amount = buy_trade.total_amount if buy_trade else 0
    profit = sell_amount - buy_amount

    order_result = await fugle_service.place_sell_order(
        stock_code=data.stock_code,
        shares=data.shares,
        price=data.price,
    )

    trade = Trade(
        date=date.today().strftime("%Y-%m-%d"),
        stock_code=data.stock_code,
        stock_name=buy_trade.stock_name if buy_trade else "",
        action="sell",
        price=data.price,
        shares=data.shares,
        total_amount=sell_amount,
        profit=profit,
        reason=data.reason,
        order_id=order_result.get("orderId", ""),
    )

    db.add(trade)
    await db.commit()
    await db.refresh(trade)

    return trade


async def get_monthly_stats(db: AsyncSession) -> dict:
    """計算本月交易統計（勝率、總損益、交易次數）"""
    from datetime import datetime
    current_month = datetime.now().strftime("%Y-%m")

    result = await db.execute(
        select(Trade).where(
            Trade.action == "sell",
            Trade.date.startswith(current_month),
        )
    )
    trades = result.scalars().all()

    total_count = len(trades)
    win_count = sum(1 for t in trades if t.profit > 0)
    loss_count = sum(1 for t in trades if t.profit <= 0)
    total_profit = sum(t.profit for t in trades)

    return {
        "month": current_month,
        "total_profit": total_profit,
        "win_count": win_count,
        "loss_count": loss_count,
        "total_count": total_count,
        "win_rate": win_count / total_count if total_count > 0 else 0,
    }
