#region 引入 SQLAlchemy 欄位型別與基底類別
# Column：定義資料表欄位
# String、Float、Date、DateTime：欄位型別
# func：用於產生資料庫端的預設值（如現在時間）
from sqlalchemy import Column, String, Float, Date, DateTime, func
from app.core.db.base import Base
#endregion

#region 引入 UUID 工具
# uuid4：產生唯一識別碼
import uuid
#endregion

#region ORM 模型：SimulationTrade — 模擬交易記錄資料表
# 作用：記錄每一筆模擬買賣交易的完整生命週期
# 狀態流程：pending → holding → selling → sold
class SimulationTrade(Base):
    # 資料表名稱
    __tablename__ = "simulation_trades"

    # 唯一識別碼，預設由 Python 產生 UUID
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # 股票代號，例如 "2330"
    stock_code = Column(String, nullable=False)

    # 股票名稱，例如 "台積電"
    stock_name = Column(String, nullable=False)

    # 目前狀態
    # pending  = 待買入（推薦當天建立，等隔天開盤買入）
    # holding  = 持有中（已買入，每天追蹤損益）
    # selling  = 待賣出（收盤達停利停損，等隔天開盤賣出）
    # sold     = 已賣出（交易結束）
    status = Column(String, nullable=False, default="pending")

    # 買入價格（隔天開盤價，pending 時為 None）
    buy_price = Column(Float, nullable=True)

    # 現在價格（每天收盤後更新）
    current_price = Column(Float, nullable=True)

    # 損益百分比（正數為獲利，負數為虧損）
    profit_pct = Column(Float, nullable=True)

    # 賣出價格（sold 時才有值）
    sell_price = Column(Float, nullable=True)

    # 賣出原因："停利" / "停損"（sold 時才有值）
    sell_reason = Column(String, nullable=True)

    # 推薦日期（評分當天的日期）
    signal_date = Column(Date, nullable=False)

    # 買入日期（隔天開盤日）
    buy_date = Column(Date, nullable=True)

    # 賣出日期
    sell_date = Column(Date, nullable=True)

    # 建立時間（資料庫端自動填入）
    created_at = Column(DateTime(timezone=True), server_default=func.now())
#endregion