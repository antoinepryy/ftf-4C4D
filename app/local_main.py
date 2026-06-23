"""Desktop entrypoint: run the whole app as a single local process.

No Redis, no Celery, no Postgres, no Docker. Runs are executed by an in-process
thread pool (DEPLOY_MODE=local) and stored in a local SQLite DB; checkpoints go
to a local S3 endpoint (a native `minio` binary, started here if bundled).

This is the module a packaged Windows .exe (PyInstaller) launches. It sets sane
defaults BEFORE the app is imported, optionally starts a bundled MinIO, then
serves the API + dashboard on http://127.0.0.1:<port>/ and opens a browser.
"""
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def data_dir() -> Path:
    if sys.platform.startswith("win"):
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    d = base / "ftf"
    (d / "minio-data").mkdir(parents=True, exist_ok=True)
    return d


def configure_env() -> dict:
    """Populate defaults for local mode without overriding anything explicit."""
    d = data_dir()
    defaults = {
        "DEPLOY_MODE": "local",
        "RUN_MODE": "subprocess",
        "DATABASE_URL": f"sqlite:///{(d / 'ftf.db').as_posix()}",
        # Raw filesystem storage by default — no S3 server / no MinIO needed.
        # Set STORAGE_DIR="" plus S3_* to use an S3 backend instead.
        "STORAGE_DIR": str(d / "storage"),
    }
    for k, v in defaults.items():
        os.environ.setdefault(k, v)
    return {**defaults, **{k: os.environ[k] for k in defaults}}


def _wait_http(url: str, timeout: float) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(url, timeout=1)
            return True
        except Exception:
            time.sleep(0.3)
    return False


def maybe_start_minio() -> subprocess.Popen | None:
    """Start a bundled native MinIO if FTF_MINIO_BIN points at one.

    If unset, assume an external local S3 is already reachable at S3_ENDPOINT.
    """
    binary = os.environ.get("FTF_MINIO_BIN")
    if not binary or not Path(binary).exists():
        return None
    env = {
        **os.environ,
        "MINIO_ROOT_USER": os.environ.get("S3_ACCESS_KEY", "minioadmin"),
        "MINIO_ROOT_PASSWORD": os.environ.get("S3_SECRET_KEY", "minioadmin"),
    }
    proc = subprocess.Popen(
        [binary, "server", str(data_dir() / "minio-data"), "--address", "127.0.0.1:9000"],
        env=env,
    )
    _wait_http("http://127.0.0.1:9000/minio/health/live", timeout=20)
    return proc


def main() -> None:
    cfg = configure_env()
    port = int(os.environ.get("FTF_PORT", "8000"))
    minio = maybe_start_minio()
    try:
        import uvicorn

        if os.environ.get("FTF_OPEN_BROWSER", "1") == "1":
            import threading
            import webbrowser

            url = f"http://127.0.0.1:{port}/"
            threading.Timer(1.5, lambda: webbrowser.open(url)).start()

        print(f"FTF local — dashboard on http://127.0.0.1:{port}/  (data: {data_dir()})")
        # import string so the app is imported AFTER env defaults are set
        uvicorn.run("app.api:app", host="127.0.0.1", port=port, log_level="info")
    finally:
        if minio is not None:
            minio.terminate()


if __name__ == "__main__":
    main()
