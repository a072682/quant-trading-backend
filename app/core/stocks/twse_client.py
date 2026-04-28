#region 引入套件
# httpx：非同步 HTTP 客戶端，用來呼叫 TWSE 開放 API
import httpx
#endregion


#region 常數設定
# TWSE 開放 API 網址：回傳所有上市股票的每日行情資料
TWSE_STOCK_LIST_URL = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
#endregion


#region 函式：fetch_twse_stocks — 從 TWSE 官網抓取所有上市股票清單
# 作用：呼叫 TWSE 開放 API，取得當日所有上市股票代碼與名稱
# 輸入：無
# 輸出：[{"code": "2330", "name": "台積電"}, ...] 存在記憶體
# 篩選條件：
#   - code 必須存在且不為空
#   - name 必須存在且不為空
#   - code 必須全為數字（排除 ETF 等非一般股票）
#   - code 長度不超過 6 碼（排除異常資料）
async def fetch_twse_stocks() -> list[dict]:
    """從 TWSE 開放 API 取得所有上市股票清單，回傳代碼與名稱的清單"""

    print("[TWSE] 開始抓取股票清單...")

    try:
        # 建立非同步 HTTP 連線，設定 30 秒逾時
        async with httpx.AsyncClient(timeout=30.0) as client:
            # 呼叫 TWSE 開放 API，帶上 User-Agent 避免被擋
            response = await client.get(
                TWSE_STOCK_LIST_URL,
                # 模擬瀏覽器請求，避免 TWSE 因無 User-Agent 拒絕回應
                headers={"User-Agent": "Mozilla/5.0"},
            )
            # 將回應解析為 JSON 格式（list of dict）
            data = response.json()

        # 從回傳的 JSON 清單中逐筆篩選有效的股票
        stocks = []
        for item in data:
            # 取出股票代碼，去除前後空白
            code = item.get("Code", "").strip()
            # 取出股票名稱，去除前後空白
            name = item.get("Name", "").strip()

            # 篩選條件：code 與 name 都存在、code 全為數字、code 長度不超過 6
            if code and name and code.isdigit() and len(code) <= 6:
                stocks.append({"code": code, "name": name})

        print(f"[TWSE] 成功取得 {len(stocks)} 支股票")
        # 回傳格式：[{"code": "2330", "name": "台積電"}, ...]
        return stocks

    except Exception as e:
        # 記錄錯誤原因，回傳空清單讓上層決定如何處理
        print(f"[TWSE] 抓取失敗：{e}")
        raise
#endregion
