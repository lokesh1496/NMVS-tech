import os
from contextlib import contextmanager
from typing import Dict, Any, Optional

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import declarative_base, sessionmaker, Session

load_dotenv()

_database_url_env = os.getenv("DATABASE_URL", "").strip()
_parsed_database_url = None
if _database_url_env:
    try:
        _parsed_database_url = make_url(_database_url_env)
    except Exception:
        raise RuntimeError("DATABASE_URL is invalid") from None

    _database_backend = _parsed_database_url.get_backend_name()
    if _database_backend == "sqlite":
        DB_TYPE = "sqlite"
    elif _database_backend in {"postgres", "postgresql"}:
        DB_TYPE = "postgres"
    else:
        raise RuntimeError("DATABASE_URL must use SQLite or PostgreSQL")
else:
    DB_TYPE = os.getenv("DB_TYPE", "sqlite").strip().lower()
    if DB_TYPE not in {"sqlite", "postgres", "postgresql"}:
        raise RuntimeError("DB_TYPE must be 'sqlite' or 'postgres'")

if DB_TYPE == "sqlite":
    if _parsed_database_url is not None:
        DATABASE_URL = _parsed_database_url
        print("Database configured for SQLite from DATABASE_URL")
    else:
        db_file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "nmvs.db"))
        DATABASE_URL = make_url(f"sqlite:///{db_file_path}")
        print(f"Database configured for SQLite at: {db_file_path}")
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False
    )
else:
    if _parsed_database_url is not None:
        POSTGRES_USER = (_parsed_database_url.username or "").strip()
        POSTGRES_PASSWORD = _parsed_database_url.password or ""
        POSTGRES_HOST = (_parsed_database_url.host or "localhost").strip()
        POSTGRES_PORT = _parsed_database_url.port or 5432
        POSTGRES_DB = (_parsed_database_url.database or "").strip()
    else:
        POSTGRES_USER = os.getenv("POSTGRES_USER", "").strip()
        POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")
        POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost").strip()
        try:
            POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
        except ValueError as exc:
            raise RuntimeError("POSTGRES_PORT must be an integer") from exc
        POSTGRES_DB = os.getenv("POSTGRES_DB", "").strip()

    missing = [
        name for name, value in (
            ("POSTGRES_USER", POSTGRES_USER),
            ("POSTGRES_PASSWORD", POSTGRES_PASSWORD),
            ("POSTGRES_DB", POSTGRES_DB),
        ) if not value
    ]
    if missing:
        raise RuntimeError(
            "PostgreSQL selected but required environment variables are missing: "
            + ", ".join(missing)
        )
    if not 1 <= POSTGRES_PORT <= 65535:
        raise RuntimeError("POSTGRES_PORT must be between 1 and 65535")

    DATABASE_URL = _parsed_database_url or URL.create(
        drivername="postgresql+psycopg2",
        username=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        database=POSTGRES_DB,
    )

    print(f"Database configured for PostgreSQL: '{POSTGRES_USER}' at {POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}")

    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        echo=False
    )

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    bind=engine
)

Base = declarative_base()


def get_db():
    """FastAPI dependency yielding a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_session():
    """
    Context manager yielding a database session with automatic commit/rollback.
    Useful in scripts and background tasks.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db(bind_engine=None) -> None:
    """Initialize all database tables in PostgreSQL."""
    target_engine = bind_engine or engine
    Base.metadata.create_all(bind=target_engine)

    if target_engine.dialect.name == "sqlite":
        device_columns = {
            column["name"]
            for column in inspect(target_engine).get_columns("devices")
        }
        if "network_type" not in device_columns:
            with target_engine.begin() as connection:
                connection.execute(
                    text(
                        "ALTER TABLE devices "
                        "ADD COLUMN network_type VARCHAR NOT NULL DEFAULT 'Unknown'"
                    )
                )
        if "source" not in device_columns:
            with target_engine.begin() as connection:
                connection.execute(
                    text(
                        "ALTER TABLE devices "
                        "ADD COLUMN source VARCHAR(16) NOT NULL DEFAULT 'manual'"
                    )
                )

        user_columns = {
            column["name"]
            for column in inspect(target_engine).get_columns("users")
        }
        if "password_reset_token_hash" not in user_columns:
            with target_engine.begin() as connection:
                connection.execute(
                    text("ALTER TABLE users ADD COLUMN password_reset_token_hash VARCHAR")
                )
        if "password_reset_token_expires_at" not in user_columns:
            with target_engine.begin() as connection:
                connection.execute(
                    text("ALTER TABLE users ADD COLUMN password_reset_token_expires_at DATETIME")
                )


def get_db_stats(session: Optional[Session] = None) -> Dict[str, Any]:
    """Return connection information and record counts for all core tables."""
    from app.users.model import User
    from app.devices.model import Device
    from app.alerts.model import Alert
    from app.monitoring.model import MonitoringHistory
    from app.speed_monitoring.model import DeviceBandwidthHistory

    db = session or SessionLocal()
    try:
        stats = {
            # Never return a database URL containing a password to API callers.
            "engine_url": engine.url.render_as_string(hide_password=True),
            "dialect": engine.dialect.name,
            "tables": {}
        }
        for model in [User, Device, Alert, MonitoringHistory, DeviceBandwidthHistory]:
            tbl_name = model.__tablename__
            try:
                stats["tables"][tbl_name] = db.query(model).count()
            except Exception:
                # Avoid leaking SQL, schema details, or credentials in diagnostics.
                stats["tables"][tbl_name] = "unavailable"
        return stats
    finally:
        if session is None:
            db.close()