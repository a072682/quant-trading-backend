from asyncio import get_event_loop
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone, timedelta

import httpx
import yfinance as yf
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models.signal_model import Signal
from app.core.models.simulation_model import SimulationTrade
from app.services.ai_service import ai_service
from app.services.futures_service import get_futures_data
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


async def calculate_score(stock_code: str, fallback: dict | None = None) -> dict:
    institutional_score = await _get_institutional_score(stock_code)
    futures_data = await get_futures_data()
    futures_score = futures_data["futures_score"]

    close = None
    yf_failed = False

    fb_ma = fallback["ma_score"] if fallback else 0
    fb_vol = fallback["volume_score"] if fallback else 0
    fb_yield = fallback["yield_score"] if fallback else 0

    ma_score = fb_ma
    volume_score = fb_vol
    yield_score = fb_yield

    try:
        loop = get_event_loop()
        yf_data = await loop.run_in_executor(
            _thread_pool, _fetch_yfinance_data, f"{stock_code}.TW"
        )

        if yf_data["close"] is None:
            yf_failed = True
        else:
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
            elif fallback is None:
                ma_score = 0

            if vol_today is not None and vol_avg5 is not None and vol_avg5 > 0:
                ratio = vol_today / vol_avg5
                if ratio > 1.5:
                    volume_score = 2
                elif ratio >= 0.7:
                    volume_score = 0
                else:
                    volume_score = -1
            elif fallback is None:
                volume_score = 0

            if dividend_yield is not None:
                dividend_percent = float(dividend_yield) * 100
                if dividend_percent >= 6.5:
                    yield_score = 2
                elif dividend_percent >= 5.0:
                    yield_score = 1
                else:
                    yield_score = -1
            elif fallback is None:
                yield_score = 0

    except Exception:
        yf_failed = True

    # yfinance 失敗時保留 fallback 分數（已在初始化時設定）

    total_score = institutional_score + ma_score + volume_score + yield_score + futures_score

    return {
        "close": close,
        "institutional_score": institutional_score,
        "ma_score": ma_score,
        "volume_score": volume_score,
        "yield_score": yield_score,
        "futures_score": futures_score,
        "total_score": total_score,
        "yf_failed": yf_failed,
    }


async def create_today_signal(
    stock_code: str, stock_name: str, db: AsyncSession, skip_ai: bool = False
) -> Signal:
    today = date.today().strftime("%Y-%m-%d")

    result = await db.execute(
        select(Signal).where(
            Signal.stock_code == stock_code,
            Signal.date == today,
        )
    )
    existing = result.scalars().first()

    if existing and existing.updated_at is not None:
        updated_at_utc = existing.updated_at
        if updated_at_utc.tzinfo is None:
            updated_at_utc = updated_at_utc.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) - updated_at_utc < timedelta(hours=1):
            return existing

    fallback = (
        {
            "ma_score": existing.ma_score,
            "volume_score": existing.volume_score,
            "yield_score": existing.yield_score,
            "futures_score": existing.futures_score,
        }
        if existing
        else None
    )

    scores = await calculate_score(stock_code, fallback=fallback)

    if skip_ai:
        ai_action = None
        ai_reason = None
    else:
        ai_result = await ai_service.analyze_signal(
            {
                "stock_code": stock_code,
                "stock_name": stock_name,
                **scores,
            }
        )
        ai_action = ai_result.get("action")
        ai_reason = ai_result.get("reason")

    now = datetime.now(timezone.utc)

    if existing:
        existing.institutional_score = scores["institutional_score"]
        existing.ma_score = scores["ma_score"]
        existing.volume_score = scores["volume_score"]
        existing.yield_score = scores["yield_score"]
        existing.futures_score = scores["futures_score"]
        existing.total_score = scores["total_score"]
        existing.ai_action = ai_action
        existing.ai_reason = ai_reason
        existing.updated_at = now
        signal = existing
    else:
        signal = Signal(
            date=today,
            stock_code=stock_code,
            stock_name=stock_name,
            institutional_score=scores["institutional_score"],
            ma_score=scores["ma_score"],
            volume_score=scores["volume_score"],
            yield_score=scores["yield_score"],
            futures_score=scores["futures_score"],
            total_score=scores["total_score"],
            ai_action=ai_action,
            ai_reason=ai_reason,
            updated_at=now,
        )
        db.add(signal)

    await db.commit()
    await db.refresh(signal)

    # TODO: 待儀表板穩定後，由前端手動買入或排程觸發，這裡暫時停用自動模擬交易
    # if scores["total_score"] >= 5 and scores["close"] is not None:
    #     open_position_result = await db.execute(
    #         select(SimulationTrade).where(
    #             SimulationTrade.stock_code == stock_code,
    #             SimulationTrade.status == "open",
    #         )
    #     )
    #     existing_open_position = open_position_result.scalars().first()
    #
    #     today_buy_result = await db.execute(
    #         select(SimulationTrade).where(
    #             SimulationTrade.stock_code == stock_code,
    #             SimulationTrade.date == today,
    #             SimulationTrade.action == "buy",
    #         )
    #     )
    #     today_buy_exists = today_buy_result.scalars().first()
    #
    #     if existing_open_position is None and today_buy_exists is None:
    #         await create_simulation_buy(
    #             stock_code=stock_code,
    #             stock_name=stock_name,
    #             price=float(scores["close"]),
    #             score=scores["total_score"],
    #             db=db,
    #         )

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


async def get_today_all_signals(db: AsyncSession) -> list[Signal]:
    today = date.today().strftime("%Y-%m-%d")
    result = await db.execute(
        select(Signal)
        .where(Signal.date == today)
        .order_by(desc(Signal.total_score))
    )
    return result.scalars().all()


async def get_top_signals(
    db: AsyncSession,
    limit: int = 3,
    min_score: int = 6,
    exclude_codes: list[str] | None = None,
) -> list[Signal]:
    today = date.today().strftime("%Y-%m-%d")
    print(f"[取得高分訊號] 查詢條件：日期={today}，最低分數={min_score}，排除={exclude_codes}")
    conditions = [Signal.date == today, Signal.total_score >= min_score]
    if exclude_codes:
        conditions.append(Signal.stock_code.notin_(exclude_codes))
    result = await db.execute(
        select(Signal)
        .where(*conditions)
        .order_by(desc(Signal.total_score))
        .limit(limit)
    )
    signals = result.scalars().all()
    print(f"[取得高分訊號] 符合條件的股票數：{len(signals)} 檔")
    return signals


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
