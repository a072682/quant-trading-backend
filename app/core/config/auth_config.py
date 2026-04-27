from pydantic_settings import BaseSettings, SettingsConfigDict

#region 認證設定


class AuthConfig(BaseSettings):
    # 從 .env 檔案讀取環境變數，編碼使用 UTF-8
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # JWT 簽名密鑰，用來加密和驗證 Token（正式環境請換成長隨機字串）
    SECRET_KEY: str = "change_me_in_production"

    # JWT 簽名演算法，HS256 是最常用的對稱式演算法
    ALGORITHM: str = "HS256"

    # Token 有效期分鐘數，預設 10080 分鐘 = 7 天
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080


# 建立全域單例，供其他模組 import 使用
auth_config = AuthConfig()

#endregion
