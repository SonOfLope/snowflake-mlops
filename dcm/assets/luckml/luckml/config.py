"""Per-environment settings read from config/<env>.yml."""

import os
from dataclasses import dataclass, fields
from pathlib import Path

import yaml


@dataclass(frozen=True)
class Config:
    env: str
    database: str
    schema: str
    source_database: str
    warehouse: str
    compute_pool: str
    role: str
    model_name: str
    feature_view: str
    feature_view_version: str
    gate_wape_max: float
    regression_tolerance: float
    risk_threshold: float
    retire_enabled: bool
    retain_versions: int
    horizon_months: int
    eval_months: int


def config_dir() -> Path:
    override = os.environ.get("LUCKML_CONFIG_DIR")
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[1] / "config"


def load(env: str) -> Config:
    path = config_dir() / f"{env}.yml"
    if not path.is_file():
        raise FileNotFoundError(f"no configuration for environment {env!r} at {path}")
    raw = yaml.safe_load(path.read_text())
    names = {f.name for f in fields(Config)}
    return Config(**{k: v for k, v in raw.items() if k in names})
