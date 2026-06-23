import json
import os
import time
from pathlib import Path


def _client():
    import boto3

    return boto3.client(
        "s3",
        endpoint_url=os.environ.get("S3_ENDPOINT") or None,
        aws_access_key_id=os.environ.get("S3_ACCESS_KEY", "x"),
        aws_secret_access_key=os.environ.get("S3_SECRET_KEY", "y"),
        region_name="us-east-1",
    )


def _make_store():
    """Return (read, write) for either a local filesystem dir or S3.

    STORAGE_DIR set → plain files on disk (no S3 server). Otherwise S3/boto3.
    Both keep the same object keys so readers see an identical layout.
    """
    storage_dir = os.environ.get("STORAGE_DIR")
    if storage_dir:
        root = Path(storage_dir)

        def read(key):
            return (root / key).read_bytes()

        def write(key, data):
            p = root / key
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)

        return read, write

    bucket = os.environ["S3_BUCKET"]
    s3 = _client()

    def read(key):
        return s3.get_object(Bucket=bucket, Key=key)["Body"].read()

    def write(key, data):
        s3.put_object(Bucket=bucket, Key=key, Body=data)

    return read, write


def main() -> None:
    client_id = os.environ["CLIENT_ID"]
    run_id = os.environ["RUN_ID"]
    nbr_pts = int(os.environ["NBR_PTS"])
    step = int(os.environ["STEP"])
    active = os.environ.get("ACTIVE_CHECKPOINT")

    read, write = _make_store()

    resumed_from = None
    if active:
        resumed_from = json.loads(read(active)).get("index")

    n_ckpts = max(1, nbr_pts // (step * 100))
    prefix = f"clients/{client_id}/runs/{run_id}/checkpoints/"

    for i in range(n_ckpts):
        time.sleep(0.01)  # simulate compute load; scaled down for prototype
        payload = {"index": i, "nbr_pts": nbr_pts, "step": step}
        if i == 0 and resumed_from is not None:
            payload["resumed_from"] = resumed_from
        write(f"{prefix}ckpt_{i:03d}.json", json.dumps(payload).encode())


if __name__ == "__main__":
    main()
