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
    # Imported lazily so the attribute is resolved at call time (monkeypatchable,
    # and avoids importing Celery wiring in local mode until first use).
    from app.tasks import run_compute

    if get_settings().deploy_mode == "local":
        _get_executor().submit(run_compute, run_id, client_id)
    else:
        run_compute.delay(run_id, client_id)
