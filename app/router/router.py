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

# 從 signals.py 引入 router，並改名為 signals_router
# 改名原因：避免與總路由器的 router 名稱衝突
from app.api.signals.signals import router as signals_router

# 引入模擬交易路由器
from app.api.simulation.simulation import router as simulation_router
#endregion

#region 建立總路由器
# 建立這個檔案自己的路由器，負責把所有 API 組合在一起
router = APIRouter()
#endregion

#region 掛載各功能路由器

# 資料庫連線檢查API
# 輸入：health_router（health.py 的路由器）
# prefix="/health"：所有 health 的 API 路徑都會加上 /health 前綴
# 輸出：GET /health → 自動對應到 health_check 函式
# tags=["Health"]：API 文件的分類標籤（不影響實際運作）
router.include_router(health_router, prefix="/health", tags=["Health"])

# 會員登錄相關API
# prefix="/auth"：所有 auth 的 API 路徑都會加上 /auth 前綴
# 輸出：
#   POST /auth/login    → 對應到 login 函式
#   POST /auth/register → 對應到 register 函式
#   POST /auth/logout   → 對應到 logout 函式
router.include_router(auth_router, prefix="/auth", tags=["Auth"])

# 抓取股票原始數據API
# prefix="/stocks"：所有 stocks 的 API 路徑都會加上 /stocks 前綴
# 輸出：
#   POST /stocks/filter → 對應到 trigger_filter 函式
#   GET  /stocks/pool   → 對應到 get_pool 函式
#   GET  /stocks/status → 對應到 get_status 函式
router.include_router(stocks_router, prefix="/stocks", tags=["Stocks"])

# 股票評分API
# prefix="/signals"：所有 signals 的 API 路徑都會加上 /signals 前綴
# 輸出：
#   POST /signals/run   → 對應到 run_scoring 函式
#   GET  /signals/today → 對應到 get_today 函式
#   GET  /signals/top   → 對應到 get_top 函式
router.include_router(signals_router, prefix="/signals", tags=["Signals"])

# 模擬交易路由：/api/simulation
router.include_router(simulation_router, prefix="/simulation", tags=["simulation"])

#endregion
