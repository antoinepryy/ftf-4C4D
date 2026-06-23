import threading

from app import dispatch


def test_enqueue_cloud_calls_delay(monkeypatch):
    calls = []

    class FakeTask:
        def delay(self, *a):
            calls.append(a)

    monkeypatch.setattr(dispatch, "get_settings",
                        lambda: type("S", (), dict(deploy_mode="cloud", local_workers=2))())
    monkeypatch.setattr("app.tasks.run_compute_task", FakeTask())
    dispatch.enqueue("r1", "c1")
    assert calls == [("r1", "c1")]


def test_enqueue_local_runs_in_thread(monkeypatch):
    seen = {}
    done = threading.Event()

    def fake_run(run_id, client_id):
        seen["args"] = (run_id, client_id)
        done.set()

    monkeypatch.setattr(dispatch, "get_settings",
                        lambda: type("S", (), dict(deploy_mode="local", local_workers=2))())
    monkeypatch.setattr("app.worker.run_compute", fake_run)
    dispatch._reset_executor()
    dispatch.enqueue("r2", "c2")
    assert done.wait(timeout=3)
    assert seen["args"] == ("r2", "c2")
