import docker
from app.config import get_settings


class RunnerTimeout(Exception):
    pass


def _docker_client():
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
