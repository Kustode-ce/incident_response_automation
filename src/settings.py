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
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

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
