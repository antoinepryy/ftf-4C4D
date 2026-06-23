import contextlib
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch, db_session):
    from app import api

    @contextlib.contextmanager
    def fake_session():
        yield db_session

    monkeypatch.setattr(api, "get_session", fake_session)
    monkeypatch.setattr(api.run_compute, "delay", lambda *a, **k: None)
    monkeypatch.setattr(api.s3, "object_exists", lambda key: True)
    return TestClient(api.app)


def test_create_run_returns_queued(client):
    resp = client.post("/clients/c1/runs", json={"nbr_pts": 100, "step": 10})
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "queued"
    assert body["client_id"] == "c1"
    assert body["run_id"]


def test_create_run_rejects_bad_params(client):
    resp = client.post("/clients/c1/runs", json={"nbr_pts": 0, "step": 10})
    assert resp.status_code == 422


def test_create_run_rejects_missing_checkpoint(client, monkeypatch):
    from app import api
    monkeypatch.setattr(api.s3, "object_exists", lambda key: False)
    resp = client.post(
        "/clients/c1/runs",
        json={"nbr_pts": 100, "step": 10, "active_checkpoint": "nope"},
    )
    assert resp.status_code == 400


def test_get_run_404(client):
    resp = client.get("/clients/c1/runs/does-not-exist")
    assert resp.status_code == 404


def test_get_and_list_runs(client):
    created = client.post("/clients/c1/runs", json={"nbr_pts": 100, "step": 10}).json()
    rid = created["run_id"]
    got = client.get(f"/clients/c1/runs/{rid}")
    assert got.status_code == 200
    assert got.json()["run_id"] == rid
    listed = client.get("/clients/c1/runs")
    assert any(r["run_id"] == rid for r in listed.json())
