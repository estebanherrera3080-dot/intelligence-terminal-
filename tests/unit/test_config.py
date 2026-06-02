"""
Unit tests for application configuration
"""

import pytest
from pydantic import ValidationError

from app.core.config import Settings, settings


@pytest.mark.unit
def test_settings_environment():
    assert settings.environment is not None
    assert settings.environment in ["development", "staging", "production", "testing"]


@pytest.mark.unit
def test_settings_database_url():
    assert settings.database_url is not None
    assert "postgresql" in settings.database_url or "sqlite" in settings.database_url


@pytest.mark.unit
def test_settings_redis_url():
    assert settings.redis_url is not None
    assert "redis" in settings.redis_url


@pytest.mark.unit
def test_settings_cors_origins():
    assert settings.cors_origins is not None
    assert isinstance(settings.cors_origins, list)
    assert len(settings.cors_origins) > 0


@pytest.mark.unit
def test_settings_api_prefix():
    assert settings.api_prefix == "/api/v1"


@pytest.mark.unit
def test_settings_allowed_hosts():
    assert settings.allowed_hosts is not None
    assert isinstance(settings.allowed_hosts, list)
    assert len(settings.allowed_hosts) > 0


@pytest.mark.unit
def test_settings_debug_flag():
    assert hasattr(settings, "debug")


@pytest.mark.unit
def test_settings_immutable():
    # Pydantic v2 frozen model raises ValidationError on field assignment
    with pytest.raises((ValidationError, TypeError)):
        settings.database_url = "invalid"


@pytest.mark.unit
def test_settings_jwt_fields():
    assert settings.jwt_algorithm == "HS256"
    assert settings.jwt_expiration_hours > 0


@pytest.mark.unit
def test_settings_market_intervals():
    assert settings.market_data_update_interval > 0
    assert settings.macro_analysis_interval > 0
    assert settings.correlation_update_interval > 0
