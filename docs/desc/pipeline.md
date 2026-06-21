# Pipeline Job

## What It Does

The `pipeline` job runs the corpus workflow as one coordinated process:

```text
scrape -> clean -> optional persist -> optional display
```

The pipeline owns only orchestration flags. Each step still loads its own job config for step-specific behavior.

The job streams records in batches so large runs do not need to keep the full raw and cleaned corpus in memory. Raw and processed JSONL files are optional outputs. This lets a run persist directly to the database, write files for inspection, or do both.

## How To Run

Default configuration:

```bash
conda activate vezilka
python -m vezilka_text_scraper.jobs.pipeline
```

Equivalent installed command:

```bash
conda activate vezilka
pipeline-wikipedia
```

Override the default config path:

```bash
python -m vezilka_text_scraper.jobs.pipeline configs/pipeline.yaml
pipeline-wikipedia configs/pipeline.yaml
```

## Default Configuration

Default config path:

```text
configs/pipeline.yaml
```

The job class owns this default through `WikipediaPipelineJob.default_config_path`.

## Configuration Fields

`scrape_config_path`
Path to the scrape job config. The pipeline uses this to discover and fetch raw Wikipedia articles.

`clean_config_path`
Path to the clean job config. The pipeline uses this to clean the raw articles already fetched in the current run. The clean config's `input_path` is ignored in pipeline mode because input comes from memory.

`persist_config_path`
Path to the persist job config. Used only when `persist_to_database` is `true`.

`display_config_path`
Path to the display job config. The pipeline uses `article_limit` from this config when `run_display` is `true`. The display source itself is controlled by `display_source` in the pipeline config.

`save_scraped_articles`
When `true`, writes fetched raw articles to `data/raw`. When `false`, raw articles are only passed in memory to the clean step.

`save_cleaned_articles`
When `true`, writes cleaned articles to `data/processed`. When `false`, cleaned articles are only kept in memory for persistence or display.

`persist_to_database`
When `true`, initializes the configured database schema if needed and persists the current run's cleaned articles.

`batch_size`
Number of articles processed through one pipeline batch. Pipeline `batch_size` overrides the scrape, clean, and persist batch sizes during pipeline runs.

`run_display`
When `true`, prints formatted cleaned article text at the end of the run.

`display_source`
Where display reads from. Supported values are `file` and `database`.

For `file`, `save_cleaned_articles` must be `true`.

For `database`, `persist_to_database` must be `true`. The concrete database backend is not configured here. It is taken from `persist_config_path`, so the pipeline displays from the same SQLite or PostgreSQL database it just persisted into.

At least one final output goal must be enabled: `save_cleaned_articles` or `persist_to_database`.

## Outputs

Depending on configuration, the pipeline can produce:

```text
data/raw/wiki_raw_<timestamp>.jsonl
data/processed/wiki_clean_<timestamp>.jsonl
database rows in the configured SQLite or PostgreSQL database
formatted console display output
```

When output run names are configured in the step configs, those names are used for the JSONL file names.

JSONL outputs are written incrementally by batch. If the pipeline fails mid-run, output files may contain successfully completed batches.

## Database Behavior

When `persist_to_database` is enabled, the pipeline initializes the database schema before persistence. If the schema and tables already exist, initialization skips existing objects and continues.

Persistence happens once per pipeline batch. If a later batch fails, earlier successful batches remain committed.

The database backend is selected in `configs/persist.yaml`; actual connection values are loaded from `.env`. Pipeline `display_source: database` always uses this same persist database config.

## Final Job Log

The job emits one final structured summary log.

On success, it logs at `INFO`, explicitly colored green when `LOG_COLOR=true`.

On failure, it logs at `ERROR`, explicitly colored red when `LOG_COLOR=true`.

The summary includes:

```text
Job
Status
Config
Step configs
Pipeline flags
Batch size and batch count
Output paths
Raw discovered, fetched, saved, and failed counts
Cleaned, saved, skipped, and failed counts
Database inserted and updated counts
Database type
Displayed count
Duration
Reason, only on failure
```
