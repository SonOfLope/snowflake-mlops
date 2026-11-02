import pytest

from luckml import config


def test_load_dev_config():
    cfg = config.load("dev")
    assert cfg.database == "DEV_ML_DB"
    assert cfg.role == "RBAC_ML_DEPLOYER_DEV"
    assert cfg.gate_wape_max == 0.4
    assert cfg.regression_tolerance == 0.10
    assert cfg.risk_threshold == 0.20
    assert cfg.schema == "SALES_FORECASTING" and cfg.model_name == "SITE_TONNES_FORECAST"


def test_unknown_env_raises():
    with pytest.raises(FileNotFoundError):
        config.load("qa")
