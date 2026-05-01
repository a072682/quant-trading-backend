#region 引入 FastAPI 相關工具
# APIRouter：建立路由器
# Depends：依賴注入
# HTTPException、status：錯誤處理
from fastapi import APIRouter, Depends, HTTPException, status
#endregion

#region 引入資料庫相關工具
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db.session import get_db
#endregion

#region 引入身份驗證工具
from app.core.auth.security import get_current_user
#endregion

#region 引入 Schema 與 Service
from app.core.schemas.common import APIResponse
from app.core.schemas.simulation_schema import SimulationTradeOut, SimulationSummaryOut
from app.services.simulation.simulation_service import (
    get_trades_by_status,
    get_all_trades,
    get_summary,
)
#endregion

#region 建立路由器
# prefix 由 router.py 統一設定為 /api/simulation
router = APIRouter()
#endregion

#region 路由：GET /active — 取得目前進行中的持倉
# 作用：取得所有 pending + holding + selling 狀態的交易記錄
# 輸入：Authorization Header（需登入）
# 輸出：APIResponse[list[SimulationTradeOut]]
@router.get("/active", response_model=APIResponse[list[SimulationTradeOut]])
async def get_active_trades(
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """取得目前所有進行中的模擬持倉"""

    print(f"[模擬交易 API] 使用者 {current_user} 查詢進行中持倉")

    # 分別取得三種進行中狀態的記錄
    pending = await get_trades_by_status(db, "pending")
    holding = await get_trades_by_status(db, "holding")
    selling = await get_trades_by_status(db, "selling")

    # 合併三種狀態的記錄
    all_active = pending + holding + selling

    # 將 ORM 物件轉換為 Schema
    items = [SimulationTradeOut.model_validate(t) for t in all_active]

    return APIResponse(
        message=f"目前進行中持倉：{len(items)} 筆",
        data=items,
    )
#endregion

#region 路由：GET /history — 取得所有已賣出的歷史記錄
# 作用：取得所有 sold 狀態的交易記錄
# 輸入：Authorization Header（需登入）
# 輸出：APIResponse[list[SimulationTradeOut]]
@router.get("/history", response_model=APIResponse[list[SimulationTradeOut]])
async def get_history_trades(
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """取得所有已完成的模擬交易歷史記錄"""

    print(f"[模擬交易 API] 使用者 {current_user} 查詢歷史記錄")

    # 取得所有已賣出記錄
    sold = await get_trades_by_status(db, "sold")

    # 將 ORM 物件轉換為 Schema
    items = [SimulationTradeOut.model_validate(t) for t in sold]

    return APIResponse(
        message=f"歷史記錄：{len(items)} 筆",
        data=items,
    )
#endregion

#region 路由：GET /summary — 取得整體績效摘要
# 作用：計算總交易次數、勝率、平均損益等統計數字
# 輸入：Authorization Header（需登入）
# 輸出：APIResponse[SimulationSummaryOut]
@router.get("/summary", response_model=APIResponse[SimulationSummaryOut])
async def get_simulation_summary(
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """取得模擬交易整體績效摘要"""

    print(f"[模擬交易 API] 使用者 {current_user} 查詢績效摘要")

    # 取得績效摘要字典
    summary_data = await get_summary(db)

    return APIResponse(
        message="取得績效摘要成功",
        data=SimulationSummaryOut(**summary_data),
    )
#endregion