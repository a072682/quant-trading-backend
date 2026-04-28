#region 引入套件
# asyncio：取得當前事件迴圈，讓同步的 yfinance 在非同步環境中執行
import asyncio

# ThreadPoolExecutor：建立執行緒池，讓同步的 yfinance 不會阻塞主執行緒
from concurrent.futures import ThreadPoolExecutor

# yfinance：查詢股票資訊（殖利率、市值、產業別）
import yfinance as yf
#endregion


#region 常數設定
# 每批次同時查詢的股票數量
BATCH_SIZE = 50

# 殖利率門檻：通過篩選至少要有 4%（百分比為單位）
MIN_YIELD_PCT = 4.0

# 市值門檻：通過篩選至少要有 50 億台幣（yfinance 台股市值單位為 TWD）
MIN_MARKET_CAP = 5_000_000_000

# 排除的產業別（sector）
EXCLUDED_SECTORS = {"Healthcare"}

# 排除的行業關鍵字（industry，不分大小寫）
EXCLUDED_INDUSTRY_KEYWORDS = ["semiconductor"]

# 執行緒池：最多同時 4 條執行緒，供 yfinance 查詢使用
_thread_pool = ThreadPoolExecutor(max_workers=4)
#endregion


#region 內部函式：_normalize_yield_pct — 將 yfinance 殖利率統一換算為百分比
# 作用：yfinance 對台股的 dividendYield 回傳格式不一致，需統一換算
# 輸入：raw（yfinance 回傳的原始殖利率，可能為 None）
# 輸出：以百分比表示的殖利率（如 4.07），或 None（無資料）
# 換算規則：
#   0.0407 → 小數形式，需 × 100 → 4.07%
#   4.07   → 已是百分比，直接使用
#   407.0  → 百分比 × 100，需 ÷ 100 → 4.07%
def _normalize_yield_pct(raw: float | None) -> float | None:
    """將 yfinance dividendYield 統一換算為百分比（%）"""
    # 若無資料直接回傳 None
    if raw is None:
        return None
    # 大於 100 代表是百分比再乘以 100，需除以 100
    if raw > 100:
        return round(raw / 100, 4)
    # 大於 1 代表已是百分比，直接使用
    if raw > 1:
        return round(raw, 4)
    # 小於等於 1 代表是小數形式，需乘以 100
    return round(raw * 100, 4)
#endregion


#region 內部函式：_fetch_yf_info_batch — 同步批次查詢 yfinance 股票資訊
# 作用：逐一查詢一批股票的殖利率、市值、產業別
# 輸入：symbols（yfinance 格式的股票代碼清單，如 ["2330.TW", "2412.TW"]）
# 輸出：{symbol: {dividend_yield, market_cap, sector, industry}} 或 {symbol: None}（查詢失敗）
# 注意：此函式為同步函式，需在執行緒池中執行，避免阻塞 asyncio 事件迴圈
def _fetch_yf_info_batch(symbols: list[str]) -> dict[str, dict | None]:
    """同步批次查詢 yfinance 股票資訊，回傳各股票的原始資料"""
    results = {}
    for symbol in symbols:
        try:
            # 使用 yfinance 查詢個股資訊
            info = yf.Ticker(symbol).info
            results[symbol] = {
                # 殖利率（原始值，格式不一致，需透過 _normalize_yield_pct 換算）
                "dividend_yield": info.get("dividendYield"),
                # 市值（台幣，單位：元）
                "market_cap": info.get("marketCap"),
                # 產業別（如 "Financial Services"）
                "sector": info.get("sector") or "",
                # 細分行業（如 "Banks—Regional"）
                "industry": info.get("industry") or "",
            }
        except Exception:
            # 查詢失敗時記為 None，後續篩選會過濾掉
            results[symbol] = None
    return results
#endregion


#region 內部函式：_passes_filter — 判斷單支股票是否通過篩選條件
# 作用：依據殖利率、市值、產業別判斷是否符合篩選標準
# 輸入：info（單支股票的 yfinance 原始資料 dict，或 None）
# 輸出：True（通過）或 False（不通過）
def _passes_filter(info: dict | None) -> bool:
    """判斷單支股票是否通過殖利率、市值、產業別的篩選條件"""
    # None 代表查詢失敗，直接排除
    if info is None:
        return False

    # 換算殖利率為百分比
    dy_pct = _normalize_yield_pct(info.get("dividend_yield"))
    # 取得市值
    mc = info.get("market_cap")
    # 取得產業別
    sector = info.get("sector", "")
    # 取得細分行業
    industry = info.get("industry", "")

    # 殖利率不足門檻，排除
    if dy_pct is None or dy_pct < MIN_YIELD_PCT:
        return False
    # 市值不足門檻，排除
    if mc is None or mc < MIN_MARKET_CAP:
        return False
    # 在排除產業別清單中，排除
    if sector in EXCLUDED_SECTORS:
        return False
    # 行業名稱包含排除關鍵字，排除
    if any(kw in industry.lower() for kw in EXCLUDED_INDUSTRY_KEYWORDS):
        return False

    # 全部條件通過
    return True
#endregion


#region 函式：filter_by_yfinance — 逐批用 yfinance 篩選符合條件的股票
# 作用：將 fetch_twse_stocks() 回傳的清單，逐批查詢 yfinance 並篩選出符合條件的股票
# 輸入：raw_stocks（記憶體裡的股票清單，格式：[{"code": "2330", "name": "台積電"}, ...]）
# 輸出：通過篩選的股票清單，格式：
#   [{"code": "2330", "name": "台積電", "yield_pct": 4.07, "market_cap": 200.00}, ...]
#   market_cap 單位：億台幣（已換算）
async def filter_by_yfinance(raw_stocks: list[dict]) -> list[dict]:
    """逐批查詢 yfinance，篩選殖利率與市值符合條件的股票"""

    print(f"[yfinance] 開始篩選，共 {len(raw_stocks)} 支股票...")

    # 取得當前 asyncio 事件迴圈，讓同步的 yfinance 可在執行緒池中執行
    loop = asyncio.get_event_loop()
    # 存放通過篩選的股票
    passed: list[dict] = []
    # 計算總批次數
    total_batches = (len(raw_stocks) - 1) // BATCH_SIZE + 1

    try:
        # 每次取 BATCH_SIZE 支股票進行批次查詢
        for i in range(0, len(raw_stocks), BATCH_SIZE):
            # 取出當前批次的股票
            batch = raw_stocks[i: i + BATCH_SIZE]
            # 轉換為 yfinance 格式的代碼（加上 .TW 後綴）
            symbols = [f"{s['code']}.TW" for s in batch]
            # 計算當前批次編號（從 1 開始）
            batch_num = i // BATCH_SIZE + 1

            try:
                # 在執行緒池中執行同步的 yfinance 查詢，避免阻塞 asyncio 事件迴圈
                info_map = await loop.run_in_executor(
                    _thread_pool, _fetch_yf_info_batch, symbols
                )
            except Exception as e:
                # 整批查詢失敗時跳過，繼續下一批
                print(f"[yfinance] 批次 {batch_num}/{total_batches} 查詢失敗：{e}")
                continue

            # 逐一檢查批次內每支股票是否通過篩選
            for stock in batch:
                symbol = f"{stock['code']}.TW"
                info = info_map.get(symbol)

                if _passes_filter(info):
                    # 換算殖利率為百分比，若為 None 則預設 0.0
                    yield_pct = _normalize_yield_pct(info["dividend_yield"]) or 0.0
                    passed.append({
                        "code": stock["code"],
                        "name": stock["name"],
                        # 殖利率四捨五入至小數點後兩位（百分比）
                        "yield_pct": round(yield_pct, 2),
                        # 市值換算為億台幣，四捨五入至小數點後兩位
                        "market_cap": round((info["market_cap"] or 0) / 1e8, 2),
                    })

            print(f"[yfinance] 批次 {batch_num}/{total_batches} 完成，目前通過 {len(passed)} 檔")

        print(f"[yfinance] 篩選完成，共通過 {len(passed)} 支")
        # 回傳格式：[{"code": ..., "name": ..., "yield_pct": ..., "market_cap": ...}, ...]
        return passed

    except Exception as e:
        print(f"[yfinance] 篩選失敗：{e}")
        raise
#endregion
