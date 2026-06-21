# Vezilka Text Scraper

Macedonian Wikipedia corpus builder for collecting clean, structured article text suitable for speech and handwriting data collection tasks.

## Setup

```bash
conda env create -f environment.yml
conda activate vezilka
cp .env.example .env
```

## Docker

Default Docker Compose run starts Postgres and runs the full pipeline job:

```bash
cp .env.example .env
docker compose up --build
```

The app container reads configs from the project `configs/` directory and writes outputs to the project `data/` and `logs/` directories.

Override the job:

```bash
VEZILKA_JOB=clean-wikipedia docker compose up --build app
```

Pass job arguments, such as a custom config path:

```bash
VEZILKA_JOB=scrape-wikipedia VEZILKA_JOB_ARGS="configs/scrape.yaml" docker compose up --build app
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

Run the clean job:

```bash
python -m vezilka_text_scraper.jobs.clean
# or
clean-wikipedia
```

To use a non-default clean configuration file:

```bash
python -m vezilka_text_scraper.jobs.clean configs/clean.yaml
# or
clean-wikipedia configs/clean.yaml
```

## Project Shape

- `src/vezilka_text_scraper/adapters`: External systems such as MediaWiki, database storage, and exports.
- `src/vezilka_text_scraper/services`: Domain workflows and reusable corpus operations.
- `src/vezilka_text_scraper/jobs`: Executable pipeline jobs.
- `src/vezilka_text_scraper/config`: Structured runtime configuration when needed.
- `src/vezilka_text_scraper/shared`: Environment variables, constants, logging, and shared exceptions.
