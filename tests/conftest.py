import os

os.environ["LEADSIGNAL_DB_URL"] = "sqlite://"  # in memory, never touches data/

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import main
from app.db import Base, init_db


@pytest.fixture()
def engine():
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    init_db(eng)
    yield eng
    Base.metadata.drop_all(eng)


@pytest.fixture()
def db(engine):
    s = sessionmaker(bind=engine, autoflush=False)()
    yield s
    s.close()


@pytest.fixture()
def client(engine):
    maker = sessionmaker(bind=engine, autoflush=False)

    def override():
        s = maker()
        try:
            yield s
        finally:
            s.close()

    main.app.dependency_overrides[main.get_db] = override
    with TestClient(main.app, follow_redirects=False) as c:
        yield c
    main.app.dependency_overrides.clear()
