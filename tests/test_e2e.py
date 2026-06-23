import os
import time
import boto3
import httpx
import pytest

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(os.environ.get("FTF_E2E") != "1", reason="needs live stack"),
]

API = "http://localhost:8000"


def _wait_done(client_id, run_id, timeout=60):
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = httpx.get(f"{API}/clients/{client_id}/runs/{run_id}").json()
        if r["status"] in ("done", "failed"):
            return r
        time.sleep(1)
    raise AssertionError("run did not finish in time")


def test_run_to_done_with_checkpoints():
    resp = httpx.post(f"{API}/clients/c1/runs", json={"nbr_pts": 1000, "step": 10})
    assert resp.status_code == 201
    run_id = resp.json()["run_id"]
    final = _wait_done("c1", run_id)
    assert final["status"] == "done"
    assert len(final["checkpoints"]) >= 1

    s3 = boto3.client("s3", endpoint_url="http://localhost:9000",
                      aws_access_key_id="minioadmin", aws_secret_access_key="minioadmin",
                      region_name="us-east-1")
    listed = s3.list_objects_v2(Bucket="ftf", Prefix=f"clients/c1/runs/{run_id}/checkpoints/")
    assert listed["KeyCount"] >= 1


def test_resume_from_previous_run():
    first = httpx.post(f"{API}/clients/c2/runs", json={"nbr_pts": 1000, "step": 10}).json()
    first_final = _wait_done("c2", first["run_id"])
    src_ckpt = first_final["checkpoints"][-1]

    second = httpx.post(
        f"{API}/clients/c2/runs",
        json={"nbr_pts": 1000, "step": 10, "active_checkpoint": src_ckpt},
    )
    assert second.status_code == 201
    second_final = _wait_done("c2", second.json()["run_id"])
    assert second_final["status"] == "done"
