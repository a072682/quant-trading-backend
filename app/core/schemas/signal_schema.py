#region 引入套件
# BaseModel：Pydantic 基底類別，用來定義資料格式並自動驗證
from pydantic import BaseModel

# Optional：代表「有值或是 None」
from typing import Optional
#endregion


#region 回應格式：SignalOut — 回傳給前端的每日評分資料
# 作用：定義前端收到的評分格式，包含所有分項分數、AI 分析結果
# 輸入範例（從 ORM 物件轉換）：SignalOut.model_validate(signal)
# 輸出範例：
# {
#   "id": "uuid",
#   "date": "2026-04-29",
#   "stock_code": "2330",
#   "stock_name": "台積電",
#   "institutional_score": 2,
#   "ma_score": 1,
#   "volume_score": 0,
#   "yield_score": 1,
#   "futures_score": 1,
#   "total_score": 5,
#   "ai_action": "buy",
#   "ai_reason": "法人持續買超，均線位置合理",
#   "confidence": 80
# }
class SignalOut(BaseModel):
    # 資料列唯一識別碼
    id: str
    # 評分日期（台灣時區，格式 YYYY-MM-DD）
    date: str
    # 股票代號（如 "2330"）
    stock_code: str
    # 股票名稱（如 "台積電"）
    stock_name: str

    # 法人買賣超得分（範圍 -2 到 +2，正值代表法人買超）
    institutional_score: int = 0
    # 均線位置得分（範圍 -1 到 +2，正值代表股價在均線附近或以下）
    ma_score: int = 0
    # 成交量得分（範圍 -1 到 +2，正值代表量能放大）
    volume_score: int = 0
    # 殖利率得分（範圍 -1 到 +2，正值代表殖利率高）
    yield_score: int = 0
    # 大盤情緒得分（範圍 -2 到 +2，正值代表大盤偏多）
    futures_score: int = 0
    # 各分項分數加總
    total_score: int = 0

    # AI 建議動作（"buy" / "watch" / "sell"，未分析時為 None）
    ai_action: Optional[str] = None
    # AI 分析說明（50 字以內的繁體中文，未分析時為 None）
    ai_reason: Optional[str] = None
    # AI 買入信心值（0 到 100，越高越值得買入，未分析時為 None）
    confidence: Optional[int] = None

    # 允許從 SQLAlchemy ORM 物件直接轉換（需設定 from_attributes=True）
    model_config = {"from_attributes": True}
#endregion
