import types

import pytest

import spice_mcp.adapters.dune.extract as extract
from spice_mcp.adapters.dune.extract import _poll_execution


class _FakeResp:
    def __init__(self, status_code: int, json_obj):
        self.status_code = status_code
        self._json = json_obj

    def json(self):
        return self._json


def test_poll_execution_timeout(monkeypatch):
    # Make requests.get always return unfinished state
    def _fake_get(*_a, **_kw):
        return _FakeResp(200, {"is_execution_finished": False, "state": "PENDING"})
    monkeypatch.setattr(extract, "_http_get", _fake_get)

    # Control time progression to trigger timeout quickly
    t0 = 1000.0
    times = [t0]

    def fake_time():
        # each call advances time by 0.6s
        times[0] += 0.6
        return times[0]

    monkeypatch.setattr(extract, "time", types.SimpleNamespace(time=fake_time, sleep=lambda s: None))

    with pytest.raises(TimeoutError):
        _poll_execution(
            {"execution_id": "e1"},
            api_key="k",
            poll_interval=0.1,
            verbose=False,
            timeout_seconds=1.0,
        )
