"""
Pytest configuration and fixtures
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.db.base import Base
from app.main import create_app


# ------------------------------------------------------------------ #
#  Mock DB session (unit tests — no real PostgreSQL needed)           #
# ------------------------------------------------------------------ #

class _MockResult:
    """Mimics the result object returned by session.execute()."""
    def scalars(self):
        m = MagicMock()
        m.all.return_value = []
        m.first.return_value = None
        return m
    def scalar_one_or_none(self):
        return None
    @property
    def rowcount(self):
        return 0


class MockAsyncSession:
    """Minimal async session that does nothing — unit tests only."""
    async def execute(self, *args, **kwargs):
        return _MockResult()
    async def commit(self):
        pass
    async def rollback(self):
        pass
    def add(self, obj):
        pass


async def _mock_get_db():
    yield MockAsyncSession()


# ------------------------------------------------------------------ #
#  Test client (with DB overridden)                                   #
# ------------------------------------------------------------------ #

@pytest.fixture
def client():
    """TestClient with PostgreSQL dependency replaced by a no-op mock."""
    from app.db.session import get_db
    app = create_app()
    app.dependency_overrides[get_db] = _mock_get_db
    return TestClient(app)


@pytest_asyncio.fixture
async def async_client():
    from app.db.session import get_db
    app = create_app()
    app.dependency_overrides[get_db] = _mock_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


# ------------------------------------------------------------------ #
#  Settings                                                           #
# ------------------------------------------------------------------ #

@pytest.fixture(scope="session")
def test_settings():
    return Settings(
        environment="testing",
        database_url="sqlite+aiosqlite:///:memory:",
        redis_url="redis://localhost:6379/1",
        jwt_secret_key="test-secret-key-32-chars-minimum!!",
    )


# ------------------------------------------------------------------ #
#  Real async DB session (integration tests only)                     #
# ------------------------------------------------------------------ #

@pytest_asyncio.fixture
async def async_session():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as session:
        yield session

    await engine.dispose()


# ------------------------------------------------------------------ #
#  Sample data fixtures                                               #
# ------------------------------------------------------------------ #

@pytest.fixture
def market_data_sample():
    return {
        "symbol": "XAUUSD",
        "open": 2042.50, "high": 2050.75, "low": 2040.25, "close": 2048.30,
        "volume": 1_500_000,
        "timestamp": "2024-05-31T14:30:00Z",
    }


@pytest.fixture
def tick_data_sample():
    return {
        "symbol": "XAUUSD",
        "bid": 2048.25, "ask": 2048.35, "price": 2048.30,
        "volume": 100,
        "timestamp": "2024-05-31T14:30:01Z",
    }


@pytest.fixture
def multiple_ohlcv():
    return [
        {"symbol": "XAUUSD", "timeframe": "1h", "open": 2042.50, "high": 2050.75,
         "low": 2040.25, "close": 2048.30, "volume": 1_500_000,
         "timestamp": "2024-05-31T14:00:00Z"},
        {"symbol": "XAUUSD", "timeframe": "1h", "open": 2048.30, "high": 2055.00,
         "low": 2046.50, "close": 2052.75, "volume": 1_600_000,
         "timestamp": "2024-05-31T15:00:00Z"},
        {"symbol": "XAUUSD", "timeframe": "1h", "open": 2052.75, "high": 2060.25,
         "low": 2050.50, "close": 2058.90, "volume": 1_400_000,
         "timestamp": "2024-05-31T16:00:00Z"},
    ]


# ------------------------------------------------------------------ #
#  Markers                                                            #
# ------------------------------------------------------------------ #

def pytest_configure(config):
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
