"""Tests for backup.py.

Most tests replace the S3 bucket and the PostgreSQL tools with fakes, so they
need only pytest. Two need more and skip without it, unless
``BACKUP_REQUIRE_INTEGRATION=1`` (set in CI), which turns the skip into a
failure:

* ``test_real_tools_backup_and_restore`` runs the real pg_dump, pg_restore
  and psql against ``BACKUP_TEST_DATABASE_URL`` (a scratch database the test
  fills) and restores into ``BACKUP_TEST_RESTORE_DATABASE_URL`` (another
  scratch database the test empties first). Both must be throwaway.
* ``test_make_s3_client_with_real_boto3`` needs boto3 installed.
"""
from __future__ import annotations

import io
import os
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

import backup
from backup import BackupError, Config

REQUIRE_ALL = os.environ.get("BACKUP_REQUIRE_INTEGRATION") == "1"
NOW = datetime(2026, 11, 24, 7, 0, 0, tzinfo=timezone.utc)
DB_URL = "postgresql://postgres:hunter2-db-pass@postgres.railway.internal:5432/railway"
ENV = {
    "BACKUP_DATABASE_URL": DB_URL,
    "BACKUP_S3_BUCKET": "ideai-backups-abc123",
    "BACKUP_S3_ENDPOINT": "https://t3.storageapi.dev",
    "BACKUP_S3_ACCESS_KEY_ID": "AKID-not-real",
    "BACKUP_S3_SECRET_ACCESS_KEY": "s3cret-key-not-real",
}
SECRETS = ("hunter2-db-pass", DB_URL, "AKID-not-real", "s3cret-key-not-real")


def needs(condition: bool, reason: str) -> None:
    if not condition:
        if REQUIRE_ALL:
            pytest.fail(f"{reason} (BACKUP_REQUIRE_INTEGRATION=1 forbids skipping)")
        pytest.skip(reason)


# ── fakes ────────────────────────────────────────────────────────────────


class FakeS3:
    """Enough of a boto3 S3 client: objects held in a dict."""

    def __init__(self, objects: dict[str, bytes] | None = None, page_size: int = 2):
        self.objects = dict(objects or {})
        self.page_size = page_size
        self.deleted: list[str] = []
        self.short_by = 0  # make head_object under-report, to fake a bad upload

    def upload_file(self, filename: str, bucket: str, key: str) -> None:
        self.objects[key] = Path(filename).read_bytes()

    def head_object(self, Bucket: str, Key: str) -> dict:
        return {"ContentLength": len(self.objects[Key]) - self.short_by}

    def delete_object(self, Bucket: str, Key: str) -> None:
        del self.objects[Key]
        self.deleted.append(Key)

    def download_file(self, bucket: str, key: str, filename: str) -> None:
        Path(filename).write_bytes(self.objects[key])

    def get_paginator(self, name: str):
        assert name == "list_objects_v2"
        client = self

        class Paginator:
            def paginate(self, Bucket: str, Prefix: str):
                keys = sorted(k for k in client.objects if k.startswith(Prefix))
                for i in range(0, max(len(keys), 1), client.page_size):
                    chunk = keys[i : i + client.page_size]
                    yield {"Contents": [{"Key": k} for k in chunk]} if chunk else {}

        return Paginator()


class FakeTools:
    """Stands in for pg_dump, pg_restore and psql."""

    def __init__(self, *, dump_bytes: bytes = b"PGDMP fake archive", tables: int = 3,
                 fail: dict[str, tuple[int, str]] | None = None, psql_out: str = "2 1 033\n",
                 scratch_tables: str = "0"):
        self.dump_bytes = dump_bytes
        self.tables = tables
        self.fail = fail or {}
        self.psql_out = psql_out
        self.scratch_tables = scratch_tables  # what the emptiness check sees
        self.calls: list[list[str]] = []

    def __call__(self, cmd):
        cmd = list(cmd)
        self.calls.append(cmd)
        name = cmd[0]
        if name == "pg_restore" and "--list" in cmd:
            name = "pg_restore --list"
        if name in self.fail:
            code, err = self.fail[name]
            return subprocess.CompletedProcess(cmd, code, "", err)
        if name == "pg_dump":
            out = next(a.split("=", 1)[1] for a in cmd if a.startswith("--file="))
            Path(out).write_bytes(self.dump_bytes)
            return subprocess.CompletedProcess(cmd, 0, "", "")
        if name == "pg_restore --list":
            lines = [";", "; Archive created at 2026-11-24"]
            lines += [f"{3000 + i}; 0 16390 TABLE DATA public t{i} postgres" for i in range(self.tables)]
            lines += ["215; 1259 16391 TABLE public t0 postgres"]
            return subprocess.CompletedProcess(cmd, 0, "\n".join(lines) + "\n", "")
        if name == "psql":
            if any("pg_tables" in a for a in cmd):
                return subprocess.CompletedProcess(cmd, 0, self.scratch_tables + "\n", "")
            return subprocess.CompletedProcess(cmd, 0, self.psql_out, "")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    def ran(self, name: str) -> list[list[str]]:
        return [c for c in self.calls if c[0] == name]


def make_config(**overrides) -> Config:
    return Config(**{**{
        "database_url": DB_URL,
        "bucket": "ideai-backups-abc123",
        "endpoint": "https://t3.storageapi.dev",
        "access_key_id": "AKID-not-real",
        "secret_access_key": "s3cret-key-not-real",
    }, **overrides})


def key_at(ts: datetime, prefix: str = "postgres/") -> str:
    return backup.object_key(prefix, ts)


# ── settings ─────────────────────────────────────────────────────────────


def test_missing_settings_are_all_named_and_nothing_is_backed_up():
    with pytest.raises(BackupError) as err:
        backup.load_config({})
    message = str(err.value)
    for name in backup.REQUIRED:
        assert name in message
    assert "Nothing was backed up" in message


def test_blank_setting_counts_as_missing():
    env = {**ENV, "BACKUP_S3_SECRET_ACCESS_KEY": "   "}
    with pytest.raises(BackupError, match="BACKUP_S3_SECRET_ACCESS_KEY"):
        backup.load_config(env)


def test_defaults_and_prefix_normalisation():
    cfg = backup.load_config({**ENV, "BACKUP_PREFIX": "nightly"})
    assert (cfg.keep, cfg.region, cfg.url_style, cfg.prefix) == (30, "auto", "virtual", "nightly/")
    assert backup.load_config(ENV).prefix == "postgres/"


@pytest.mark.parametrize("value", ["0", "-3", "ten", "2.5"])
def test_bad_keep_is_refused(value):
    with pytest.raises(BackupError, match="BACKUP_KEEP"):
        backup.load_config({**ENV, "BACKUP_KEEP": value})


def test_bad_url_style_is_refused():
    with pytest.raises(BackupError, match="URL_STYLE"):
        backup.load_config({**ENV, "BACKUP_S3_URL_STYLE": "dns"})


# ── naming, pruning, redaction ──────────────────────────────────────────


def test_object_key_is_utc_and_sorts_by_time():
    eastern = timezone(timedelta(hours=-5))
    assert backup.object_key("postgres/", datetime(2026, 11, 24, 2, 0, tzinfo=eastern)) == \
        "postgres/ideai-20261124T070000Z.dump"
    keys = [key_at(NOW - timedelta(days=d)) for d in (0, 10, 3)]
    assert sorted(keys) == [key_at(NOW - timedelta(days=10)), key_at(NOW - timedelta(days=3)), key_at(NOW)]
    assert backup.dump_time(key_at(NOW)) == NOW


def test_prune_keeps_the_newest_and_touches_nothing_else():
    ours = [key_at(NOW - timedelta(days=d)) for d in range(5)]
    foreign = [
        "postgres/notes.txt",
        "postgres/archive/ideai-20200101T000000Z.dump",  # nested: not ours to prune
        "other/ideai-20200101T000000Z.dump",              # another prefix
        "postgres/ideai-20200101T000000Z.dump.partial",
    ]
    doomed = backup.keys_to_prune(ours + foreign, "postgres/", keep=2)
    assert doomed == sorted(ours)[:3]


def test_prune_never_returns_the_protected_key():
    future = key_at(NOW + timedelta(days=400))  # a clock-skewed object sorts after today's
    today = key_at(NOW)
    assert backup.keys_to_prune([future, today], "postgres/", keep=1, protect=today) == []


def test_prune_refuses_keep_below_one():
    with pytest.raises(BackupError):
        backup.keys_to_prune([key_at(NOW)], "postgres/", keep=0)


def test_redact_removes_urls_passwords_and_keys():
    cfg = make_config()
    text = f"could not connect: {DB_URL} (password hunter2-db-pass) key AKID-not-real/s3cret-key-not-real"
    clean = backup.redact(text, cfg.secrets())
    for secret in SECRETS:
        assert secret not in clean
    assert "[redacted]" in clean


@pytest.mark.parametrize("other, same", [
    ("postgresql://u2:other@postgres.railway.internal:5432/railway", True),
    ("postgresql://postgres:x@POSTGRES.railway.internal/railway", True),
    ("postgresql://ci@127.0.0.1:55433/restore_drill", False),
    ("postgresql://postgres:x@postgres.railway.internal:5432/scratch", False),
])
def test_same_database(other, same):
    assert backup.same_database(DB_URL, other) is same


# ── a backup run ─────────────────────────────────────────────────────────


def test_backup_dumps_verifies_uploads_and_prunes(tmp_path):
    old = {key_at(NOW - timedelta(days=d)): b"old" for d in range(1, 6)}
    s3 = FakeS3(old)
    tools = FakeTools()
    logs: list[str] = []
    key = backup.run_backup(make_config(keep=3), client=s3, run=tools, now=NOW, workdir=tmp_path, log=logs.append)

    assert key == "postgres/ideai-20261124T070000Z.dump"
    assert s3.objects[key] == tools.dump_bytes
    dump_cmd = tools.ran("pg_dump")[0]
    assert {"--format=custom", "--no-owner", "--no-privileges", f"--dbname={DB_URL}"} <= set(dump_cmd)
    assert len(s3.deleted) == 3 and key not in s3.deleted
    assert sorted(backup.our_dumps(s3.objects, "postgres/")) == [
        key_at(NOW - timedelta(days=2)), key_at(NOW - timedelta(days=1)), key
    ]
    assert "Backup OK" in logs[-1] and "3 tables with data" in logs[-1]
    assert not any(secret in line for line in logs for secret in SECRETS)


def test_pg_dump_failure_uploads_nothing_and_is_redacted(tmp_path):
    s3 = FakeS3()
    tools = FakeTools(fail={"pg_dump": (1, f'connection to "{DB_URL}" failed: password hunter2-db-pass rejected')})
    with pytest.raises(BackupError) as err:
        backup.run_backup(make_config(), client=s3, run=tools, now=NOW, workdir=tmp_path, log=print)
    assert "pg_dump failed" in str(err.value)
    assert "hunter2-db-pass" not in str(err.value) and DB_URL not in str(err.value)
    assert s3.objects == {}


def test_empty_dump_is_not_uploaded(tmp_path):
    s3 = FakeS3()
    with pytest.raises(BackupError, match="empty"):
        backup.run_backup(make_config(), client=s3, run=FakeTools(dump_bytes=b""), now=NOW, workdir=tmp_path, log=print)
    assert s3.objects == {}


def test_dump_without_table_data_is_not_uploaded(tmp_path):
    s3 = FakeS3()
    with pytest.raises(BackupError, match="no table data"):
        backup.run_backup(make_config(), client=s3, run=FakeTools(tables=0), now=NOW, workdir=tmp_path, log=print)
    assert s3.objects == {}


def test_unreadable_dump_is_not_uploaded(tmp_path):
    s3 = FakeS3()
    tools = FakeTools(fail={"pg_restore --list": (1, "pg_restore: error: input file does not appear to be a valid archive")})
    with pytest.raises(BackupError, match="pg_restore --list failed"):
        backup.run_backup(make_config(), client=s3, run=tools, now=NOW, workdir=tmp_path, log=print)
    assert s3.objects == {}


def test_short_upload_fails_and_prunes_nothing(tmp_path):
    old = {key_at(NOW - timedelta(days=d)): b"old" for d in range(1, 4)}
    s3 = FakeS3(old)
    s3.short_by = 1
    with pytest.raises(BackupError, match="expected"):
        backup.run_backup(make_config(keep=1), client=s3, run=FakeTools(), now=NOW, workdir=tmp_path, log=print)
    assert s3.deleted == []


# ── main(): exit codes, heartbeat, no secrets in output ─────────────────


@pytest.fixture
def wired(monkeypatch):
    """main() with the bucket and tools faked and heartbeat pings recorded."""
    s3, tools, pings = FakeS3(), FakeTools(), []

    class Response(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def urlopen(url, timeout):
        pings.append(url)
        return Response(b"OK")

    monkeypatch.setattr(backup, "make_s3_client", lambda cfg: s3)
    monkeypatch.setattr(backup, "run_command", tools)
    monkeypatch.setattr(backup.urllib.request, "urlopen", urlopen)
    return s3, tools, pings


def test_main_missing_settings_exits_1_and_pings_fail(wired, capsys):
    s3, tools, pings = wired
    code = backup.main(["backup"], env={"BACKUP_HEARTBEAT_URL": "https://hc-ping.com/abc"})
    err = capsys.readouterr().err
    assert code == 1
    assert "BACKUP FAILED (backup): Missing settings" in err
    assert pings == ["https://hc-ping.com/abc/fail"]
    assert tools.calls == [] and s3.objects == {}


def test_main_success_exits_0_and_pings(wired, capsys):
    s3, tools, pings = wired
    code = backup.main([], env={**ENV, "BACKUP_HEARTBEAT_URL": "https://hc-ping.com/abc"})
    out = capsys.readouterr().out
    assert code == 0
    assert len(backup.our_dumps(s3.objects, "postgres/")) == 1
    assert pings == ["https://hc-ping.com/abc"]
    assert "Backup OK" in out


def test_main_failure_output_never_holds_a_secret(wired, capsys):
    s3, tools, pings = wired
    tools.fail["pg_dump"] = (1, f"FATAL: could not connect with {DB_URL} / hunter2-db-pass")
    code = backup.main(["backup"], env=ENV)
    captured = capsys.readouterr()
    assert code == 1
    for secret in SECRETS:
        assert secret not in captured.out + captured.err
    assert "pg_dump failed" in captured.err


def test_main_unexpected_exception_still_exits_1(wired, monkeypatch, capsys):
    def boom(cfg):
        raise RuntimeError(f"endpoint refused AKID-not-real {DB_URL}")

    monkeypatch.setattr(backup, "make_s3_client", boom)
    assert backup.main(["backup"], env=ENV) == 1
    err = capsys.readouterr().err
    assert "RuntimeError" in err and "AKID-not-real" not in err and DB_URL not in err


def test_main_unknown_command_exits_1(wired, capsys):
    assert backup.main(["restore"], env=ENV) == 1
    assert "Unknown command" in capsys.readouterr().err


def test_heartbeat_failure_does_not_fail_the_backup(wired, monkeypatch):
    def down(url, timeout):
        raise OSError("monitor unreachable")

    monkeypatch.setattr(backup.urllib.request, "urlopen", down)
    assert backup.main([], env={**ENV, "BACKUP_HEARTBEAT_URL": "https://hc-ping.com/abc"}) == 0


# ── restore check ────────────────────────────────────────────────────────


def test_restore_check_with_no_dumps_fails(tmp_path):
    with pytest.raises(BackupError, match="No dumps"):
        backup.run_restore_check(make_config(), client=FakeS3({"postgres/x.txt": b"x"}), run=FakeTools(),
                                 now=NOW, workdir=tmp_path, log=print)


def test_restore_check_reads_the_newest_dump_without_restoring(tmp_path):
    newest = key_at(NOW - timedelta(hours=3))
    s3 = FakeS3({key_at(NOW - timedelta(days=2)): b"older", newest: b"newest"})
    tools = FakeTools()
    logs: list[str] = []
    assert backup.run_restore_check(make_config(), client=s3, run=tools, now=NOW, workdir=tmp_path, log=logs.append) == newest
    assert "3.0 hours old" in logs[0]
    assert [c for c in tools.calls if c[0] == "pg_restore" and "--list" not in c] == []
    assert "nothing was restored" in logs[-1]


def test_restore_check_refuses_the_production_database(tmp_path):
    s3 = FakeS3({key_at(NOW): b"dump"})
    cfg = make_config(restore_database_url="postgresql://admin:pw@postgres.railway.internal:5432/railway")
    tools = FakeTools()
    with pytest.raises(BackupError, match="Refusing"):
        backup.run_restore_check(cfg, client=s3, run=tools, now=NOW, workdir=tmp_path, log=print)
    assert [c for c in tools.calls if c[0] == "pg_restore" and "--list" not in c] == []


def test_restore_check_needs_only_the_bucket_settings():
    bucket_only = {k: v for k, v in ENV.items() if k != "BACKUP_DATABASE_URL"}
    assert backup.load_config(bucket_only, "restore-check").database_url == ""
    with pytest.raises(BackupError, match="BACKUP_DATABASE_URL"):
        backup.load_config(bucket_only, "backup")
    with pytest.raises(BackupError, match="Nothing was checked"):
        backup.load_config({"BACKUP_DATABASE_URL": DB_URL}, "restore-check")


def test_restore_check_refuses_a_database_that_is_not_empty(tmp_path):
    s3 = FakeS3({key_at(NOW): b"dump"})
    tools = FakeTools(scratch_tables="41")
    cfg = make_config(database_url="", restore_database_url="postgresql://ci@127.0.0.1:55433/restore_drill")
    with pytest.raises(BackupError, match="already holds 41 table"):
        backup.run_restore_check(cfg, client=s3, run=tools, now=NOW, workdir=tmp_path, log=print)
    assert [c for c in tools.calls if c[0] == "pg_restore" and "--list" not in c] == []


def test_restore_check_restores_into_scratch_and_counts(tmp_path):
    scratch = "postgresql://ci@127.0.0.1:55433/restore_drill"
    s3 = FakeS3({key_at(NOW): b"dump"})
    tools = FakeTools(psql_out="7 12 033\n")
    logs: list[str] = []
    backup.run_restore_check(make_config(restore_database_url=scratch), client=s3, run=tools, now=NOW,
                             workdir=tmp_path, log=logs.append)
    restore_cmd = [c for c in tools.calls if c[0] == "pg_restore" and "--list" not in c][0]
    assert {"--single-transaction", "--exit-on-error", "--no-owner", f"--dbname={scratch}"} <= set(restore_cmd)
    assert logs[-1] == "Restore OK into the scratch database: 7 users, 12 projects, migration 033."


# ── real tools and real boto3 ───────────────────────────────────────────


def _psql(url: str, sql: str) -> str:
    result = subprocess.run(["psql", url, "--no-psqlrc", "-v", "ON_ERROR_STOP=1", "-At", "-c", sql],
                            capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def test_real_tools_backup_and_restore(tmp_path):
    source = os.environ.get("BACKUP_TEST_DATABASE_URL", "")
    target = os.environ.get("BACKUP_TEST_RESTORE_DATABASE_URL", "")
    needs(bool(source and target), "BACKUP_TEST_DATABASE_URL and BACKUP_TEST_RESTORE_DATABASE_URL not set")
    assert not backup.same_database(source, target), "the two test databases must differ"

    _psql(source, "DROP TABLE IF EXISTS users, projects, alembic_version; "
                  "CREATE TABLE users (id serial PRIMARY KEY, email text); "
                  "CREATE TABLE projects (id serial PRIMARY KEY, user_id int REFERENCES users(id), name text); "
                  "CREATE TABLE alembic_version (version_num varchar(32) PRIMARY KEY); "
                  "INSERT INTO users (email) VALUES ('a@example.test'), ('b@example.test'); "
                  "INSERT INTO projects (user_id, name) VALUES (1, 'Idea'); "
                  "INSERT INTO alembic_version VALUES ('033');")
    _psql(target, "DROP SCHEMA public CASCADE; CREATE SCHEMA public;")

    s3 = FakeS3()
    logs: list[str] = []
    cfg = make_config(database_url=source, restore_database_url=target)
    key = backup.run_backup(cfg, client=s3, run=backup.run_command, now=NOW, workdir=tmp_path, log=logs.append)
    assert s3.objects[key][:5] == b"PGDMP"  # pg_dump's custom-format magic
    assert "3 tables with data" in logs[-1]

    restore_dir = tmp_path / "restore"
    restore_dir.mkdir()
    backup.run_restore_check(cfg, client=s3, run=backup.run_command, now=NOW, workdir=restore_dir, log=logs.append)
    assert logs[-1] == "Restore OK into the scratch database: 2 users, 1 projects, migration 033."
    assert _psql(target, "SELECT name FROM projects") == "Idea"


def test_make_s3_client_with_real_boto3():
    try:
        import boto3  # noqa: F401
    except ImportError:
        needs(False, "boto3 is not installed")
    client = backup.make_s3_client(make_config())
    assert client.meta.endpoint_url == "https://t3.storageapi.dev"
    assert client.meta.config.s3["addressing_style"] == "virtual"
    assert client.meta.region_name == "auto"
