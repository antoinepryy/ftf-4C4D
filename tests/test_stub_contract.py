import json
import boto3
import pytest
from moto import mock_aws
from stub import compute


@pytest.fixture
def s3_ctx(monkeypatch):
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket="ftf")
        env = {
            "CLIENT_ID": "c1", "RUN_ID": "r1",
            "NBR_PTS": "1000", "STEP": "10",
            "S3_ENDPOINT": "", "S3_ACCESS_KEY": "x",
            "S3_SECRET_KEY": "y", "S3_BUCKET": "ftf",
        }
        for k, v in env.items():
            monkeypatch.setenv(k, v)
        yield client


def test_writes_checkpoints_under_prefix(s3_ctx):
    compute.main()
    resp = s3_ctx.list_objects_v2(Bucket="ftf", Prefix="clients/c1/runs/r1/checkpoints/")
    keys = sorted(o["Key"] for o in resp["Contents"])
    assert keys[0] == "clients/c1/runs/r1/checkpoints/ckpt_000.json"
    assert len(keys) >= 1


def test_resume_reads_active_checkpoint(s3_ctx, monkeypatch):
    s3_ctx.put_object(
        Bucket="ftf",
        Key="clients/c1/runs/r0/checkpoints/ckpt_002.json",
        Body=json.dumps({"index": 2}).encode(),
    )
    monkeypatch.setenv("ACTIVE_CHECKPOINT", "clients/c1/runs/r0/checkpoints/ckpt_002.json")
    monkeypatch.setenv("RUN_ID", "r1")
    compute.main()
    obj = s3_ctx.get_object(Bucket="ftf", Key="clients/c1/runs/r1/checkpoints/ckpt_000.json")
    body = json.loads(obj["Body"].read())
    assert body["resumed_from"] == 2
