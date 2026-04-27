#region 引入套件
# datetime：用來取得目前時間
# timezone：用來指定時區（這裡使用 UTC 世界標準時間）
from datetime import datetime, timezone

# APIRouter：FastAPI 提供的路由器，用來定義這個檔案的 API 端點
from fastapi import APIRouter

# check_database：從 health_service 引入確認資料庫連線的函式
from app.services.health.health_service import check_database
#endregion

#region 建立路由器
# 建立一個路由器實例，所有在這個檔案定義的 API 都會掛載在這個路由器下
router = APIRouter()
#endregion

#region 健康確認端點
# 作用：確認伺服器和資料庫連線是否正常
# 輸入：無（GET 請求，不需要任何參數）
# 輸出：永遠回傳 HTTP 200，內容包含連線狀態和時間
@router.get("")
async def health_check():

    # 呼叫 check_database()，確認資料庫是否連線正常
    # 輸入：無
    # 輸出："ok"（正常）或 "error"（失敗）
    db_status = await check_database()

    # 組合回傳內容並回傳給前端
    # 輸入：db_status = "ok" 或 "error"
    # 輸出範例（正常）：
    # {
    #   "success": true,
    #   "server": "ok",
    #   "database": "ok",
    #   "timestamp": "2026-04-27T14:00:00+00:00"
    # }
    # 輸出範例（失敗）：
    # {
    #   "success": false,
    #   "server": "ok",
    #   "database": "error",
    #   "timestamp": "2026-04-27T14:00:00+00:00"
    # }
    return {
        # db_status == "ok" 是條件判斷
        # 輸入：db_status = "ok"  → 輸出：success = true
        # 輸入：db_status = "error" → 輸出：success = false
        "success": db_status == "ok", # 整體是否正常

        # 伺服器本身只要能回應這個 API 就代表正常
        "server": "ok", # 伺服器狀況

        # 直接放入 check_database() 回傳的結果
        "database": db_status, # 資料庫狀況

        # 取得目前伺服器的時間（UTC 世界標準時間）
        # 並轉換成文字格式（ISO 8601 格式）
        # 輸出範例："2026-04-27T14:00:00.123456+00:00"
        "timestamp": datetime.now(timezone.utc).isoformat(), # 伺服器時間
    }
#endregion
