from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://ftf:ftf@localhost:5432/ftf"
    broker_url: str = "redis://localhost:6379/0"
    s3_endpoint: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "ftf"
    stub_image: str = "stub-compute:latest"
    docker_network: str = "ftf_default"
    run_timeout_s: int = 120
    # "docker": worker launches a real sibling container (local, needs docker socket).
    # "subprocess": worker runs the compute module in-process as a subprocess
    #               (no docker socket; safe on shared hosts / PaaS like Coolify).
    run_mode: str = "docker"
    # "cloud": runs are enqueued on Celery/Redis and consumed by separate workers.
    # "local": single-process desktop mode — runs execute in an in-process thread
    #          pool (no Redis/Celery/Postgres needed; pair with a sqlite DATABASE_URL).
    deploy_mode: str = "cloud"
    local_workers: int = 2
    # When set, checkpoints are stored as plain files under this directory
    # (no S3 server needed). Empty = use the S3 backend above. The same value is
    # passed to the compute process as STORAGE_DIR so both sides agree.
    storage_dir: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
