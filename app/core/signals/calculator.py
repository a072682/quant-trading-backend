#region 引入套件
# asyncio：取得事件迴圈，讓同步的 yfinance 在非同步環境中執行
import asyncio

# datetime、timezone、timedelta：計算台灣時區的今日日期
from datetime import datetime, timezone, timedelta

# httpx：非同步 HTTP 客戶端，用來呼叫 TWSE 法人資料 API
import httpx

# yfinance：查詢股票歷史行情（收盤價、成交量、殖利率）
import yfinance as yf
#endregion


#region 常數設定
# 台灣時區（UTC+8）
TW_TZ = timezone(timedelta(hours=8))

# TWSE 三大法人買賣超 API 網址（T86 報表）
# 回傳當日所有股票的外資、投信、自營商買賣超資料
TWSE_INSTITUTIONAL_URL = "https://www.twse.com.tw/rwd/zh/fund/T86"

# 法人合計淨買超門檻（單位：股）
# 1000 張 × 1000 股/張 = 1,000,000 股
INSTITUTIONAL_THRESHOLD = 1_000_000

# 均線乘數：低於均線 × 0.98 視為相對低點（買進訊號）
MA_LOWER_BOUND = 0.98

# 均線乘數：高於均線 × 1.05 視為相對高點（過熱）
MA_UPPER_BOUND = 1.05

# 量比門檻：今日量 / 5日均量 > 1.5 視為放量
VOLUME_HIGH_RATIO = 1.5

# 量比門檻：量比 < 0.7 視為縮量
VOLUME_LOW_RATIO = 0.7

# 殖利率高分門檻（%）：≥ 6.5% 給最高分
YIELD_HIGH = 6.5

# 殖利率中分門檻（%）：5.0% ≤ 殖利率 < 6.5% 給中分
YIELD_MID = 5.0

# 大盤漲跌幅門檻（%）：> 1% 視為偏多，< -1% 視為偏空
MARKET_THRESHOLD = 1.0
#endregion


#region 函式：fetch_institutional_score — 從 TWSE API 抓取法人買賣超，計算得分
# 作用：查詢今日外資與投信的合計淨買超，轉換為評分
# 輸入：stock_code（股票代號，字串，例如 "2330"）
# 輸出：整數分數（-2 到 +2）
# 計分規則：
#   外資 + 投信合計淨買超 > 1000 張 → +2
#   合計淨買超 > 0 張          → +1
#   合計淨買超 ≤ 0 張          → -2
#   查不到資料                  → 0
async def fetch_institutional_score(stock_code: str) -> int:
    """從 TWSE T86 報表抓取今日法人買賣超，計算得分"""

    print(f"[法人評分] 開始查詢 {stock_code} 法人資料...")

    try:
        # 取得台灣今日日期，格式為 YYYYMMDD（TWSE API 要求）
        today_str = datetime.now(TW_TZ).strftime("%Y%m%d")

        async with httpx.AsyncClient(timeout=20.0) as client:
            # 呼叫 TWSE T86 API，取得當日所有股票的法人買賣超資料
            response = await client.get(
                TWSE_INSTITUTIONAL_URL,
                params={
                    "response": "json",
                    "date": today_str,
                    # ALL：取得全部股票的三大法人資料
                    "selectType": "ALL",
                },
                headers={"User-Agent": "Mozilla/5.0"},
            )
            data = response.json()

        # stat != "OK" 代表當日無資料（例如假日或盤後尚未公布）
        if data.get("stat") != "OK":
            print(f"[法人評分] {stock_code} 今日無法人資料（stat={data.get('stat')}）")
            return 0

        # 逐筆搜尋目標股票代號
        for row in data.get("data", []):
            # T86 欄位順序：[0]代號 [1]名稱 [2]外資買進 [3]外資賣出 [4]外資淨買超
            #               [5]投信買進 [6]投信賣出 [7]投信淨買超 [8]自營商 [9]合計
            if row[0].strip() != stock_code:
                continue

            # 去除千分位逗號後轉換為整數（例如 "1,234,567" → 1234567）
            # 外資淨買超（欄位索引 4），單位：股
            foreign_net = int(row[4].replace(",", "").strip())
            # 投信淨買超（欄位索引 7），單位：股
            trust_net = int(row[7].replace(",", "").strip())
            # 合計淨買超
            total_net = foreign_net + trust_net

            # 計分邏輯
            if total_net > INSTITUTIONAL_THRESHOLD:
                # 大幅買超，強烈看多訊號
                score = 2
            elif total_net > 0:
                # 小幅買超，溫和看多訊號
                score = 1
            else:
                # 賣超，看空訊號
                score = -2

            print(f"[法人評分] {stock_code} 得分：{score}（外資{foreign_net:+,}，投信{trust_net:+,}）")
            return score

        # 找不到該股票代號的資料
        print(f"[法人評分] {stock_code} 在法人資料中找不到對應記錄，得分：0")
        return 0

    except Exception as e:
        print(f"[法人評分] {stock_code} 查詢失敗：{e}")
        return 0
#endregion


#region 函式：fetch_ma_score — 從 yfinance 抓取均線資料，計算得分
# 作用：取得近 30 天收盤價，計算 20 日均線，比較今日收盤價位置
# 輸入：stock_code（股票代號，字串）
# 輸出：整數分數（-1 到 +2）
# 計分規則：
#   今日收盤價 < 20日均線 × 0.98 → +2（明顯低於均線，相對低點）
#   今日收盤價 ≤ 20日均線 × 1.05 → +1（接近均線，合理位置）
#   今日收盤價 > 20日均線 × 1.05 → -1（明顯高於均線，相對高點）
#   查不到資料                     → 0
async def fetch_ma_score(stock_code: str) -> int:
    """取得 yfinance 近 30 天收盤價，計算 20 日均線得分"""

    print(f"[均線評分] 開始查詢 {stock_code} 均線資料...")

    try:
        # 使用 asyncio.to_thread 在獨立執行緒中執行同步的 yfinance 查詢
        # 避免阻塞 asyncio 事件迴圈
        def _get_history():
            return yf.Ticker(f"{stock_code}.TW").history(period="30d")

        df = await asyncio.to_thread(_get_history)

        # 資料不足（少於 20 筆）無法計算均線
        if df is None or len(df) < 20:
            print(f"[均線評分] {stock_code} 資料不足，得分：0")
            return 0

        # 今日收盤價（最後一筆）
        price = float(df["Close"].iloc[-1])
        # 20 日均線（最後 20 筆收盤價的平均）
        ma20 = float(df["Close"].tail(20).mean())

        # 計分邏輯
        if price < ma20 * MA_LOWER_BOUND:
            # 股價明顯低於均線，相對低點，買入訊號
            score = 2
        elif price <= ma20 * MA_UPPER_BOUND:
            # 股價在均線附近（合理區間），中性偏多
            score = 1
        else:
            # 股價明顯高於均線，相對高點，過熱訊號
            score = -1

        print(f"[均線評分] {stock_code} 收盤價：{price:.2f}，20日均線：{ma20:.2f}，得分：{score}")
        return score

    except Exception as e:
        print(f"[均線評分] {stock_code} 查詢失敗：{e}")
        return 0
#endregion


#region 函式：fetch_volume_score — 從 yfinance 抓取成交量，計算量比得分
# 作用：計算今日成交量相對於近 5 日均量的比值（量比）
# 輸入：stock_code（股票代號，字串）
# 輸出：整數分數（-1 到 +2）
# 計分規則：
#   量比 > 1.5  → +2（明顯放量，主力介入訊號）
#   量比 0.7～1.5 → 0（正常量能，中性）
#   量比 < 0.7  → -1（明顯縮量，觀望訊號）
#   查不到資料   → 0
async def fetch_volume_score(stock_code: str) -> int:
    """取得 yfinance 近 30 天成交量，計算量比得分"""

    print(f"[成交量評分] 開始查詢 {stock_code} 成交量資料...")

    try:
        # 在獨立執行緒中執行同步的 yfinance 查詢
        def _get_history():
            return yf.Ticker(f"{stock_code}.TW").history(period="30d")

        df = await asyncio.to_thread(_get_history)

        # 資料不足（少於 6 筆）無法計算 5 日均量
        if df is None or len(df) < 6:
            print(f"[成交量評分] {stock_code} 資料不足，得分：0")
            return 0

        # 今日成交量（最後一筆）
        today_vol = float(df["Volume"].iloc[-1])
        # 近 5 日均量（不含今日，取倒數第 2 至第 6 筆）
        avg_vol_5 = float(df["Volume"].iloc[-6:-1].mean())

        # 避免除以零
        if avg_vol_5 == 0:
            return 0

        # 量比 = 今日成交量 / 近 5 日均量
        ratio = today_vol / avg_vol_5

        # 計分邏輯
        if ratio > VOLUME_HIGH_RATIO:
            # 明顯放量，主力買進訊號
            score = 2
        elif ratio < VOLUME_LOW_RATIO:
            # 明顯縮量，市場觀望
            score = -1
        else:
            # 量能正常，中性
            score = 0

        print(f"[成交量評分] {stock_code} 量比：{ratio:.2f}，得分：{score}")
        return score

    except Exception as e:
        print(f"[成交量評分] {stock_code} 查詢失敗：{e}")
        return 0
#endregion


#region 函式：fetch_yield_score — 從 yfinance 抓取殖利率，計算得分
# 作用：查詢該股票的年化殖利率，給予評分
# 輸入：stock_code（股票代號，字串）
# 輸出：整數分數（-1 到 +2）
# 計分規則：
#   殖利率 ≥ 6.5% → +2（高殖利率，具吸引力）
#   殖利率 5.0% 到 6.5% → +1（中等殖利率，尚可）
#   殖利率 < 5.0%  → -1（殖利率偏低）
#   查不到資料      → 0
async def fetch_yield_score(stock_code: str) -> int:
    """取得 yfinance 殖利率資料，計算得分"""

    print(f"[殖利率評分] 開始查詢 {stock_code} 殖利率...")

    try:
        # 在獨立執行緒中執行同步的 yfinance 查詢
        def _get_info():
            return yf.Ticker(f"{stock_code}.TW").info

        info = await asyncio.to_thread(_get_info)

        # 取得殖利率原始值（yfinance 格式不一致，需換算）
        raw_yield = info.get("dividendYield")

        if raw_yield is None:
            print(f"[殖利率評分] {stock_code} 無殖利率資料，得分：0")
            return 0

        # 換算為百分比（%）
        # yfinance 台股殖利率格式不一致：0.0407 / 4.07 / 407.0 均有可能
        if raw_yield > 100:
            # 百分比再乘以 100，需除以 100
            yield_pct = raw_yield / 100
        elif raw_yield > 1:
            # 已是百分比，直接使用
            yield_pct = raw_yield
        else:
            # 小數形式，需乘以 100
            yield_pct = raw_yield * 100

        # 計分邏輯
        if yield_pct >= YIELD_HIGH:
            # 高殖利率，對存股投資人具吸引力
            score = 2
        elif yield_pct >= YIELD_MID:
            # 中等殖利率，尚可接受
            score = 1
        else:
            # 殖利率偏低，不符合存股條件
            score = -1

        print(f"[殖利率評分] {stock_code} 殖利率：{yield_pct:.2f}%，得分：{score}")
        return score

    except Exception as e:
        print(f"[殖利率評分] {stock_code} 查詢失敗：{e}")
        return 0
#endregion


#region 函式：fetch_market_score — 從 yfinance 抓取大盤資料，計算市場情緒得分
# 作用：查詢台灣加權指數（^TWII）當日漲跌幅與成交量，評估整體市場情緒
# 輸入：無（大盤資料所有股票共用，只需抓一次）
# 輸出：整數分數（-2 到 +2）
# 計分規則：
#   大盤漲幅 > +1% 且成交量增加 → +2（強多頭，放量上漲）
#   大盤漲幅 > +1%              → +1（偏多，但量能不足）
#   大盤跌幅 < -1% 且成交量增加 → -2（強空頭，放量下跌）
#   大盤跌幅 < -1%              → -1（偏空，但量能萎縮）
#   漲跌幅在 ±1% 以內           → 0（盤整，中性）
#   查不到資料                   → 0
async def fetch_market_score() -> int:
    """取得台灣加權指數漲跌幅與成交量，計算市場情緒得分"""

    print("[大盤評分] 開始查詢大盤資料...")

    try:
        # 在獨立執行緒中執行同步的 yfinance 查詢
        # period="2d"：取最近 2 個交易日，用於計算今日漲跌幅
        def _get_market():
            return yf.Ticker("^TWII").history(period="2d")

        df = await asyncio.to_thread(_get_market)

        # 至少需要 2 筆才能計算漲跌幅
        if df is None or len(df) < 2:
            print("[大盤評分] 大盤資料不足，得分：0")
            return 0

        # 今日收盤價
        close_today = float(df["Close"].iloc[-1])
        # 昨日收盤價
        close_prev = float(df["Close"].iloc[-2])
        # 今日成交量
        vol_today = float(df["Volume"].iloc[-1])
        # 昨日成交量
        vol_prev = float(df["Volume"].iloc[-2])

        # 計算漲跌幅（百分比）
        pct = ((close_today - close_prev) / close_prev) * 100
        # 判斷今日成交量是否大於昨日（量增）
        vol_increased = vol_today > vol_prev

        # 計分邏輯
        if pct > MARKET_THRESHOLD and vol_increased:
            # 大漲且放量，強多頭訊號
            score = 2
        elif pct > MARKET_THRESHOLD:
            # 大漲但量能不足，偏多但力道弱
            score = 1
        elif pct < -MARKET_THRESHOLD and vol_increased:
            # 大跌且放量，強空頭訊號
            score = -2
        elif pct < -MARKET_THRESHOLD:
            # 大跌但量能萎縮，偏空但力道弱
            score = -1
        else:
            # 盤整，市場中性
            score = 0

        print(f"[大盤評分] 大盤漲跌幅：{pct:.2f}%，得分：{score}")
        return score

    except Exception as e:
        print(f"[大盤評分] 查詢失敗：{e}")
        return 0
#endregion


#region 函式：calculate_total_score — 呼叫所有分項函式，計算並回傳所有分數
# 作用：依序取得各分項評分，加總為總分，回傳完整評分字典
# 輸入：
#   stock_code（股票代號，字串）
#   stock_name（股票名稱，字串）
#   market_score（已預先取得的大盤評分，整數）
#       注意：market_score 由外部傳入，避免每支股票都重複抓一次大盤資料
# 輸出：字典，包含所有分項分數和 total_score
#   {
#     "institutional_score": ...,
#     "ma_score": ...,
#     "volume_score": ...,
#     "yield_score": ...,
#     "futures_score": ...,   ← 大盤分數存入 futures_score 欄位（對應資料庫欄位名稱）
#     "total_score": ...,
#   }
async def calculate_total_score(
    stock_code: str,
    stock_name: str,
    market_score: int,
) -> dict:
    """呼叫所有分項評分函式，計算並回傳完整評分字典"""

    print(f"[評分] 開始計算 {stock_code} {stock_name} 總分...")

    # 同時呼叫四個分項評分函式（法人、均線、成交量、殖利率）
    # asyncio.gather：並行執行多個 async 函式，等全部完成後再繼續
    institutional, ma, volume, yld = await asyncio.gather(
        fetch_institutional_score(stock_code),
        fetch_ma_score(stock_code),
        fetch_volume_score(stock_code),
        fetch_yield_score(stock_code),
    )

    # 計算總分（加總所有分項）
    total = institutional + ma + volume + yld + market_score

    print(f"[評分] {stock_code} 總分：{total}（法人:{institutional} 均線:{ma} 量:{volume} 殖:{yld} 大盤:{market_score}）")

    # 回傳完整評分字典，鍵名對應 Signal 資料表欄位名稱
    return {
        # 法人買賣超得分
        "institutional_score": institutional,
        # 均線位置得分
        "ma_score": ma,
        # 成交量量比得分
        "volume_score": volume,
        # 殖利率得分
        "yield_score": yld,
        # 大盤情緒得分（存入 futures_score 欄位）
        "futures_score": market_score,
        # 加總總分
        "total_score": total,
    }
#endregion
