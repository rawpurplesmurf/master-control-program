"""Pytest configuration helpers for the master-control-program project."""
import os
import sys
import types
from pathlib import Path

# Ensure the project root is importable when tests run from the repository root.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Provide lightweight stand-ins for optional dependencies when they are absent.
if "apscheduler.schedulers.asyncio" not in sys.modules:
    aps_pkg = types.ModuleType("apscheduler")
    aps_pkg.__path__ = []

    schedulers_pkg = types.ModuleType("apscheduler.schedulers")
    schedulers_pkg.__path__ = []

    asyncio_pkg = types.ModuleType("apscheduler.schedulers.asyncio")

    class _AsyncIOScheduler:
        def add_job(self, *args, **kwargs):  # pragma: no cover - simple stub
            return None

        def start(self):  # pragma: no cover - simple stub
            return None

        def shutdown(self):  # pragma: no cover - simple stub
            return None

    asyncio_pkg.AsyncIOScheduler = _AsyncIOScheduler

    aps_pkg.schedulers = schedulers_pkg
    schedulers_pkg.asyncio = asyncio_pkg

    sys.modules["apscheduler"] = aps_pkg
    sys.modules["apscheduler.schedulers"] = schedulers_pkg
    sys.modules["apscheduler.schedulers.asyncio"] = asyncio_pkg

if "sqlalchemy" not in sys.modules:
    sqlalchemy_pkg = types.ModuleType("sqlalchemy")
    sqlalchemy_pkg.__path__ = []

    class _Column:
        def __init__(self, *args, **kwargs):  # pragma: no cover - simple stub
            return None

    class _ScalarType:
        def __init__(self, *args, **kwargs):  # pragma: no cover - simple stub
            return None

    def _create_engine(*args, **kwargs):  # pragma: no cover - simple stub
        return types.SimpleNamespace()

    sqlalchemy_pkg.create_engine = _create_engine
    sqlalchemy_pkg.Column = _Column
    sqlalchemy_pkg.Integer = _ScalarType
    sqlalchemy_pkg.String = _ScalarType
    sqlalchemy_pkg.Text = _ScalarType
    sqlalchemy_pkg.DateTime = _ScalarType

    orm_pkg = types.ModuleType("sqlalchemy.orm")

    class _Session:
        def close(self):  # pragma: no cover - simple stub
            return None

        def add(self, *args, **kwargs):  # pragma: no cover - simple stub
            return None

        def commit(self):  # pragma: no cover - simple stub
            return None

        def rollback(self):  # pragma: no cover - simple stub
            return None

        def query(self, *args, **kwargs):  # pragma: no cover - simple stub
            class _Result(list):
                def all(self_inner):
                    return []

            return _Result()

    def _sessionmaker(*args, **kwargs):  # pragma: no cover - simple stub
        def _factory():
            return _Session()

        return _factory

    orm_pkg.sessionmaker = _sessionmaker
    orm_pkg.Session = _Session

    ext_pkg = types.ModuleType("sqlalchemy.ext")
    declarative_pkg = types.ModuleType("sqlalchemy.ext.declarative")

    def _declarative_base():  # pragma: no cover - simple stub
        metadata = types.SimpleNamespace(create_all=lambda bind=None: None)

        class _Base:
            pass

        _Base.metadata = metadata
        return _Base

    declarative_pkg.declarative_base = _declarative_base
    ext_pkg.declarative = declarative_pkg

    exc_pkg = types.ModuleType("sqlalchemy.exc")

    class _SQLAlchemyError(Exception):
        pass

    exc_pkg.SQLAlchemyError = _SQLAlchemyError

    sys.modules["sqlalchemy"] = sqlalchemy_pkg
    sys.modules["sqlalchemy.orm"] = orm_pkg
    sys.modules["sqlalchemy.ext"] = ext_pkg
    sys.modules["sqlalchemy.ext.declarative"] = declarative_pkg
    sys.modules["sqlalchemy.exc"] = exc_pkg

# Provide deterministic defaults for environment variables expected by the app.
DEFAULT_ENV = {
    "MYSQL_USER": "test_user",
    "MYSQL_PASSWORD": "test_password",
    "MYSQL_HOST": "localhost",
    "MYSQL_DB": "test_db",
    "HA_URL": "http://home-assistant.local",
    "HA_TOKEN": "test-token",
    "OLLAMA_URL": "http://ollama.local",
}

for key, value in DEFAULT_ENV.items():
    os.environ.setdefault(key, value)
