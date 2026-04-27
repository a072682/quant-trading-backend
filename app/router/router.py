#region 引入套件
# APIRouter：FastAPI 提供的路由器，用來建立這個檔案的總路由器
from fastapi import APIRouter

# 從 health.py 引入 router，並改名為 health_router
# 改名原因：避免與下方的 router 名稱衝突
# 輸入：health.py 裡的 router = APIRouter()
# 輸出：health_router（health.py 的路由器）
from app.api.health.health import router as health_router
#endregion

#region 建立總路由器
# 建立這個檔案自己的路由器，負責把所有 API 組合在一起
router = APIRouter()
#endregion

#region 掛載各功能路由器
# 把 health_router 掛載到總路由器上
# 輸入：health_router（health.py 的路由器）
# prefix="/health"：所有 health 的 API 路徑都會加上 /health 前綴
# 輸出：GET /health → 自動對應到 health_check 函式
# tags=["Health"]：API 文件的分類標籤（不影響實際運作）
router.include_router(health_router, prefix="/health", tags=["Health"])

# ── 以下路由暫時全部註解，架構重整中 ──────────────────────────
# from app.api.v1.endpoints import auth, positions, signals, simulation, stocks, trades
#
# router.include_router(auth.router,       prefix="/auth",       tags=["Auth"])
# router.include_router(signals.router,    prefix="/signals",    tags=["Signals"])
# router.include_router(stocks.router,     prefix="/stocks",     tags=["Stocks"])
# router.include_router(trades.router,     prefix="/trades",     tags=["Trades"])
# router.include_router(positions.router,  prefix="/positions",  tags=["Positions"])
# router.include_router(simulation.router, prefix="/simulation", tags=["Simulation"])
#endregion
