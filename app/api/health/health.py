from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.services.health.health_service import check_database

router = APIRouter()


@router.get("")
async def health_check():
    """確認伺服器與資料庫連線是否正常"""
    db_status = await check_database()
    success = db_status == "ok"

    body = {
        "success": success,
        "server": "ok",
        "database": db_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    if not success:
        return JSONResponse(status_code=503, content=body)
    return body
