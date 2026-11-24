# Ide/AI nightly database backup: a Railway cron service. See README.md.
# Build context is this folder (the service's root directory, ops/db-backup).

# The codename is pinned because the PGDG apt line below names it; a floating
# tag that rolls to a new Debian release would break the install.
FROM python:3.12-slim-bookworm

# pg_dump must be at least the server's major version. Railway's Postgres
# runs 17 (ghcr.io/railwayapp-templates/postgres-ssl:17). If the server is
# upgraded, raise this too, or every run fails with a version mismatch.
ARG PG_MAJOR=17

RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl \
 && install -d /usr/share/postgresql-common/pgdg \
 && curl -fsSL -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc \
      https://www.postgresql.org/media/keys/ACCC4CF8.asc \
 && echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] https://apt.postgresql.org/pub/repos/apt bookworm-pgdg main" \
      > /etc/apt/sources.list.d/pgdg.list \
 && apt-get update \
 && apt-get install -y --no-install-recommends "postgresql-client-${PG_MAJOR}" \
 && apt-get purge -y curl \
 && apt-get autoremove -y \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backup.py .

RUN useradd --create-home --uid 10001 backup
USER backup

# The cron runs this once per schedule; it must exit when done.
CMD ["python", "backup.py"]
