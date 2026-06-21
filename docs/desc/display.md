# Display Job

## What It Does

The `display` job reads cleaned article records from `data/processed` and prints a small number of articles in a human-readable console format.

It is an inspection/debugging job. It does not create or modify corpus data. It only prints article titles, section headings, and section content so processed output can be read without JSON escaping or `\n` artifacts.

## How To Run

Default configuration:

```bash
conda activate vezilka
python -m vezilka_text_scraper.jobs.display
```

Equivalent installed command:

```bash
conda activate vezilka
display-wikipedia
```

Override the default config path:

```bash
python -m vezilka_text_scraper.jobs.display configs/display.yaml
display-wikipedia configs/display.yaml
```

## Default Configuration

Default config path:

```text
configs/display.yaml
```

The job class owns this default through `WikipediaDisplayJob.default_config_path`.

## Configuration Fields

`input_path`
Path to a processed JSONL file. When `null`, the newest `data/processed/*.jsonl` file is used.

`article_limit`
Number of articles to print from the start of the processed file.

## Output

The job prints formatted text directly to the console. It does not write files.

For each article it prints:

```text
article title
section heading
section content
```

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
Read
Displayed
Duration
Reason, only on failure
```
