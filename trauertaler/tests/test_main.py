import tempfile
from typing import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
import os
from trauertaler.models import Base as DBBase
from trauertaler.config import config
from trauertaler.database import get_db
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

    response = client.get("/username/2")
    assert response.status_code == 400

    response = client.post(
        "/admin/add_user",
        auth=("admin", config.admin_pass),
        json={"username": "hoho", "password": "bla"},
    )
    assert response.status_code == 200, response.json()
    assert response.json() == 2

    response = client.get("/username/1")
    assert response.status_code == 200
    assert response.json() == "hihi"

    response = client.get("/uuid/hihi")
    assert response.status_code == 200
    assert response.json() == "1"

    response = client.get("/uuid/hihia")
    assert response.status_code == 400

    response = client.post(
        "/token",
        content=f"grant_type=password&username=hihi&password=bla",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200
    token_1 = response.json()["access_token"]

    response = client.post(
        "/token",
        content=f"grant_type=password&username=hoho&password=bla",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200
    token_2 = response.json()["access_token"]

    response = client.get(
        "/transactions",
        headers={"Authorization": f"Bearer {token_1}"},
    )
    assert response.status_code == 200
    assert response.json() == []

    response = client.post(
        "/admin/set_amount",
        auth=("admin", config.admin_pass),
        json={"userid": 1, "amount": 2000},
    )
    assert response.status_code == 200
    assert response.json() == 2000

    response = client.get(
        "/ledger",
        headers={"Authorization": f"Bearer {token_1}"},
    )
    assert response.status_code == 200
    assert response.json() == 2000

    response = client.post(
        "/transactions",
        headers={
            "Authorization": f"Bearer {token_1}",
        },
        json={"receiver_id": 2, "amount": 1000},
    )
    assert response.status_code == 200
    assert response.json()["amount"] == 1000
    assert str(response.json()["receiver_id"]) == str(2)
    assert str(response.json()["sender_id"]) == str(1)

    with client.websocket_connect(
        "/subscribe",
        headers={"Authorization": f"Bearer {token_1}"},
    ) as websocket:
        response = client.post(
            "/transactions",
            headers={
                "Authorization": f"Bearer {token_2}",
            },
            json={"receiver_id": 1, "amount": 200},
        )
        data = websocket.receive_json()
        assert str(data["sender"]) == str(2)
        assert str(data["receiver"]) == str(1)
        assert str(data["amount"] == 200)
