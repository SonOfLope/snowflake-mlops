import json

import pandas as pd

from jobs import train
from luckml import data, registry, session
from luckml.features import FEATURE_COLUMNS


def _bad_frame():
    months = pd.date_range("2025-01-01", periods=12, freq="MS")
    rows = []
    for site in (101, 102):
        for i, m in enumerate(months):
            tonnes = 1000.0 if i < 9 else 10.0
            rows.append(
                {"SITE_ID": site, "MONTH": m, "TONNES": tonnes, "LAG_1": 1000.0, "LAG_2": 1000.0,
                 "LAG_3": 1000.0, "MONTH_NUM": m.month}
            )
    return pd.DataFrame(rows)


def test_train_main_fails_gate_without_logging(monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(session, "connect", lambda cfg: object())
    monkeypatch.setattr(data, "load_feature_frame", lambda s, cfg: _bad_frame())
    monkeypatch.setattr(registry, "version_exists", lambda s, cfg, v: False)
    monkeypatch.setattr(registry, "log", lambda *a, **k: calls.append(a))
    monkeypatch.setattr(train, "write_run_log", lambda *a, **k: None)
    monkeypatch.setattr(train.forecast, "write", lambda *a, **k: calls.append(a))
    rc = train.main(["--env", "dev", "--version", "VTEST", "--run-id", "t1"])
    last = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert rc == 1
    assert last["gate"] is False and last["version"] == "VTEST" and "wape" in last
    assert calls == []


def _good_frame():
    months = pd.date_range("2025-01-01", periods=12, freq="MS")
    return pd.DataFrame(
        [{"SITE_ID": site, "MONTH": m, "TONNES": 1000.0 + i, "LAG_1": 1000.0, "LAG_2": 1000.0, "LAG_3": 1000.0, "MONTH_NUM": m.month}
         for site in (101, 102) for i, m in enumerate(months)]
    )


def test_train_logs_a_model_refitted_on_the_full_history_after_the_gate(monkeypatch, capsys):
    fits, logged = [], []
    monkeypatch.setattr(session, "connect", lambda cfg: object())
    monkeypatch.setattr(data, "load_feature_frame", lambda s, cfg: _good_frame())
    monkeypatch.setattr(registry, "version_exists", lambda s, cfg, v: False)
    monkeypatch.setattr(registry, "log", lambda s, cfg, m, v, metrics, sample: logged.append((m, len(sample))))
    monkeypatch.setattr(train, "write_run_log", lambda *a, **k: None)
    monkeypatch.setattr(train.forecast, "write", lambda *a, **k: 0)
    real_fit = train.model.fit
    monkeypatch.setattr(train.model, "fit", lambda frame: fits.append(len(frame)) or real_fit(frame))
    assert train.main(["--env", "dev", "--version", "VTEST", "--run-id", "t1"]) == 0
    assert fits == [18, 24]          # scored on a fit without the three held-out months, logged after a refit on all 24 rows
    assert logged[0][1] == 24
    last = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert last["gate"] is True and last["rows"] == 6


def test_train_writes_the_held_out_rows_from_the_fit_without_them(monkeypatch):
    fits, written = [], []
    monkeypatch.setattr(session, "connect", lambda cfg: object())
    monkeypatch.setattr(data, "load_feature_frame", lambda s, cfg: _good_frame())
    monkeypatch.setattr(registry, "version_exists", lambda s, cfg, v: False)
    monkeypatch.setattr(registry, "log", lambda *a, **k: None)
    monkeypatch.setattr(train, "write_run_log", lambda *a, **k: None)
    monkeypatch.setattr(train.forecast, "write", lambda s, cfg, rows, v, r, **k: written.append((rows, v, r, k)) or len(rows))
    real_fit = train.model.fit
    monkeypatch.setattr(train.model, "fit", lambda frame: fits.append(real_fit(frame)) or fits[-1])
    assert train.main(["--env", "dev", "--version", "VTEST", "--run-id", "t1"]) == 0
    rows, version, run_id, _ = written[0]
    assert (version, run_id, len(rows)) == ("VTEST", "t1", 6)
    assert list(rows["ACTUAL_TONNES"]) == [1009.0, 1010.0, 1011.0] * 2
    assert list(rows["FORECAST_TONNES"]) == list(fits[0].predict(rows[FEATURE_COLUMNS]))   # the fit that never saw these months


def test_train_writes_the_training_rows_scored_by_the_refit_as_the_versions_baseline(monkeypatch):
    fits, written = [], []
    monkeypatch.setattr(session, "connect", lambda cfg: object())
    monkeypatch.setattr(data, "load_feature_frame", lambda s, cfg: _good_frame())
    monkeypatch.setattr(registry, "version_exists", lambda s, cfg, v: False)
    monkeypatch.setattr(registry, "log", lambda *a, **k: None)
    monkeypatch.setattr(train, "write_run_log", lambda *a, **k: None)
    monkeypatch.setattr(train.forecast, "write", lambda s, cfg, rows, v, r, **k: written.append((rows, v, k)) or len(rows))
    real_fit = train.model.fit
    monkeypatch.setattr(train.model, "fit", lambda frame: fits.append(real_fit(frame)) or fits[-1])
    assert train.main(["--env", "dev", "--version", "VTEST", "--run-id", "t1"]) == 0
    rows, version, _ = next(w for w in written if w[2].get("table") == "BASELINE_SITE_MONTH")
    assert version == "VTEST" and len(rows) == 24
    assert list(rows["FORECAST_TONNES"]) == list(fits[1].predict(rows[FEATURE_COLUMNS]))   # the refit, what the version will produce
    assert list(rows["ACTUAL_TONNES"]) == list(_good_frame()["TONNES"])
