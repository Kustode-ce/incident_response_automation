from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "incident-response-automation"
    environment: str = "development"
    log_level: str = "INFO"
    debug: bool = False

    api_host: str = "0.0.0.0"
    api_port: int = 8000

    database_url: str = "postgresql+asyncpg://user:pass@localhost:5432/incident_response"
    db_pool_size: int = 20
    db_max_overflow: int = 10
    db_pool_recycle_seconds: int = 3600
    sql_echo: bool = False

    redis_url: str = "redis://localhost:6379/0"

    openai_api_key: str | None = None
    anthropic_api_key: str | None = None

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
