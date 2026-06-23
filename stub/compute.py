import json
import os
import time

import boto3


def _client():
    return boto3.client(
        "s3",
        endpoint_url=os.environ.get("S3_ENDPOINT") or None,
        aws_access_key_id=os.environ.get("S3_ACCESS_KEY", "x"),
        aws_secret_access_key=os.environ.get("S3_SECRET_KEY", "y"),
        region_name="us-east-1",
    )


def main() -> None:
    client_id = os.environ["CLIENT_ID"]
    run_id = os.environ["RUN_ID"]
    nbr_pts = int(os.environ["NBR_PTS"])
    step = int(os.environ["STEP"])
    bucket = os.environ["S3_BUCKET"]
    active = os.environ.get("ACTIVE_CHECKPOINT")

    s3 = _client()

    resumed_from = None
    if active:
        obj = s3.get_object(Bucket=bucket, Key=active)
        resumed_from = json.loads(obj["Body"].read()).get("index")

    n_ckpts = max(1, nbr_pts // (step * 100))
    prefix = f"clients/{client_id}/runs/{run_id}/checkpoints/"

    for i in range(n_ckpts):
        time.sleep(0.01)  # simulate compute load; scaled down for prototype
        payload = {"index": i, "nbr_pts": nbr_pts, "step": step}
        if i == 0 and resumed_from is not None:
            payload["resumed_from"] = resumed_from
        s3.put_object(
            Bucket=bucket,
            Key=f"{prefix}ckpt_{i:03d}.json",
            Body=json.dumps(payload).encode(),
        )


if __name__ == "__main__":
    main()
