import logging
from asyncio import get_event_loop
from concurrent.futures import ThreadPoolExecutor

import yfinance as yf

_thread_pool = ThreadPoolExecutor(max_workers=2)
logger = logging.getLogger(__name__)

FUTURES_TICKER = "TWN=F"
SPOT_TICKER = "^TWII"


def _fetch_hist_valid(ticker_symbol: str) -> "pd.DataFrame | None":
    """取得歷史資料並確認 Close 欄位有有效數值，否則回傳 None。"""
    import pandas as pd
    ticker = yf.Ticker(ticker_symbol)
    hist = ticker.history(period="2d")
    if hist.empty:
        return None
    if "Close" not in hist.columns or not hist["Close"].notna().any():
        return None
    hist = hist.dropna(subset=["Close"])
    if len(hist) < 1:
        return None
    return hist


def _calc_change_and_volume(hist) -> tuple[float, float]:
    """計算漲跌幅與成交量變化率。"""
    close = hist["Close"]
    today_price = float(close.iloc[-1])
    prev_price = float(close.iloc[-2]) if len(close) >= 2 else today_price
    change_pct = (today_price - prev_price) / prev_price * 100 if prev_price != 0 else 0.0

    if "Volume" in hist.columns and hist["Volume"].notna().any():
        vol = hist["Volume"].dropna()
        today_vol = float(vol.iloc[-1]) if len(vol) >= 1 else 0.0
        prev_vol = float(vol.iloc[-2]) if len(vol) >= 2 else 0.0
    else:
        today_vol = prev_vol = 0.0

    vol_change_pct = (today_vol - prev_vol) / prev_vol * 100 if prev_vol != 0 else 0.0
    return change_pct, vol_change_pct


def _fetch_futures_raw() -> dict:
    # 先嘗試 TWN=F（CME 台灣期貨）
    f_hist = _fetch_hist_valid(FUTURES_TICKER)

    if f_hist is not None:
        change_pct, vol_change_pct = _calc_change_and_volume(f_hist)
        futures_today = float(f_hist["Close"].iloc[-1])

        s_hist = _fetch_hist_valid(SPOT_TICKER)
        spot_price = float(s_hist["Close"].iloc[-1]) if s_hist is not None else None
        price_spread = (futures_today - spot_price) if spot_price is not None else 0.0

        return {
            "ok": True,
            "futures_change_pct": change_pct,
            "volume_change_pct": vol_change_pct,
            "price_spread": price_spread,
        }

    logger.warning(f"[期貨] {FUTURES_TICKER} 無有效資料，切換備援至 {SPOT_TICKER}")

    # 備援：使用 ^TWII 大盤指數
    s_hist = _fetch_hist_valid(SPOT_TICKER)
    if s_hist is not None:
        change_pct, vol_change_pct = _calc_change_and_volume(s_hist)
        return {
            "ok": True,
            "futures_change_pct": change_pct,
            "volume_change_pct": vol_change_pct,
            "price_spread": 0.0,
        }

    logger.error(f"[期貨] {FUTURES_TICKER} 與 {SPOT_TICKER} 均無法取得資料，futures_score 設為 0")
    return {"ok": False}


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
    except Exception as e:
        logger.error(f"[期貨] 取得台指期貨資料時發生例外：{e}")
        return {"futures_change_pct": 0.0, "volume_change_pct": 0.0, "price_spread": 0.0, "futures_score": 0}
