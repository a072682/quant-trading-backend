from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict

#region 應用程式基本設定


class AppConfig(BaseSettings):
    # 從 .env 檔案讀取環境變數，編碼使用 UTF-8
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # 執行環境，影響 Swagger 文件是否開啟（development 開啟，production 關閉）
    APP_ENV: str = "development"

    # CORS 白名單，多個來源以英文逗號分隔，例如 "http://localhost:5173,https://my-site.com"
    ALLOWED_ORIGINS: str = "http://localhost:5173"

    @property
    def origins_list(self) -> List[str]:
        # 將逗號分隔的字串切分為清單，並去除每個來源前後的空白
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]


# 建立全域單例，供其他模組 import 使用
app_config = AppConfig()

#endregion
