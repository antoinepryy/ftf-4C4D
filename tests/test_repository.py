from app.models import Run


def test_run_model_defaults(db_session):
    run = Run(run_id="r1", client_id="c1", nbr_pts=10, step=2)
    db_session.add(run)
    db_session.commit()
    fetched = db_session.get(Run, "r1")
    assert fetched.status == "queued"
    assert fetched.checkpoints == []
