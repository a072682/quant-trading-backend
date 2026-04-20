from app.services.fugle_service import fugle_service


async def get_positions() -> list:
    """從富果 API 查詢目前帳戶持倉"""
    positions = await fugle_service.get_positions()
    return positions
