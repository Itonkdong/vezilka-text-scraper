# Vezilka Text Scraper

Macedonian Wikipedia corpus builder for collecting clean, structured article text suitable for speech and handwriting data collection tasks.

## Setup

```bash
conda env create -f environment.yml
conda activate vezilka-text-scraper
cp .env.example .env
```

For pip-only environments:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Project Shape

- `src/vezilka_text_scraper/adapters`: External systems such as MediaWiki, database storage, and exports.
- `src/vezilka_text_scraper/services`: Domain workflows and reusable corpus operations.
- `src/vezilka_text_scraper/jobs`: Executable pipeline jobs.
- `src/vezilka_text_scraper/config`: Structured runtime configuration when needed.
- `src/vezilka_text_scraper/shared`: Environment variables, constants, logging, and shared exceptions.
