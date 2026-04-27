from pydantic_settings import BaseSettings, SettingsConfigDict

#region 資料庫設定


class DatabaseConfig(BaseSettings):
    # 從 .env 檔案讀取環境變數，編碼使用 UTF-8
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # 資料庫使用者名稱
    DB_USER: str = "postgres"

    # 資料庫主機位址（本機開發用 localhost，部署時填雲端主機）
    DB_HOST: str = "localhost"

    # 資料庫名稱
    DB_DATABASE: str = "quant_db"

    # 資料庫密碼
    DB_PASSWORD: str = "password"

    # 資料庫連接埠，PostgreSQL 預設為 5432
    DB_PORT: int = 5432

    # 是否啟用 SSL 加密連線（部署到雲端時通常需要設為 True）
    DB_SSL: bool = False

    @property
    def DATABASE_URL(self) -> str:
        # 組合 asyncpg 格式的連線字串
        base = (
            f"postgresql+asyncpg://"
            f"{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}"
            f"/{self.DB_DATABASE}"
        )
        # 若 DB_SSL 為 True 則附加 SSL 參數，否則直接回傳基本連線字串
        return f"{base}?ssl=require" if self.DB_SSL else base


# 建立全域單例，供其他模組 import 使用
db_config = DatabaseConfig()

#endregion
