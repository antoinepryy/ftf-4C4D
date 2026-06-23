from pathlib import Path

import boto3
from botocore.exceptions import ClientError
from app.config import get_settings


def get_client():
    s = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=s.s3_endpoint or None,
        aws_access_key_id=s.s3_access_key,
        aws_secret_access_key=s.s3_secret_key,
        region_name="us-east-1",
    )


def checkpoint_prefix(client_id: str, run_id: str) -> str:
    return f"clients/{client_id}/runs/{run_id}/checkpoints/"


def list_checkpoints(client_id: str, run_id: str) -> list[str]:
    prefix = checkpoint_prefix(client_id, run_id)
    sd = get_settings().storage_dir
    if sd:
        base = Path(sd) / prefix
        if not base.exists():
            return []
        return sorted(prefix + f.name for f in base.iterdir() if f.is_file())
    client = get_client()
    resp = client.list_objects_v2(Bucket=get_settings().s3_bucket, Prefix=prefix)
    keys = [obj["Key"] for obj in resp.get("Contents", [])]
    return sorted(keys)


def object_exists(key: str) -> bool:
    sd = get_settings().storage_dir
    if sd:
        return (Path(sd) / key).is_file()
    client = get_client()
    try:
        client.head_object(Bucket=get_settings().s3_bucket, Key=key)
        return True
    except ClientError:
        return False


def ensure_bucket() -> None:
    sd = get_settings().storage_dir
    if sd:
        Path(sd).mkdir(parents=True, exist_ok=True)
        return
    client = get_client()
    bucket = get_settings().s3_bucket
    try:
        client.head_bucket(Bucket=bucket)
    except ClientError:
        client.create_bucket(Bucket=bucket)
