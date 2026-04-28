from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.core.schemas.common import APIResponse
from app.services import position_service

router = APIRouter()


@router.get("/", response_model=APIResponse[list])
async def get_positions(
    _=Depends(get_current_user),
):
    """查詢目前帳戶持倉（從富果 API 取得）"""
    positions = await position_service.get_positions()
    return APIResponse(message="取得持倉成功", data=positions)
