# Database backup: a Railway cron service

Every night `backup.py` dumps the production PostgreSQL database with `pg_dump`, checks the dump's
table of contents (`pg_restore --list` must list at least one table with data), uploads it to a
**private** S3-compatible bucket, checks the stored size, and deletes all but the newest 30 dumps. The
nightly check does not read table rows: only the restore drill below restores the data and reads it.
Any problem, including a missing setting or a `pg_dump` that waits more than 5 minutes for a lock or
runs past 2 hours, ends the run with exit code 1, and an optional heartbeat monitor emails when a
night fails or never runs.

It replaces `.github/workflows/db-backup.yml`. That workflow never produced a backup (its secret was
never set, and it skipped the dump while reporting success), and on this public repository its
artifact would have been downloadable by anyone signed in to GitHub.

## One-time setup (Railway dashboard, Ide/AI project)

1. **Bucket.** Create → Bucket, named `ideai-backups`, in the region nearest Postgres (US East).
   Railway buckets are private: only their credentials can read them.
2. **Service.** Create → GitHub Repo → `Vybecode-LTD/Ide_AI`, named `db-backup`. In Settings → Source,
   set Root Directory to `/ops/db-backup`. It builds from this folder's `Dockerfile`. Give it no public
   domain.
3. **Variables** on `db-backup`, all as references, so no value is ever copied:

   | Variable | Set it to |
   |---|---|
   | `BACKUP_DATABASE_URL` | `${{Postgres.DATABASE_URL}}` |
   | `BACKUP_S3_BUCKET`, `BACKUP_S3_ENDPOINT`, `BACKUP_S3_ACCESS_KEY_ID`, `BACKUP_S3_SECRET_ACCESS_KEY`, `BACKUP_S3_REGION` | The bucket's matching credential: type `${{ideai-backups.` and pick it from the list |
   | `BACKUP_S3_URL_STYLE` | `virtual`, or `path` if the bucket's Credentials tab says so |
   | `BACKUP_HEARTBEAT_URL` | Optional, recommended: step 5 |
   | `BACKUP_KEEP` | Optional: how many dumps to keep (default 30) |

4. **Check the schedule.** Settings → Deploy should show Cron Schedule `0 7 * * *` (07:00 UTC, 02:00
   Eastern) and Restart Policy "Never", from `railway.toml`. If either is missing, set it there:
   Railway doesn't always apply the file.
5. **Heartbeat.** Create a free check at [healthchecks.io](https://healthchecks.io) (any monitor with
   ping URLs and a `/fail` suffix works): period 1 day, grace 2 hours, email alerts on. Put its ping
   URL in `BACKUP_HEARTBEAT_URL`. Each run pings it on success and `<url>/fail` on failure, so a failed
   night and a night that never ran both send an email. Without it, a failed run shows only as a
   failed deployment in Railway.
6. **First run.** Deploy the service and start one run (or set the schedule a few minutes ahead, then
   back). Its log should end with
   `Backup OK: postgres/ideai-<UTC time>.dump, <bytes> bytes, <n> tables with data.`
   Then do the restore drill below once.

Railway's own volume backups for the Postgres service (Postgres → Backups) are a separate layer and
worth keeping on. The bucket lives in the same Railway account as the database; for a copy outside
Railway, point the same variables at any private S3-compatible bucket (Cloudflare R2, Backblaze B2).

## Restore drill (once after the first backup, then every quarter)

A backup is only proven once it has been restored. On a PC with PostgreSQL client tools 17 or newer
(`pg_restore --version`) and Python 3.12, in PowerShell:

```powershell
createdb -h localhost -U postgres ideai_restore_drill
python -m venv "$env:LOCALAPPDATA\IdeAI\backup-venv"
& "$env:LOCALAPPDATA\IdeAI\backup-venv\Scripts\python.exe" -m pip install -r C:\DEV\Ide_AI\ops\db-backup\requirements.txt
```

Then, in the same window, set the four `BACKUP_S3_*` values from the bucket's Credentials tab
(`$env:BACKUP_S3_BUCKET = "..."` and so on: this window only, never in a file). This window doesn't
see the service's variables, so if `db-backup` sets `BACKUP_PREFIX`, `BACKUP_S3_REGION` or
`BACKUP_S3_URL_STYLE`, set the same values here too (otherwise the defaults `postgres/`, `auto` and
`virtual` apply, and a different prefix would restore the wrong folder or find nothing). Then run:

```powershell
$env:RESTORE_DATABASE_URL = "postgresql://postgres@localhost:5432/ideai_restore_drill"
& "$env:LOCALAPPDATA\IdeAI\backup-venv\Scripts\python.exe" C:\DEV\Ide_AI\ops\db-backup\backup.py restore-check
```

It downloads the newest dump, checks its table of contents, restores it in one transaction, counts
the restored users and projects, and ends with
`Restore OK into the scratch database: <n> users, <n> projects, migration <id>.`
Close the window, then `dropdb -h localhost -U postgres ideai_restore_drill`.

Without `RESTORE_DATABASE_URL`, `restore-check` only downloads the newest dump and checks its table of
contents. It
refuses a target that already holds a table, and one that matches `BACKUP_DATABASE_URL` when that is
set. `pg_restore` runs without `--clean`, so it never drops anything.

## Settings

| Variable | Needed for | Meaning |
|---|---|---|
| `BACKUP_DATABASE_URL` | backup | The database to dump |
| `BACKUP_S3_BUCKET`, `BACKUP_S3_ENDPOINT`, `BACKUP_S3_ACCESS_KEY_ID`, `BACKUP_S3_SECRET_ACCESS_KEY` | both | The private bucket |
| `BACKUP_S3_REGION` | | Default `auto` |
| `BACKUP_S3_URL_STYLE` | | `virtual` (default) or `path` |
| `BACKUP_PREFIX` | | Folder in the bucket, default `postgres/` |
| `BACKUP_KEEP` | | Dumps to keep, default 30; at least 1 |
| `BACKUP_HEARTBEAT_URL` | | Monitor ping URL; pinged by `backup` only |
| `RESTORE_DATABASE_URL` | | `restore-check` only: an empty scratch database to restore into |

Only objects named `ideai-<UTC time>.dump` directly under the prefix are ever pruned or restored. No
log line prints a URL, password or key.

## Tests

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest
```

Two tests skip unless their tools are present: one runs the real `pg_dump`, `pg_restore` and `psql`
against two throwaway databases named by `BACKUP_TEST_DATABASE_URL` and
`BACKUP_TEST_RESTORE_DATABASE_URL` (the test empties the second one), and one builds a real boto3
client. CI (`.github/workflows/ci.yml`, job "Database backup") provides both and sets
`BACKUP_REQUIRE_INTEGRATION=1`, which turns those skips into failures.
