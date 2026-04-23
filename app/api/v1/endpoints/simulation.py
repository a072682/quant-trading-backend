from fastapi import APIRouter, Depends

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.simulation import SimulationTrade
from app.schemas.common import APIResponse
from app.schemas.simulation import SimulationSummaryOut, SimulationTradeOut
from app.services.simulation_service import get_simulation_summary

router = APIRouter()


@router.get("/trades", response_model=APIResponse[list[SimulationTradeOut]])
async def get_simulation_trades(
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    result = await db.execute(
        select(SimulationTrade).order_by(desc(SimulationTrade.created_at))
    )
    trades = result.scalars().all()
    return APIResponse(message="取得模擬交易紀錄成功", data=trades)


@router.get("/positions", response_model=APIResponse[list[SimulationTradeOut]])
async def get_simulation_positions(
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    result = await db.execute(
        select(SimulationTrade)
        .where(SimulationTrade.status == "open")
        .order_by(desc(SimulationTrade.created_at))
    )
    positions = result.scalars().all()
    return APIResponse(message="取得模擬持倉成功", data=positions)


@router.get("/summary", response_model=APIResponse[SimulationSummaryOut])
async def get_summary(
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    summary = await get_simulation_summary(db)
    return APIResponse(message="取得模擬交易摘要成功", data=summary)
