import tempfile
from typing import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
import os
from trauertaler.models import Base as DBBase
from trauertaler.config import config
from trauertaler.database import  get_db
from trauertaler.main import app

client = TestClient(app)
SQLALCHEMY_DATABASE_URL = f"sqlite:///:memory:"
db_temppath = tempfile.mkstemp(suffix=".db")[1]
SQLALCHEMY_DATABASE_URL = f"sqlite:///{db_temppath}"


def teardown_module() -> None:
    """teardown any state that was previously setup with a setup_module
    method.
    """
    os.remove(db_temppath)


engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


DBBase.metadata.create_all(bind=engine)


def override_get_db() -> Generator[Session, None, None]:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


def test_read_item() -> None:
    print(config.admin_pass)
    response = client.post(
        "/admin/add_user",
        auth=("admin", config.admin_pass + "a"),
        json={"username": "hihi", "password": "bla"},
    )
    assert response.status_code == 401

    response = client.post(
        "/admin/add_user",
        auth=("admin", config.admin_pass),
        json={"username": "hihi", "password": "bla"},
    )
    assert response.status_code == 200, response.json()
    assert response.json() == 1

    response = client.get("/username/1")
    assert response.status_code == 200
    assert response.json() == "hihi"

    response = client.get("/username/2")
    assert response.status_code == 400

    response = client.get("/uuid/hihi")
    assert response.status_code == 200
    assert response.json() == "1"

    response = client.get("/uuid/hihia")
    assert response.status_code == 400
