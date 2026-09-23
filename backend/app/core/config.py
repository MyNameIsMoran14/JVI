from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+asyncpg://med:med@localhost:5432/med"
    redis_url: str = "redis://localhost:6379/0"
    files_dir: str = "./data/files"

    telegram_bot_token: str = ""
    telegram_webhook_secret: str = ""
    allowed_telegram_ids: str = ""
    mini_app_url: str = ""

    jwt_secret: str = "change-me"

    llm_base_url: str = "https://api.aitunnel.ru/v1/"
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    llm_vision_model: str = "gpt-4o-mini"

    sql_echo: bool = False

    @property
    def allowed_telegram_id_set(self) -> set[int]:
        return {int(chunk) for chunk in self.allowed_telegram_ids.split(",") if chunk.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
