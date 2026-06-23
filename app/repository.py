from sqlalchemy import select
from app.models import Run
from app.schemas import RunCreate


def create_run(session, run_id: str, client_id: str, data: RunCreate) -> Run:
    run = Run(
        run_id=run_id,
        client_id=client_id,
        nbr_pts=data.nbr_pts,
        step=data.step,
        active_checkpoint=data.active_checkpoint,
        status="queued",
        checkpoints=[],
    )
    session.add(run)
    session.commit()
    return run


def get_run(session, client_id: str, run_id: str) -> Run | None:
    run = session.get(Run, run_id)
    if run is None or run.client_id != client_id:
        return None
    return run


def list_runs(session, client_id: str) -> list[Run]:
    return list(session.scalars(select(Run).where(Run.client_id == client_id)))


def set_status(session, run_id: str, status: str, error: str | None = None) -> None:
    run = session.get(Run, run_id)
    run.status = status
    if error is not None:
        run.error = error
    session.commit()


def set_checkpoints(session, run_id: str, keys: list[str]) -> None:
    run = session.get(Run, run_id)
    run.checkpoints = keys
    session.commit()
