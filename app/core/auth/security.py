#region 引入套件

# datetime、timedelta、timezone：用來計算 Token 到期時間（UTC 時區）
from datetime import datetime, timedelta, timezone

# Optional：標示函式參數或回傳值可為 None
from typing import Optional

# bcrypt：業界標準密碼加密函式庫，加密後無法反推原始密碼
import bcrypt

# jwt：產生與驗證 JWT Token（JSON Web Token）
# JWTError：token 無效或過期時拋出的例外
from jose import JWTError, jwt

# auth_config：讀取 JWT 相關設定（SECRET_KEY、ALGORITHM、過期時間）
from app.core.config.auth_config import auth_config

#endregion


#region 函式：hash_password — 將明碼密碼加密
def hash_password(password: str) -> str:
    """將明碼密碼加密，回傳加密後的字串"""
    # 注意：不印出明碼或加密後的密碼，避免敏感資訊外洩
    print(f"[安全模組] 開始加密密碼")  

    # bcrypt.gensalt()：每次產生不同的隨機鹽值，確保相同密碼加密結果也不同
    # encode("utf-8")：bcrypt 只接受 bytes，需先將字串轉為 bytes
    # decode("utf-8")：將加密結果從 bytes 轉回字串，方便存入資料庫
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    # 記錄加密完成
    print(f"[安全模組] 密碼加密完成")  
    # hash_password
    # 回傳字串：加密後的密碼，格式範例："$2b$12$xxxxxxxxxxxxx"
    return hashed

#endregion


#region 函式：verify_password — 驗證密碼是否與加密密碼相符
def verify_password(plain: str, hashed: str) -> bool:
    """確認明碼密碼是否與加密密碼相符"""
    # 注意：不印出明碼或加密結果，避免敏感資訊外洩
    print(f"[安全模組] 開始驗證密碼")  

    # bcrypt.checkpw()：將明碼加密後與 hashed 比對，安全地驗證密碼
    result = bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
     # 記錄驗證結果
    print(f"[安全模組] 密碼驗證結果：{'相符' if result else '不相符'}") 

    # verify_password
    # 回傳布林值：True（相符）或 False（不相符）
    return result
#endregion


#region 函式：create_access_token — 產生登入憑證（JWT Token）
def create_access_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    """產生 JWT Token，subject 為使用者 id"""

    # subject：使用者 id，存入 token 的 sub 欄位
    # expires_delta：自訂有效時間，不傳則使用 auth_config 的預設值
    # 記錄開始產生
    print(f"[安全模組] 開始產生 Token，使用者 id：{subject}")  

    # 計算 Token 到期時間：若有傳入 expires_delta 就用它，否則使用設定檔的預設值
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=auth_config.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    # payload：Token 的內容，sub 為使用者識別碼，exp 為到期時間
    payload = {"sub": subject, "exp": expire}

    # jwt.encode()：用 SECRET_KEY 對 payload 進行簽名，產生 token 字串
    token = jwt.encode(payload, auth_config.SECRET_KEY, algorithm=auth_config.ALGORITHM)

    # 記錄產生完成
    print(f"[安全模組] Token 產生完成，有效期至：{expire.isoformat()}")  

    # create_access_token
    # 回傳字串：JWT Token，格式範例："eyJhbGciOiJIUzI1NiJ9.xxxxx"
    return token
#endregion


#region 函式：decode_token — 解讀並驗證 token 是否有效
def decode_token(token: str) -> Optional[str]:
    """解讀並驗證 JWT Token，回傳使用者 id 或 None"""

    # 記錄解碼開始
    print(f"[安全模組] 開始解碼並驗證 Token")  

    try:
        # jwt.decode()：驗證簽名與到期時間，成功則回傳 payload 字典
        payload = jwt.decode(
            token, auth_config.SECRET_KEY, algorithms=[auth_config.ALGORITHM]
        )
        # payload.get("sub")：取出使用者 id（subject）
        user_id = payload.get("sub")

        # 記錄驗證成功
        print(f"[安全模組] Token 有效，使用者 id：{user_id}")  

        # decode_token
        # 回傳字串：使用者 id（有效）
        return user_id

    except JWTError:
        # Token 無效（簽名錯誤、格式錯誤）或已過期，回傳 None
        # 記錄驗證失敗
        print(f"[安全模組] Token 無效或已過期")  

        # decode_token
        # 回傳字串：None（無效或已過期）
        return None

#endregion
