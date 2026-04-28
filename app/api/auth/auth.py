#region 引入 FastAPI 相關套件
# APIRouter：定義這個模組的路由群組
# Depends：FastAPI 依賴注入，讓函式自動取得所需物件
# HTTPException：拋出 HTTP 錯誤（如 400、401）
# status：HTTP 狀態碼常數（如 status.HTTP_401_UNAUTHORIZED）
from fastapi import APIRouter, Depends, HTTPException, status

# OAuth2PasswordRequestForm：FastAPI 內建的登入表單解析器
# 自動從請求 body 取出 username 和 password 欄位
from fastapi.security import OAuth2PasswordRequestForm
#endregion


#region 引入資料庫連線依賴
# AsyncSession：非同步資料庫連線物件類型
from sqlalchemy.ext.asyncio import AsyncSession

# get_db：FastAPI 依賴注入函式，負責借出並歸還資料庫連線
from app.core.db.session import get_db
#endregion


#region 引入安全模組
# verify_password：驗證明碼密碼是否與雜湊密碼相符
# create_access_token：產生 JWT Token
# hash_password：將明碼密碼加密為雜湊字串
from app.core.auth.security import verify_password, create_access_token, hash_password
#endregion


#region 引入 API 回應格式
# APIResponse：統一的 API 回傳格式，包含 message 與 data 欄位
from app.core.schemas.common import APIResponse
#endregion


#region 引入使用者相關 auth_service 函式
# get_user_by_email：用 email 查詢使用者，找到回傳 User 物件，找不到回傳 None
# create_user：建立新使用者並寫入資料庫，回傳帶有 id 的 User 物件
# check_email_exists：確認 email 是否已被註冊，回傳 True 或 False
from app.services.auth.auth_service import get_user_by_email, create_user, check_email_exists
#endregion


#region 引入 Pydantic 資料驗證
# BaseModel：Pydantic 基礎模型，用來定義請求 / 回應的資料結構
from pydantic import BaseModel
#endregion


#region 建立路由器
# 此模組的所有路由都會掛在這個 router 下
# 由 main.py 或上層 router 負責決定 prefix（如 /auth）
router = APIRouter()
#endregion


#region 回應模型：TokenOut — 登入 / 註冊成功後回傳的 Token 資料
# access_token：JWT Token 字串，前端每次請求需帶在 Authorization Header
# token_type：固定為 "bearer"，告知前端 Token 的驗證方式
class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
#endregion


#region 請求模型：RegisterIn — 註冊時前端傳入的資料
# email：使用者的電子信箱，作為唯一識別帳號
# username：使用者顯示名稱
# password：明碼密碼（後端會加密後才存入資料庫）
class RegisterIn(BaseModel):
    email: str
    username: str
    password: str
#endregion


#region 路由：POST /login — 使用者登入
# 作用：驗證帳號密碼，成功則回傳 JWT Token
# 輸入：OAuth2PasswordRequestForm（帳號填入 email，密碼填入 password）
#       db（資料庫連線，由 get_db 自動提供）
# 輸出：APIResponse[TokenOut]（含 JWT Token 的統一格式回應）
@router.post("/login", response_model=APIResponse[TokenOut])
async def login(
    # OAuth2PasswordRequestForm：FastAPI 內建表單，自動解析 username / password
    form_data: OAuth2PasswordRequestForm = Depends(),
    # get_db：依賴注入，自動借出一條資料庫連線，請求結束後自動歸還
    db: AsyncSession = Depends(get_db),
):
    """使用者登入，驗證帳號密碼後回傳 JWT Token"""

    print(f"[登入] 收到登入請求，帳號：{form_data.username}")

    # 用 email 查詢使用者（form_data.username 欄位實際填入 email）
    # 輸入：db 連線、email 字串
    # 輸出：User 物件 或 None
    user = await get_user_by_email(db, form_data.username)

    # 若使用者不存在，或密碼驗證失敗，回傳 401 錯誤
    # verify_password(明碼, 雜湊碼) → True 表示相符
    if not user or not verify_password(form_data.password, user.hashed_password):
        print(f"[登入] 帳號或密碼錯誤，拒絕登入")
        raise HTTPException(
            # 401 Unauthorized：身份驗證失敗
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="帳號或密碼錯誤",
        )

    # 驗證通過，產生 JWT Token
    # subject 為使用者 id（字串），作為 token 的識別資訊
    token = create_access_token(subject=str(user.id))

    print(f"[登入] 登入成功，使用者 id：{user.id}")

    # 回傳統一格式的成功回應，data 包含 Token 資訊
    return APIResponse(
        message="登入成功",
        data=TokenOut(access_token=token),
    )
#endregion


#region 路由：POST /register — 使用者註冊
# 作用：建立新帳號，成功後自動登入並回傳 JWT Token
# 輸入：RegisterIn（email、username、password）
#       db（資料庫連線，由 get_db 自動提供）
# 輸出：APIResponse[TokenOut]（含 JWT Token 的統一格式回應），HTTP 201 Created
@router.post("/register", response_model=APIResponse[TokenOut], status_code=201)
async def register(
    # data：前端傳入的註冊資料，由 Pydantic 自動驗證格式
    data: RegisterIn,
    # get_db：依賴注入，自動借出一條資料庫連線，請求結束後自動歸還
    db: AsyncSession = Depends(get_db),
):
    """使用者註冊，建立帳號後自動回傳 JWT Token"""

    print(f"[註冊] 收到註冊請求，email：{data.email}")

    # 確認 email 是否已被使用
    # 輸入：db 連線、email 字串
    # 輸出：True（已存在）或 False（可以註冊）
    exists = await check_email_exists(db, data.email)

    # 若 email 已存在，回傳 400 錯誤，禁止重複註冊
    if exists:
        print(f"[註冊] email 已被使用，拒絕註冊：{data.email}")
        raise HTTPException(
            # 400 Bad Request：請求資料有誤（此 email 已被佔用）
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="此 Email 已被註冊",
        )

    # email 尚未被使用，建立新使用者
    # hash_password(data.password)：先將明碼加密，再傳給 create_user
    # 輸入：db 連線、email、username、加密後密碼
    # 輸出：帶有完整欄位（含 id）的 User 物件
    user = await create_user(db, data.email, data.username, hash_password(data.password))

    # 建立成功，產生 JWT Token（讓使用者不需再手動登入）
    token = create_access_token(subject=str(user.id))

    print(f"[註冊] 註冊成功，使用者 id：{user.id}")

    # 回傳統一格式的成功回應，HTTP 201 Created
    return APIResponse(
        message="註冊成功",
        data=TokenOut(access_token=token),
    )
#endregion
