"""One Snowpark session per process: the job's own inside Snowflake, the pipeline token in CI, a named connection locally.

A named connection keeps its own role; the deployer role is taken only on the token path."""

import os

from snowflake.snowpark import Session
from snowflake.snowpark.context import get_active_session
from snowflake.snowpark.exceptions import SnowparkSessionException

from luckml.config import Config


def connect(cfg: Config) -> Session:
    try:
        return get_active_session()
    except SnowparkSessionException:
        token = os.environ.get("SNOWFLAKE_TOKEN")
    if token:
        builder = Session.builder.configs(
            {
                "account": os.environ["SNOWFLAKE_ACCOUNT"],
                "user": os.environ["SNOWFLAKE_USER"],
                "authenticator": "WORKLOAD_IDENTITY",
                "workload_identity_provider": "OIDC",
                "token": token,
                "role": cfg.role,
                "warehouse": cfg.warehouse,
                "database": cfg.database,
                "schema": "WORKSPACE",
            }
        )
        return builder.create()
    session = Session.builder.config("connection_name", os.environ.get("SNOWFLAKE_CONNECTION_NAME", "default")).create()
    session.use_warehouse(cfg.warehouse)
    session.use_database(cfg.database)
    session.use_schema("WORKSPACE")
    return session
