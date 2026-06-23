import pytest
from app import worker as tasks, repository
from app.schemas import RunCreate


@pytest.fixture
def patched(monkeypatch, db_session):
    # route get_session() to the in-memory test session
    import contextlib

    @contextlib.contextmanager
    def fake_session():
        yield db_session

    monkeypatch.setattr(tasks, "get_session", fake_session)
    return db_session


def test_run_compute_success(patched, monkeypatch):
    repository.create_run(patched, "r1", "c1", RunCreate(nbr_pts=10, step=2))
    monkeypatch.setattr(tasks.runner, "build_env", lambda run: {"X": "1"})
    monkeypatch.setattr(tasks.runner, "run_container", lambda env: 0)
    monkeypatch.setattr(tasks.s3, "list_checkpoints",
                        lambda c, r: ["clients/c1/runs/r1/checkpoints/ckpt_000.json"])
    tasks.run_compute("r1", "c1")
    run = repository.get_run(patched, "c1", "r1")
    assert run.status == "done"
    assert run.checkpoints == ["clients/c1/runs/r1/checkpoints/ckpt_000.json"]


def test_run_compute_failure_on_nonzero_exit(patched, monkeypatch):
    repository.create_run(patched, "r2", "c1", RunCreate(nbr_pts=10, step=2))
    monkeypatch.setattr(tasks.runner, "build_env", lambda run: {"X": "1"})
    monkeypatch.setattr(tasks.runner, "run_container", lambda env: 1)
    tasks.run_compute("r2", "c1")
    run = repository.get_run(patched, "c1", "r2")
    assert run.status == "failed"
    assert "exit" in (run.error or "").lower()


def test_run_compute_failure_on_timeout(patched, monkeypatch):
    repository.create_run(patched, "r3", "c1", RunCreate(nbr_pts=10, step=2))
    monkeypatch.setattr(tasks.runner, "build_env", lambda run: {"X": "1"})

    def boom(env):
        raise tasks.runner.RunnerTimeout("timed out")

    monkeypatch.setattr(tasks.runner, "run_container", boom)
    tasks.run_compute("r3", "c1")
    run = repository.get_run(patched, "c1", "r3")
    assert run.status == "failed"
    assert "timed out" in run.error


def test_run_compute_failure_on_unexpected_exception(patched, monkeypatch):
    repository.create_run(patched, "r4", "c1", RunCreate(nbr_pts=10, step=2))
    monkeypatch.setattr(tasks.runner, "build_env", lambda run: {"X": "1"})

    def boom(env):
        raise RuntimeError("image not found")

    monkeypatch.setattr(tasks.runner, "run_container", boom)
    tasks.run_compute("r4", "c1")
    run = repository.get_run(patched, "c1", "r4")
    assert run.status == "failed"
    assert run.error and "image not found" in run.error


def test_run_compute_failure_when_run_not_found_for_client(patched, monkeypatch):
    # row exists for c1 but the task is dispatched with a mismatched client.
    # get_run returns None -> the run must end failed, not stuck in running.
    repository.create_run(patched, "r5", "c1", RunCreate(nbr_pts=10, step=2))
    monkeypatch.setattr(tasks.runner, "run_container",
                        lambda env: pytest.fail("run_container must not be called"))
    tasks.run_compute("r5", "other")
    run = repository.get_run(patched, "c1", "r5")
    assert run.status == "failed"
    assert run.error and "not found" in run.error
