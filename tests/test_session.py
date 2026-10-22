from snowflake.snowpark.exceptions import SnowparkSessionException

from luckml import config, session


class FakeSession:
    def __init__(self):
        self.calls = []

    def use_role(self, r):
        self.calls.append(("role", r))

    def use_warehouse(self, w):
        self.calls.append(("warehouse", w))

    def use_database(self, d):
        self.calls.append(("database", d))

    def use_schema(self, s):
        self.calls.append(("schema", s))


class FakeBuilder:
    def __init__(self):
        self.conf = {}

    def config(self, k, v):
        self.conf[k] = v
        return self

    def configs(self, d):
        self.conf.update(d)
        return self

    def create(self):
        return FakeSession()


class FakeSessionClass:
    builder = FakeBuilder()


def test_named_connection_keeps_the_connections_role(monkeypatch):
    monkeypatch.setenv("SNOWFLAKE_CONNECTION_NAME", "mine")
    monkeypatch.setattr(session, "get_active_session", lambda: (_ for _ in ()).throw(SnowparkSessionException("none")))
    monkeypatch.setattr(session, "Session", FakeSessionClass)
    s = session.connect(config.load("dev"))
    assert FakeSessionClass.builder.conf["connection_name"] == "mine"
    assert ("role", "RBAC_ML_DEPLOYER_DEV") not in s.calls
    assert ("warehouse", "ML_WH") in s.calls and ("database", "DEV_ML_DB") in s.calls
