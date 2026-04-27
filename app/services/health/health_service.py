from sqlalchemy import text

from app.db.session import AsyncSessionLocal


async def check_database() -> str:
    print("[健康確認] 開始確認資料庫連線...")
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
        print("[健康確認] 資料庫連線正常 ✓")
        return "ok"
    except Exception as e:
        print(f"[健康確認] 資料庫連線失敗 ✗ ({e})")
        return "error"
