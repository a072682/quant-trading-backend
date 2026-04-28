#region 引入套件
# BaseModel：Pydantic 基底類別，用來定義資料格式並自動驗證
from pydantic import BaseModel
#endregion


#region 回應格式：TokenOut — 登入或註冊成功後回傳的 Token 資料
# 作用：定義前端收到的 Token 格式
# 輸入範例：TokenOut(access_token="eyJxxx")
# 輸出範例：
# {
#   "access_token": "eyJxxx...",
#   "token_type": "bearer"
# }
class TokenOut(BaseModel):
    # JWT Token 字串，前端每次請求需帶在 Authorization Header
    access_token: str
    # Token 驗證方式，固定為 "bearer"
    token_type: str = "bearer"
#endregion


#region 請求格式：RegisterIn — 註冊時前端傳入的資料
# 作用：定義前端註冊時需要傳入的欄位格式
# 輸入範例：{"email": "andy@example.com", "username": "Andy", "password": "mypassword"}
# 所有欄位都是必填，不可為空
class RegisterIn(BaseModel):
    # 電子郵件地址，作為登入帳號
    email: str
    # 使用者顯示名稱
    username: str
    # 明碼密碼，後端會加密後才存入資料庫
    password: str
#endregion
