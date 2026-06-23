from app.celery_app import celery
from app.worker import run_compute


@celery.task(name="run_compute")
def run_compute_task(run_id: str, client_id: str) -> None:
    run_compute(run_id, client_id)
