# Financial News Aggregator

A Python pipeline that collects, classifies, scrapes, and summarizes financial news for AI companies: **OpenAI, Anthropic, Google DeepMind, Microsoft, and Meta**.

## How It Works

The system runs a 6-step pipeline:

1. **Collect** — Fetches articles from Google News RSS feeds, Yahoo Finance RSS, and optionally NewsAPI (free tier)
2. **Classify (initial)** — Tags articles by company using keyword matching on titles; discards unrelated articles
3. **Scrape** — Resolves Google News redirect URLs and extracts full article text using `trafilatura`
4. **Classify (refined)** — Re-classifies with full text to catch additional company mentions
5. **Summarize** — Generates 30–40 word summaries using Ollama (local LLM)
6. **Store** — Saves results to a SQLite database and exports to CSV

## Setup

### 1. Install Ollama

Download and install [Ollama](https://ollama.com), then pull the model:

```bash
ollama pull llama3.2:3b
```

Make sure Ollama is running before starting the pipeline (`ollama serve`).

### 2. Clone and install dependencies

```bash
cd news-aggregator
python -m venv venv
source venv/bin/activate   # macOS/Linux
# venv\Scripts\activate    # Windows
pip install -r requirements.txt
```

### 3. Configure API keys (optional)

```bash
cp .env.example .env
```

Edit `.env` and add your NewsAPI key if you have one:

- **`NEWSAPI_KEY`** (optional) — Get one at [newsapi.org](https://newsapi.org). The system works without it (RSS feeds alone provide good coverage), but adding it increases article volume.

### 4. Run the pipeline

```bash
python main.py
```

## Output

| File | Description |
|---|---|
| `news_articles.db` | SQLite database with all articles |
| `news_articles.csv` | CSV export with title, date, URL, companies, summary |
| `pipeline.log` | Full execution log |

### Database schema

| Column | Type | Description |
|---|---|---|
| `title` | TEXT | Article headline |
| `published_date` | TEXT | ISO 8601 publish date |
| `source_url` | TEXT | Original article URL (unique) |
| `companies` | TEXT | Comma-separated company tags |
| `summary` | TEXT | 30–40 word AI-generated summary |
| `source` | TEXT | Collection source (rss / newsapi) |
| `scraped_at` | TIMESTAMP | When the article was processed |

## Project Structure

```
news-aggregator/
├── main.py              # Entry point — orchestrates the pipeline
├── collector.py         # News fetching from RSS + NewsAPI
├── classifier.py        # Company tagging via keyword matching
├── scraper.py           # Google News URL decoding + full-text extraction
├── summarizer.py        # Ollama (local LLM) summarization
├── storage.py           # SQLite storage + CSV export
├── config.py            # Configuration, company keywords, settings
├── requirements.txt
├── .env.example
└── README.md
```

## Key Design Decisions

- **Two-pass classification**: Articles are first filtered by title (fast, avoids scraping irrelevant URLs), then re-classified with full text to catch additional company mentions.
- **Google News URL decoding**: Google News RSS feeds provide encoded redirect URLs. The scraper reverse-engineers Google's internal `batchexecute` API to resolve the real article URLs.
- **Blocked domain list**: Paywalled sites (NYT, WSJ, Bloomberg, etc.) are detected and skipped instantly to avoid wasting time on retries.
- **Concurrent scraping**: Uses `ThreadPoolExecutor` with 10 workers for parallel article fetching.
- **Local LLM summarization**: Uses Ollama with `llama3.2:3b` — no API keys needed, no rate limits, runs entirely on-device.
- **Keyword matching over LLM classification**: Cheaper, faster, and deterministic. The keyword list covers company names, products, and key people.
- **Graceful degradation**: Failed scrapes don't halt the pipeline. Articles without full text are kept and classified by title alone (summary will be `None`).

## Test Set

**AI Companies**: OpenAI, Anthropic, Google DeepMind, Microsoft, Meta
