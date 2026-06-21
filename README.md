# Vezilka Text Scraper

Vezilka Text Scraper builds a Macedonian Wikipedia corpus for the Vezilka project. It scrapes raw article data, cleans MediaWiki markup into readable Macedonian text, optionally persists the corpus to SQLite or PostgreSQL, and can display samples for manual inspection.

The project is organized as small jobs that can be run independently or through one full pipeline. Job behavior is controlled by YAML files in `configs/`; runtime/environment concerns such as logging and database connection values are controlled through `.env`.

## Setup

Use the project conda environment:

```bash
conda env create -f environment.yml
conda activate vezilka
cp .env.example .env
```

Install the package in editable mode when working locally:

```bash
pip install -e ".[dev]"
```

Start the PostgreSQL service:

```bash
docker compose up -d --build postgres
```

Once the database is running, execute the full Wikipedia ingestion pipeline:

```bash
pipeline-wikipedia
```

This command runs the complete pipeline, including category discovery, article collection, text cleaning, metadata extraction, and database ingestion.

## Docker

Default Docker Compose starts PostgreSQL and runs the full pipeline job:

```bash
cp .env.example .env
docker compose up --build
```

The app container reads configs from `configs/` and writes outputs to `data/` and `logs/`.

Override the job:

```bash
VEZILKA_JOB=clean-wikipedia docker compose up --build app
```

Pass job arguments, such as a custom config path:

```bash
VEZILKA_JOB=scrape-wikipedia VEZILKA_JOB_ARGS="configs/scrape.yaml" docker compose up --build app
```

## Jobs

`scrape`
Discovers articles from approved Macedonian Wikipedia categories and writes raw JSONL records to `data/raw`. Details: [docs/desc/scrape.md](docs/desc/scrape.md).

`clean`
Reads raw JSONL, removes MediaWiki noise, extracts sections, computes quality stats, tags sensitivity status, and writes processed JSONL to `data/processed`. Details: [docs/desc/clean.md](docs/desc/clean.md).

`init-database`
Creates or repairs the required SQLite/PostgreSQL schema for persisted corpus records. Details: [docs/desc/init_database.md](docs/desc/init_database.md).

`persist`
Reads cleaned JSONL and upserts articles, sections, categories, and sensitivity metadata into the configured database. Details: [docs/desc/persist.md](docs/desc/persist.md).

`display`
Prints readable article samples from files or the database, with optional random sampling. Details: [docs/desc/display.md](docs/desc/display.md).

`pipeline`
Runs scrape, clean, optional persist, and optional display as one batch-streaming workflow. Details: [docs/desc/pipeline.md](docs/desc/pipeline.md).

## Running

Run the default full pipeline:

```bash
pipeline-wikipedia
```

Run individual jobs:

```bash
scrape-wikipedia
clean-wikipedia
init-database
persist-wikipedia --with-init
display-wikipedia
```

Each job owns a default config path. You can override it by passing a config file:

```bash
scrape-wikipedia configs/scrape.yaml
pipeline-wikipedia configs/pipeline.yaml
```

## Configuration

YAML configs live in `configs/` and control job logic such as categories, limits, batch sizes, output behavior, display source, and whether the pipeline should save files or persist to the database.

`.env` is for runtime settings such as logging color/level, MediaWiki connection settings, and database credentials/paths.

The pipeline is batch-streaming: it scrapes a batch, cleans that batch, optionally saves it, optionally persists it, and then moves to the next batch. This avoids holding the whole corpus in memory for large runs.

## Outputs

Raw scraped records are JSONL files in `data/raw`.

Cleaned corpus records are JSONL files in `data/processed`.

Persisted corpus records go to PostgreSQL by default or SQLite when configured.

Cleaned articles include sensitivity metadata:

- `safe`: no configured sensitive keywords were detected.
- `caution`: broader or contextual sensitive terms were detected.
- `restricted`: high-risk sensitive terms were detected.

Flagged articles are not removed. They are kept in files and the database with their sensitivity status and matched keywords so downstream usage can decide how to handle them.

## Project Shape

- `src/vezilka_text_scraper/adapters`: external systems such as MediaWiki, JSONL files, database storage, and exports.
- `src/vezilka_text_scraper/services`: domain workflows and reusable corpus operations.
- `src/vezilka_text_scraper/jobs`: executable jobs.
- `src/vezilka_text_scraper/shared`: environment variables, constants, logging, and shared exceptions.
- `configs`: YAML job configuration.
- `docs/desc`: detailed job documentation.

## Verification

Use the conda environment:

```bash
/Users/itonkdong/miniconda3/envs/vezilka/bin/python -m pytest
/Users/itonkdong/miniconda3/envs/vezilka/bin/python -m ruff check .
/Users/itonkdong/miniconda3/envs/vezilka/bin/python -m mypy src tests
```

## Contribution

This work was done by Viktor Kostadinoski as part of the Vezilka project, specifically the Doniraj Vezilka part of the project, under the supervision of prof. Dimitar Trajanov.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).
