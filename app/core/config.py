# from pydantic_settings import BaseSettings, SettingsConfigDict
# from typing import List


# class Settings(BaseSettings):
#     model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

#     APP_ENV: str = "development"
#     SECRET_KEY: str
#     ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080
#     ALGORITHM: str = "HS256"

#     DATABASE_URL: str

#     ALLOWED_ORIGINS: str = "http://localhost:5173"

#     FUGLE_API_KEY: str = ""
#     FUGLE_API_SECRET: str = ""

#     ANTHROPIC_API_KEY: str = ""

#     TWSE_BASE_URL: str = "https://www.twse.com.tw/exchangeReport"

#     @property
#     def origins_list(self) -> List[str]:
#         return [o.strip() for o in self.ALLOWED_ORIGINS.split(",")]


# settings = Settings()
