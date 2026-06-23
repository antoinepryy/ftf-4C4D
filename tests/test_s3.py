import boto3
import pytest
from moto import mock_aws
from app import s3


@pytest.fixture
def s3_env(monkeypatch):
    monkeypatch.setenv("S3_ENDPOINT", "")  # let moto intercept default endpoint
    s3.get_settings.cache_clear()
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket="ftf")
        monkeypatch.setattr(s3, "get_client", lambda: client)
        yield client


def test_checkpoint_prefix():
    assert s3.checkpoint_prefix("c1", "r1") == "clients/c1/runs/r1/checkpoints/"


def test_list_checkpoints_sorted(s3_env):
    for name in ["ckpt_001.json", "ckpt_000.json"]:
        s3_env.put_object(Bucket="ftf", Key=f"clients/c1/runs/r1/checkpoints/{name}", Body=b"{}")
    keys = s3.list_checkpoints("c1", "r1")
    assert keys == [
        "clients/c1/runs/r1/checkpoints/ckpt_000.json",
        "clients/c1/runs/r1/checkpoints/ckpt_001.json",
    ]


def test_object_exists(s3_env):
    s3_env.put_object(Bucket="ftf", Key="clients/c1/runs/r1/checkpoints/ckpt_000.json", Body=b"{}")
    assert s3.object_exists("clients/c1/runs/r1/checkpoints/ckpt_000.json")
    assert not s3.object_exists("clients/c1/runs/r1/checkpoints/nope.json")
