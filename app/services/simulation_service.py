from asyncio import get_event_loop
from concurrent.futures import ThreadPoolExecutor
from datetime import date

import yfinance as yf
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.simulation import SimulationTrade

_thread_pool = ThreadPoolExecutor(max_workers=4)


def _fetch_current_price(ticker_symbol: str) -> float | None:
    ticker = yf.Ticker(ticker_symbol)
    hist = ticker.history(period="5d")

    if hist.empty:
        return None

    return float(hist["Close"].iloc[-1])


async def create_simulation_buy(
    stock_code: str,
    stock_name: str,
    price: float,
    score: int,
    db: AsyncSession,
) -> SimulationTrade | None:
    if price <= 0:
        return None

    shares = int(10000 / price)
    if shares <= 0:
        return None

    trade = SimulationTrade(
        date=date.today().strftime("%Y-%m-%d"),
        stock_code=stock_code,
        stock_name=stock_name,
        action="buy",
        price=price,
        shares=shares,
        total_amount=shares * price,
        signal_score=score,
        status="open",
        buy_price=None,
        profit=0.0,
        profit_pct=0.0,
    )

    db.add(trade)
    await db.commit()
    await db.refresh(trade)
    return trade


async def check_and_close_positions(db: AsyncSession) -> list[SimulationTrade]:
    result = await db.execute(
        select(SimulationTrade)
        .where(SimulationTrade.status == "open")
        .order_by(desc(SimulationTrade.created_at))
    )
    open_positions = result.scalars().all()
    closed_positions: list[SimulationTrade] = []
    loop = get_event_loop()

    for position in open_positions:
        current_price = await loop.run_in_executor(
            _thread_pool, _fetch_current_price, f"{position.stock_code}.TW"
        )

        if current_price is None:
            continue

        original_buy_price = position.buy_price or position.price
        should_take_profit = current_price >= original_buy_price * 1.06
        should_stop_loss = current_price <= original_buy_price * 0.97

        if not should_take_profit and not should_stop_loss:
            continue

        original_amount = position.shares * original_buy_price
        sell_amount = position.shares * current_price
        profit = sell_amount - original_amount

        position.action = "sell"
        position.price = current_price
        position.total_amount = sell_amount
        position.status = "closed"
        position.buy_price = original_buy_price
        position.profit = profit
        position.profit_pct = profit / original_amount if original_amount > 0 else 0.0
        closed_positions.append(position)

    if closed_positions:
        await db.commit()
        for position in closed_positions:
            await db.refresh(position)

    return closed_positions


async def get_simulation_summary(db: AsyncSession) -> dict:
    total_profit_result = await db.execute(
        select(func.coalesce(func.sum(SimulationTrade.profit), 0.0)).where(
            SimulationTrade.status == "closed"
        )
    )
    total_profit = float(total_profit_result.scalar() or 0.0)

    win_count_result = await db.execute(
        select(func.count()).select_from(SimulationTrade).where(
            SimulationTrade.status == "closed",
            SimulationTrade.profit > 0,
        )
    )
    win_count = int(win_count_result.scalar() or 0)

    loss_count_result = await db.execute(
        select(func.count()).select_from(SimulationTrade).where(
            SimulationTrade.status == "closed",
            SimulationTrade.profit <= 0,
        )
    )
    loss_count = int(loss_count_result.scalar() or 0)

    open_positions_result = await db.execute(
        select(func.count()).select_from(SimulationTrade).where(
            SimulationTrade.status == "open"
        )
    )
    open_positions = int(open_positions_result.scalar() or 0)

    total_count = win_count + loss_count

    return {
        "total_profit": total_profit,
        "win_count": win_count,
        "loss_count": loss_count,
        "total_count": total_count,
        "win_rate": win_count / total_count if total_count > 0 else 0.0,
        "open_positions": open_positions,
    }
