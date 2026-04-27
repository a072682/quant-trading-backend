#region 引入套件
# text：將純文字字串轉換成 SQLAlchemy 可以執行的 SQL 指令
from sqlalchemy import text

# AsyncSessionLocal：從 session.py 引入控制連線通道的函式
from app.core.db.session import AsyncSessionLocal
#endregion


#region 確認資料庫連線函式
# 作用：嘗試連線資料庫並執行一個最簡單的查詢，確認連線是否正常
# 輸入：無
# 輸出：連線正常回傳 "ok"，連線失敗回傳 "error"
async def check_database() -> str:

    # 開始確認，印出 log 讓伺服器端知道這個動作已開始
    print("[健康確認] 開始確認資料庫連線...")

    try:
        # 向工廠借一條資料庫連線，命名為 db_link
        # 這個區塊結束後，連線自動歸還，不需要手動關閉
        async with AsyncSessionLocal() as db_link:

            # execute為執行SQL指令
            # 輸入：SELECT 1（最簡單的 SQL 指令，不查任何資料表）
            # 輸出：資料庫回傳數字 1（代表連線正常可以溝通）
            # 目的：只是確認連線通了，不做任何實際查詢
            await db_link.execute(text("SELECT 1"))

        # 執行到這裡代表連線成功，印出成功 log
        print("[健康確認] 資料庫連線正常 ✓")

        # 回傳 "ok" 給呼叫這個函式的地方（health.py）
        return "ok"

    except Exception as e:
        # 執行到這裡代表連線失敗
        # Exception：任何種類的錯誤都會被捕捉到
        # e：錯誤的詳細內容，印出來方便除錯
        print(f"[健康確認] 資料庫連線失敗 ✗ ({e})")

        # 回傳 "error" 給呼叫這個函式的地方（health.py）
        return "error"
#endregion
