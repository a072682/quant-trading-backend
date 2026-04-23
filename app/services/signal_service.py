from asyncio import get_event_loop
from concurrent.futures import ThreadPoolExecutor
from datetime import date

import httpx
import yfinance as yf
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.signal import Signal
from app.models.simulation import SimulationTrade
from app.services.ai_service import ai_service
from app.services.simulation_service import create_simulation_buy

_thread_pool = ThreadPoolExecutor(max_workers=4)


def _fetch_yfinance_data(ticker_symbol: str) -> dict:
    ticker = yf.Ticker(ticker_symbol)
    hist = ticker.history(period="30d")

    if hist.empty or len(hist) < 2:
        return {
            "close": None,
            "ma20": None,
            "vol_today": None,
            "vol_avg5": None,
            "dividend_yield": None,
        }

    close_today = float(hist["Close"].iloc[-1])
    ma20 = (
        float(hist["Close"].tail(20).mean())
        if len(hist) >= 20
        else float(hist["Close"].mean())
    )
    vol_today = float(hist["Volume"].iloc[-1])
    vol_avg5 = (
        float(hist["Volume"].tail(6).iloc[:-1].mean())
        if len(hist) >= 6
        else float(hist["Volume"].mean())
    )

    try:
        info = ticker.info
        dividend_yield = info.get("dividendYield")
    except Exception:
        dividend_yield = None

    return {
        "close": close_today,
        "ma20": ma20,
        "vol_today": vol_today,
        "vol_avg5": vol_avg5,
        "dividend_yield": dividend_yield,
    }


async def _get_institutional_score(stock_code: str) -> int:
    date_str = date.today().strftime("%Y%m%d")
    url = "https://www.twse.com.tw/rwd/zh/fund/T86"

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                url,
                params={"response": "json", "date": date_str, "selectType": "ALL"},
                headers={"User-Agent": "Mozilla/5.0"},
            )
            data = response.json()

        if data.get("stat") != "OK":
            return 0

        fields = data.get("fields", [])
        rows = data.get("data", [])

        try:
            foreign_idx = fields.index("外陸資買賣超股數(不含外資自營商)")
            trust_idx = fields.index("投信買賣超股數")
        except ValueError:
            try:
                foreign_idx = next(
                    i for i, field in enumerate(fields) if "外" in field and "買賣超" in field
                )
                trust_idx = next(
                    i for i, field in enumerate(fields) if "投信" in field and "買賣超" in field
                )
            except StopIteration:
                return 0

        for row in rows:
            if row[0].strip() != stock_code.strip():
                continue

            foreign_net = int(row[foreign_idx].replace(",", "").replace("+", "") or 0)
            trust_net = int(row[trust_idx].replace(",", "").replace("+", "") or 0)
            net_total = foreign_net + trust_net

            if net_total > 1000:
                return 2
            if net_total > 0:
                return 1
            return -2

        return 0
    except Exception:
        return 0


async def calculate_score(stock_code: str) -> dict:
    institutional_score = await _get_institutional_score(stock_code)

    close = None
    ma_score = 0
    volume_score = 0
    yield_score = 0

    try:
        loop = get_event_loop()
        yf_data = await loop.run_in_executor(
            _thread_pool, _fetch_yfinance_data, f"{stock_code}.TW"
        )

        close = yf_data["close"]
        ma20 = yf_data["ma20"]
        vol_today = yf_data["vol_today"]
        vol_avg5 = yf_data["vol_avg5"]
        dividend_yield = yf_data["dividend_yield"]

        if close is not None and ma20 is not None and ma20 > 0:
            if close < ma20 * 0.98:
                ma_score = 2
            elif close <= ma20 * 1.05:
                ma_score = 1
            else:
                ma_score = -1

        if vol_today is not None and vol_avg5 is not None and vol_avg5 > 0:
            ratio = vol_today / vol_avg5
            if ratio > 1.5:
                volume_score = 2
            elif ratio >= 0.7:
                volume_score = 0
            else:
                volume_score = -1

        if dividend_yield is not None:
            dividend_percent = float(dividend_yield) * 100
            if dividend_percent >= 6.5:
                yield_score = 2
            elif dividend_percent >= 5.0:
                yield_score = 1
            else:
                yield_score = -1
    except Exception:
        pass

    total_score = institutional_score + ma_score + volume_score + yield_score

    return {
        "close": close,
        "institutional_score": institutional_score,
        "ma_score": ma_score,
        "volume_score": volume_score,
        "yield_score": yield_score,
        "total_score": total_score,
    }


async def create_today_signal(
    stock_code: str, stock_name: str, db: AsyncSession
) -> Signal:
    today = date.today().strftime("%Y-%m-%d")
    scores = await calculate_score(stock_code)

    ai_result = await ai_service.analyze_signal(
        {
            "stock_code": stock_code,
            "stock_name": stock_name,
            **scores,
        }
    )

    result = await db.execute(
        select(Signal).where(
            Signal.stock_code == stock_code,
            Signal.date == today,
        )
    )
    signal = result.scalars().first()

    if signal:
        signal.institutional_score = scores["institutional_score"]
        signal.ma_score = scores["ma_score"]
        signal.volume_score = scores["volume_score"]
        signal.yield_score = scores["yield_score"]
        signal.total_score = scores["total_score"]
        signal.ai_action = ai_result.get("action")
        signal.ai_reason = ai_result.get("reason")
    else:
        signal = Signal(
            date=today,
            stock_code=stock_code,
            stock_name=stock_name,
            institutional_score=scores["institutional_score"],
            ma_score=scores["ma_score"],
            volume_score=scores["volume_score"],
            yield_score=scores["yield_score"],
            total_score=scores["total_score"],
            ai_action=ai_result.get("action"),
            ai_reason=ai_result.get("reason"),
        )
        db.add(signal)

    await db.commit()
    await db.refresh(signal)

    if scores["total_score"] >= 5 and scores["close"] is not None:
        open_position_result = await db.execute(
            select(SimulationTrade).where(
                SimulationTrade.stock_code == stock_code,
                SimulationTrade.status == "open",
            )
        )
        existing_open_position = open_position_result.scalars().first()

        if existing_open_position is None:
            await create_simulation_buy(
                stock_code=stock_code,
                stock_name=stock_name,
                price=float(scores["close"]),
                score=scores["total_score"],
                db=db,
            )

    return signal


async def get_today_signal(stock_code: str, db: AsyncSession) -> Signal | None:
    today = date.today().strftime("%Y-%m-%d")
    result = await db.execute(
        select(Signal).where(
            Signal.stock_code == stock_code,
            Signal.date == today,
        )
    )
    return result.scalars().first()


async def get_signal_history(stock_code: str, db: AsyncSession) -> list[Signal]:
    result = await db.execute(
        select(Signal)
        .where(Signal.stock_code == stock_code)
        .order_by(desc(Signal.date))
        .limit(30)
    )
    return result.scalars().all()


async def get_signals_by_date(query_date: str, db: AsyncSession) -> list[Signal]:
    result = await db.execute(
        select(Signal).where(Signal.date == query_date).order_by(Signal.stock_code)
    )
    return result.scalars().all()


async def get_stats(db: AsyncSession) -> dict:
    count_result = await db.execute(select(func.count()).select_from(Signal))
    record_count = count_result.scalar()

    latest_result = await db.execute(
        select(Signal.created_at).order_by(desc(Signal.created_at)).limit(1)
    )
    last_created_at = latest_result.scalar()

    return {
        "lastRunAt": last_created_at.isoformat() if last_created_at else None,
        "recordCount": record_count,
    }
