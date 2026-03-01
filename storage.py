"""Data storage — SQLite database and CSV export."""

import csv
import logging
import sqlite3

from config import CSV_PATH, DB_PATH

logger = logging.getLogger(__name__)

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    published_date TEXT,
    source_url TEXT UNIQUE NOT NULL,
    companies TEXT NOT NULL,
    summary TEXT,
    source TEXT,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


def init_db() -> sqlite3.Connection:
    """Create the database and articles table if they don't exist."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute(CREATE_TABLE_SQL)
    conn.commit()
    logger.info("Database initialized: %s", DB_PATH)
    return conn


def store_articles(articles: list[dict], conn: sqlite3.Connection) -> int:
    """Insert articles into the SQLite database. Skips duplicates by URL."""
    inserted = 0
    skipped = 0

    for article in articles:
        companies_str = ", ".join(article.get("companies", []))
        try:
            conn.execute(
                """
                INSERT OR IGNORE INTO articles
                    (title, published_date, source_url, companies, summary, source)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    article.get("title", ""),
                    article.get("published_date"),
                    article["url"],
                    companies_str,
                    article.get("summary"),
                    article.get("source", ""),
                ),
            )
            if conn.total_changes:
                inserted += 1
        except sqlite3.IntegrityError:
            skipped += 1

    conn.commit()
    logger.info("Database: %d inserted, %d skipped (duplicate URL)", inserted, skipped)
    return inserted


def export_csv(conn: sqlite3.Connection) -> str:
    """Export all articles from the database to a CSV file."""
    cursor = conn.execute(
        """
        SELECT title, published_date, source_url, companies, summary
        FROM articles
        ORDER BY published_date DESC
        """
    )

    rows = cursor.fetchall()
    headers = ["Title", "Published Date", "Source URL", "Companies", "Summary"]

    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)

    logger.info("Exported %d articles to %s", len(rows), CSV_PATH)
    return CSV_PATH


def get_company_counts(conn: sqlite3.Connection) -> dict[str, int]:
    """Return a count of articles per company tag."""
    cursor = conn.execute("SELECT companies FROM articles")
    counts: dict[str, int] = {}
    for (companies_str,) in cursor:
        for company in companies_str.split(", "):
            company = company.strip()
            if company:
                counts[company] = counts.get(company, 0) + 1
    return counts
