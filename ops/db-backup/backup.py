"""
Nightly PostgreSQL backup for Ide/AI, run as a Railway cron service.

    pg_dump (custom format) -> check it reads back (pg_restore --list)
    -> upload to a private S3-compatible bucket -> prune old dumps
    -> optional heartbeat ping

Every problem ends the run with exit code 1, including a missing setting, so
a backup that did not happen never looks like one that did. (Audit finding
C-4: the old GitHub workflow skipped its dump on every run for months and
still reported success. On a public repository its artifact would also have
been downloadable by anyone signed in to GitHub.)

Usage:
    python backup.py                 take a backup (the cron's start command)
    python backup.py restore-check   download the newest dump and prove it
                                     restores (see README.md, "Restore drill")

Settings come from environment variables; see README.md for the list. No
value is ever printed: database URLs, passwords and keys are redacted from
every message.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence
from urllib.parse import urlsplit

BUCKET_SETTINGS = (
    "BACKUP_S3_BUCKET",
    "BACKUP_S3_ENDPOINT",
    "BACKUP_S3_ACCESS_KEY_ID",
    "BACKUP_S3_SECRET_ACCESS_KEY",
)
REQUIRED = ("BACKUP_DATABASE_URL",) + BUCKET_SETTINGS
# restore-check reads only the bucket; the production URL, when given, is
# used just to refuse restoring over it.
REQUIRED_FOR_RESTORE_CHECK = BUCKET_SETTINGS
DEFAULT_KEEP = 30
DEFAULT_PREFIX = "postgres/"
# Only objects named like this are ever pruned or restored, so a shared
# bucket or a mistyped prefix can never cost anything but our own dumps.
DUMP_NAME = re.compile(r"ideai-(\d{8}T\d{6}Z)\.dump")
STAMP_FORMAT = "%Y%m%dT%H%M%SZ"

Runner = Callable[[Sequence[str]], "subprocess.CompletedProcess[str]"]
Logger = Callable[[str], None]


class BackupError(Exception):
    """A failure with a message that is safe to print once redacted."""


@dataclass(frozen=True)
class Config:
    database_url: str
    bucket: str
    endpoint: str
    access_key_id: str
    secret_access_key: str
    region: str = "auto"
    url_style: str = "virtual"
    prefix: str = DEFAULT_PREFIX
    keep: int = DEFAULT_KEEP
    heartbeat_url: str = ""
    restore_database_url: str = ""

    def secrets(self) -> list[str]:
        """Every value that must never reach a log line."""
        values = [
            self.database_url,
            self.restore_database_url,
            self.access_key_id,
            self.secret_access_key,
            self.heartbeat_url,
        ]
        for url in (self.database_url, self.restore_database_url):
            password = _password(url)
            if password:
                values.append(password)
        return [v for v in values if v]


def _password(url: str) -> str:
    try:
        return urlsplit(url).password or ""
    except ValueError:
        return ""


def redact(text: str, secrets: Iterable[str]) -> str:
    """Replace every secret in ``text`` with ``[redacted]``, longest first."""
    for secret in sorted(set(secrets), key=len, reverse=True):
        if secret:
            text = text.replace(secret, "[redacted]")
    return text


def load_config(env: Mapping[str, str], command: str = "backup") -> Config:
    """Read the settings, or raise BackupError naming every missing one."""
    required = REQUIRED if command == "backup" else REQUIRED_FOR_RESTORE_CHECK
    missing = [name for name in required if not env.get(name, "").strip()]
    if missing:
        outcome = "Nothing was backed up." if command == "backup" else "Nothing was checked."
        raise BackupError("Missing settings: " + ", ".join(missing) + ". " + outcome)
    keep_raw = env.get("BACKUP_KEEP", "").strip() or str(DEFAULT_KEEP)
    try:
        keep = int(keep_raw)
    except ValueError:
        raise BackupError(f"BACKUP_KEEP must be a whole number, not {keep_raw!r}.") from None
    if keep < 1:
        raise BackupError("BACKUP_KEEP must be at least 1.")
    prefix = env.get("BACKUP_PREFIX", DEFAULT_PREFIX).strip()
    if prefix and not prefix.endswith("/"):
        prefix += "/"
    url_style = env.get("BACKUP_S3_URL_STYLE", "virtual").strip().lower() or "virtual"
    if url_style not in ("virtual", "path"):
        raise BackupError("BACKUP_S3_URL_STYLE must be 'virtual' or 'path'.")
    return Config(
        database_url=env.get("BACKUP_DATABASE_URL", "").strip(),
        bucket=env["BACKUP_S3_BUCKET"].strip(),
        endpoint=env["BACKUP_S3_ENDPOINT"].strip(),
        access_key_id=env["BACKUP_S3_ACCESS_KEY_ID"].strip(),
        secret_access_key=env["BACKUP_S3_SECRET_ACCESS_KEY"].strip(),
        region=env.get("BACKUP_S3_REGION", "").strip() or "auto",
        url_style=url_style,
        prefix=prefix,
        keep=keep,
        heartbeat_url=env.get("BACKUP_HEARTBEAT_URL", "").strip(),
        restore_database_url=env.get("RESTORE_DATABASE_URL", "").strip(),
    )


def object_key(prefix: str, now: datetime) -> str:
    """``<prefix>ideai-20261124T070000Z.dump``: names sort by time."""
    return f"{prefix}ideai-{now.astimezone(timezone.utc).strftime(STAMP_FORMAT)}.dump"


def our_dumps(keys: Iterable[str], prefix: str) -> list[str]:
    """Keys directly under ``prefix`` named like our dumps, oldest first."""
    return sorted(
        k for k in keys if k.startswith(prefix) and DUMP_NAME.fullmatch(k[len(prefix):])
    )


def keys_to_prune(keys: Iterable[str], prefix: str, keep: int, protect: str = "") -> list[str]:
    """The dumps beyond the newest ``keep``. ``protect`` is never returned."""
    if keep < 1:
        raise BackupError("Refusing to prune with keep < 1.")
    ours = our_dumps(keys, prefix)
    old = ours[:-keep] if len(ours) > keep else []
    return [k for k in old if k != protect]


def dump_time(key: str) -> datetime:
    match = DUMP_NAME.search(key)
    if not match:
        raise BackupError(f"Not a dump name: {key}")
    return datetime.strptime(match.group(1), STAMP_FORMAT).replace(tzinfo=timezone.utc)


def same_database(a: str, b: str) -> bool:
    """True when two connection URLs name the same host, port and database."""
    if not a or not b:
        return False
    if a == b:
        return True
    try:
        pa, pb = urlsplit(a), urlsplit(b)
        return (
            (pa.hostname or "").lower() == (pb.hostname or "").lower()
            and (pa.port or 5432) == (pb.port or 5432)
            and pa.path.strip("/") == pb.path.strip("/")
        )
    except ValueError:
        return False


def run_command(cmd: Sequence[str]) -> "subprocess.CompletedProcess[str]":
    return subprocess.run(list(cmd), capture_output=True, text=True, check=False)


def _check(result: "subprocess.CompletedProcess[str]", what: str, secrets: list[str]) -> None:
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()[-2000:]
        raise BackupError(f"{what} failed (exit {result.returncode}): {redact(detail, secrets)}")


def dump_database(cfg: Config, path: Path, run: Runner) -> None:
    result = run(
        [
            "pg_dump",
            "--format=custom",
            "--no-owner",
            "--no-privileges",
            f"--file={path}",
            f"--dbname={cfg.database_url}",
        ]
    )
    _check(result, "pg_dump", cfg.secrets())


def verify_dump(path: Path, run: Runner, secrets: list[str]) -> int:
    """Prove the archive reads back; return how many tables carry data."""
    if not path.exists() or path.stat().st_size == 0:
        raise BackupError("pg_dump wrote an empty file.")
    result = run(["pg_restore", "--list", str(path)])
    _check(result, "pg_restore --list", secrets)
    tables = sum(1 for line in result.stdout.splitlines() if " TABLE DATA " in line)
    if tables == 0:
        raise BackupError("The dump holds no table data.")
    return tables


def psql_value(run: Runner, url: str, sql: str, what: str, secrets: list[str]) -> str:
    """Run one query with psql and return its output, space-separated."""
    result = run(
        [
            "psql",
            url,
            "--no-psqlrc",
            "--tuples-only",
            "--no-align",
            "--field-separator= ",
            "--set=ON_ERROR_STOP=1",
            f"--command={sql}",
        ]
    )
    _check(result, what, secrets)
    return result.stdout.strip()


def make_s3_client(cfg: Config) -> Any:
    """A boto3 S3 client for any S3-compatible store (Railway, R2, B2...)."""
    import boto3  # imported here so the tests need only the standard library
    from botocore.config import Config as BotoConfig

    return boto3.client(
        "s3",
        endpoint_url=cfg.endpoint,
        aws_access_key_id=cfg.access_key_id,
        aws_secret_access_key=cfg.secret_access_key,
        region_name=cfg.region,
        config=BotoConfig(
            retries={"max_attempts": 5, "mode": "standard"},
            s3={"addressing_style": cfg.url_style},
            # Some S3-compatible stores reject the checksums newer boto3
            # sends by default; send them only where the API requires it.
            request_checksum_calculation="when_required",
            response_checksum_validation="when_required",
        ),
    )


def list_keys(client: Any, bucket: str, prefix: str) -> list[str]:
    keys: list[str] = []
    for page in client.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=prefix):
        keys.extend(obj["Key"] for obj in page.get("Contents", []))
    return keys


def upload(client: Any, cfg: Config, path: Path, key: str) -> None:
    client.upload_file(str(path), cfg.bucket, key)
    stored = client.head_object(Bucket=cfg.bucket, Key=key)["ContentLength"]
    expected = path.stat().st_size
    if stored != expected:
        raise BackupError(f"Uploaded {key} holds {stored} bytes, expected {expected}.")


def prune(client: Any, cfg: Config, protect: str) -> list[str]:
    doomed = keys_to_prune(list_keys(client, cfg.bucket, cfg.prefix), cfg.prefix, cfg.keep, protect)
    for key in doomed:
        client.delete_object(Bucket=cfg.bucket, Key=key)
    return doomed


def ping(url: str, ok: bool, log: Logger, opener: Callable[..., Any] | None = None) -> None:
    """Tell a dead-man's-switch monitor how the run went (healthchecks.io
    style: the URL on success, ``<url>/fail`` on failure). A ping that fails
    is logged and never changes the exit code."""
    opener = opener or urllib.request.urlopen
    target = url if ok else url.rstrip("/") + "/fail"
    try:
        with opener(target, timeout=10):
            pass
    except Exception as exc:  # noqa: BLE001 - the monitor is best-effort
        log(f"Heartbeat ping failed ({type(exc).__name__}).")


def run_backup(cfg: Config, *, client: Any, run: Runner, now: datetime, workdir: Path, log: Logger) -> str:
    key = object_key(cfg.prefix, now)
    path = workdir / "backup.dump"
    dump_database(cfg, path, run)
    tables = verify_dump(path, run, cfg.secrets())
    size = path.stat().st_size
    upload(client, cfg, path, key)
    pruned = prune(client, cfg, protect=key)
    log(
        f"Backup OK: {key}, {size} bytes, {tables} tables with data. "
        f"Pruned {len(pruned)} older dump(s); keeping the newest {cfg.keep}."
    )
    return key


def run_restore_check(cfg: Config, *, client: Any, run: Runner, now: datetime, workdir: Path, log: Logger) -> str:
    dumps = our_dumps(list_keys(client, cfg.bucket, cfg.prefix), cfg.prefix)
    if not dumps:
        raise BackupError(f"No dumps found under '{cfg.prefix}' in the bucket.")
    latest = dumps[-1]
    hours = (now - dump_time(latest)).total_seconds() / 3600
    path = workdir / "restore.dump"
    client.download_file(cfg.bucket, latest, str(path))
    secrets = cfg.secrets()
    tables = verify_dump(path, run, secrets)
    log(f"Newest dump {latest} ({hours:.1f} hours old, {len(dumps)} kept) reads back: {tables} tables with data.")
    if not cfg.restore_database_url:
        log("RESTORE_DATABASE_URL is not set, so nothing was restored. Set it to an empty scratch database to restore.")
        return latest
    if same_database(cfg.restore_database_url, cfg.database_url):
        raise BackupError("RESTORE_DATABASE_URL names the production database. Refusing to restore over it.")
    existing = psql_value(
        run,
        cfg.restore_database_url,
        "SELECT count(*) FROM pg_catalog.pg_tables "
        "WHERE schemaname NOT IN ('pg_catalog', 'information_schema')",
        "Checking the scratch database is empty",
        secrets,
    )
    if existing != "0":
        raise BackupError(
            f"The scratch database already holds {existing} table(s). "
            "Restore only into an empty database; refusing."
        )
    restored = run(
        [
            "pg_restore",
            "--no-owner",
            "--no-privileges",
            "--exit-on-error",
            "--single-transaction",
            f"--dbname={cfg.restore_database_url}",
            str(path),
        ]
    )
    _check(restored, "pg_restore into the scratch database", secrets)
    counted = psql_value(
        run,
        cfg.restore_database_url,
        "SELECT (SELECT count(*) FROM users), (SELECT count(*) FROM projects), "
        "(SELECT version_num FROM alembic_version)",
        "Counting rows in the restored copy",
        secrets,
    )
    users, projects, revision = (counted.split() + ["?", "?", "?"])[:3]
    log(f"Restore OK into the scratch database: {users} users, {projects} projects, migration {revision}.")
    return latest


def main(argv: Sequence[str] | None = None, env: Mapping[str, str] | None = None) -> int:
    env = os.environ if env is None else env
    args = list(sys.argv[1:] if argv is None else argv)
    command = args[0] if args else "backup"

    def log(message: str) -> None:
        print(message, flush=True)

    def log_error(message: str) -> None:
        print(message, file=sys.stderr, flush=True)

    heartbeat = env.get("BACKUP_HEARTBEAT_URL", "").strip() if command == "backup" else ""
    secrets = [env.get(name, "") for name in REQUIRED + ("RESTORE_DATABASE_URL", "BACKUP_HEARTBEAT_URL")]
    try:
        if command not in ("backup", "restore-check"):
            raise BackupError(f"Unknown command {command!r}. Use 'backup' or 'restore-check'.")
        cfg = load_config(env, command)
        secrets = cfg.secrets()
        client = make_s3_client(cfg)
        step = run_backup if command == "backup" else run_restore_check
        with tempfile.TemporaryDirectory() as tmp:
            step(cfg, client=client, run=run_command, now=datetime.now(timezone.utc), workdir=Path(tmp), log=log)
    except Exception as exc:  # noqa: BLE001 - any failure must exit 1, redacted
        reason = exc if isinstance(exc, BackupError) else f"{type(exc).__name__}: {exc}"
        log_error(f"BACKUP FAILED ({command}): {redact(str(reason), secrets)}")
        if heartbeat:
            ping(heartbeat, ok=False, log=log_error)
        return 1
    if heartbeat:
        ping(heartbeat, ok=True, log=log)
    return 0


if __name__ == "__main__":
    sys.exit(main())
