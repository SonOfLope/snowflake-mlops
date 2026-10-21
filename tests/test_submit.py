from luckml import config, session, submit


class FakeJob:
    id = "DEV_ML_DB.WORKSPACE.JOB_1"
    status = "DONE"

    def __init__(self):
        self.waits = []

    def wait(self, timeout=None):
        self.waits.append(timeout)
        return "DONE"

    def get_logs(self):
        return 'starting\n{"version": "V1", "mape": 0.2, "gate": true}'


def test_submit_run_waits_on_one_session(monkeypatch):
    sessions = []
    job = FakeJob()
    monkeypatch.setattr(session, "connect", lambda cfg: sessions.append(object()) or sessions[-1])
    captured = {}

    def fake_submit(path, pool, **kwargs):
        captured.update(path=path, pool=pool, **kwargs)
        return job

    monkeypatch.setattr(submit, "submit_from_stage", fake_submit)
    out = submit.run(config.load("dev"), "train", "V1", "run1", "b1")
    assert len(sessions) == 1
    assert job.waits == [1800]
    assert out["version"] == "V1" and out["gate"] is True
    assert captured["path"] == "@DEV_ML_DB.WORKSPACE.CODE/b1/"
    assert captured["pool"] == "ML_CPU_POOL"
    assert captured["entrypoint"] == "jobs/train.py"
    assert "imports" not in captured
