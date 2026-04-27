from pydantic_settings import BaseSettings, SettingsConfigDict

#region 第三方 API 金鑰設定


class ApiConfig(BaseSettings):
    # 從 .env 檔案讀取環境變數，編碼使用 UTF-8
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Anthropic Claude API 金鑰，用於 AI 分析功能（未設定時 AI 功能會降級）
    ANTHROPIC_API_KEY: str = ""

    # 富果 API 金鑰，用於台股即時報價與下單（未設定時交易功能無法使用）
    FUGLE_API_KEY: str = ""

    # 富果 API 密鑰，與 FUGLE_API_KEY 配對使用
    FUGLE_API_SECRET: str = ""


# 建立全域單例，供其他模組 import 使用
api_config = ApiConfig()

#endregion
