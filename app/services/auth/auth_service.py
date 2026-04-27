from sqlalchemy.ext.asyncio import AsyncSession  # 非同步資料庫連線類型
from sqlalchemy import select  # SQL SELECT 查詢建構器

from app.core.models.user_model import User  # 使用者資料庫模型


#region 函式：get_user_by_email — 用 email 查詢使用者

async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    """
    用 email 在資料庫中查詢使用者。
    找到回傳 User 物件，找不到回傳 None。
    對應原本 login 端點的 select(User).where(User.email == ...) 邏輯。
    """
    print(f"[會員服務] 查詢使用者：{email}")  # 記錄查詢開始

    # 建立 SELECT 查詢，條件為 email 欄位完全相符
    result = await db.execute(
        select(User).where(User.email == email)  # 篩選條件：email 必須完全一致
    )
    # scalar_one_or_none()：找到一筆就回傳物件，找不到就回傳 None，找到多筆會拋例外
    user = result.scalar_one_or_none()

    print(f"[會員服務] 查詢結果：{'找到' if user else '找不到'}")  # 記錄查詢結果
    return user

#endregion


#region 函式：create_user — 建立新使用者並寫入資料庫
async def create_user(
    db: AsyncSession,           # 資料庫連線（由端點透過 Depends 注入）
    email: str,                 # 使用者 email（唯一識別）
    username: str,              # 使用者顯示名稱
    hashed_password: str,       # 已由 hash_password() 加密的密碼字串
) -> User:
    """
    建立新的 User 物件並寫入資料庫。
    寫入後透過 db.refresh() 確保回傳的物件含有資料庫產生的欄位（如 id、created_at）。
    對應原本 register 端點的 db.add(user) → db.commit() → db.refresh(user) 邏輯。
    """
    print(f"[會員服務] 建立新使用者：{email}")  # 記錄建立開始

    # 建立 User ORM 物件，尚未寫入資料庫
    user = User(
        email=email,                        # 設定 email 欄位
        username=username,                  # 設定使用者名稱欄位
        hashed_password=hashed_password,    # 設定加密後的密碼欄位
    )

    db.add(user)        # 將物件加入當前 Session（標記為待寫入）
    await db.commit()   # 執行 INSERT，將資料正式寫入資料庫
    await db.refresh(user)  # 從資料庫重新載入物件，取得 id 等自動產生的欄位

    print(f"[會員服務] 使用者建立完成：{email}")  # 記錄建立結果
    return user  # 回傳帶有完整欄位（含 id）的 User 物件
#endregion


#region 函式：check_email_exists — 確認 email 是否已被註冊
async def check_email_exists(db: AsyncSession, email: str) -> bool:
    """
    確認指定 email 是否已存在於資料庫。
    回傳 True 表示已被註冊（不可再使用），回傳 False 表示可以註冊。
    內部呼叫 get_user_by_email，避免重複查詢資料庫。
    """
    print(f"[會員服務] 確認 email 是否存在：{email}")  # 記錄確認開始

    # 直接呼叫 get_user_by_email，不重複撰寫查詢邏輯
    user = await get_user_by_email(db, email)

    result = user is not None  # True 表示已存在，False 表示可以註冊
    print(f"[會員服務] 確認結果：{'已存在' if result else '可以註冊'}")  # 記錄確認結果
    return result
#endregion
