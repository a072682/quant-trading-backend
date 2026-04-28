from fastapi import APIRouter, Depends

from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_current_user

from app.core.schemas.common import APIResponse
from app.core.schemas.trade import TradeBuyIn, TradeSellIn, TradeOut, MonthlyStatsOut

from app.services import trade_service

router = APIRouter()


@router.post("/buy", response_model=APIResponse[TradeOut], status_code=201)
async def buy_stock(
    data: TradeBuyIn,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """執行買進：呼叫富果 API 下單，並儲存交易紀錄"""
    trade = await trade_service.execute_buy(data, db)
    return APIResponse(message="買進委託成功", data=trade)


@router.post("/sell", response_model=APIResponse[TradeOut], status_code=201)
async def sell_stock(
    data: TradeSellIn,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """執行賣出：呼叫富果 API 下單，計算損益並儲存紀錄"""
    trade = await trade_service.execute_sell(data, db)
    return APIResponse(message="賣出委託成功", data=trade)


@router.get("/monthly-stats", response_model=APIResponse[MonthlyStatsOut])
async def get_monthly_stats(
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """取得本月交易統計（勝率、總損益、交易次數）"""
    stats = await trade_service.get_monthly_stats(db)
    return APIResponse(message="取得月度統計成功", data=stats)
