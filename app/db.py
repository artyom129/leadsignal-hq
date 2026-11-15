import os
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


def default_url() -> str:
    """Database URL. Override with LEADSIGNAL_DB_URL (tests use an in-memory SQLite)."""
    env = os.environ.get("LEADSIGNAL_DB_URL")
    if env:
        return env
    path = Path(__file__).resolve().parent.parent / "data" / "leadsignal.db"
    path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{path}"


engine = create_engine(default_url(), connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db(bind=None) -> None:
    """Create tables and upgrade databases made by older versions."""
    from . import models  # noqa: F401  (register tables)

    bind = bind or engine
    Base.metadata.create_all(bind=bind)
    insp = inspect(bind)
    names = {i["name"] for i in insp.get_indexes("leads")}
    if "uq_leads_email" not in names:
        with bind.begin() as conn:
            try:
                conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_leads_email ON leads (email)"))
            except Exception:
                # Old data already holds duplicate emails: keep working, the
                # application-level check still blocks new duplicates.
                pass
