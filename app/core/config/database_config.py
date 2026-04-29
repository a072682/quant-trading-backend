#region 引入套件
# BaseSettings：負責「實際去讀取」並「轉換成對應的資料型別」
# SettingsConfigDict：告訴程式「去哪裡找設定」（指定 .env 檔案的位置）
from pydantic_settings import BaseSettings, SettingsConfigDict
#endregion

#region 資料庫設定
class DatabaseConfig(BaseSettings):
    # 找到指定位置並讀取 .env 檔案讀取環境變數，編碼使用 UTF-8
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

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

    # 組合Neon資料庫連線用的 asyncpg 格式連線字串
    # @property只是讓DATABASE_URL呼叫時不用加()就會執行
    # 不追加使用案例:engine = create_async_engine(db_config.DATABASE_URL())
    # 追加使用案例:engine = create_async_engine(db_config.DATABASE_URL)
    # 差別只有()單純是為了一致性跟方便才加的
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
#endregion


#region 建立全域單例，供其他模組 import 使用
db_config = DatabaseConfig()
#endregion
