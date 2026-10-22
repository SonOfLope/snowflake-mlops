import pytest

from luckml import config


def test_load_dev_config():
    cfg = config.load("dev")
    assert cfg.database == "DEV_ML_DB"
    assert cfg.role == "RBAC_ML_DEPLOYER_DEV"
    assert cfg.gate_mape_max == 0.35
    assert cfg.regression_tolerance == 0.10


def test_unknown_env_raises():
    with pytest.raises(FileNotFoundError):
        config.load("qa")
