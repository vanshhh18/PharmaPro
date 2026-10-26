from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "AIVOA"
    environment: str = "development"
    api_prefix: str = "/api"

    database_host: str = "localhost"
    database_port: int = 5432
    database_user: str = "aivoa"
    database_password: str = ""
    database_name: str = "aivoa"
    database_url: str = ""

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    max_upload_bytes: int = 10 * 1024 * 1024
    max_report_chars: int = 200000

    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def get_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        return (
            f"postgresql+psycopg://{self.database_user}:{self.database_password}"
            f"@{self.database_host}:{self.database_port}/{self.database_name}"
        )

    def redacted_database_url(self) -> str:
        url = self.get_database_url()
        if self.database_password:
            url = url.replace(self.database_password, "***")
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
