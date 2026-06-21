# Init Database Job

## What It Does

The `init-database` job creates the database schema required by the `persist` job.

It supports SQLite and PostgreSQL through the same database config shape used by `persist`. If the schema and tables already exist, the job skips them and validates that the database is ready.

## How To Run

Default configuration:

```bash
conda activate vezilka
python -m vezilka_text_scraper.jobs.init_database
```

Equivalent installed command:

```bash
conda activate vezilka
init-database
```

Start local PostgreSQL:

```bash
docker compose up -d postgres
```

Then set `database.type: postgresql` in the config and use the `POSTGRES_*` values from `.env`.

Override the default config path:

```bash
python -m vezilka_text_scraper.jobs.init_database configs/init_database.yaml
init-database configs/init_database.yaml
```

## Default Configuration

Default config path:

```text
configs/init_database.yaml
```

The job class owns this default through `InitDatabaseJob.default_config_path`.

## Configuration Fields

`database.type`
Database backend selected by YAML. Supported values are `sqlite`, `postgres`, and `postgresql`. `postgres` is normalized to `postgresql`.

Database connection details are loaded from `.env` through `shared/env_variables.py`.

For SQLite, use:

```text
SQLITE_DATABASE_PATH
```

For PostgreSQL, use:

```text
POSTGRES_HOST
POSTGRES_PORT
POSTGRES_USER
POSTGRES_PASSWORD
POSTGRES_DATABASE
POSTGRES_SCHEMA
```

## Created Tables

The job creates these tables when missing:

```text
articles
sections
wiki_categories
article_wiki_categories
source_categories
article_source_categories
```

If tables already exist, they are not recreated. If existing tables are missing required columns, final validation fails.

## Final Job Log

The job emits one final structured summary log.

On success, it logs at `INFO`, explicitly colored green when `LOG_COLOR=true`.

On failure, it logs at `ERROR`, explicitly colored red when `LOG_COLOR=true`.

The summary includes:

```text
Job
Status
Config
Database
DB URL
Schema made
Existing
Created
Duration
Reason, only on failure
```
