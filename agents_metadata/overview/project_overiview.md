# Project Overview: Macedonian Wikipedia Corpus Builder

## 1. Project Goal

The goal of this project is to build a high-quality, structured corpus of Macedonian-language text extracted from Wikipedia articles. Unlike traditional Wikipedia corpus projects that are primarily intended for Natural Language Processing (NLP) tasks, the purpose of this corpus is to serve as a source of diverse, natural, and representative Macedonian text samples for data collection campaigns involving human participants.

The collected articles will be used to generate reading and writing tasks that participants will complete by:

* Reading the text aloud, enabling the collection of spoken Macedonian language recordings.
* Handwriting the text on paper or digital devices, enabling the collection of modern handwritten Macedonian language samples.

The resulting audio recordings and handwritten documents will later be used to develop and train machine learning systems for tasks such as speech recognition, speech processing, handwriting recognition, optical character recognition (OCR), writer-independent handwriting modeling, and other technologies related to the Macedonian language.

To support these goals, the corpus must contain clean, well-structured, and human-readable text that represents a wide range of topics, vocabulary, writing styles, sentence lengths, and linguistic constructs. The system should automatically collect articles from selected Wikipedia categories, remove Wikipedia-specific formatting and non-content elements, extract the meaningful textual content, enrich it with useful metadata, and store it in a structured database for later selection, filtering, and generation of participant tasks.

The final deliverable is a reusable pipeline capable of continuously building and maintaining a high-quality repository of Macedonian text samples suitable for large-scale speech and handwriting data collection initiatives.
⸻

## 2. High-Level Architecture

Wikipedia Categories
          │
          ▼
 Category Discovery
          │
          ▼
 Article Collection
          │
          ▼
 Content Extraction
          │
          ▼
 Text Cleaning
          │
          ▼
 Metadata Extraction
          │
          ▼
 Database Storage
          │
          ▼
 Export / Analytics

⸻

## 3. Functional Requirements

The system must:

Category Crawling

* Start from one or more predefined Wikipedia categories.
* Discover all articles within those categories.
* Optionally traverse subcategories.
* Avoid duplicate articles.
* Maintain article-category relationships.

Article Collection

For every discovered article:

* Retrieve page metadata.
* Retrieve page content.
* Retrieve page revision information.
* Generate canonical article URL.

Text Processing

Extract only meaningful encyclopedic content.

Remove:

* Infoboxes
* Navigation templates
* Reference sections
* Citations
* External links
* Categories
* Images
* Tables
* Metadata templates
* Edit markers
* Navigation boxes
* Footer sections

Keep:

* Title
* Section headings
* Main article text

Database Storage

Store:

* Article information
* Categories
* Statistics
* Section structure
* Crawl metadata

⸻

## 4. Technology Stack

Language

Python 3.11+

Libraries

HTTP/API

requests

Wikipedia Parsing

mwparserfromhell

This library parses MediaWiki markup directly and is significantly cleaner than HTML scraping.

HTML Processing

beautifulsoup4
lxml

Used only when necessary.

Data Validation

pydantic

ORM

sqlalchemy

Database

Development:

SQLite

Production:

PostgreSQL

Logging

logging

Progress Tracking

tqdm

⸻

## 5. Why Use MediaWiki API Instead of Scraping HTML

The project should use the MediaWiki API whenever possible.

Advantages:

* Stable interface
* Faster requests
* Structured responses
* Access to raw wiki markup
* Easier extraction of categories
* Easier extraction of revisions
* Easier cleaning process

Avoid parsing rendered HTML unless absolutely necessary.

⸻

## 6. Initial Category Set

Suggested starting categories:

Географија
Историја
Наука
Биологија
Култура
Спорт
Технологија
Образование
Математика
Уметност

The crawler should support any category provided by configuration.

Example:

categories:
  - Географија
  - Историја
  - Наука

⸻

## 7. Category Traversal Strategy

Wikipedia categories are hierarchical.

Example:

Географија
 ├─ Реки
 ├─ Планини
 ├─ Езера
 └─ Градови

The crawler should support:

Mode 1

Only direct articles.

Mode 2

Recursive traversal.

max_depth = 3

Recommended default:

recursive = true
max_depth = 2

Maintain a visited category set to prevent loops.

⸻

## 8. Article Collection Pipeline

For each article:

Step 1

Discover page.

Step 2

Retrieve metadata.

Step 3

Retrieve content.

Step 4

Clean content.

Step 5

Generate statistics.

Step 6

Store in database.

⸻

## 9. Metadata To Store

For every article:

page_id
title
url
language
categories
revision_id
last_modified
scraped_at

Optional:

page_length
num_sections
num_words
num_characters

⸻

## 10. Text Cleaning Pipeline

This is the most important component.

Input:

Raw MediaWiki Markup

Output:

Clean Macedonian Text

⸻

Remove Templates

Example:

{{Infobox}}

Remove completely.

⸻

Remove References

Example:

<ref>Some source</ref>

Remove.

⸻

Remove Citation Markers

Example:

[1]
[2]
[15]

Remove.

⸻

Remove External Links

Example:

[https://example.com]

Remove URL.

Optionally keep visible text.

⸻

Remove Categories

Example:

[[Категорија:Географија]]

Remove.

⸻

Remove Files

Example:

[[Податотека:image.jpg]]

Remove.

⸻

Remove Tables

Example:

{| class="wikitable"
...
|}

Remove.

⸻

Remove Navigation Sections

Remove sections such as:

Наводи
Референци
Извори
Надворешни врски
Видете исто така
Белешки

⸻

Normalize Whitespace

Convert:

multiple spaces
multiple newlines
tabs

into clean formatting.

⸻

11. Section Extraction

Preserve article structure.

Example:

Македонија
Историја
...
Географија
...
Население
...

Store each section separately.

Benefits:

* Better retrieval
* Better chunking
* Better embeddings

⸻

12. Database Design

Articles Table

articles

Columns:

id
page_id
title
url
language
raw_text
clean_text
word_count
char_count
section_count
revision_id
created_at

⸻

Categories Table

categories

Columns:

id
name

⸻

Article Categories

Many-to-many relationship.

article_categories

Columns:

article_id
category_id

⸻

Sections

sections

Columns:

id
article_id
heading
content
word_count
char_count
position

⸻

## 13. Corpus Statistics

Generate:

Total Articles
Total Categories
Total Words
Total Characters
Average Article Length
Average Section Length
Largest Article
Smallest Article

Store or compute dynamically.

⸻

14. Deduplication

Prevent:

* Duplicate pages
* Redirect pages
* Same article reached through multiple categories

Use:

page_id

as the unique identifier.

⸻

15. Quality Filtering

Skip:

Very Small Pages

Example:

< 100 words

Disambiguation Pages

Example:

Скопје (појаснување)

Redirects

Store optionally but exclude from corpus.

⸻

16. Configuration System

Use YAML.

Example:

categories:
  - Географија
  - Историја
recursive: true
max_depth: 2
min_word_count: 100
database:
  type: postgres

⸻

17. Export Capabilities

Allow exporting to:

JSON

{
  "title": "...",
  "text": "..."
}

JSONL

Preferred for ML.

{"title":"...","text":"..."}

CSV

For analysis.

Parquet

For large-scale processing.

⸻

19. Success Criteria

The project is considered successful when:

1. Categories can be crawled automatically.
2. Articles are collected without duplication.
3. Text is cleaned successfully.
4. Section structure is preserved.
5. Metadata is stored correctly.
6. Database can be queried efficiently.
7. Corpus can be exported for NLP and ML tasks.
8. The resulting dataset contains only meaningful encyclopedic content with minimal Wikipedia-specific noise.

The final deliverable should be a reusable Macedonian Wikipedia corpus generation pipeline that can be rerun periodically to refresh and expand the dataset.