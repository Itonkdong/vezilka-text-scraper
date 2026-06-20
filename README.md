# Vezilka Text Scraper

Macedonian Wikipedia corpus builder for collecting clean, structured article text suitable for speech and handwriting data collection tasks.

## Setup

```bash
conda env create -f environment.yml
conda activate vezilka
cp .env.example .env
```

For pip-only environments:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

Run the raw scrape job:

```bash
python -m vezilka_text_scraper.jobs.scrape
# or
scrape-wikipedia
```

To use a non-default configuration file:

```bash
python -m vezilka_text_scraper.jobs.scrape configs/scrape.yaml
# or
scrape-wikipedia configs/scrape.yaml
```

## Project Shape

- `src/vezilka_text_scraper/adapters`: External systems such as MediaWiki, database storage, and exports.
- `src/vezilka_text_scraper/services`: Domain workflows and reusable corpus operations.
- `src/vezilka_text_scraper/jobs`: Executable pipeline jobs.
- `src/vezilka_text_scraper/config`: Structured runtime configuration when needed.
- `src/vezilka_text_scraper/shared`: Environment variables, constants, logging, and shared exceptions.
