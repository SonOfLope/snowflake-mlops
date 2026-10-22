"""One Snowpark session per process: the job's own inside Snowflake, a named connection locally.

A named connection keeps its own role."""

import os

from snowflake.snowpark import Session
from snowflake.snowpark.context import get_active_session
from snowflake.snowpark.exceptions import SnowparkSessionException

from luckml.config import Config


def connect(cfg: Config) -> Session:
    try:
        return get_active_session()
    except SnowparkSessionException:
        pass
    session = Session.builder.config("connection_name", os.environ.get("SNOWFLAKE_CONNECTION_NAME", "default")).create()
    session.use_warehouse(cfg.warehouse)
    session.use_database(cfg.database)
    session.use_schema("WORKSPACE")
    return session
