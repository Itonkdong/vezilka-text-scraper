# Persist Job

## What It Does

The `persist` job reads cleaned article records from `data/processed` and stores them in a SQL database.

It persists article metadata, cleaned text, sections, Wikipedia categories, source discovery categories, and article-category relationships. The job validates that the database connection, schema, tables, and required columns already exist before writing.

This job does not create or migrate database schema. Schema creation belongs to a separate init or migration job.

## How To Run

Default configuration:

```bash
conda activate vezilka
python -m vezilka_text_scraper.jobs.persist
```

Equivalent installed command:

```bash
conda activate vezilka
persist-wikipedia
```

Initialize the database before persisting:

```bash
conda activate vezilka
persist-wikipedia --with-init
```

Override the default config path:

```bash
python -m vezilka_text_scraper.jobs.persist configs/persist.yaml
persist-wikipedia configs/persist.yaml
```

## Default Configuration

Default config path:

```text
configs/persist.yaml
```

The job class owns this default through `WikipediaPersistJob.default_config_path`.

## Configuration Fields

`input_path`
Path to a cleaned processed JSONL file. When `null`, the newest `data/processed/*.jsonl` file is used.

`article_limit`
Optional number of records to persist from the start of the processed file. When `null`, all records are persisted.

`batch_size`
Number of cleaned JSONL records to read and persist in one database transaction.

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

`--with-init`
Optional CLI flag that runs database initialization before persistence using the same database config from `configs/persist.yaml`. If everything already exists, initialization skips existing objects and persist continues.

## Required Database Tables

The job expects these tables to already exist:

```text
articles
sections
wiki_categories
article_wiki_categories
source_categories
article_source_categories
```

The job fails before writing if any table or required column is missing.

## Persistence Behavior

Articles are upserted by Wikipedia `page_id`.

When an existing article is updated, the job replaces that article's sections, Wikipedia category links, and source category links with the current cleaned JSONL record.

The job reads and persists records in batches. Each batch uses its own transaction. If batch N fails, that batch rolls back and the job fails, but earlier successful batches remain committed.

## Final Job Log

The job emits one final structured summary log.

On success, it logs at `INFO`, explicitly colored green when `LOG_COLOR=true`.

On failure, it logs at `ERROR`, explicitly colored red when `LOG_COLOR=true`.

The summary includes:

```text
Job
Status
Config
Input
Database
DB URL
Read
Inserted
Updated
Sections
Wiki links
Source links
With init
Batch size
Batches
Duration
Reason, only on failure
```
