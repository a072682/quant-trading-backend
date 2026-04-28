#region 引入套件
# uuid：用來產生唯一識別碼（每個使用者都有一個不重複的 id）
import uuid

# datetime、timezone：用來記錄帳號建立時間，並指定 UTC 時區
from datetime import datetime, timezone

# String、Boolean、DateTime：定義資料表欄位的資料類型
from sqlalchemy import String, Boolean, DateTime

# Mapped、mapped_column：定義欄位與 Python 類型的對應關係
from sqlalchemy.orm import Mapped, mapped_column

# Base：所有資料表設計圖的基底類別，繼承它才能被 SQLAlchemy 認識
from app.core.db.base import Base
#endregion


#region 資料表設計圖：User — 使用者資料表
# 這個類別對應資料庫裡的 users 資料表
# 每一個 User 物件 = 資料庫裡 users 資料表的一列資料
class User(Base):

    # 指定對應的資料表名稱
    # __tablename__為指定寫法
    __tablename__ = "users"

    # 使用者唯一識別碼
    # primary_key=True：這是主鍵，每筆資料不重複
    # default：新增使用者時自動產生一組 uuid 字串
    # 輸入：無（自動產生）
    # 輸出範例："550e8400-e29b-41d4-a716-446655440000"
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # 電子郵件地址
    # nullable=False：不可以是空值，必填
    # unique=True：不允許重複，每個 email 只能註冊一次
    # index=True：建立索引，讓用 email 查詢時速度更快
    email: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )

    # 使用者名稱（顯示用）
    # nullable=False：不可以是空值，必填
    username: Mapped[str] = mapped_column(String(100), nullable=False)

    # 加密後的密碼
    # 注意：這裡存的是加密過的密碼，不是明碼
    # nullable=False：不可以是空值，必填
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    # 帳號是否啟用
    # default=True：新帳號預設為啟用狀態
    # 輸入：無（自動設定）
    # 輸出：True（啟用）或 False（停用）
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # 帳號建立時間
    # timezone=True：儲存時包含時區資訊
    # default：新增使用者時自動記錄當下的 UTC 時間
    # 輸入：無（自動產生）
    # 輸出範例："2026-04-27T14:00:00+00:00"
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
#endregion
