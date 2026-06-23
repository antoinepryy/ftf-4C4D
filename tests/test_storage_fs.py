import json
from pathlib import Path

from app import s3
from stub import compute


def _fs_settings(storage_dir):
    return type("S", (), dict(storage_dir=str(storage_dir), s3_bucket="ftf"))()


def test_s3_fs_backend_list_exists_ensure(tmp_path, monkeypatch):
    monkeypatch.setattr(s3, "get_settings", lambda: _fs_settings(tmp_path))
    s3.ensure_bucket()  # fs: just makes the root dir, no S3 call
    prefix = s3.checkpoint_prefix("c1", "r1")
    base = tmp_path / prefix
    base.mkdir(parents=True)
    (base / "ckpt_001.json").write_text("{}")
    (base / "ckpt_000.json").write_text("{}")

    assert s3.list_checkpoints("c1", "r1") == [
        "clients/c1/runs/r1/checkpoints/ckpt_000.json",
        "clients/c1/runs/r1/checkpoints/ckpt_001.json",
    ]
    assert s3.object_exists("clients/c1/runs/r1/checkpoints/ckpt_000.json")
    assert not s3.object_exists("clients/c1/runs/r1/checkpoints/nope.json")


def test_s3_fs_list_empty_when_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(s3, "get_settings", lambda: _fs_settings(tmp_path))
    assert s3.list_checkpoints("c1", "ghost") == []


def test_stub_writes_to_filesystem(tmp_path, monkeypatch):
    for k, v in {
        "CLIENT_ID": "c1", "RUN_ID": "r1", "NBR_PTS": "2000", "STEP": "10",
        "S3_BUCKET": "ftf", "STORAGE_DIR": str(tmp_path),
    }.items():
        monkeypatch.setenv(k, v)
    compute.main()
    ckpts = sorted((tmp_path / "clients/c1/runs/r1/checkpoints").glob("ckpt_*.json"))
    assert [p.name for p in ckpts] == ["ckpt_000.json", "ckpt_001.json"]
    assert json.loads(ckpts[0].read_text())["index"] == 0


def test_stub_fs_resume_reads_active_checkpoint(tmp_path, monkeypatch):
    src = tmp_path / "clients/c1/runs/r0/checkpoints"
    src.mkdir(parents=True)
    (src / "ckpt_002.json").write_text(json.dumps({"index": 2}))
    for k, v in {
        "CLIENT_ID": "c1", "RUN_ID": "r1", "NBR_PTS": "2000", "STEP": "10",
        "S3_BUCKET": "ftf", "STORAGE_DIR": str(tmp_path),
        "ACTIVE_CHECKPOINT": "clients/c1/runs/r0/checkpoints/ckpt_002.json",
    }.items():
        monkeypatch.setenv(k, v)
    compute.main()
    first = tmp_path / "clients/c1/runs/r1/checkpoints/ckpt_000.json"
    assert json.loads(first.read_text())["resumed_from"] == 2
