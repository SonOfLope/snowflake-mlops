from types import SimpleNamespace

from luckml import config, registry


class FakeRegistry:
    def __init__(self, names, default=None):
        self._names = names
        self._default = default

    def models(self):
        return [SimpleNamespace(name=n) for n in self._names]

    def get_model(self, name):
        if name not in self._names:
            raise ValueError(f"Unable to find model {name}")
        return SimpleNamespace(default=SimpleNamespace(version_name=self._default))


def test_default_version_is_none_before_the_first_model(monkeypatch):
    cfg = config.load("prod")
    monkeypatch.setattr(registry, "open", lambda s, c: FakeRegistry([]))
    assert registry.default_version(None, cfg) is None


def test_default_version_reads_the_default_once_a_model_exists(monkeypatch):
    cfg = config.load("prod")
    monkeypatch.setattr(registry, "open", lambda s, c: FakeRegistry([cfg.model_name], default="M202612030600"))
    assert registry.default_version(None, cfg) == "M202612030600"
