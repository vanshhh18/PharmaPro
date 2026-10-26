import os

# Must run before app modules import (settings are read at import time).
os.environ["DATABASE_NAME"] = "aivoa_test"
os.environ.setdefault("ENVIRONMENT", "testing")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.config import settings
from app.db import get_engine, get_session_factory
from app.main import app
from app.models import Base


def _ensure_test_database() -> None:
    admin_url = settings.get_database_url().rsplit("/", 1)[0] + "/postgres"
    admin_engine = create_engine(admin_url, connect_args={"connect_timeout": 5})
    with admin_engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": settings.database_name}
        ).scalar()
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{settings.database_name}"'))
    admin_engine.dispose()


_ensure_test_database()


@pytest.fixture(scope="session")
def test_schema():
    engine = get_engine()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield engine


@pytest.fixture
def client(test_schema) -> TestClient:
    session = get_session_factory()()
    try:
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(text(f'TRUNCATE TABLE "{table.name}" RESTART IDENTITY CASCADE'))
        session.commit()
    finally:
        session.close()

    with TestClient(app) as client:
        yield client
