"""Run dispatch: enqueue a run for execution under the configured deploy mode.

cloud → Celery (separate worker processes consume a Redis queue).
local → an in-process thread pool (single-process desktop mode, no broker).
"""
from concurrent.futures import ThreadPoolExecutor

from app.config import get_settings

_executor: ThreadPoolExecutor | None = None


def _get_executor() -> ThreadPoolExecutor:
    global _executor
    if _executor is None:
        _executor = ThreadPoolExecutor(
            max_workers=get_settings().local_workers, thread_name_prefix="ftf-worker"
        )
    return _executor


def _reset_executor() -> None:
    """Drop the pool (tests; reconfigures worker count on next enqueue)."""
    global _executor
    if _executor is not None:
        _executor.shutdown(wait=False)
    _executor = None


def enqueue(run_id: str, client_id: str) -> None:
    # Imported lazily and per-mode: local never imports app.tasks, so Celery/kombu
    # stay out of the desktop build entirely.
    if get_settings().deploy_mode == "local":
        from app.worker import run_compute

        _get_executor().submit(run_compute, run_id, client_id)
    else:
        from app.tasks import run_compute_task

        run_compute_task.delay(run_id, client_id)
