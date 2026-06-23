import contextlib

import pytest
from fastapi.testclient import TestClient

from app import repository
from app.schemas import RunCreate


def _seed(session):
    # c1: one done, one failed, one running
    repository.create_run(session, "a1", "c1", RunCreate(nbr_pts=10, step=2))
    repository.create_run(session, "a2", "c1", RunCreate(nbr_pts=10, step=2))
    repository.create_run(session, "a3", "c1", RunCreate(nbr_pts=10, step=2))
    repository.set_status(session, "a1", "done")
    repository.set_status(session, "a2", "failed", error="boom")
    repository.set_status(session, "a3", "running")
    # c2: one queued
    repository.create_run(session, "b1", "c2", RunCreate(nbr_pts=10, step=2))


def test_list_all_runs_no_filter(db_session):
    _seed(db_session)
    runs = repository.list_all_runs(db_session)
    assert {r.run_id for r in runs} == {"a1", "a2", "a3", "b1"}


def test_list_all_runs_status_filter(db_session):
    _seed(db_session)
    failed = repository.list_all_runs(db_session, status="failed")
    assert [r.run_id for r in failed] == ["a2"]
    done = repository.list_all_runs(db_session, status="done")
    assert [r.run_id for r in done] == ["a1"]


def test_client_summaries_counts(db_session):
    _seed(db_session)
    summaries = {s["client_id"]: s for s in repository.client_summaries(db_session)}
    assert summaries["c1"] == {
        "client_id": "c1", "total": 3, "done": 1, "failed": 1, "running": 1, "queued": 0,
    }
    assert summaries["c2"] == {
        "client_id": "c2", "total": 1, "done": 0, "failed": 0, "running": 0, "queued": 1,
    }


@pytest.fixture
def client(monkeypatch, db_session):
    from app import api

    @contextlib.contextmanager
    def fake_session():
        yield db_session

    monkeypatch.setattr(api, "get_session", fake_session)
    return TestClient(api.app)


def test_get_clients_endpoint(client, db_session):
    _seed(db_session)
    resp = client.get("/clients")
    assert resp.status_code == 200
    rows = {r["client_id"]: r for r in resp.json()}
    assert rows["c1"]["done"] == 1
    assert rows["c1"]["failed"] == 1
    assert rows["c2"]["queued"] == 1


def test_get_all_runs_endpoint_with_filter(client, db_session):
    _seed(db_session)
    resp = client.get("/runs", params={"status": "failed"})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["run_id"] == "a2"
    assert body[0]["error"] == "boom"


def test_dashboard_index_served(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "FTF" in resp.text
