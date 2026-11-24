"""
Backend Sentry settings: an error event must carry the error, never the
request body or stack-frame locals that hold a user's idea or conversation.

The end-to-end test runs Sentry for real in a subprocess (so its global
patches never touch the other tests), sends the event to a capturing
transport, and checks for a marker that was in the request. A positive
control with the SDK's defaults shows the marker does leak without our
options, so the test can tell the difference.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from app.core.config import Settings
from app.core.error_tracking import init_error_tracking, sentry_options

BACKEND = Path(__file__).resolve().parents[1]
DSN = "https://public@o1.ingest.sentry.io/1"
MARKER = "MARKER-my-secret-startup-idea"


def make_settings(dsn: str = DSN) -> Settings:
    return Settings(DATABASE_URL="sqlite+aiosqlite:///:memory:", SENTRY_DSN=dsn)


def test_options_keep_bodies_locals_and_pii_out():
    opts = sentry_options(make_settings())
    assert opts["send_default_pii"] is False
    assert opts["max_request_body_size"] == "never"
    assert opts["include_local_variables"] is False
    assert opts["dsn"] == DSN


def test_option_names_are_ones_the_sdk_accepts():
    import sentry_sdk

    client = sentry_sdk.Client(**sentry_options(make_settings()))  # unknown names raise TypeError
    try:
        assert client.options["max_request_body_size"] == "never"
        assert client.options["include_local_variables"] is False
    finally:
        client.close()


def test_no_dsn_means_no_sentry(monkeypatch):
    import sentry_sdk

    def fail(**kwargs):
        raise AssertionError("sentry_sdk.init must not run without a DSN")

    monkeypatch.setattr(sentry_sdk, "init", fail)
    assert init_error_tracking(make_settings(dsn="")) is False


def test_dsn_starts_sentry_with_our_options(monkeypatch):
    import sentry_sdk

    calls = []
    monkeypatch.setattr(sentry_sdk, "init", lambda **kwargs: calls.append(kwargs))
    assert init_error_tracking(make_settings()) is True
    assert calls == [sentry_options(make_settings())]


SCRIPT = r"""
import json, os, sys
import sentry_sdk
from sentry_sdk.transport import Transport
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from app.core.config import Settings
from app.core.error_tracking import sentry_options

class Capture(Transport):
    def __init__(self):
        super().__init__()
        self.payloads = []

    def capture_envelope(self, envelope):
        self.payloads.append(envelope.serialize().decode("utf-8", "replace"))

settings = Settings(DATABASE_URL="sqlite+aiosqlite:///:memory:", SENTRY_DSN=sys.argv[2],
                    SENTRY_TRACES_SAMPLE_RATE=0.0)
if sys.argv[1] == "ours":
    options = sentry_options(settings)
else:  # the SDK's defaults, apart from PII
    options = {"dsn": settings.SENTRY_DSN, "send_default_pii": False}
capture = Capture()
sentry_sdk.init(transport=capture, **options)

app = FastAPI()

@app.post("/boom")
async def boom(request: Request):
    payload = await request.json()
    idea = payload["text"]
    raise RuntimeError("boom while handling an idea of %d characters" % len(idea))

TestClient(app, raise_server_exceptions=False).post("/boom", json={"text": os.environ["SENTRY_TEST_MARKER"]})
sentry_sdk.flush()
print(json.dumps(capture.payloads))
"""


def capture_events(mode: str) -> list[str]:
    # The marker goes in through the environment, not argv: Sentry records
    # sys.argv on every event, which would "leak" it whatever the options.
    env = {**os.environ, "SENTRY_TEST_MARKER": MARKER}
    env.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")  # app.core.config needs one
    result = subprocess.run(
        [sys.executable, "-c", SCRIPT, mode, DSN],
        cwd=BACKEND, env=env, capture_output=True, text=True, timeout=60, check=False,
    )
    assert result.returncode == 0, result.stderr[-2000:]
    return json.loads(result.stdout.strip().splitlines()[-1])


@pytest.mark.parametrize("mode, leaks", [("defaults", True), ("ours", False)])
def test_error_event_never_holds_the_request_or_locals(mode, leaks):
    payloads = capture_events(mode)
    events = [p for p in payloads if "RuntimeError" in p]
    assert events, f"no error event was captured ({mode}); the test would prove nothing"
    assert (MARKER in "".join(events)) is leaks
