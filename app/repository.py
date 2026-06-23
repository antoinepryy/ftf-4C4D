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


_STATUSES = ("done", "failed", "running", "queued")


def list_all_runs(session, status: str | None = None) -> list[Run]:
    stmt = select(Run).order_by(Run.created_at.desc())
    if status is not None:
        stmt = stmt.where(Run.status == status)
    return list(session.scalars(stmt))


def client_summaries(session) -> list[dict]:
    """Per-client run counts, one row per client, broken down by status."""
    summaries: dict[str, dict] = {}
    for run in session.scalars(select(Run)):
        s = summaries.setdefault(
            run.client_id,
            {"client_id": run.client_id, "total": 0, **{k: 0 for k in _STATUSES}},
        )
        s["total"] += 1
        if run.status in _STATUSES:
            s[run.status] += 1
    return sorted(summaries.values(), key=lambda s: s["client_id"])


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
