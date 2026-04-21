from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.signal import Signal
from app.services.ai_service import ai_service

import httpx
import yfinance as yf
from asyncio import get_event_loop
from concurrent.futures import ThreadPoolExecutor
from app.core.config import settings
from datetime import date

_thread_pool = ThreadPoolExecutor(max_workers=4)


def _fetch_yfinance_data(ticker_symbol: str) -> dict:
    """在執行緒中同步呼叫 yfinance，回傳均線、成交量與殖利率相關數據"""
    ticker = yf.Ticker(ticker_symbol)
    hist = ticker.history(period="30d")

    if hist.empty or len(hist) < 2:
        return {"close": None, "ma20": None, "vol_today": None, "vol_avg5": None, "dividend_yield": None}

    close_today = float(hist["Close"].iloc[-1])
    ma20 = float(hist["Close"].tail(20).mean()) if len(hist) >= 20 else float(hist["Close"].mean())
    vol_today = float(hist["Volume"].iloc[-1])
    vol_avg5 = float(hist["Volume"].tail(6).iloc[:-1].mean()) if len(hist) >= 6 else float(hist["Volume"].mean())

    try:
        info = ticker.info
        dividend_yield = info.get("dividendYield")  # 例如 0.065 代表 6.5%
        print(f"[yfinance] {ticker_symbol} 殖利率原始值: {dividend_yield}")
    except Exception as e:
        print(f"[yfinance] {ticker_symbol} 殖利率取得失敗: {e}")
        dividend_yield = None

    return {
        "close": close_today,
        "ma20": ma20,
        "vol_today": vol_today,
        "vol_avg5": vol_avg5,
        "dividend_yield": dividend_yield,
    }


async def _get_institutional_score(stock_code: str) -> int:
    """呼叫 TWSE T86 API，取得外資+投信買賣超合計並計算法人得分"""
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
            print(f"  TWSE T86 回傳狀態非 OK：{data.get('stat')}")
            return 0

        # fields 欄位順序：[證券代號, 證券名稱, ..., 外資買賣超, 投信買賣超, ...]
        fields = data.get("fields", [])
        rows = data.get("data", [])

        try:
            foreign_idx = fields.index("外陸資買賣超股數(千股)")
            trust_idx = fields.index("投信買賣超股數(千股)")
            code_idx = 0
        except ValueError:
            # 嘗試備用欄位名稱
            try:
                foreign_idx = next(i for i, f in enumerate(fields) if "外" in f and "買賣超" in f)
                trust_idx = next(i for i, f in enumerate(fields) if "投信" in f and "買賣超" in f)
                code_idx = 0
            except StopIteration:
                print(f"  無法解析 T86 欄位：{fields}")
                return 0

        for row in rows:
            if row[code_idx].strip() == stock_code.strip():
                foreign_net = int(row[foreign_idx].replace(",", "").replace("+", "") or 0)
                trust_net = int(row[trust_idx].replace(",", "").replace("+", "") or 0)
                net_total = foreign_net + trust_net

                if net_total > 1000:
                    return 2
                elif net_total > 0:
                    return 1
                else:
                    return -2

        print(f"  T86 找不到股票代號 {stock_code}")
        return 0

    except Exception as e:
        print(f"  TWSE T86 呼叫失敗，法人得分設為 0：{e}")
        return 0


async def calculate_score(stock_code: str) -> dict:
    """
    計算指定股票的今日評分（法人 + 均線 + 成交量 + 殖利率）
    回傳各參數得分與總分
    """
    # --- 法人得分（TWSE T86） ---
    institutional_score = await _get_institutional_score(stock_code)

    # --- 均線 & 成交量 & 殖利率得分（yfinance，非同步執行緒） ---
    ma_score = 0
    volume_score = 0
    yield_score = 0
    ticker_symbol = f"{stock_code}.TW"

    try:
        loop = get_event_loop()
        yf_data = await loop.run_in_executor(
            _thread_pool, _fetch_yfinance_data, ticker_symbol
        )

        close = yf_data["close"]
        ma20 = yf_data["ma20"]
        vol_today = yf_data["vol_today"]
        vol_avg5 = yf_data["vol_avg5"]
        dividend_yield = yf_data["dividend_yield"]

        # 均線得分
        if close is not None and ma20 is not None and ma20 > 0:
            if close < ma20 * 0.98:
                ma_score = 2
            elif close <= ma20 * 1.05:
                ma_score = 1
            else:
                ma_score = -1

        # 成交量得分
        if vol_today is not None and vol_avg5 is not None and vol_avg5 > 0:
            ratio = vol_today / vol_avg5
            if ratio > 1.5:
                volume_score = 2
            elif ratio >= 0.7:
                volume_score = 0
            else:
                volume_score = -1

        # 殖利率得分（yfinance 回傳已是百分比，如 9.93 代表 9.93%）
        if dividend_yield is not None:
            if dividend_yield >= 6.5:
                yield_score = 2
            elif dividend_yield >= 5.0:
                yield_score = 1
            else:
                yield_score = -1

    except Exception as e:
        print(f"  yfinance 呼叫失敗，均線/成交量/殖利率得分設為 0：{e}")

    total_score = institutional_score + ma_score + volume_score + yield_score

    return {
        "institutional_score": institutional_score,
        "ma_score": ma_score,
        "volume_score": volume_score,
        "yield_score": yield_score,
        "total_score": total_score,
    }


async def create_today_signal(
    stock_code: str, stock_name: str, db: AsyncSession
) -> Signal:
    """
    計算今日評分 → 呼叫 AI 分析 → 儲存至資料庫
    若今日已有紀錄則更新，否則新增
    """
    today = date.today().strftime("%Y-%m-%d")
    scores = await calculate_score(stock_code)

    ai_result = await ai_service.analyze_signal({
        "stock_code": stock_code,
        "stock_name": stock_name,
        **scores,
    })

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

    return signal


async def get_today_signal(stock_code: str, db: AsyncSession) -> Signal:
    """從資料庫查詢指定股票的今日評分訊號"""
    today = date.today().strftime("%Y-%m-%d")
    result = await db.execute(
        select(Signal).where(
            Signal.stock_code == stock_code,
            Signal.date == today,
        )
    )
    return result.scalars().first()
