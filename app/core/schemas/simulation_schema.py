#region 引入 Pydantic 基底類別與型別工具
# BaseModel：所有 Schema 的基底類別
# Optional：代表欄位可以是 None
from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime
#endregion

#region Schema：SimulationTradeOut — 模擬交易記錄的回傳格式
# 作用：定義前端收到的模擬交易資料格式
class SimulationTradeOut(BaseModel):
    # 唯一識別碼
    id: str
    # 股票代號，例如 "2330"
    stock_code: str
    # 股票名稱，例如 "台積電"
    stock_name: str
    # 目前狀態：pending（待買入）/ holding（持有中）/ selling（待賣出）/ sold（已賣出）
    status: str
    # 買入價格（隔天開盤價，pending 時為 None）
    buy_price: Optional[float] = None
    # 現在價格（每天更新）
    current_price: Optional[float] = None
    # 損益百分比（正數為獲利，負數為虧損）
    profit_pct: Optional[float] = None
    # 賣出價格（sold 時才有值）
    sell_price: Optional[float] = None
    # 賣出原因："停利" / "停損"（sold 時才有值）
    sell_reason: Optional[str] = None
    # 推薦日期（評分當天）
    signal_date: date
    # 買入日期（隔天開盤日）
    buy_date: Optional[date] = None
    # 賣出日期
    sell_date: Optional[date] = None
    # 建立時間
    created_at: datetime

    # 允許從 ORM 物件直接建立
    model_config = {"from_attributes": True}
#endregion

#region Schema：SimulationSummaryOut — 模擬交易整體績效摘要
# 作用：定義前端收到的績效摘要格式
class SimulationSummaryOut(BaseModel):
    # 總交易次數（已賣出的筆數）
    total_trades: int
    # 獲利次數
    win_trades: int
    # 虧損次數
    lose_trades: int
    # 勝率（百分比）
    win_rate: float
    # 平均損益（百分比）
    avg_profit_pct: float
    # 目前持倉數量（pending + holding + selling）
    active_count: int
#endregion