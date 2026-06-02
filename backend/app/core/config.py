"""
Application configuration
"""

import warnings
from functools import lru_cache

from pydantic_settings import BaseSettings

_INSECURE_JWT_SECRET = "your-secret-key-change-in-production"


class Settings(BaseSettings):
    """Application settings"""

    # Application
    app_name: str = "Intelligence Terminal"
    version: str = "0.1.0"
    environment: str = "development"
    debug: bool = True

    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/intelligence_terminal"
    database_echo: bool = False
    database_pool_size: int = 20
    database_max_overflow: int = 10

    # Redis
    redis_url: str = "redis://localhost:6379"

    # API
    api_prefix: str = "/api/v1"
    cors_origins: list = ["http://localhost:3000", "http://localhost:8000"]
    allowed_hosts: list = ["localhost", "127.0.0.1"]

    # JWT
    jwt_secret_key: str = _INSECURE_JWT_SECRET
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
    market_data_update_interval: int = 60
    macro_analysis_interval: int = 300
    correlation_update_interval: int = 3600

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "frozen": True}

    def __init__(self, **data):
        super().__init__(**data)
        if self.jwt_secret_key == _INSECURE_JWT_SECRET and self.environment == "production":
            raise ValueError("jwt_secret_key must be changed in production")
        if self.jwt_secret_key == _INSECURE_JWT_SECRET:
            warnings.warn("Using insecure default JWT secret key — set JWT_SECRET_KEY in .env", stacklevel=2)


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


settings = get_settings()
