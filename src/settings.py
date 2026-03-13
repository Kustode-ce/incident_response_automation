import os
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings


def _build_database_url() -> str:
    """Construct DATABASE_URL from individual POSTGRES_* env vars if not set explicitly."""
    explicit = os.getenv("DATABASE_URL")
    if explicit:
        return explicit
    user = quote_plus(os.getenv("POSTGRES_USER", "user"))
    password = quote_plus(os.getenv("POSTGRES_PASSWORD", "pass"))
    server = os.getenv("POSTGRES_SERVER", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "incident_response")
    ssl_mode = os.getenv("DB_SSL_MODE", "")
    url = f"postgresql+asyncpg://{user}:{password}@{server}:{port}/{db}"
    if ssl_mode:
        url += f"?ssl={ssl_mode}"
    return url


def _build_redis_url(db: str = "0") -> str:
    """Construct a Redis URL from REDIS_HOST/REDIS_PASSWORD env vars if REDIS_URL is not set."""
    explicit = os.getenv("REDIS_URL")
    if explicit:
        return explicit
    host = os.getenv("REDIS_HOST", "localhost")
    port = os.getenv("REDIS_PORT", "6379")
    password = os.getenv("REDIS_PASSWORD", "")
    if password:
        return f"redis://:{quote_plus(password)}@{host}:{port}/{db}"
    return f"redis://{host}:{port}/{db}"


class Settings(BaseSettings):
    app_name: str = "incident-response-automation"
    environment: str = "development"
    log_level: str = "INFO"
    debug: bool = False

    api_host: str = "0.0.0.0"
    api_port: int = 8000

    database_url: str = _build_database_url()
    db_pool_size: int = 20
    db_max_overflow: int = 10
    db_pool_recycle_seconds: int = 3600
    sql_echo: bool = False

    redis_url: str = _build_redis_url("0")
    celery_broker_url: str = _build_redis_url("0")
    celery_result_backend: str = _build_redis_url("1")

    # ML providers
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    enable_ml_classification: bool = False
    enable_ml_root_cause: bool = False

    # Observability stack (backend cluster services)
    prometheus_url: str = "http://prometheus:9090"
    loki_url: str = "http://loki:3100"
    tempo_url: str = "http://tempo:3200"
    grafana_url: str = "http://grafana:3000"

    # Slack
    slack_webhook_url: str = ""
    slack_bot_token: str = ""
    slack_incidents_channel: str = "#incidents"

    # Jira
    jira_url: str = ""
    jira_username: str = ""
    jira_api_token: str = ""
    jira_project: str = "INC"

    # GitHub
    github_token: str = ""
    github_repo: str = ""

    # Feature flags
    enable_observability_enrichment: bool = True
    enable_slack_notifications: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
