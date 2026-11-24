"""
Backend Sentry settings: an error event must carry the error, never the
request body or stack-frame locals that hold a user's idea or conversation,
and never a share-link token or query string from the request URL.

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
from app.core.error_tracking import (
    init_error_tracking,
    scrub_breadcrumb,
    scrub_event,
    scrub_url,
    sentry_options,
)

BACKEND = Path(__file__).resolve().parents[1]
DSN = "https://public@o1.ingest.sentry.io/1"
MARKER = "MARKER-my-secret-startup-idea"
LOGGED_EMAIL = "MARKER-person@example.com"
SHARE_TOKEN = "SHARETOKEN-Zx81kLm"
QUERY_SECRET = "QUERYSECRET-oauth-code"


def make_settings(dsn: str = DSN) -> Settings:
    return Settings(DATABASE_URL="sqlite+aiosqlite:///:memory:", SENTRY_DSN=dsn)


def test_options_keep_bodies_locals_and_pii_out():
    opts = sentry_options(make_settings())
    assert opts["send_default_pii"] is False
    assert opts["max_request_body_size"] == "never"
    assert opts["include_local_variables"] is False
    assert opts["before_send"] is scrub_event
    assert opts["before_send_transaction"] is scrub_event
    assert opts["before_breadcrumb"] is scrub_breadcrumb
    assert opts["dsn"] == DSN


def test_scrub_url_masks_share_tokens_and_drops_queries():
    api = "https://backend-production-9c212.up.railway.app/api/v1"
    assert scrub_url(f"{api}/sharing/public/tok9/ratings?x=1#f") == f"{api}/sharing/public/[token]/ratings"
    assert scrub_url("https://myide.ai/shared/tok9") == "https://myide.ai/shared/[token]"
    assert scrub_url(f"{api}/integrations/notion/callback?code=c&state=s") == f"{api}/integrations/notion/callback"
    assert scrub_url(f"{api}/projects/0b1c") == f"{api}/projects/0b1c"


def test_scrub_event_keeps_method_and_url_only_and_scrubs_breadcrumbs():
    event = {
        "request": {"method": "GET", "url": "http://x/api/v1/sharing/public/tok9", "query_string": "code=c",
                    "headers": {"Referer": "https://myide.ai/shared/tok9"}, "env": {"REMOTE_ADDR": "203.0.113.9"}},
        "breadcrumbs": {"values": [
            {"type": "log", "category": "app.routers.clerk_webhook", "message": "User created: a@b.example"},
            {"category": "httplib", "data": {"url": "https://api.example/v1?key=k", "http.query": "key=k"}},
        ]},
    }
    out = scrub_event(event)
    assert out["request"] == {"method": "GET", "url": "http://x/api/v1/sharing/public/[token]"}
    assert out["breadcrumbs"]["values"] == [{"category": "httplib", "data": {"url": "https://api.example/v1"}}]
    assert scrub_event({"message": "no request"}) == {"message": "no request"}


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
import json, logging, os, sys
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
    logging.getLogger("app.routers.clerk_webhook").warning("User created: %s", os.environ["SENTRY_TEST_EMAIL"])
    payload = await request.json()
    idea = payload["text"]
    raise RuntimeError("boom while handling an idea of %d characters" % len(idea))

@app.get("/api/v1/sharing/public/{token}/comments")
async def shared(token: str):
    raise RuntimeError("boom while opening a share link")

client = TestClient(app, raise_server_exceptions=False)
client.post("/boom", json={"text": os.environ["SENTRY_TEST_MARKER"]})
client.get("/api/v1/sharing/public/%s/comments?code=%s"
           % (os.environ["SENTRY_TEST_TOKEN"], os.environ["SENTRY_TEST_QUERY"]))
sentry_sdk.flush()
print(json.dumps(capture.payloads))
"""


def capture_events(mode: str) -> list[str]:
    # The marker goes in through the environment, not argv: Sentry records
    # sys.argv on every event, which would "leak" it whatever the options.
    env = {**os.environ, "SENTRY_TEST_MARKER": MARKER, "SENTRY_TEST_EMAIL": LOGGED_EMAIL,
           "SENTRY_TEST_TOKEN": SHARE_TOKEN, "SENTRY_TEST_QUERY": QUERY_SECRET}
    env.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")  # app.core.config needs one
    result = subprocess.run(
        [sys.executable, "-c", SCRIPT, mode, DSN],
        cwd=BACKEND, env=env, capture_output=True, text=True, timeout=60, check=False,
    )
    assert result.returncode == 0, result.stderr[-2000:]
    return json.loads(result.stdout.strip().splitlines()[-1])


@pytest.fixture(scope="module")
def captured() -> dict[str, list[str]]:
    return {mode: capture_events(mode) for mode in ("defaults", "ours")}


@pytest.mark.parametrize("mode, leaks", [("defaults", True), ("ours", False)])
def test_error_event_never_holds_the_request_or_locals(captured, mode, leaks):
    events = [p for p in captured[mode] if "an idea of" in p]
    assert events, f"no error event was captured ({mode}); the test would prove nothing"
    assert (MARKER in "".join(events)) is leaks


@pytest.mark.parametrize("mode, leaks", [("defaults", True), ("ours", False)])
def test_error_event_never_holds_log_breadcrumbs(captured, mode, leaks):
    # Log lines become breadcrumbs by default; some log an email or model output.
    events = [p for p in captured[mode] if "an idea of" in p]
    assert events, f"no error event was captured ({mode}); the test would prove nothing"
    assert (LOGGED_EMAIL in "".join(events)) is leaks


@pytest.mark.parametrize("mode, leaks", [("defaults", True), ("ours", False)])
def test_error_event_masks_share_tokens_and_drops_query_strings(captured, mode, leaks):
    events = [p for p in captured[mode] if "share link" in p]
    assert events, f"no share-link error event was captured ({mode}); the test would prove nothing"
    sent = "".join(events)
    assert (SHARE_TOKEN in sent) is leaks
    assert (QUERY_SECRET in sent) is leaks
    if not leaks:
        assert "/sharing/public/[token]/comments" in sent  # the route is still identifiable
