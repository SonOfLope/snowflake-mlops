"""The Model Registry in <ENV>_ML_DB.MODELS."""

import lightgbm
import pandas as pd
from snowflake.ml.model import type_hints
from snowflake.ml.registry import Registry

from luckml.config import Config
from luckml.features import FEATURE_COLUMNS


def open(session, cfg: Config) -> Registry:
    return Registry(session=session, database_name=cfg.database, schema_name="MODELS")


def log(session, cfg: Config, m, version: str, metrics: dict, sample: pd.DataFrame):
    return open(session, cfg).log_model(
        m,
        model_name=cfg.model_name,
        version_name=version,
        metrics={k: v for k, v in metrics.items() if v is not None},
        sample_input_data=sample[FEATURE_COLUMNS].head(10),
        task=type_hints.Task.TABULAR_REGRESSION,
        conda_dependencies=[f"lightgbm=={lightgbm.__version__}"],
        target_platforms=["WAREHOUSE"],
        comment="Monthly site tonnes, LightGBM on lags 1 to 3 and the month number.",
    )


def version_exists(session, cfg: Config, version: str) -> bool:
    reg = open(session, cfg)
    if not any(m.name.upper() == cfg.model_name.upper() for m in reg.models()):
        return False
    return any(v.version_name.upper() == version.upper() for v in reg.get_model(cfg.model_name).versions())


def get_version(session, cfg: Config, version: str):
    return open(session, cfg).get_model(cfg.model_name).version(version)


def default_version(session, cfg: Config) -> str:
    return open(session, cfg).get_model(cfg.model_name).default.version_name
