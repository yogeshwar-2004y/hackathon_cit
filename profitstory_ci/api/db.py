import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

# We get the connection string from the environment variable
DATABASE_URL = os.environ.get("DATABASE_URL")

def get_connection():
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL environment variable is not set. Please provide your Neon DB connection string.")
    return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Enable pgvector extension
    cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # Price history
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS price_history (
        id      SERIAL PRIMARY KEY,
        asin    TEXT    NOT NULL,
        price   REAL    NOT NULL,
        date    TEXT    NOT NULL
    )
    """)

    # Review statistics
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS review_stats (
        id             SERIAL PRIMARY KEY,
        asin           TEXT    NOT NULL,
        avg_sentiment  REAL,
        review_count   INTEGER,
        rating         REAL,
        review_spike   INTEGER,
        scraped_at     TEXT
    )
    """)

    # Agent run results
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS agent_results (
        id           SERIAL PRIMARY KEY,
        run_id       TEXT    NOT NULL,
        product_asin TEXT    NOT NULL,
        result_json  TEXT    NOT NULL,
        created_at   TEXT    NOT NULL
    )
    """)
    
    # Review Embeddings
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS review_embeddings (
        id          SERIAL PRIMARY KEY,
        asin        TEXT NOT NULL,
        document    TEXT NOT NULL,
        metadata    JSONB,
        embedding   vector(1536), -- OpenAI text-embedding-3-small uses 1536 dims
        created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()

def save_price_to_db(asin: str, price: float, date_str: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO price_history (asin, price, date) VALUES (%s, %s, %s)",
        (asin, price, date_str)
    )
    conn.commit()
    conn.close()

def save_review_stats(asin: str, avg_sentiment: float, review_count: int, rating: float, review_spike: int, scraped_at: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO review_stats (asin, avg_sentiment, review_count, rating, review_spike, scraped_at) VALUES (%s, %s, %s, %s, %s, %s)",
        (asin, avg_sentiment, review_count, rating, review_spike, scraped_at)
    )
    conn.commit()
    conn.close()

def save_agent_result(run_id: str, product_asin: str, result_json: str, created_at: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO agent_results (run_id, product_asin, result_json, created_at) VALUES (%s, %s, %s, %s)",
        (run_id, product_asin, result_json, created_at)
    )
    conn.commit()
    conn.close()

def get_price_history(asin: str, limit: int = 30) -> list:
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute(
        "SELECT date, price FROM price_history WHERE asin = %s ORDER BY date DESC LIMIT %s",
        (asin, limit)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]
    
def get_latest_agent_result():
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute(
        "SELECT * FROM agent_results ORDER BY id DESC LIMIT 1"
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

if __name__ == "__main__":
    init_db()
    print("Database initialized.")
