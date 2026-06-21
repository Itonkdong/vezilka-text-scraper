# Scrape Job

## What It Does

The `scrape` job collects raw Macedonian Wikipedia article data and writes it to a JSONL file in `data/raw`.

This job is the first step in the corpus pipeline. It does not clean, normalize, section, or store articles in the database. It only discovers articles from approved Wikipedia categories, fetches the current raw MediaWiki wikitext and metadata, and saves those raw records for later processing jobs.

## How To Run

Default configuration:

```bash
conda activate vezilka
python -m vezilka_text_scraper.jobs.scrape
```

Equivalent installed command:

```bash
conda activate vezilka
scrape-wikipedia
```

Override the default config path:

```bash
python -m vezilka_text_scraper.jobs.scrape configs/scrape.yaml
scrape-wikipedia configs/scrape.yaml
```

## Default Configuration

Default config path:

```text
configs/scrape.yaml
```

The job class owns this default through `WikipediaScrapeJob.default_config_path`.

## Configuration Fields

`categories`
List of root Wikipedia categories to crawl. The user may only choose from the supported category list:

```text
Биологија, Географија, Историја, Култура, Математика,
Наука, Образование, Спорт, Технологија, Уметност
```

`recursive`
Whether to traverse subcategories.

`max_depth`
Maximum subcategory traversal depth. `0` means only direct articles from the configured categories.

`total_article_limit`
Maximum number of unique articles to save across the whole run. Ignored when `per_category_article_limit` is set.

`per_category_article_limit`
Maximum number of unique articles to save per configured root category. When this is set, it overrides the global `total_article_limit`.

`include_redirects`
Whether redirect pages should be saved. Default behavior excludes redirects.

`namespace`
Wikipedia namespace for article pages. Use `0` for normal encyclopedic articles.

`request_delay_seconds`
Delay between category-member requests. This keeps live API runs more polite and easier to throttle.

`continue_on_error`
Whether to skip failed categories/articles and continue the run. If false, the job fails on the first expected adapter error.

`batch_size`
Number of fetched raw articles to hold in memory before writing the next JSONL batch.

`output_run_name`
Optional JSONL file name for the run. If omitted, the job writes `wiki_raw_<timestamp>.jsonl`.

## Output

Output directory:

```text
data/raw
```

Output format:

```text
JSONL, one raw article record per line
```

The file is written incrementally by batch. If the job fails mid-run, the file may contain successfully completed batches.

Example output path:

```text
data/raw/wiki_raw_20260620_181800.jsonl
```

## Output Fields

`page_id`
Stable numeric Wikipedia page ID.

`title`
Article title at scrape time.

`url`
Canonical article URL.

`language`
Wikipedia language code. For this project it is usually `mk`.

`categories`
Categories attached to the article in Wikipedia metadata.

`revision_id`
Exact Wikipedia revision ID that was fetched.

`last_modified`
Timestamp of the fetched Wikipedia revision.

`scraped_at`
Timestamp when this project scraped the article.

`source_categories`
Configured root category or categories through which the article was discovered.

`raw_wikitext`
Raw MediaWiki markup for the article. This is intentionally not cleaned text.

## Final Job Log

The job emits one final structured summary log.

On success, it logs at `INFO`, which is green when `LOG_COLOR=true`.

On failure, it logs at `ERROR`, which is red when `LOG_COLOR=true`.

The summary includes:

```text
Job
Status
Config
Output
Discovered
Saved
Failed
Batch size
Batches
Duration
Reason, only on failure
```
