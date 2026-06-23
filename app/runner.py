import subprocess
import sys

from app.config import get_settings


class RunnerTimeout(Exception):
    pass


def _docker_client():
    import docker  # imported lazily so subprocess mode needs no docker SDK/socket

    return docker.from_env()


def build_env(run) -> dict[str, str]:
    s = get_settings()
    env = {
        "CLIENT_ID": run.client_id,
        "RUN_ID": run.run_id,
        "NBR_PTS": str(run.nbr_pts),
        "STEP": str(run.step),
        "S3_ENDPOINT": s.s3_endpoint,
        "S3_ACCESS_KEY": s.s3_access_key,
        "S3_SECRET_KEY": s.s3_secret_key,
        "S3_BUCKET": s.s3_bucket,
    }
    if run.active_checkpoint:
        env["ACTIVE_CHECKPOINT"] = run.active_checkpoint
    if s.storage_dir:
        env["STORAGE_DIR"] = s.storage_dir
    return env


def run_container(env: dict[str, str]) -> int:
    s = get_settings()
    client = _docker_client()
    container = client.containers.run(
        s.stub_image,
        environment=env,
        network=s.docker_network,
        detach=True,
    )
    try:
        result = container.wait(timeout=s.run_timeout_s)
    except Exception as exc:  # docker raises ReadTimeout on timeout
        raise RunnerTimeout(str(exc)) from exc
    finally:
        container.remove(force=True)
    return int(result["StatusCode"])


def run_subprocess(env: dict[str, str]) -> int:
    """Run the compute module in a child process (no docker socket required)."""
    import os

    s = get_settings()
    child_env = {**os.environ, **env}
    if getattr(sys, "frozen", False):
        # In a PyInstaller build sys.executable is the bundled app, which ignores
        # "-m": re-invoke it with a marker so its entrypoint runs the stub instead.
        cmd = [sys.executable]
        child_env["FTF_CHILD"] = "stub"
    else:
        cmd = [sys.executable, "-m", "stub.compute"]
    try:
        proc = subprocess.run(cmd, env=child_env, timeout=s.run_timeout_s)
    except subprocess.TimeoutExpired as exc:
        raise RunnerTimeout(str(exc)) from exc
    return proc.returncode


def execute(env: dict[str, str]) -> int:
    """Dispatch to the configured run mode and return the compute exit code."""
    if get_settings().run_mode == "subprocess":
        return run_subprocess(env)
    return run_container(env)
