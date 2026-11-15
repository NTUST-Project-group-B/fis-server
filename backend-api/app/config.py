"""讀取 .env 設定。"""

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # 必填。沒設定時，第一次送通知就會報錯並指出缺哪個欄位。
    # 用 SecretStr,印出設定時只會顯示 **********,URL 不會出現在 log。
    discord_webhook_url: SecretStr


@lru_cache
def get_settings() -> Settings:
    return Settings()
