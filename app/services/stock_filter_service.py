from asyncio import get_event_loop
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import httpx
import yfinance as yf
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.stock_pool import StockPool

_thread_pool = ThreadPoolExecutor(max_workers=4)

TWSE_STOCK_LIST_URL = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
BATCH_SIZE = 50
MIN_YIELD_PCT = 4.0        # 4%（統一以百分比為單位比較）
MIN_MARKET_CAP = 5_000_000_000  # 50億（yfinance 台股市值單位為 TWD）
EXCLUDED_SECTORS = {"Healthcare"}
EXCLUDED_INDUSTRY_KEYWORDS = ["semiconductor"]


def _normalize_yield_pct(raw: float | None) -> float | None:
    """將 yfinance dividendYield 統一換算為百分比（%）。
    yfinance 對台股回傳格式不一致：
      0.0407 → 小數，需 × 100 → 4.07%
      4.07   → 已是百分比，直接使用
      407.0  → 百分比 × 100，需 ÷ 100 → 4.07%
    """
    if raw is None:
        return None
    if raw > 100:
        return round(raw / 100, 4)
    if raw > 1:
        return round(raw, 4)
    return round(raw * 100, 4)


async def _fetch_twse_stock_list() -> list[dict]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            TWSE_STOCK_LIST_URL,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        data = response.json()

    stocks = []
    for item in data:
        code = item.get("Code", "").strip()
        name = item.get("Name", "").strip()
        if code and name and code.isdigit() and len(code) <= 6:
            stocks.append({"code": code, "name": name})
    return stocks


def _fetch_yf_info_batch(symbols: list[str]) -> dict[str, dict | None]:
    results = {}
    for symbol in symbols:
        try:
            info = yf.Ticker(symbol).info
            results[symbol] = {
                "dividend_yield": info.get("dividendYield"),
                "market_cap": info.get("marketCap"),
                "sector": info.get("sector") or "",
                "industry": info.get("industry") or "",
            }
        except Exception:
            results[symbol] = None
    return results


def _passes_filter(info: dict | None) -> bool:
    if info is None:
        return False
    dy_pct = _normalize_yield_pct(info.get("dividend_yield"))
    mc = info.get("market_cap")
    sector = info.get("sector", "")
    industry = info.get("industry", "")

    if dy_pct is None or dy_pct < MIN_YIELD_PCT:
        return False
    if mc is None or mc < MIN_MARKET_CAP:
        return False
    if sector in EXCLUDED_SECTORS:
        return False
    if any(kw in industry.lower() for kw in EXCLUDED_INDUSTRY_KEYWORDS):
        return False
    return True


async def filter_stock_pool() -> list[dict]:
    """從 TWSE 取得上市股票清單，批次驗證殖利率與市值，回傳通過篩選的股票"""
    print("[stock_filter] 開始篩選...")
    try:
        stocks = await _fetch_twse_stock_list()
        print(f"[stock_filter] TWSE 取得 {len(stocks)} 檔股票")
    except Exception as e:
        print(f"[stock_filter] 抓取 TWSE 清單失敗: {e}")
        return []

    loop = get_event_loop()
    passed: list[dict] = []

    for i in range(0, len(stocks), BATCH_SIZE):
        batch = stocks[i : i + BATCH_SIZE]
        symbols = [f"{s['code']}.TW" for s in batch]

        try:
            info_map = await loop.run_in_executor(
                _thread_pool, _fetch_yf_info_batch, symbols
            )
        except Exception as e:
            print(f"[stock_filter] 批次 {i//BATCH_SIZE + 1} yfinance 失敗: {e}")
            continue

        for stock in batch:
            symbol = f"{stock['code']}.TW"
            info = info_map.get(symbol)
            if _passes_filter(info):
                yield_pct = _normalize_yield_pct(info["dividend_yield"]) or 0.0
                passed.append(
                    {
                        "code": stock["code"],
                        "name": stock["name"],
                        "yield_pct": round(yield_pct, 2),
                        "market_cap": round((info["market_cap"] or 0) / 1e8, 2),
                    }
                )

        print(
            f"[stock_filter] 批次 {i//BATCH_SIZE + 1}/{(len(stocks)-1)//BATCH_SIZE + 1} 完成，目前通過 {len(passed)} 檔"
        )

    return passed


async def save_stock_pool(stocks: list[dict], db: AsyncSession) -> None:
    """清空舊股票池並寫入新結果"""
    print(f"[save_stock_pool] 刪除舊資料中...")
    await db.execute(delete(StockPool))
    now = datetime.now(timezone.utc)
    for s in stocks:
        db.add(
            StockPool(
                stock_code=s["code"],
                stock_name=s["name"],
                yield_pct=s["yield_pct"],
                market_cap=s["market_cap"],
                updated_at=now,
            )
        )
    print(f"[save_stock_pool] 準備 commit {len(stocks)} 筆資料...")
    await db.commit()
    print(f"[save_stock_pool] commit 完成 ✓")
