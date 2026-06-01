"""
Application configuration
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    app_name: str = "Jardin Secreto Terminal"
    version: str = "0.1.0"
    environment: str = "development"
    debug: bool = True

    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/jardinsecreto"
    database_echo: bool = False
    database_pool_size: int = 20
    database_max_overflow: int = 10

    # Redis
    redis_url: str = "redis://localhost:6379"

    # API
    api_prefix: str = "/api/v1"
    cors_origins: list = ["*"]

    # JWT
    jwt_secret_key: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24

    # External APIs
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    # Data providers
    polygon_api_key: str = ""
    twelve_data_api_key: str = ""
    alpha_vantage_api_key: str = ""

    # Market data
    market_data_update_interval: int = 60  # seconds
    macro_analysis_interval: int = 300     # 5 minutes
    correlation_update_interval: int = 3600  # 1 hour

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


settings = get_settings()
