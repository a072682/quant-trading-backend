# 引入「非同步上下文管理器」工具，用來寫 lifespan（啟動/關閉）函式
from contextlib import asynccontextmanager

# 引入 FastAPI 框架本體，用來建立 API 應用程式
from fastapi import FastAPI

# 引入跨來源資源共用設定，讓前端可以呼叫後端 API
from fastapi.middleware.cors import CORSMiddleware

# 引入.env檔案參數確認控制文件頁面是否開放、哪些前端可以呼叫後端
from app.core.config.app_config import app_config

# 引入路由器，負責把所有 API 端點組合在一起
from app.router.router import router

# 引入資料庫引擎，負責建立連線池
from app.core.db.session import engine

# 引入資料表的基底類別，用來建立所有資料表
from app.core.db.base import Base

# ── 排程器暫時停用，架構重整中 ──────────────────────────────────────────────
# from datetime import datetime, timezone
# from sqlalchemy import select
# from app.db.session import AsyncSessionLocal
# from app.scheduler.jobs import create_scheduler
#
# async def _recover_stale_filter_status() -> None:
#     """將上次重啟前未完成的 running 狀態改為 failed"""
#     from app.models.stock_pool import FilterStatus
#     async with AsyncSessionLocal() as db:
#         result = await db.execute(
#             select(FilterStatus).where(FilterStatus.status == "running")
#         )
#         stale = result.scalars().all()
#         for fs in stale:
#             fs.status = "failed"
#             fs.completed_at = datetime.now(timezone.utc)
#             fs.error_message = "伺服器重啟，任務中斷"
#         if stale:
#             await db.commit()
#             print(f"⚠️  已將 {len(stale)} 筆殘留 running 狀態修正為 failed")


#region 用來定義應用程式「啟動時」和「關閉時」要做的事(並沒有執行)
# asynccontextmanager：讓函式可以用 async with 語法
@asynccontextmanager
async def lifespan(app: FastAPI):
    
    # 應用程式啟動時執行：
    # engine.begin() 開啟一個資料庫連線
    # conn.run_sync(Base.metadata.create_all) 檢查並建立所有資料表
    # （如果資料表已存在則跳過，不會重複建立）
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ 資料表初始化完成")

    # 排程器暫時停用
    # await _recover_stale_filter_status()
    # scheduler = create_scheduler()
    # scheduler.start()
    # print("✅ 排程器啟動完成")

    # yield 是分界點：
    # yield 之前 = 啟動時執行
    # yield 之後 = 關閉時執行
    yield

    # 排程器暫時停用
    # scheduler.shutdown()
    # print("🛑 排程器已停止")

    # 應用程式關閉時執行：
    # 釋放所有資料庫連線，讓資源正確歸還
    await engine.dispose()
    print("🛑 資料庫連線已釋放")
#endregion


#region 建立 FastAPI 應用程式實例
app = FastAPI(
    title="量化交易系統 API",    # API 文件的標題
    version="1.0.0",            # API 版本號
    lifespan=lifespan,          # 綁定上面定義的啟動/關閉流程
    # 只有在開發環境才開啟 /docs 文件頁面
    # 正式環境（production）關閉，避免 API 結構外洩
    docs_url="/docs" if app_config.APP_ENV == "development" else None,
    redoc_url=None,             # 關閉另一種文件格式（redoc）
)
#endregion

#region 加入 CORS 中介層（middleware）：
# 讓前端（不同網域）可以呼叫後端 API
# 沒有這個設定，瀏覽器會因為安全性限制拒絕跨網域請求
app.add_middleware(
    CORSMiddleware,
    allow_origins=app_config.origins_list,  # 允許哪些網域來源（從設定檔讀取）
    allow_credentials=True,               # 允許帶 Cookie 或 Authorization Header
    allow_methods=["*"],                  # 允許所有 HTTP 方法（GET POST PUT DELETE 等）
    allow_headers=["*"],                  # 允許所有 HTTP Header
)
#endregion

#region 引入router
# 所有 API 的路徑都會以 /api 開頭
# 例如：router 裡的 /health → 實際路徑是 /api/health
app.include_router(router, prefix="/api")
#endregion

# ── 舊路由暫時停用，已移至 app/router/router.py 統一管理 ────────────────────
# from app.api.v1.router import router as v1_router
# from app.api.v1.endpoints.ws import router as ws_router
# app.include_router(v1_router, prefix="/api/v1")
# app.include_router(ws_router)
