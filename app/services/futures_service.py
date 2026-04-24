from asyncio import get_event_loop
from concurrent.futures import ThreadPoolExecutor

import yfinance as yf

_thread_pool = ThreadPoolExecutor(max_workers=2)

FUTURES_TICKER = "TXF=F"
SPOT_TICKER = "^TWII"


def _fetch_futures_raw() -> dict:
    futures = yf.Ticker(FUTURES_TICKER)
    spot = yf.Ticker(SPOT_TICKER)

    f_hist = futures.history(period="2d")
    s_hist = spot.history(period="2d")

    if f_hist.empty or len(f_hist) < 1:
        return {"ok": False}

    futures_today = float(f_hist["Close"].iloc[-1])
    futures_prev = float(f_hist["Close"].iloc[-2]) if len(f_hist) >= 2 else futures_today
    futures_change_pct = (futures_today - futures_prev) / futures_prev * 100 if futures_prev != 0 else 0.0

    today_volume = float(f_hist["Volume"].iloc[-1]) if "Volume" in f_hist.columns else 0.0
    yesterday_volume = float(f_hist["Volume"].iloc[-2]) if len(f_hist) >= 2 and "Volume" in f_hist.columns else 0.0
    volume_change_pct = (
        (today_volume - yesterday_volume) / yesterday_volume * 100
        if yesterday_volume != 0
        else 0.0
    )

    spot_price = float(s_hist["Close"].iloc[-1]) if not s_hist.empty else None
    price_spread = (futures_today - spot_price) if spot_price is not None else 0.0

    return {
        "ok": True,
        "futures_change_pct": futures_change_pct,
        "volume_change_pct": volume_change_pct,
        "price_spread": price_spread,
    }


def _calc_futures_score(data: dict) -> int:
    score = 0

    change = data["futures_change_pct"]
    if change > 1:
        score += 1
    elif change < -1:
        score -= 1

    vol_change = data["volume_change_pct"]
    if vol_change > 0 and change > 0:
        score += 1
    elif vol_change > 0 and change < 0:
        score -= 1

    spread = data["price_spread"]
    if spread > 50:
        score += 1
    elif spread < -50:
        score -= 1

    return max(-3, min(3, score))


async def get_futures_data() -> dict:
    loop = get_event_loop()
    try:
        raw = await loop.run_in_executor(_thread_pool, _fetch_futures_raw)
        if not raw.get("ok"):
            return {"futures_change_pct": 0.0, "volume_change_pct": 0.0, "price_spread": 0.0, "futures_score": 0}

        futures_score = _calc_futures_score(raw)
        return {
            "futures_change_pct": round(raw["futures_change_pct"], 2),
            "volume_change_pct": round(raw["volume_change_pct"], 2),
            "price_spread": round(raw["price_spread"], 2),
            "futures_score": futures_score,
        }
    except Exception:
        return {"futures_change_pct": 0.0, "volume_change_pct": 0.0, "price_spread": 0.0, "futures_score": 0}
