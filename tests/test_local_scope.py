import contextlib

import pytest
from fastapi.testclient import TestClient

from app import repository
from app.schemas import RunCreate


@pytest.fixture
def local_client(monkeypatch, db_session):
    from app import api

    @contextlib.contextmanager
    def fake_session():
        yield db_session

    monkeypatch.setattr(api, "get_session", fake_session)
    monkeypatch.setattr(api, "enqueue", lambda *a, **k: None)
    monkeypatch.setattr(api.s3, "object_exists", lambda key: True)
    monkeypatch.setattr(
        api, "get_settings",
        lambda: type("S", (), dict(deploy_mode="local", local_client_id="me"))(),
    )
    # seed two clients
    repository.create_run(db_session, "x1", "me", RunCreate(nbr_pts=10, step=2))
    repository.create_run(db_session, "x2", "other", RunCreate(nbr_pts=10, step=2))
    return TestClient(api.app)


def test_clients_scoped_to_owner(local_client):
    rows = local_client.get("/clients").json()
    assert [r["client_id"] for r in rows] == ["me"]


def test_runs_scoped_to_owner(local_client):
    rows = local_client.get("/runs").json()
    assert {r["run_id"] for r in rows} == {"x1"}


def test_create_forced_to_owner(local_client):
    # even posting to another client id, the run is created under the owner
    resp = local_client.post("/clients/someoneelse/runs", json={"nbr_pts": 50, "step": 5})
    assert resp.status_code == 201
    assert resp.json()["client_id"] == "me"


def test_config_endpoint_reports_owner(local_client):
    cfg = local_client.get("/config").json()
    assert cfg == {"deploy_mode": "local", "client_id": "me"}
