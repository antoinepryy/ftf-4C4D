import pytest
from app import runner
from app.models import Run


def test_execute_dispatches_on_run_mode(monkeypatch):
    monkeypatch.setattr(runner, "run_container", lambda env: ("docker", env))
    monkeypatch.setattr(runner, "run_subprocess", lambda env: ("subprocess", env))

    monkeypatch.setattr(runner, "get_settings",
                        lambda: type("S", (), dict(run_mode="subprocess"))())
    assert runner.execute({"X": "1"}) == ("subprocess", {"X": "1"})

    monkeypatch.setattr(runner, "get_settings",
                        lambda: type("S", (), dict(run_mode="docker"))())
    assert runner.execute({"X": "1"}) == ("docker", {"X": "1"})


def test_build_env_maps_contract(monkeypatch):
    monkeypatch.setattr(runner, "get_settings", lambda: type(
        "S", (), dict(
            s3_endpoint="http://minio:9000", s3_access_key="a",
            s3_secret_key="b", s3_bucket="ftf",
            stub_image="stub-compute:latest", docker_network="ftf_default",
            run_timeout_s=10,
        ))())
    run = Run(run_id="r1", client_id="c1", nbr_pts=1000, step=10,
              active_checkpoint="clients/c1/runs/r0/checkpoints/ckpt_002.json")
    env = runner.build_env(run)
    assert env["CLIENT_ID"] == "c1"
    assert env["RUN_ID"] == "r1"
    assert env["NBR_PTS"] == "1000"
    assert env["STEP"] == "10"
    assert env["ACTIVE_CHECKPOINT"] == "clients/c1/runs/r0/checkpoints/ckpt_002.json"
    assert env["S3_BUCKET"] == "ftf"


def test_build_env_omits_absent_checkpoint(monkeypatch):
    monkeypatch.setattr(runner, "get_settings", lambda: type(
        "S", (), dict(
            s3_endpoint="http://minio:9000", s3_access_key="a",
            s3_secret_key="b", s3_bucket="ftf",
            stub_image="stub-compute:latest", docker_network="ftf_default",
            run_timeout_s=10,
        ))())
    run = Run(run_id="r1", client_id="c1", nbr_pts=10, step=2, active_checkpoint=None)
    env = runner.build_env(run)
    assert "ACTIVE_CHECKPOINT" not in env


def test_run_container_returns_exit_code(monkeypatch):
    class FakeContainer:
        def wait(self, timeout=None):
            return {"StatusCode": 0}
        def remove(self, force=False):
            pass

    class FakeContainers:
        def run(self, image, environment, network, detach):
            assert detach is True
            return FakeContainer()

    class FakeDocker:
        containers = FakeContainers()

    monkeypatch.setattr(runner, "_docker_client", lambda: FakeDocker())
    monkeypatch.setattr(runner, "get_settings", lambda: type(
        "S", (), dict(stub_image="stub-compute:latest",
                      docker_network="ftf_default", run_timeout_s=10))())
    code = runner.run_container({"CLIENT_ID": "c1"})
    assert code == 0
