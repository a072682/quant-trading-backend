from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.core.config import settings
from app.api.v1.router import router as v1_router
from app.api.v1.endpoints.ws import router as ws_router
from app.db.session import engine, AsyncSessionLocal
from app.db.base import Base
from app.scheduler.jobs import create_scheduler


async def _recover_stale_filter_status() -> None:
    """將上次重啟前未完成的 running 狀態改為 failed"""
    from app.models.stock_pool import FilterStatus  # 避免循環 import

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(FilterStatus).where(FilterStatus.status == "running")
        )
        stale = result.scalars().all()
        for fs in stale:
            fs.status = "failed"
            fs.completed_at = datetime.now(timezone.utc)
            fs.error_message = "伺服器重啟，任務中斷"
        if stale:
            await db.commit()
            print(f"⚠️  已將 {len(stale)} 筆殘留 running 狀態修正為 failed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """應用程式生命週期管理：啟動時初始化，關閉時釋放資源"""

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ 資料表初始化完成")

    await _recover_stale_filter_status()

    scheduler = create_scheduler()
    scheduler.start()
    print("✅ 排程器啟動完成")

    yield

    scheduler.shutdown()
    print("🛑 排程器已停止")

    await engine.dispose()
    print("🛑 資料庫連線已釋放")


app = FastAPI(
    title="量化交易系統 API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.APP_ENV == "development" else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_router, prefix="/api/v1")
app.include_router(ws_router)


@app.get("/api/health", tags=["Health"])
async def health():
    """健康檢查端點：確認 API 正常運行"""
    return {"success": True, "message": "量化交易系統 API 運行中"}
