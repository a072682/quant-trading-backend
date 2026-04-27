from datetime import datetime, timezone

from fastapi import APIRouter

from app.services.health.health_service import check_database

router = APIRouter()


@router.get("")
async def health_check():
    """確認伺服器與資料庫連線是否正常，永遠回傳 HTTP 200"""
    db_status = await check_database()

    return {
        "success": db_status == "ok",
        "server": "ok",
        "database": db_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
