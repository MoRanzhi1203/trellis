from __future__ import annotations

import os
import tempfile
from pathlib import Path

TEST_DB = Path(tempfile.gettempdir()) / f"trellis_test_{os.getpid()}.db"
if TEST_DB.exists():
    TEST_DB.unlink()
os.environ["TRELLIS_DATABASE_URL"] = f"sqlite:///{TEST_DB.as_posix()}"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db.base import Base  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def database():
    Base.metadata.create_all(engine)
    from app.config import PROJECT_ROOT
    from app.importers.legacy_importer import run_legacy_import

    with SessionLocal() as session:
        run_legacy_import(session, PROJECT_ROOT)
    yield
    engine.dispose()
    TEST_DB.unlink(missing_ok=True)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
