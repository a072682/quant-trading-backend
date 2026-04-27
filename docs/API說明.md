# API 說明

> 所有 API 的基礎網址：`/api/v1`
>
> 除了「登入」和「註冊」以外，所有 API 都需要在 HTTP Header 帶上登入取得的 Token：
> ```
> Authorization: Bearer <你的 token>
> ```

---

## 一、認證（/api/v1/auth）

### POST /auth/login — 登入

**用途**：用帳號密碼換取登入 Token，之後呼叫其他 API 都需要帶上這個 Token。

**輸入參數**（JSON 格式）：
```json
{
  "email": "user@example.com",
  "password": "yourpassword"
}
```

**回傳格式**：
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer"
}
```

**前端使用**：登入頁面

---

### POST /auth/register — 註冊

**用途**：建立新帳號。

**輸入參數**（JSON 格式）：
```json
{
  "email": "user@example.com",
  "username": "我的名字",
  "password": "yourpassword"
}
```

**回傳格式**：
```json
{
  "message": "註冊成功",
  "data": {
    "id": "uuid...",
    "email": "user@example.com",
    "username": "我的名字"
  }
}
```

**前端使用**：註冊頁面

---

## 二、評分訊號（/api/v1/signals）

### GET /signals/today — 取得單一股票今日評分

**用途**：查詢某一檔股票「今天」的評分結果。

**輸入參數**（URL Query）：
- `stock_code`：股票代號，例如 `2886`

**範例**：`GET /api/v1/signals/today?stock_code=2886`

**回傳格式**：
```json
{
  "message": "取得今日評分成功",
  "data": {
    "id": "uuid...",
    "date": "2026-04-27",
    "stock_code": "2886",
    "stock_name": "兆豐金",
    "institutional_score": 2,
    "ma_score": 1,
    "volume_score": 0,
    "yield_score": 2,
    "futures_score": 1,
    "total_score": 6,
    "ai_action": "buy",
    "ai_reason": "法人持續買超，殖利率高，大盤偏多，建議逢低布局。",
    "created_at": "2026-04-27T06:00:00Z",
    "updated_at": "2026-04-27T06:00:00Z"
  }
}
```

**前端使用**：個股詳情頁面

---

### GET /signals/today-all — 取得今日所有股票評分

**用途**：列出今天所有已評分的股票，按照總分由高到低排列。

**輸入參數**：無

**回傳格式**：
```json
{
  "message": "取得今日所有評分成功",
  "data": [
    { "stock_code": "2886", "total_score": 8, ... },
    { "stock_code": "0056", "total_score": 6, ... }
  ]
}
```

**前端使用**：儀表板主頁的評分排行清單

---

### GET /signals/top — 取得今日推薦股票

**用途**：取得今日高分且「目前沒有模擬持倉」的推薦股票清單。

**輸入參數**（URL Query，都是選填）：
- `limit`：最多回傳幾筆，預設 3，最多 50
- `min_score`：最低分數門檻，預設 6

**範例**：`GET /api/v1/signals/top?limit=5&min_score=6`

**回傳格式**：同 today-all，只是只包含符合條件的股票

**前端使用**：儀表板的「今日推薦」卡片區塊

---

### GET /signals/history/{stock_code} — 歷史評分紀錄

**用途**：查詢某一檔股票最近 30 天的評分歷史。

**輸入參數**（URL Path）：
- `stock_code`：股票代號，例如 `2886`

**範例**：`GET /api/v1/signals/history/2886`

**回傳格式**：同 today 的格式，但是陣列，最多 30 筆，按日期由新到舊排列

**前端使用**：個股詳情頁面的歷史走勢圖

---

### GET /signals/by-date/{date} — 查詢特定日期評分

**用途**：查詢某一天所有股票的評分結果。

**輸入參數**（URL Path）：
- `date`：日期，格式 `YYYY-MM-DD`，例如 `2026-04-25`

**範例**：`GET /api/v1/signals/by-date/2026-04-25`

**回傳格式**：評分資料陣列，按股票代號排序

**前端使用**：歷史日期查詢頁面

---

### GET /signals/stats — 系統統計資訊

**用途**：取得系統的基本統計，例如資料庫裡有幾筆評分記錄、最後一次執行時間。

**輸入參數**：無

**回傳格式**：
```json
{
  "message": "取得統計資訊成功",
  "data": {
    "lastRunAt": "2026-04-27T06:00:00Z",
    "recordCount": 1234
  }
}
```

**前端使用**：儀表板的系統狀態顯示區域

---

### POST /signals/run-now — 手動觸發評分計算

**用途**：立即對指定股票（或整個股票池）執行評分計算，**含 AI 分析**。這就是前端「立即計算今日評分」按鈕觸發的 API。

**輸入參數**（JSON，選填）：
```json
{
  "stocks": [
    { "code": "2886", "name": "兆豐金" },
    { "code": "0056", "name": "元大高股息" }
  ]
}
```
> 若不傳 stocks，系統會自動用「整個股票池」計算；若股票池是空的，則用預設 5 檔。

**回傳格式**：所有計算完成的評分資料陣列

**注意**：這個 API 會等所有股票都算完才回傳，若股票多可能等待較久。

**前端使用**：儀表板的「立即計算今日評分」按鈕

---

### POST /signals/run-stock — 對單一股票立即評分

**用途**：對指定的一檔股票立即計算評分（含 AI 分析），通常在「新增股票到追蹤清單」後呼叫。

**輸入參數**（JSON）：
```json
{
  "stock_code": "2886",
  "stock_name": "兆豐金"
}
```

**回傳格式**：該股票的評分結果（單一物件）

**前端使用**：新增股票追蹤後的即時評分

---

### POST /signals/run-full — 全量評分（背景執行）

**用途**：對股票池所有股票執行全量評分，在**背景執行**（不需要等待），完成後自動對高分股票補做 AI 分析。

**輸入參數**：無

**回傳格式**：
```json
{
  "message": "全量評分已開始，將在背景執行，完成後自動更新資料庫"
}
```

> 若目前已有全量評分在執行中，會拒絕新的請求並回傳錯誤。

**前端使用**：管理頁面的「全量重算」功能按鈕

---

## 三、股票管理（/api/v1/stocks）

### GET /stocks/kline/{stock_code} — 取得 K 線數據

**用途**：取得某一檔股票最近 3 個月的每日 K 線（開高低收量）資料，用來畫圖表。

**輸入參數**（URL Path）：
- `stock_code`：股票代號，例如 `2886`

**範例**：`GET /api/v1/stocks/kline/2886`

**回傳格式**：
```json
{
  "message": "取得K線數據成功",
  "data": [
    {
      "time": "2026-01-02",
      "open": 38.5,
      "high": 39.2,
      "low": 38.1,
      "close": 38.9,
      "volume": 15234000
    }
  ]
}
```

**前端使用**：個股詳情頁面的 K 線走勢圖

---

### GET /stocks/pool — 取得股票池清單

**用途**：列出目前股票池裡所有的股票（通過篩選條件的追蹤名單）。

**輸入參數**：無

**回傳格式**：
```json
{
  "message": "取得股票池成功",
  "data": [
    {
      "stock_code": "2886",
      "stock_name": "兆豐金",
      "yield_pct": 5.8,
      "market_cap": 3200.5,
      "updated_at": "2026-04-21T00:00:00Z"
    }
  ]
}
```

**前端使用**：股票池管理頁面的清單顯示

---

### GET /stocks/status — 取得篩選任務狀態

**用途**：查詢最近一次「股票池篩選」背景任務的進度（前端用這個輪詢，知道有沒有完成）。

**輸入參數**：無

**回傳格式**：
```json
{
  "message": "取得狀態成功",
  "data": {
    "id": "uuid...",
    "status": "completed",
    "started_at": "2026-04-21T00:00:00Z",
    "completed_at": "2026-04-21T00:05:30Z",
    "stock_count": 87,
    "error_message": null
  }
}
```

status 的可能值：
- `running`：正在執行中
- `completed`：已完成
- `failed`：執行失敗（error_message 會有說明）

**前端使用**：股票池頁面的篩選進度顯示

---

### POST /stocks/filter — 啟動股票池篩選

**用途**：手動啟動一次股票池篩選任務（背景執行）。系統會去查詢台灣證交所的全部上市股票，篩選出符合條件的股票更新到股票池。

**輸入參數**：無

**回傳格式**：
```json
{
  "message": "篩選已開始，請透過 GET /stocks/status 輪詢進度"
}
```

> 若目前已有篩選任務在執行，會回傳錯誤拒絕新請求。

**前端使用**：股票池管理頁面的「重新篩選」按鈕

---

## 四、實際交易（/api/v1/trades）

### POST /trades/buy — 執行買進

**用途**：對特定股票下買進委託，透過富果 API 送出真實訂單，並記錄交易紀錄。

**輸入參數**（JSON）：
```json
{
  "stock_code": "2886",
  "stock_name": "兆豐金",
  "price": 38.5,
  "shares": 1000,
  "reason": "法人買超，殖利率高"
}
```

**回傳格式**：
```json
{
  "message": "買進委託成功",
  "data": {
    "id": "uuid...",
    "date": "2026-04-27",
    "stock_code": "2886",
    "action": "buy",
    "price": 38.5,
    "shares": 1000,
    "total_amount": 38500,
    "profit": 0,
    "order_id": "富果訂單號碼"
  }
}
```

**前端使用**：交易執行頁面的買進按鈕

---

### POST /trades/sell — 執行賣出

**用途**：對特定股票下賣出委託，計算損益後記錄。

**輸入參數**（JSON）：
```json
{
  "stock_code": "2886",
  "stock_name": "兆豐金",
  "price": 41.0,
  "shares": 1000,
  "buy_price": 38.5,
  "reason": "達到目標獲利"
}
```

**回傳格式**：同買進，profit 欄位會填入損益金額

**前端使用**：交易執行頁面的賣出按鈕

---

### GET /trades/monthly-stats — 本月交易統計

**用途**：查詢這個月的整體交易績效（勝率、總損益、交易次數等）。

**輸入參數**：無

**回傳格式**：
```json
{
  "message": "取得月度統計成功",
  "data": {
    "total_trades": 5,
    "win_trades": 3,
    "win_rate": 60.0,
    "total_profit": 12500.0
  }
}
```

**前端使用**：儀表板的本月績效摘要區塊

---

## 五、帳戶持倉（/api/v1/positions）

### GET /positions — 查詢目前持倉

**用途**：透過富果 API 查詢目前帳戶裡實際持有的股票和數量。

**輸入參數**：無

**回傳格式**：持倉清單（格式依富果 API 回傳為準）

**前端使用**：帳戶持倉頁面

---

## 六、模擬交易（/api/v1/simulation）

### GET /simulation/trades — 所有模擬交易紀錄

**用途**：列出所有模擬交易的買賣紀錄（包含已平倉和持倉中），按時間由新到舊排列。

**輸入參數**：無

**回傳格式**：
```json
{
  "message": "取得模擬交易紀錄成功",
  "data": [
    {
      "id": "uuid...",
      "date": "2026-04-25",
      "stock_code": "0056",
      "stock_name": "元大高股息",
      "action": "buy",
      "price": 35.2,
      "shares": 1000,
      "total_amount": 35200,
      "signal_score": 7,
      "status": "closed",
      "buy_price": 35.2,
      "profit": 2112,
      "profit_pct": 6.0
    }
  ]
}
```

**前端使用**：模擬交易頁面的歷史紀錄清單

---

### GET /simulation/positions — 目前模擬持倉

**用途**：列出目前「持倉中（status=open）」的模擬交易。

**輸入參數**：無

**回傳格式**：同 simulation/trades，但只包含 status=open 的資料

**前端使用**：模擬交易頁面的「目前持倉」區塊

---

### GET /simulation/summary — 模擬交易績效摘要

**用途**：統計所有已平倉的模擬交易績效（勝率、總損益、平均損益）。

**輸入參數**：無

**回傳格式**：
```json
{
  "message": "取得模擬交易摘要成功",
  "data": {
    "total_closed": 12,
    "win_count": 8,
    "win_rate": 66.7,
    "total_profit": 15800.0,
    "avg_profit_pct": 4.2
  }
}
```

**前端使用**：模擬交易頁面的績效統計卡片

---

## 七、WebSocket（即時行情）

### WS /ws — 即時股價推播

**用途**：透過 WebSocket 長連線推播即時股價（目前為模擬資料，基準價 ±0.5% 隨機波動）。

**連線方式**：`ws://後端網址/ws`

**回傳格式**（伺服器定期推送）：
```json
{
  "stock_code": "2886",
  "price": 38.75,
  "change_pct": 0.32
}
```

**前端使用**：儀表板的即時行情顯示

---

## 八、前端頁面與 API 對應表

| 前端頁面 | 呼叫的 API |
|---------|-----------|
| 登入頁面 | POST /auth/login |
| 儀表板主頁 | GET /signals/today-all、GET /signals/top、GET /signals/stats、GET /trades/monthly-stats、WS /ws |
| 「立即計算」按鈕 | POST /signals/run-now |
| 「全量重算」按鈕 | POST /signals/run-full |
| 個股詳情頁 | GET /signals/today、GET /signals/history/{code}、GET /stocks/kline/{code} |
| 股票池管理頁 | GET /stocks/pool、GET /stocks/status、POST /stocks/filter |
| 交易執行頁 | POST /trades/buy、POST /trades/sell |
| 帳戶持倉頁 | GET /positions |
| 模擬交易頁 | GET /simulation/trades、GET /simulation/positions、GET /simulation/summary |

---

## 附錄：統一回傳格式

所有 API 都採用同一種回傳結構：

```json
{
  "message": "說明文字",
  "data": "實際資料（可能是物件、陣列或 null）"
}
```

若發生錯誤，HTTP 狀態碼會是 4xx 或 5xx，格式如下：
```json
{
  "detail": "錯誤說明文字"
}
```
