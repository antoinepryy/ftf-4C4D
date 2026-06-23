from app.celery_app import celery
from app.db import get_session
from app import repository, runner, s3


@celery.task(name="run_compute")
def run_compute(run_id: str, client_id: str) -> None:
    with get_session() as session:
        repository.set_status(session, run_id, "running")
        run = repository.get_run(session, client_id, run_id)

    try:
        if run is None:
            raise RuntimeError(f"run {run_id} not found for client {client_id}")
        env = runner.build_env(run)
        try:
            exit_code = runner.run_container(env)
        except runner.RunnerTimeout as exc:
            with get_session() as session:
                repository.set_status(session, run_id, "failed", error=str(exc))
            return

        with get_session() as session:
            if exit_code == 0:
                keys = s3.list_checkpoints(client_id, run_id)
                repository.set_checkpoints(session, run_id, keys)
                repository.set_status(session, run_id, "done")
            else:
                repository.set_status(
                    session, run_id, "failed", error=f"container exit code {exit_code}"
                )
    except Exception as exc:
        with get_session() as session:
            repository.set_status(session, run_id, "failed", error=f"worker error: {exc}")
