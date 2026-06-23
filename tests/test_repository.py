from app.models import Run
from app.schemas import RunCreate
from app import repository


def test_run_model_defaults(db_session):
    run = Run(run_id="r1", client_id="c1", nbr_pts=10, step=2)
    db_session.add(run)
    db_session.commit()
    fetched = db_session.get(Run, "r1")
    assert fetched.status == "queued"
    assert fetched.checkpoints == []


def test_create_and_get_run(db_session):
    repository.create_run(db_session, "r2", "c1", RunCreate(nbr_pts=50, step=5))
    run = repository.get_run(db_session, "c1", "r2")
    assert run is not None
    assert run.nbr_pts == 50
    assert run.status == "queued"


def test_get_run_wrong_client_returns_none(db_session):
    repository.create_run(db_session, "r3", "c1", RunCreate(nbr_pts=50, step=5))
    assert repository.get_run(db_session, "other", "r3") is None


def test_set_status_and_checkpoints(db_session):
    repository.create_run(db_session, "r4", "c1", RunCreate(nbr_pts=50, step=5))
    repository.set_status(db_session, "r4", "running")
    repository.set_checkpoints(db_session, "r4", ["clients/c1/runs/r4/checkpoints/ckpt_000.json"])
    repository.set_status(db_session, "r4", "done")
    run = repository.get_run(db_session, "c1", "r4")
    assert run.status == "done"
    assert run.checkpoints == ["clients/c1/runs/r4/checkpoints/ckpt_000.json"]


def test_list_runs(db_session):
    repository.create_run(db_session, "r5", "c2", RunCreate(nbr_pts=1, step=1))
    repository.create_run(db_session, "r6", "c2", RunCreate(nbr_pts=1, step=1))
    runs = repository.list_runs(db_session, "c2")
    assert {r.run_id for r in runs} == {"r5", "r6"}
