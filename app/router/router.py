#region 引入套件
# APIRouter：FastAPI 提供的路由器，用來建立這個檔案的總路由器
from fastapi import APIRouter

# 從 health.py 引入 router，並改名為 health_router
# 改名原因：避免與下方的 router 名稱衝突
# 輸入：health.py 裡的 router = APIRouter()
# 輸出：health_router（health.py 的路由器）
from app.api.health.health import router as health_router

# 從 auth.py 引入 router，並改名為 auth_router
# 改名原因：避免與總路由器的 router 名稱衝突
from app.api.auth.auth import router as auth_router

# 從 stocks.py 引入 router，並改名為 stocks_router
# 改名原因：避免與總路由器的 router 名稱衝突
from app.api.stocks.stocks import router as stocks_router
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

# 把 auth_router 掛載到總路由器上
# prefix="/auth"：所有 auth 的 API 路徑都會加上 /auth 前綴
# 輸出：
#   POST /auth/login    → 對應到 login 函式
#   POST /auth/register → 對應到 register 函式
#   POST /auth/logout   → 對應到 logout 函式
router.include_router(auth_router, prefix="/auth", tags=["Auth"])

# 把 stocks_router 掛載到總路由器上
# prefix="/stocks"：所有 stocks 的 API 路徑都會加上 /stocks 前綴
# 輸出：
#   POST /stocks/filter → 對應到 trigger_filter 函式
#   GET  /stocks/pool   → 對應到 get_pool 函式
#   GET  /stocks/status → 對應到 get_status 函式
router.include_router(stocks_router, prefix="/stocks", tags=["Stocks"])

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
