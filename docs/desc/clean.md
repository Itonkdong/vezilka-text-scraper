# Clean Job

## What It Does

The `clean` job reads raw Wikipedia JSONL records from `data/raw`, cleans each article's `raw_wikitext` into readable Macedonian text, extracts sections, applies quality filters, and writes structured processed JSONL records to `data/processed`.

This job does not store data in the database. It prepares clean article records for later storage, analytics, selection, and export jobs.

## How To Run

Default configuration:

```bash
conda activate vezilka
python -m vezilka_text_scraper.jobs.clean
```

Equivalent installed command:

```bash
conda activate vezilka
clean-wikipedia
```

Override the default config path:

```bash
python -m vezilka_text_scraper.jobs.clean configs/clean.yaml
clean-wikipedia configs/clean.yaml
```

## Default Configuration

Default config path:

```text
configs/clean.yaml
```

The job class owns this default through `WikipediaCleanJob.default_config_path`.

## Configuration Fields

`input_path`
Path to a raw scraper JSONL file. When `null`, the newest `data/raw/*.jsonl` file is used.

`output_run_name`
Optional JSONL file name for the processed output. If omitted, the job writes `wiki_clean_<timestamp>.jsonl`.

`min_word_count`
Minimum number of words required in the final cleaned text. Articles below this count are skipped.

`skip_disambiguation_pages`
Whether to skip articles whose titles look like disambiguation pages.

`continue_on_error`
Whether to skip failed records and continue. If false, the job fails on the first cleaning error.

`remove_templates`
Remove MediaWiki templates such as infoboxes and metadata boxes.

`remove_references`
Remove `<ref>` and `<references>` markup.

`remove_tables`
Remove wiki table blocks.

`remove_files`
Remove image/file links.

`remove_categories`
Remove category links from article content.

`remove_external_links`
Keep visible external-link labels and remove URL-only links.

`remove_navigation_sections`
Remove sections such as `Наводи`, `Референци`, `Извори`, `Надворешни врски`, `Видете исто така`, and `Белешки`.

`normalize_whitespace`
Normalize repeated spaces, tabs, and blank lines.

## Output

Output directory:

```text
data/processed
```

Output format:

```text
JSONL, one cleaned article record per line
```

Example output path:

```text
data/processed/wiki_clean_20260621_120000.jsonl
```

## Output Fields

`page_id`
Stable numeric Wikipedia page ID.

`title`
Article title at scrape time.

`url`
Canonical article URL.

`language`
Wikipedia language code.

`categories`
Categories attached to the article in Wikipedia metadata.

`revision_id`
Exact Wikipedia revision ID that was cleaned.

`last_modified`
Timestamp of the fetched Wikipedia revision.

`scraped_at`
Timestamp when the raw article was scraped.

`cleaned_at`
Timestamp when this job cleaned the article.

`source_categories`
Configured root category or categories through which the article was discovered.

`clean_text`
Readable cleaned article text, including title and section headings.

`word_count`
Word count of `clean_text`.

`char_count`
Character count of `clean_text`.

`section_count`
Number of cleaned sections.

`sections`
Ordered list of cleaned sections. Each section has `heading`, `content`, `word_count`, `char_count`, and `position`.

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
Output
Read
Cleaned
Skipped
Failed
Duration
Reason, only on failure
```
