from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.db.session import get_db
from app.main import app
from app.models import Base

engine = create_async_engine("sqlite+aiosqlite:///:memory:")
TestSession = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

# Use a >=32-byte secret to suppress the InsecureKeyLengthWarning from PyJWT.
_TEST_JWT_SECRET = "scopeproof-test-secret-key-change-me-in-production-32bytes"


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestSession() as session:
        yield session


@pytest.fixture(autouse=True)
async def reset_db() -> AsyncGenerator[None, None]:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(autouse=True)
def use_test_jwt_secret(monkeypatch):
    """Override the JWT secret with a >=32-byte value to avoid InsecureKeyLengthWarning."""
    monkeypatch.setattr(settings, "JWT_SECRET_KEY", _TEST_JWT_SECRET)


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
