"""
Shared Configuration
Pydantic settings for the Business Intelligence Platform
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application configuration"""
    
    # Application
    app_name: str = "Business Intelligence Platform"
    environment: str = "development"  # development, staging, production
    debug: bool = False
    log_level: str = "INFO"
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 4
    
    # Database
    database_url: str
    sql_echo: bool = False
    db_pool_size: int = 20
    db_max_overflow: int = 10
    db_pool_recycle: int = 3600
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_max_connections: int = 50
    
    # Vector Database (Optional)
    qdrant_host: Optional[str] = None
    qdrant_port: int = 6333
    qdrant_api_key: Optional[str] = None
    qdrant_collection: str = "bi_embeddings"
    
    # Authentication
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    
    # CORS
    cors_origins: str = "*"
    
    # ML Models
    preload_models: bool = True
    model_cache_ttl: int = 3600
    
    # OpenAI
    openai_api_key: Optional[str] = None
    openai_org_id: Optional[str] = None
    
    # Anthropic
    anthropic_api_key: Optional[str] = None
    
    # Forecasting
    forecast_min_data_points: int = 14
    forecast_default_horizon: int = 30
    forecast_confidence_level: float = 0.95
    
    # Health Scoring
    health_score_cache_ttl: int = 300  # 5 minutes
    health_score_min_data_points: int = 100
    
    # Cost Tracking
    enable_cost_tracking: bool = True
    cost_tracking_interval: int = 3600  # 1 hour
    
    # Observability
    enable_metrics: bool = True
    metrics_port: int = 9090
    enable_tracing: bool = False
    otel_exporter_otlp_endpoint: Optional[str] = None
    otel_service_name: str = "bi-platform"
    
    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = 100
    
    # Feature Flags
    enable_forecasting: bool = True
    enable_health_scoring: bool = True
    enable_cost_intelligence: bool = True
    enable_customer_success: bool = True
    enable_recommendations: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        env_prefix = ""


# Singleton settings instance
settings = Settings()
```

