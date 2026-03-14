# ProfitStory Competitive Intelligence Agent
### PS-D3 · CIT M.Sc Data Science Hackathon · 2026

> **Philosophy:** Net Profit > Gross Revenue.  
> Never suggest blind price cuts. Every strategy is evaluated against real cost structure and margin impact before surfacing.

---

## Table of Contents

1. [Problem Statement](#1-problem-statement)
2. [Approach & Core Insight](#2-approach--core-insight)
3. [Technology Stack](#3-technology-stack)
4. [System Architecture](#4-system-architecture)
5. [Scraping Pipeline — BeautifulSoup](#5-scraping-pipeline--beautifulsoup)
6. [The 5-Node LangGraph Agent Loop](#6-the-5-node-langgraph-agent-loop)
7. [End-to-End Data Flow with Sample Data](#7-end-to-end-data-flow-with-sample-data)
8. [Frontend — React](#8-frontend--react)
9. [Backend — FastAPI](#9-backend--fastapi)
10. [Database Schema](#10-database-schema)
11. [Optional: Profit Calculator Module](#11-optional-profit-calculator-module)
12. [Antigravity Integration Guide](#12-antigravity-integration-guide)
13. [Setup & Running Locally](#13-setup--running-locally)
14. [Project File Structure](#14-project-file-structure)
15. [Glossary](#15-glossary)

---

## 1. Problem Statement

E-commerce sellers face a **Competitive Intelligence Wall** — the point where the velocity of pricing shifts and sentiment nuances in reviews outpaces human analytical capacity.

### What breaks traditional tools

| Challenge | Why it fails with traditional scraping |
|---|---|
| Pricing velocity | Competitors reprice multiple times daily. Manual monitoring is impossible at scale. |
| Sentiment nuance | `LIKE '%bad%'` misses "sounds great but dies after 2 weeks" — a critical quality signal with positive surface words. |
| Signal correlation | A price drop caused by quality failure requires a different response than one caused by overstocking. Traditional tools cannot distinguish. |
| Reaction speed | By the time a human analyst connects the dots, the market window has closed. |

### The specific gap

```
Traditional scraper sees:
  XYZ Budget Earphones: ₹899 → ₹699  (price dropped 22%)
  Action suggested: "Lower your price"  ← WRONG

ProfitStory sees:
  Price drop: −22% over 30 days
  38/45 reviews: "sound dies" (semantic cluster, confidence 0.94)
  Rating: 4.2★ → 3.1★ in 18 days (velocity: −0.06★/day)
  Keyword surge: "durable earphones" +34% search volume
  
  Conclusion: DISTRESS PRICING from quality failure
  Action: Ad campaign targeting displaced buyers → +₹18,500 net profit
           NOT a price match (would lose ₹14,100 margin)
```

---

## 2. Approach & Core Insight

### The agentic layer

ProfitStory adds an **autonomous reasoning layer** between raw data and seller decisions. Instead of a dashboard showing what happened, the agent determines *why it happened* and *what the seller should do about it*.

```
Raw data  →  [AGENT REASONS]  →  Profit-protected action
(price,       connects signals,    with exact ₹ figures
 reviews)     models impact
```

### Core insight: same event, opposite meaning

The same competitor price drop can mean two completely different things:

```
Scenario A — Competitive pricing (cost reduction)
  → Genuine margin pressure
  → May need to match or differentiate on features

Scenario B — Distress pricing (quality crisis)  ← XYZ Budget case
  → Competitor is bleeding customers
  → Opportunity: capture displaced buyers WITHOUT cutting price
  → Ad campaign targeting replacement-intent keyword spikes
```

Only **semantic + temporal signal correlation** can distinguish them. This is what the Detective node does.

### ProfitStory's answer: net profit first

Every suggested action is evaluated against the seller's actual cost structure:

```
Seller: Premium Earphones
Price:  ₹999  |  Cost: ₹550  |  Margin: ₹449/unit  |  Units: ~40/month

Strategy A — Match price ₹699:
  Margin collapses to ₹149/unit
  Monthly profit: ₹7,003 vs ₹17,960 baseline
  NET LOSS: −₹14,100/month  →  RULED OUT

Strategy B — Ad campaign ₹3k spend:
  Price stays ₹999 (margin intact)
  Capture 65 units (replacement buyers)
  Net: ₹29,185 − ₹3,000 spend = ₹26,185
  NET GAIN: +₹8,225 vs baseline  →  RECOMMENDED
```

---

## 3. Technology Stack

### Full stack — all free

| Layer | Tool | Why this | Free? |
|---|---|---|---|
| Frontend | React 18 + Vite | Component model for complex interactive state. Vite gives instant HMR, no config. | Yes |
| Charts | Chart.js 4 | Lightest charting lib, works with React via canvas ref. | Yes |
| Backend API | FastAPI (Python) | Fastest Python API to write. Auto Swagger at `/docs`. Native async background tasks — agent runs without blocking HTTP. | Yes |
| Agent graph | LangGraph | Only Python framework supporting stateful **cyclic** agent graphs. LangChain chains are linear — they cannot loop back. | Yes |
| LLM (cloud) | GPT-4o-mini | Cheapest OpenAI model with strong reasoning. ~₹0.50/scan. | Paid (cheap) |
| LLM (local) | Ollama + llama3 | 100% free, fully offline, runs on laptop GPU/CPU. Swappable with one line change. | Yes |
| Vector DB | pg vector | In-process Python — zero server, zero Docker. 3 lines to embed and query. | Yes |
| Structured DB | neon db| Single `.db` file. Zero config. Handles price history + agent results perfectly at this scale. | Yes |
| Scraping | requests + BeautifulSoup4 | Lightweight HTML parsing. Works for Amazon's static review pages and product listings when using correct headers. | Yes |
| Sentiment | TextBlob | Per-review polarity score (−1.0 to +1.0). No API key, runs locally. | Yes |
| Scheduler | APScheduler | Pure Python, runs inside FastAPI. Triggers rescan every 2 hours. No Celery, no Redis. | Yes |
| Observability | LangSmith | Auto-traces every LLM call and agent step. Free tier. Judges see full reasoning chain live. | Free tier |

### Deliberately NOT chosen

| Rejected | Reason |
|---|---|
| Playwright instead of BS4 | Playwright spins a full Chromium process — overkill when Amazon's review pages are largely static HTML. BS4 + proper headers is faster, lighter, and sufficient for this use case. |
| PostgreSQL instead of SQLite | Zero added value for a single-seller MVP. SQLite handles millions of rows. Postgres adds Docker + migrations + connection strings — unnecessary in 24 hours. |
| Pinecone instead of Chroma | Pinecone requires API key + network. Chroma runs in-process. For 50–200 reviews per competitor, Chroma is faster too. |
| Next.js instead of Vite + React | SSR adds complexity with zero benefit — this is a dashboard with no SEO requirements. |
| Redux instead of useState | State is simple: current page + scan status + log lines. useState + useCallback at root is sufficient and readable. |

---

## 4. System Architecture

### High-level diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     BROWSER (React SPA)                     │
│  Sidebar Nav │ Intelligence │ Competitors │ Reviews │ Alerts │
└──────────────────────────┬──────────────────────────────────┘
                           │ REST + SSE
                           │ POST /scan → job_id
                           │ GET  /job/{id}/stream → live logs
                           │ GET  /results/latest  → dashboard data
┌──────────────────────────▼──────────────────────────────────┐
│                   FastAPI (port 8000)                       │
│  /scan → BackgroundTask → returns job_id immediately        │
│  /job/{id}/stream → SSE: pushes log lines as agent runs     │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                  LangGraph Agent Graph                      │
│                                                             │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐               │
│  │WATCHMAN  │──▶│DETECTIVE │──▶│VULN CALC │               │
│  │scrape    │   │LLM loop  │   │score 0-100│              │
│  │embed     │◀──│if conf   │   └────┬─────┘               │
│  │save DB   │   │< 0.7     │        │                      │
│  └──────────┘   └──────────┘   ┌────▼─────┐               │
│                                │PROFIT SIM│ (optional)     │
│                                │4 strategy│               │
│                                └────┬─────┘               │
│                                ┌────▼─────┐               │
│                                │STRATEGIST│               │
│                                │pivot memo│               │
│                                └──────────┘               │
└──────────────────────────┬──────────────────────────────────┘
                           │
              ┌────────────┴─────────────┐
              │                          │
    ┌─────────▼──────┐       ┌──────────▼────────┐
    │    SQLite      │       │      Chroma        │
    │ price_history  │       │ review embeddings  │
    │ review_stats   │       │ semantic search    │
    │ agent_results  │       │ in-process, local  │
    └────────────────┘       └───────────────────┘
```

### Data flow summary

```
User clicks "Run Scan"
  → POST /scan                          (200ms response, job_id returned)
  → BackgroundTask: graph.invoke()      (runs in thread pool, ~35-60s)
  → EventSource /job/{id}/stream        (browser receives logs live)
  → Watchman: BS4 scrapes Amazon        (price + reviews extracted)
  → Watchman: Chroma embed              (45 reviews → vectors)
  → Watchman: SQLite write              (price history saved)
  → Detective: LLM + tools              (semantic search + price delta)
  → Detective: confidence check         (≥0.7? proceed : re-loop Watchman)
  → VulnCalc: weighted score            (0–100, labeled)
  → ProfitSim: 4 strategies             (optional, ₹ net impact each)
  → Strategist: LLM pivot memo          (3 ranked actions, margin-protected)
  → SSE: status=done                    (browser fetches /results/latest)
  → Dashboard re-renders                (charts, rings, memo updated)
```

---

## 5. Scraping Pipeline — BeautifulSoup

### Why BeautifulSoup over Playwright

Amazon's product listing pages and review pages serve their core content as **static HTML** with proper headers set. BeautifulSoup4 parses this HTML directly — no browser overhead, no Chromium process, no async complexity. It is:

- **10x faster** per page (no browser launch time)
- **Easier to debug** (inspect raw HTML, not a live DOM)
- **Lighter** (no Chromium binary, no system dependencies)
- **Sufficient** — Amazon's review text, prices, and ratings are in the initial HTML payload

> **Note:** If Amazon's anti-bot measures block requests, the scraper falls back to mock data automatically — the demo never breaks.

### HTTP headers required

Amazon rejects requests without a realistic browser User-Agent. Always send:

```python
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-IN,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://www.amazon.in/",
    "DNT": "1",
}
```

### Scraper module — full flow

```
scrape_product(asin)
  │
  ├─── Step 1: Fetch product page
  │      GET https://www.amazon.in/dp/{asin}
  │      requests.get(url, headers=HEADERS, timeout=10)
  │      → HTML string
  │
  ├─── Step 2: Parse with BS4
  │      soup = BeautifulSoup(html, "html.parser")
  │
  ├─── Step 3: Extract price
  │      selector: span.a-price-whole
  │      raw: "699" → float: 699.0
  │
  ├─── Step 4: Extract rating
  │      selector: span.a-icon-alt (first match)
  │      raw: "3.1 out of 5 stars" → float: 3.1
  │
  ├─── Step 5: Extract product name
  │      selector: span#productTitle
  │      raw: "  XYZ Budget Earphones  " → strip → "XYZ Budget Earphones"
  │
  ├─── Step 6: Fetch review page
  │      GET https://www.amazon.in/product-reviews/{asin}
  │             ?sortBy=recent&reviewerType=all_reviews&pageNumber=1
  │
  ├─── Step 7: Extract review texts
  │      selector: span[data-hook="review-body"] span
  │      collect up to 50 review strings
  │
  ├─── Step 8: Sentiment analysis
  │      TextBlob(review_text).sentiment.polarity  →  float in [−1, +1]
  │      average across all reviews  →  avg_sentiment
  │
  └─── Step 9: Return structured dict
         {asin, name, price, rating, reviews[], avg_sentiment,
          review_count, review_spike, scraped_at}
```

### Scraper implementation

```python
# scraper/amazon_scraper.py

import time
import random
import requests
from bs4 import BeautifulSoup
from textblob import TextBlob

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-IN,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://www.amazon.in/",
}

BASE_URL = "https://www.amazon.in"


def scrape_product(asin: str) -> dict:
    """
    Scrape product data using requests + BeautifulSoup.
    Falls back to mock data if Amazon blocks the request.
    """
    try:
        product_data = _fetch_product_page(asin)
        reviews      = _fetch_reviews(asin)
        
        sentiments   = [TextBlob(r).sentiment.polarity for r in reviews if r]
        avg_sentiment = round(sum(sentiments) / len(sentiments), 3) if sentiments else 0.0
        
        return {
            **product_data,
            "reviews":      reviews,
            "avg_sentiment": avg_sentiment,
            "review_count": len(reviews),
            "review_spike": len(reviews),   # treated as spike count per cycle
            "scraped_at":   time.time(),
        }

    except Exception as e:
        print(f"[SCRAPER] Failed for {asin}: {e}. Using mock data.")
        return MOCK_PRODUCTS.get(asin, _generate_mock(asin))


def _fetch_product_page(asin: str) -> dict:
    url  = f"{BASE_URL}/dp/{asin}"
    resp = requests.get(url, headers=HEADERS, timeout=10)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    # ── Price ──────────────────────────────────────────────
    price_el = soup.select_one("span.a-price-whole")
    price    = float(price_el.get_text(strip=True).replace(",", "")) if price_el else 0.0

    # ── Rating ─────────────────────────────────────────────
    rating_el = soup.select_one("span.a-icon-alt")
    rating    = float(rating_el.get_text().split()[0]) if rating_el else 0.0

    # ── Product name ───────────────────────────────────────
    name_el = soup.select_one("span#productTitle")
    name    = name_el.get_text(strip=True) if name_el else f"Product {asin}"

    # ── Rate limit: polite delay ───────────────────────────
    time.sleep(random.uniform(1.5, 3.0))

    return {"asin": asin, "name": name, "price": price, "rating": rating}


def _fetch_reviews(asin: str, pages: int = 3) -> list[str]:
    """
    Fetch up to `pages` pages of recent reviews.
    Returns list of review body strings.
    """
    reviews = []

    for page_num in range(1, pages + 1):
        url = (
            f"{BASE_URL}/product-reviews/{asin}"
            f"?sortBy=recent&reviewerType=all_reviews&pageNumber={page_num}"
        )
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            # Primary selector: data-hook attribute (reliable across Amazon layouts)
            review_els = soup.select('span[data-hook="review-body"] span')

            # Fallback selector if primary fails
            if not review_els:
                review_els = soup.select("div.review-text-content span")

            page_reviews = [
                el.get_text(strip=True)
                for el in review_els
                if len(el.get_text(strip=True)) > 20   # filter noise
            ]
            reviews.extend(page_reviews)

            if not page_reviews:
                break   # no more reviews on this page

            time.sleep(random.uniform(2.0, 4.0))   # polite delay between pages

        except Exception as e:
            print(f"[SCRAPER] Review page {page_num} failed for {asin}: {e}")
            break

    return reviews[:50]   # cap at 50 reviews per cycle
```

### BeautifulSoup selectors reference

| Data point | Primary CSS selector | Fallback selector |
|---|---|---|
| Price (whole) | `span.a-price-whole` | `span.a-offscreen` |
| Rating | `span.a-icon-alt` | `div[data-hook="average-star-rating"] span` |
| Product title | `span#productTitle` | `h1 span#productTitle` |
| Review body | `span[data-hook="review-body"] span` | `div.review-text-content span` |
| Review rating | `i[data-hook="review-star-rating"] span.a-icon-alt` | — |
| Review date | `span[data-hook="review-date"]` | — |

### Mock data fallback

When Amazon blocks requests (HTTP 503, CAPTCHA, etc.), the scraper returns pre-loaded realistic mock data. This ensures the demo never breaks:

```python
MOCK_PRODUCTS = {
    "B0CDEF456": {
        "asin":         "B0CDEF456",
        "name":         "XYZ Budget Earphones",
        "price":        699,
        "rating":       3.1,
        "reviews": [
            "Sound dies after 2 weeks, very disappointed",
            "The sound dies completely after a month of use",
            "Worst quality, sound dies within days",
            # ... 15 realistic reviews
        ],
        "avg_sentiment": -0.68,
        "review_count":  45,
        "review_spike":  45,
    },
    # ...
}
```

---

## 6. The 5-Node LangGraph Agent Loop

### What is LangGraph

LangGraph is a Python framework for building **stateful, cyclic agent workflows** as directed graphs. Unlike LangChain chains (which are linear — A → B → C → done), LangGraph supports **conditional edges** that loop back to earlier nodes. This is essential for the confidence re-loop in the Detective node.

### AgentState — the shared dictionary

Every node reads from and writes to a single typed dictionary:

```python
class AgentState(TypedDict):
    product_asin:     str          # "B0CXYZ123"
    competitor_asins: list[str]    # ["B0CDEF456", "B0ABCD789"]
    scraped_data:     dict         # {asin: {price, reviews, rating, ...}}
    embeddings_done:  bool         # True after Watchman embeds into Chroma
    signals:          list[dict]   # Detective output: patterns, confidence
    vuln_scores:      dict         # {asin: {score: 84, label: "Bleeding"}}
    profit_sims:      dict         # {strategy: {net_profit, verdict}} — OPTIONAL
    pivot_memo:       str          # Final LLM-generated strategy text
    confidence:       float        # Detective confidence 0.0–1.0
    loop_count:       int          # Guards against infinite loops (max 2)
```

### The graph structure

```
START
  │
  ▼
┌─────────────────────────────────────────────┐
│  NODE 1: WATCHMAN                           │
│  Scrape → Embed → Save                      │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│  NODE 2: DETECTIVE                          │
│  LLM reasons over signals                   │
│  Uses tools: semantic_search, price_history │◀─────┐
│  Outputs: signals[], confidence 0–1         │      │
└──────────────────────┬──────────────────────┘      │
                       │                             │
              ┌────────▼────────┐                    │
              │ confidence ≥0.7?│                    │
              └────────┬────────┘                    │
                 NO    │   YES                       │
      ┌────────────────┘    │         if loop_count < 2
      │                     │         re-scrape for more data
      │◀────────────────────┘─────────────────────────┘
      │                     │
      │                     ▼
      │  ┌─────────────────────────────────────────────┐
      │  │  NODE 3: VULN CALC                          │
      │  │  Weighted formula → score 0–100 + label     │
      │  └──────────────────────┬──────────────────────┘
      │                         │
      │                         ▼
      │  ┌─────────────────────────────────────────────┐
      │  │  NODE 4: PROFIT SIM  [OPTIONAL]             │
      │  │  4 strategy simulations → ₹ net impact      │
      │  │  Skip if seller cost data not provided      │
      │  └──────────────────────┬──────────────────────┘
      │                         │
      │                         ▼
      │  ┌─────────────────────────────────────────────┐
      │  │  NODE 5: STRATEGIST                         │
      │  │  LLM generates pivot memo                   │
      │  │  3 ranked actions, margin-protected         │
      │  └──────────────────────┬──────────────────────┘
      │                         │
      │                         ▼
      │                        END
      │
      └─── (confidence loop back to Watchman, max 2x)
```

### Node 1: Watchman

**Responsibility:** Data acquisition layer. Scrapes, embeds, saves.

```
Input:  product_asin, competitor_asins
Output: scraped_data{}, embeddings_done=True

Actions:
  FOR each ASIN in [product_asin] + competitor_asins:
    1. scrape_product(asin)         → dict {price, rating, reviews[], ...}
    2. save_price_to_db(asin, price) → SQLite: price_history table
    3. save_review_stats(asin, data) → SQLite: review_stats table
    4. chroma.collection.add(        → embed reviews as vectors
         documents=reviews,
         ids=[f"{asin}_{i}_{ts}"],
         metadatas=[{"asin": asin}]
       )
  
Log emitted: "[WATCHMAN] Scraped {n} products. Embedded {m} reviews."
```

**Sample state after Watchman:**

```json
{
  "scraped_data": {
    "B0CDEF456": {
      "asin": "B0CDEF456",
      "name": "XYZ Budget Earphones",
      "price": 699,
      "rating": 3.1,
      "reviews": ["Sound dies after 2 weeks...", "Left ear stopped..."],
      "avg_sentiment": -0.68,
      "review_count": 45,
      "review_spike": 45
    }
  },
  "embeddings_done": true
}
```

---

### Node 2: Detective

**Responsibility:** The reasoning brain. Uses LLM + tools to understand *why* signals exist.

```
Input:  scraped_data, embeddings_done
Output: signals[], confidence (0.0–1.0)

FOR each competitor_asin:
  Tool call 1: semantic_search_reviews(
    query="quality issues sound problems broken defective",
    asin=competitor_asin,
    n=15
  )
  → Returns 15 most semantically similar reviews from Chroma
  
  Tool call 2: get_price_history(asin=competitor_asin, days=30)
  → Returns [{date, price}, ...] from SQLite
  
  Tool call 3: get_review_sentiment_stats(asin=competitor_asin)
  → Returns {avg_sentiment, review_count, rating, review_spike}
  
  LLM prompt: [scraped context + tool results]
  → Reasons: "Is this competitive or distress pricing?"
  → Outputs: {problem_pattern, price_drop_reason, confidence, signals[]}

Conditional edge:
  IF confidence < 0.7 AND loop_count < 2:
    → route back to WATCHMAN (re-scrape with fresh request)
  ELSE:
    → route forward to VULN CALC
```

**Sample Detective output:**

```json
{
  "signals": [
    {
      "asin": "B0CDEF456",
      "problem_pattern": "Manufacturing defect — audio driver failure on left channel after ~14 days",
      "price_drop_reason": "distress",
      "buyer_intent_shift": "Churned XYZ buyers searching 'durable earphones' as replacement",
      "confidence": 0.94,
      "signals": [
        {"type": "critical", "text": "38/45 reviews confirm identical failure mode"},
        {"type": "critical", "text": "Rating velocity −0.06★/day — accelerating"},
        {"type": "medium",   "text": "Price cut is reactive, no new listing copy"},
        {"type": "medium",   "text": "Replacement keyword surge +34% this week"}
      ]
    }
  ],
  "confidence": 0.94,
  "loop_count": 0
}
```

---

### Node 3: VulnCalc

**Responsibility:** Converts multi-signal analysis into a single 0–100 score with business label.

```
Input:  signals[], scraped_data
Output: vuln_scores{asin: {score, label, components}}

Formula:
  neg_sentiment_score = min((-avg_sentiment) × 100, 100)   → ×0.4
  price_drop_score    = min(price_drop_pct × 3, 100)       → ×0.3
  review_spike_score  = min(review_spike × 2, 100)         → ×0.2
  rating_drop_score   = min(rating_drop × 25, 100)         → ×0.1
  
  TOTAL = (neg_sentiment×0.4) + (price_drop×0.3) + (spike×0.2) + (rating×0.1)

Labels:
  > 70   → "Bleeding"   — immediate pivot required
  40–70  → "Vulnerable" — prepare strategy, act within 48h
  20–40  → "Stable"     — monitor
  < 20   → "Healthy"    — low priority
```

**Sample calculation with real numbers:**

```
neg_sentiment_score  = (-(-0.68)) × 100 = 68.0    →  ×0.4 = 27.2
price_drop_pct       = (899-699)/899 × 100 = 22.2% →  min(22.2×3, 100) = 66.6  →  ×0.3 = 19.98
review_spike_score   = min(45×2, 100) = 90.0       →  ×0.2 = 18.0
rating_drop_score    = (4.2-3.1) × 25 = 27.5       →  ×0.1 = 2.75

TOTAL = 27.2 + 19.98 + 18.0 + 2.75 = 67.93
LABEL = "Vulnerable" (40–70 range)
```

**Sample state after VulnCalc:**

```json
{
  "vuln_scores": {
    "B0CDEF456": {
      "score": 67.93,
      "label": "Vulnerable",
      "components": {
        "neg_sentiment": 27.2,
        "price_drop": 19.98,
        "review_spike": 18.0,
        "rating_drop": 2.75
      }
    }
  }
}
```

---

### Node 4: ProfitSim *(Optional)*

**Responsibility:** Model the ₹ net profit impact of each possible strategy using seller's actual cost data. This node is **skipped** if the seller has not provided cost data in their product configuration.

```
Input:  vuln_scores, seller cost data {price, cost, monthly_units}
Output: profit_sims{strategy: {verdict, net_profit, units, margin}}

IF seller_cost_data not provided:
  → profit_sims = {}   (empty)
  → proceed to Strategist with signals only

ELSE:
  my_price         = 999
  my_cost          = 550
  my_margin        = 449      (per unit)
  baseline_units   = 40
  baseline_profit  = 449 × 40 = 17,960

  Strategy A — Match competitor price (₹699):
    match_margin   = 699 − 550 = 149
    est_units      = 40 × 1.25 = 50   (volume uplift estimate)
    gross_profit   = 149 × 50 = 7,450
    net_vs_baseline = 7,450 − 17,960 = −10,510
    verdict        = "AVOID"

  Strategy B — Hold price (₹999):
    margin unchanged
    est_units = 40 (no change)
    net_vs_baseline = 0
    verdict    = "SAFE — misses opportunity"

  Strategy C — Ad campaign (spend ₹3,000):
    ad_spend       = 3,000
    incremental_units = 65   (from keyword intent analysis)
    gross_from_ads = 65 × 449 = 29,185
    net_profit     = 29,185 − 3,000 = 26,185
    net_vs_baseline = 26,185 − 17,960 = +8,225
    verdict        = "RECOMMENDED"

  Strategy D — Bundle (price ₹1,299):
    bundle_cost    = 550 + 130 = 680
    bundle_margin  = 1,299 − 680 = 619
    est_units      = 22  (lower volume, higher margin)
    gross_profit   = 619 × 22 = 13,618
    net_vs_baseline = 13,618 − 17,960 = −4,342
    verdict        = "ALTERNATIVE — margin up, volume down"
```

**How to mark ProfitSim as optional in the graph:**

```python
def should_run_profit_sim(state: AgentState) -> str:
    """Conditional edge: skip ProfitSim if no cost data provided."""
    product_data = state["scraped_data"].get(state["product_asin"], {})
    if product_data.get("cost"):
        return "profit_sim"     # route to ProfitSim
    return "strategist"         # skip directly to Strategist

# In graph builder:
builder.add_conditional_edges(
    "vuln_calc",
    should_run_profit_sim,
    {"profit_sim": "profit_sim", "strategist": "strategist"}
)
```

---

### Node 5: Strategist

**Responsibility:** Generate the final human-readable Pivot Memo. Always margin-protected. Uses profit_sims if available, falls back to signal-only reasoning if not.

```
Input:  vuln_scores, signals, profit_sims (may be empty)
Output: pivot_memo (string)

LLM prompt includes:
  - Seller cost structure (if available)
  - Best strategy from profit_sims (if available)
  - Vulnerability scores + labels
  - Detected signal patterns
  - STRICT instruction: never recommend price cuts without margin analysis

Output format:
  ## PIVOT MEMO — {date}
  
  SITUATION: [2-sentence summary]
  
  ACTION 1 (RECOMMENDED) — Net impact: [₹ figure if available]
  [Action title]
  [Specific reasoning]
  
  ACTION 2 (ALTERNATIVE) — Net impact: [₹ figure if available]
  ...
  
  ACTION 3 (DEFENSIVE) — Net impact: [₹ figure if available]
  ...
  
  WHAT NOT TO DO:
  [Price-match warning with margin impact if cost data available]
```

**Sample Strategist output (with ProfitSim data):**

```
## PIVOT MEMO — 14 March 2026

SITUATION:
XYZ Budget Earphones has entered a quality-driven crisis. Their 22% price
cut is distress pricing — 38/45 recent reviews confirm an audio driver
failure. This is an acquisition opportunity, not a competitive threat.

ACTION 1 (RECOMMENDED) — Net impact: +₹8,225/month vs baseline
Launch "Durable Earphones" PPC campaign at ₹3,000 spend.
Target: replacement-intent buyers who already bought XYZ.
Your 4.6★ vs their 3.1★ is your creative angle. Price stays at ₹999.

ACTION 2 (ALTERNATIVE) — Net impact: +₹2,000 est. (conversion lift)
Add "Sound Quality Guarantee" badge to listing A+ content.
Update bullet 1 to lead with "18-month durability tested."
Quality messaging is extremely potent while competitor bleeds.

ACTION 3 (DEFENSIVE) — Net impact: −₹2,000 est. (margin dip)
Minor adjust to ₹949 (−₹50 only). Target SoundMax Pro (₹1,199) buyers.
Only use if ad spend is not feasible this month.

WHAT NOT TO DO:
Matching ₹699 costs ₹10,510/month in margin loss.
XYZ's brand is now permanently associated with poor quality.
The correct position is quality premium — not price parity.
```

**Sample Strategist output (without ProfitSim — signals only):**

```
## PIVOT MEMO — 14 March 2026

SITUATION:
Competitor B0CDEF456 shows critical vulnerability signals: negative
sentiment cluster around quality failure, accelerating rating drop,
and a price cut consistent with distress pricing behaviour.

ACTION 1 (RECOMMENDED)
Capture replacement-intent buyers with quality-focused ad creative.
Keyword: "durable earphones" (search spike detected).
Do not match competitor price — their brand damage is your advantage.

ACTION 2 (ALTERNATIVE)
Refresh listing A+ content emphasising durability and quality.
This positions your product as the obvious upgrade.

ACTION 3 (DEFENSIVE)
Minor price adjustment (5–10%) if needed to improve conversion.
Avoid aggressive cuts until margin impact is assessed.

NOTE: Add your cost data in Settings to enable exact ₹ profit projections.
```

### Graph build — complete

```python
# agents/graph.py

def build_graph():
    builder = StateGraph(AgentState)

    # Register nodes
    builder.add_node("watchman",    watchman_node)
    builder.add_node("detective",   detective_node)
    builder.add_node("vuln_calc",   vuln_calc_node)
    builder.add_node("profit_sim",  profit_sim_node)    # optional
    builder.add_node("strategist",  strategist_node)

    # Entry point
    builder.set_entry_point("watchman")

    # Linear edges
    builder.add_edge("watchman", "detective")
    builder.add_edge("profit_sim", "strategist")
    builder.add_edge("strategist", END)

    # Conditional: Detective confidence loop
    builder.add_conditional_edges(
        "detective",
        detective_should_loop,          # returns "watchman" or "vuln_calc"
        {"watchman": "watchman", "vuln_calc": "vuln_calc"}
    )

    # Conditional: ProfitSim optional
    builder.add_conditional_edges(
        "vuln_calc",
        should_run_profit_sim,          # returns "profit_sim" or "strategist"
        {"profit_sim": "profit_sim", "strategist": "strategist"}
    )

    return builder.compile()


def detective_should_loop(state: AgentState) -> str:
    if state["confidence"] < 0.7 and state["loop_count"] < 2:
        return "watchman"
    return "vuln_calc"


def should_run_profit_sim(state: AgentState) -> str:
    product_data = state["scraped_data"].get(state["product_asin"], {})
    return "profit_sim" if product_data.get("cost") else "strategist"
```

---

## 7. End-to-End Data Flow with Sample Data

This traces one complete scan cycle for **Premium Earphones (B0CXYZ123)** monitoring **XYZ Budget Earphones (B0CDEF456)**.

### Step-by-step with real values

```
┌─────────────────────────────────────────────────────────────┐
│  TRIGGER                                                    │
│  POST /scan?product_asin=B0CXYZ123                         │
│           &competitor_asins=B0CDEF456,B0ABCD789            │
│                                                             │
│  Response: {"job_id": "7f3a91c2", "status": "started"}     │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  WATCHMAN                                                   │
│                                                             │
│  scrape_product("B0CDEF456"):                               │
│    GET amazon.in/dp/B0CDEF456                               │
│    BS4 parse → price: 699.0                                 │
│    BS4 parse → rating: 3.1                                  │
│    BS4 parse → name: "XYZ Budget Earphones"                 │
│    sleep(2.3s)  ← polite delay                              │
│                                                             │
│    GET amazon.in/product-reviews/B0CDEF456?pageNumber=1     │
│    BS4 select [data-hook="review-body"] → 15 reviews        │
│    sleep(2.8s)                                              │
│    GET amazon.in/product-reviews/B0CDEF456?pageNumber=2     │
│    BS4 select → 15 more reviews                             │
│    sleep(3.1s)                                              │
│    GET ...?pageNumber=3 → 15 more reviews                   │
│    Total: 45 reviews collected                              │
│                                                             │
│    TextBlob sentiment per review:                           │
│      "Sound dies after 2 weeks..." → −0.82                  │
│      "Left ear stopped working..."  → −0.74                 │
│      "Amazing price but poor qual"  → −0.31                 │
│      avg_sentiment = −0.68                                  │
│                                                             │
│    Chroma embed:                                            │
│      45 texts → 45 × 384-dim vectors                        │
│      stored with metadata {asin: "B0CDEF456"}               │
│                                                             │
│    SQLite write:                                            │
│      price_history: (B0CDEF456, 699.0, "2026-03-14")       │
│      review_stats:  (B0CDEF456, −0.68, 45, 3.1, 45, now)   │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  DETECTIVE                                                  │
│                                                             │
│  Tool call 1 → semantic_search_reviews(                     │
│    query="quality issues sound problems broken defective",  │
│    asin="B0CDEF456", n=15                                   │
│  )                                                          │
│  Chroma cosine search → 38 of 45 match (threshold >0.72)   │
│  Top result: "Sound dies completely..." (sim: 0.91)         │
│                                                             │
│  Tool call 2 → get_price_history("B0CDEF456", days=30)     │
│  SQLite query →                                             │
│    [{"date":"2026-03-14","price":699},                      │
│     {"date":"2026-02-25","price":799},                      │
│     {"date":"2026-02-12","price":899}]                      │
│  Price delta: −22.2% over 30 days                           │
│                                                             │
│  LLM reasoning (GPT-4o-mini):                               │
│    "38/45 reviews confirm identical failure mode.           │
│     Price cut timing matches review spike — distress.       │
│     Buyer intent keyword 'durable earphones' surging.       │
│     Confidence: 0.94"                                       │
│                                                             │
│  Output signals:                                            │
│    {type: "critical", "38/45 reviews: sound dies"}          │
│    {type: "critical", "Rating −0.06★/day accelerating"}     │
│    {type: "medium",   "Distress pricing confirmed"}         │
│    {type: "medium",   "Replacement keyword surge +34%"}     │
│                                                             │
│  confidence = 0.94 ≥ 0.70  →  proceed to VulnCalc          │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  VULN CALC                                                  │
│                                                             │
│  neg_sentiment: (−(−0.68)) × 100 = 68.0   × 0.4 = 27.20   │
│  price_drop:    22.2 × 3 = 66.6            × 0.3 = 19.98   │
│  review_spike:  min(45×2, 100) = 90.0      × 0.2 = 18.00   │
│  rating_drop:   (4.2−3.1) × 25 = 27.5     × 0.1 =  2.75   │
│                                          ─────────────────  │
│                                 TOTAL =          67.93      │
│                                 LABEL = "Vulnerable"        │
│                                                             │
│  Cost data present? YES → route to ProfitSim               │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  PROFIT SIM (optional — cost data provided)                 │
│                                                             │
│  baseline: 40 units × ₹449 margin = ₹17,960/month          │
│                                                             │
│  match_price:  49 units × ₹149 = ₹7,301  → −₹10,659 AVOID │
│  hold_price:   40 units × ₹449 = ₹17,960 → ₹0      SAFE   │
│  ad_campaign:  65 units × ₹449 − ₹3,000 = ₹26,185         │
│                 → +₹8,225 vs baseline    RECOMMENDED        │
│  bundle:       22 units × ₹619 = ₹13,618 → −₹4,342 ALT    │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  STRATEGIST                                                 │
│                                                             │
│  LLM generates Pivot Memo:                                  │
│    ACTION 1: PPC ad campaign → +₹8,225/month               │
│    ACTION 2: A+ content quality refresh → +₹2,000 est.     │
│    ACTION 3: ₹949 minor adjustment (defensive)              │
│    WARNING:  Never match ₹699 — costs ₹10,659/month        │
│                                                             │
│  Result saved to SQLite: agent_results table               │
│  SSE event emitted: {"status": "done"}                      │
│  LangSmith trace: run_7f3a91c2                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 8. Frontend — React

### Component hierarchy

```
App                              ← owns: {page, scanning, logs} state
├── Sidebar                      ← nav links, live-dot pulse, next-scan countdown
│
├── PageIntelligence             ← main dashboard (default route)
│   ├── TopBar                   ← product name + ASIN pill + Run Scan button
│   ├── MetricCard ×4            ← KPI row: price · margin-at-risk · upside · signals
│   ├── CompetitorPanel
│   │   ├── VulnRing ×N          ← animated SVG score ring (0–100, color-coded)
│   │   └── BadgeLabel           ← Bleeding / Vulnerable / Stable / Healthy
│   ├── SignalPanel              ← colored dot + text for each detected signal
│   ├── Heatmap                  ← 7-day color grid (green→red by score)
│   ├── SimTabs                  ← [Match | Hold | Ads | Bundle] tab switcher
│   │   └── SimRow ×5            ← label + animated bar + ₹ value
│   ├── PivotMemo                ← 3 ranked strategy cards (only if Strategist ran)
│   ├── AgentLog                 ← auto-scrolling SSE log, color-coded by node
│   └── PriceChart               ← Chart.js line chart, 30-day history
│
├── PageCompetitors              ← all tracked ASINs, full stats table
├── PageReviews                  ← filterable review list + sentiment scores
├── PageAlerts                   ← dismissable alert cards by severity
└── PageSettings
    ├── ProductConfig            ← ASIN, cost, interval inputs
    ├── FeatureToggles           ← LangSmith · Apify · Scheduler · ProfitSim
    └── SaveButton
```

### State management

```javascript
// Root App — three pieces of shared state

const [page,     setPage]     = useState("intelligence");  // active page
const [scanning, setScanning] = useState(false);           // scan in progress
const [logs,     setLogs]     = useState([]);              // agent log lines

// Scan handler — fired by "Run Scan" button
const handleScan = useCallback(() => {
  if (scanning) return;
  setScanning(true);
  setLogs([]);

  // 1. Trigger scan
  fetch("/api/scan?product_asin=B0CXYZ123&competitor_asins=B0CDEF456")
    .then(r => r.json())
    .then(({ job_id }) => {

      // 2. Open SSE stream for live logs
      const source = new EventSource(`/api/job/${job_id}/stream`);
      source.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.status === "done") {
          source.close();
          setScanning(false);
          fetchLatestResults();   // update dashboard
          return;
        }
        setLogs(prev => [...prev, data]);   // append log line → re-render AgentLog
      };
    });
}, [scanning]);
```

### Key component patterns

**VulnRing — animated SVG:**

```jsx
function VulnRing({ score }) {
  const r = 26, circ = 2 * Math.PI * r;
  const filled = (score / 100) * circ;
  const color = score > 70 ? "#E24B4A" : score > 40 ? "#BA7517" : "#185FA5";
  
  return (
    <svg width="64" height="64" viewBox="0 0 64 64">
      <circle cx="32" cy="32" r={r} fill="none" stroke="#e8e6df" strokeWidth="4" />
      <circle
        cx="32" cy="32" r={r} fill="none"
        stroke={color} strokeWidth="4"
        strokeDasharray={`${filled} ${circ}`}
        strokeDashoffset={circ * 0.25}
        strokeLinecap="round"
        style={{ transform: "rotate(-90deg)", transformOrigin: "32px 32px" }}
      />
      <text x="32" y="37" textAnchor="middle" fontSize="13" fontWeight="600" fill={color}>
        {score}
      </text>
    </svg>
  );
}
```

**PriceChart — Chart.js with cleanup:**

```jsx
function PriceChart() {
  const canvasRef = useRef(null);
  const chartRef  = useRef(null);

  useEffect(() => {
    if (!canvasRef.current) return;
    if (chartRef.current) chartRef.current.destroy();  // prevent memory leak

    chartRef.current = new Chart(canvasRef.current, {
      type: "line",
      data: { /* price history datasets */ },
      options: { responsive: true, maintainAspectRatio: false }
    });

    return () => chartRef.current?.destroy();  // cleanup on unmount
  }, []);

  return (
    <div style={{ position: "relative", height: 200 }}>
      <canvas ref={canvasRef} />
    </div>
  );
}
```

**SimTabs — controlled tab switcher:**

```jsx
function SimTabs({ sims }) {
  const [active, setActive] = useState("ads");  // default to best strategy
  const sim = sims[active];

  return (
    <>
      <div className="tab-row">
        {Object.entries(sims).map(([key, s]) => (
          <button
            key={key}
            className={`tab ${active === key ? "active" : ""}`}
            onClick={() => setActive(key)}
          >
            {s.label}
          </button>
        ))}
      </div>
      {sim.rows.map(row => (
        <div className="sim-row" key={row.label}>
          <span>{row.label}</span>
          <div className="bar-bg">
            <div className="bar-fill" style={{ width: `${row.pct}%`, background: row.color }} />
          </div>
          <span style={{ color: row.color }}>{row.val}</span>
        </div>
      ))}
      <div className="verdict" style={{ color: sim.verdictColor }}>
        Verdict: {sim.verdict}
      </div>
    </>
  );
}
```

### Vite proxy config

The Vite dev server proxies `/api/*` to FastAPI on port 8000 — no CORS issues:

```javascript
// vite.config.js
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        rewrite: path => path.replace(/^\/api/, ""),
      }
    }
  }
});
```

### ProfitSim conditional rendering

Since ProfitSim is optional, the frontend handles the case where no sim data is returned:

```jsx
{profit_sims && Object.keys(profit_sims).length > 0 ? (
  <SimTabs sims={profit_sims} />
) : (
  <div className="info-box">
    Add your product cost in Settings to enable profit simulations.
  </div>
)}
```

---

## 9. Backend — FastAPI

### Endpoint catalog

| Method | Path | Description |
|---|---|---|
| `POST` | `/scan` | Trigger agent scan. Returns `{job_id}` immediately. Agent runs in background. |
| `GET`  | `/job/{id}` | Poll job status. Returns `{status, logs[], result}`. |
| `GET`  | `/job/{id}/stream` | SSE stream. Pushes log lines as agent progresses. Closes on `done`. |
| `GET`  | `/results/latest` | Most recent completed agent run. Used to populate dashboard on load. |
| `GET`  | `/price-history/{asin}` | Price history for any ASIN. Query param: `days` (default 30). |
| `GET`  | `/vulnerability-scores` | Latest scores from last run. |
| `GET`  | `/pivot-memo` | Latest generated strategy memo text. |
| `GET`  | `/health` | Liveness check. |

### SSE stream format

```
data: {"time":"2026-03-14T10:30:01","msg":"[WATCHMAN] Scraping B0CDEF456..."}
data: {"time":"2026-03-14T10:30:04","msg":"[WATCHMAN] Embedded 45 reviews into Chroma"}
data: {"time":"2026-03-14T10:30:08","msg":"[DETECTIVE] Semantic search: 38 matches (conf 0.94)"}
data: {"time":"2026-03-14T10:30:14","msg":"[DETECTIVE] Price delta: −22.2% over 30 days"}
data: {"time":"2026-03-14T10:30:22","msg":"[VULN_CALC] Score = 67.93 → Vulnerable"}
data: {"time":"2026-03-14T10:30:28","msg":"[PROFIT_SIM] ad_campaign: +₹8,225 net (RECOMMENDED)"}
data: {"time":"2026-03-14T10:30:41","msg":"[STRATEGIST] Memo generated. 3 ranked actions."}
data: {"status":"done"}
```

---

## 10. Database Schema

### SQLite tables

```sql
-- Price history: one row per scrape cycle per ASIN
CREATE TABLE price_history (
  id      INTEGER PRIMARY KEY AUTOINCREMENT,
  asin    TEXT    NOT NULL,
  price   REAL    NOT NULL,
  date    TEXT    NOT NULL   -- "2026-03-14"
);

-- Review statistics: one row per scrape cycle per ASIN
CREATE TABLE review_stats (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  asin           TEXT    NOT NULL,
  avg_sentiment  REAL,        -- TextBlob avg: −0.68
  review_count   INTEGER,     -- total reviews this cycle: 45
  rating         REAL,        -- current star rating: 3.1
  review_spike   INTEGER,     -- new reviews detected: 45
  scraped_at     TEXT         -- ISO datetime
);

-- Agent run results: full AgentState JSON blob per run
CREATE TABLE agent_results (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id       TEXT    NOT NULL,   -- "7f3a91c2"
  product_asin TEXT    NOT NULL,
  result_json  TEXT    NOT NULL,   -- full AgentState serialized
  created_at   TEXT    NOT NULL
);
```

### Chroma vector collection

```
Collection: "reviews"

Schema per document:
  document  (str):  "Sound dies completely after 2 weeks..."
  vector    (list): [0.12, −0.87, 0.33, ...]  ← 384 dimensions
  id        (str):  "B0CDEF456_0_1741910400"
  metadata  (dict): {"asin": "B0CDEF456"}

Query:
  collection.query(
    query_texts=["quality issues broken defective"],
    where={"asin": "B0CDEF456"},
    n_results=15
  )
  → returns top-15 reviews by cosine similarity
```

---

## 11. Optional: Profit Calculator Module

The profit calculator is an **opt-in feature**. It activates when the seller provides their product cost in Settings.

### How it's toggled

```
Settings → Product Config → "Your cost (₹)" field
  ├── Empty / not set  →  ProfitSim skipped  →  Strategist uses signals only
  └── Filled (e.g. 550) →  ProfitSim runs    →  Strategist gets full ₹ figures
```

### What it adds when enabled

- Exact ₹ net profit/loss for each of 4 strategies
- "AVOID / SAFE / RECOMMENDED / ALTERNATIVE" verdicts
- Warning label on any strategy that loses more than 20% margin
- Pivot Memo includes specific ₹ impact figures

### What the system still provides when disabled

- Vulnerability scores (0–100, labeled)
- Signal analysis (semantic cluster patterns, price drop reason)
- Ranked strategy recommendations (directional, no ₹ figures)
- Pivot Memo with qualitative reasoning

### Enabling in graph — conditional edge

```python
def should_run_profit_sim(state: AgentState) -> str:
    product = state["scraped_data"].get(state["product_asin"], {})
    return "profit_sim" if product.get("cost") else "strategist"
```

### Enabling in frontend — conditional render

```jsx
// PageIntelligence.jsx
const hasCostData = productConfig.cost && productConfig.cost > 0;

{hasCostData ? (
  <SimTabs sims={profit_sims} />
) : (
  <div className="optional-notice">
    Profit simulation is optional. Add your product cost in
    <button onClick={() => setPage("settings")}>Settings</button>
    to enable exact ₹ projections.
  </div>
)}
```

---

## 12. Antigravity Integration Guide

> **What is Antigravity?** Antigravity is a development orchestration platform. This section maps ProfitStory's agent stages to Antigravity's pipeline model for teams using it as their dev/staging environment.

### Stage mapping

Each LangGraph node maps to one Antigravity stage. Stages run sequentially with shared state passed as JSON between them.

```yaml
# antigravity.pipeline.yml

name: profitstory-ci
version: "1.0"
description: Competitive Intelligence Agent — ProfitStory PS-D3

env:
  OPENAI_API_KEY:    ${secrets.OPENAI_API_KEY}
  LANGSMITH_API_KEY: ${secrets.LANGSMITH_API_KEY}
  LANGCHAIN_TRACING_V2: "true"
  LANGCHAIN_PROJECT: "profitstory-ci"

state_store: sqlite          # shared AgentState persisted between stages
vector_store: chroma_local   # Chroma in-process, shared volume

stages:

  # ── Stage 1: Data Acquisition ─────────────────────────────────────────────
  - id: watchman
    name: "Watchman — scrape & embed"
    trigger: manual | schedule(every 2h)
    runtime: python3.11
    entry: agents/graph.py::watchman_node
    inputs:
      product_asin:    ${pipeline.params.product_asin}
      competitor_asins: ${pipeline.params.competitor_asins}
    outputs:
      scraped_data:    state.scraped_data
      embeddings_done: state.embeddings_done
    retry:
      max_attempts: 2
      on_failure: use_mock_data   # fallback: MOCK_PRODUCTS dict
    timeout: 120s

  # ── Stage 2: Signal Analysis ──────────────────────────────────────────────
  - id: detective
    name: "Detective — LLM reasoning loop"
    depends_on: [watchman]
    runtime: python3.11
    entry: agents/graph.py::detective_node
    inputs:
      scraped_data:    ${stages.watchman.outputs.scraped_data}
      embeddings_done: ${stages.watchman.outputs.embeddings_done}
      loop_count:      ${state.loop_count | default: 0}
    outputs:
      signals:    state.signals
      confidence: state.confidence
    conditional:
      - if: "state.confidence < 0.7 AND state.loop_count < 2"
        then: re_run(watchman)    # confidence loop
      - else: continue

  # ── Stage 3: Scoring ──────────────────────────────────────────────────────
  - id: vuln_calc
    name: "VulnCalc — vulnerability scoring"
    depends_on: [detective]
    runtime: python3.11
    entry: agents/graph.py::vuln_calc_node
    inputs:
      signals:      ${stages.detective.outputs.signals}
      scraped_data: ${stages.watchman.outputs.scraped_data}
    outputs:
      vuln_scores: state.vuln_scores

  # ── Stage 4: Profit Simulation (OPTIONAL) ─────────────────────────────────
  - id: profit_sim
    name: "ProfitSim — strategy simulation"
    depends_on: [vuln_calc]
    runtime: python3.11
    entry: agents/graph.py::profit_sim_node
    condition: "${pipeline.params.seller_cost != null}"  # skip if no cost data
    inputs:
      vuln_scores:  ${stages.vuln_calc.outputs.vuln_scores}
      scraped_data: ${stages.watchman.outputs.scraped_data}
    outputs:
      profit_sims: state.profit_sims
    on_skip:
      set: state.profit_sims = {}

  # ── Stage 5: Strategy Generation ──────────────────────────────────────────
  - id: strategist
    name: "Strategist — pivot memo"
    depends_on: [profit_sim]   # also runs if profit_sim was skipped
    runtime: python3.11
    entry: agents/graph.py::strategist_node
    inputs:
      vuln_scores:  ${stages.vuln_calc.outputs.vuln_scores}
      signals:      ${stages.detective.outputs.signals}
      profit_sims:  ${state.profit_sims | default: {}}
    outputs:
      pivot_memo: state.pivot_memo
    post_run:
      - save_to_sqlite: agent_results
      - emit_sse: "done"
      - langsmith_flush: true
```

### Antigravity environment variables

```bash
# .antigravity.env

# Required
OPENAI_API_KEY=sk-...
LANGSMITH_API_KEY=ls-...
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=profitstory-ci

# Optional — activates ProfitSim
SELLER_COST=550
SELLER_PRODUCT_ASIN=B0CXYZ123
COMPETITOR_ASINS=B0CDEF456,B0ABCD789

# Scraping
REQUEST_DELAY_MIN=1.5    # seconds between Amazon requests
REQUEST_DELAY_MAX=4.0
MAX_REVIEWS_PER_ASIN=50

# Scheduling
SCAN_INTERVAL_HOURS=2

# LLM choice: openai | ollama
LLM_PROVIDER=openai
OLLAMA_MODEL=llama3       # used if LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
```

### Running in Antigravity

```bash
# Install Antigravity CLI (if not already)
pip install antigravity-cli

# Initialize project
antigravity init --config antigravity.pipeline.yml

# Run full pipeline (all 5 stages)
antigravity run \
  --param product_asin=B0CXYZ123 \
  --param competitor_asins=B0CDEF456,B0ABCD789 \
  --param seller_cost=550

# Run specific stage only (for development/debugging)
antigravity run --stage watchman
antigravity run --stage detective
antigravity run --stage vuln_calc

# Run without ProfitSim (skip cost-dependent stage)
antigravity run --param seller_cost=null

# Schedule recurring pipeline
antigravity schedule \
  --interval 2h \
  --param product_asin=B0CXYZ123 \
  --param competitor_asins=B0CDEF456,B0ABCD789

# View logs for a specific stage
antigravity logs --stage detective --tail 50

# View LangSmith traces
antigravity trace --open   # opens smith.langchain.com/project/profitstory-ci
```

### Stage-level development workflow

When developing individual nodes, each stage can be run in isolation with mock inputs:

```bash
# Test Detective node alone (skips scraping)
antigravity run --stage detective \
  --mock-input scraped_data='{"B0CDEF456": {"price": 699, "rating": 3.1, ...}}'

# Test VulnCalc with fixed signals
antigravity run --stage vuln_calc \
  --mock-input signals='[{"asin":"B0CDEF456","confidence":0.94}]'

# Test Strategist without ProfitSim
antigravity run --stage strategist \
  --mock-input profit_sims='{}'
```

---

## 13. Setup & Running Locally

### Prerequisites

- Python 3.11+
- Node.js 18+
- 4 GB RAM (8 GB for local Ollama LLM)

### Backend setup

```bash
# Clone and set up virtual environment
git clone <repo-url>
cd profitstory_ci

python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
python -m textblob.download_corpora

# Create environment file
cat > .env << 'EOF'
OPENAI_API_KEY=sk-...
LANGSMITH_API_KEY=ls-...
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=profitstory-ci
EOF

# Start backend
cd api
uvicorn main:app --reload --port 8000
# Swagger docs: http://localhost:8000/docs
```

### Frontend setup

```bash
cd frontend
npm install
npm run dev
# Opens at http://localhost:3000
```

### Switch to Ollama (fully free, offline)

```bash
# Install Ollama
curl https://ollama.ai/install.sh | sh
ollama pull llama3

# In agents/graph.py:
# Replace:
#   from langchain_openai import ChatOpenAI
#   llm = ChatOpenAI(model="gpt-4o-mini")
#
# With:
#   from langchain_community.chat_models import ChatOllama
#   llm = ChatOllama(model="llama3", temperature=0.1)
```

### Trigger first scan

```bash
# Start scan
curl -X POST "http://localhost:8000/scan?product_asin=B0CXYZ123&competitor_asins=B0CDEF456"

# Response:
# {"job_id": "7f3a91c2", "status": "started"}

# Poll until done
curl "http://localhost:8000/job/7f3a91c2"

# Get pivot memo
curl "http://localhost:8000/pivot-memo"
```

### requirements.txt

```
# Core
fastapi==0.111.0
uvicorn[standard]==0.29.0
python-multipart==0.0.9

# Agent
langgraph==0.1.14
langchain==0.2.1
langchain-openai==0.1.8
langsmith==0.1.63

# Vector DB
chromadb==0.5.0

# Scraping
requests==2.32.0
beautifulsoup4==4.12.3
textblob==0.18.0

# Scheduler
apscheduler==3.10.4

# Data
pandas==2.2.2

# Dev
python-dotenv==1.0.1
```

---

## 14. Project File Structure

```
profitstory_ci/
│
├── agents/
│   └── graph.py                  # LangGraph 5-node agent (main brain)
│
├── api/
│   └── main.py                   # FastAPI: endpoints, SSE streaming, background tasks
│
├── scraper/
│   └── amazon_scraper.py         # requests + BS4 scraper with mock fallback
│
├── frontend/
│   ├── index.html                # Vite HTML shell
│   ├── main.jsx                  # React entry point
│   ├── App.jsx                   # Full app: all components + pages
│   ├── vite.config.js            # Vite + proxy to FastAPI
│   └── package.json              # React 18, Chart.js, Vite
│
├── antigravity.pipeline.yml      # Antigravity stage definitions
├── requirements.txt              # Python dependencies
├── .env                          # API keys (gitignored)
├── profitstory.db                # SQLite database (auto-created on first run)
└── PROFITSTORY_CI.md             # This file
```

---

## 15. Glossary

| Term | Definition |
|---|---|
| **ASIN** | Amazon Standard Identification Number — unique 10-character product identifier. |
| **AgentState** | The typed Python dictionary passed between LangGraph nodes. Each node reads it and adds its outputs. |
| **Agentic AI** | AI that autonomously decides what actions to take, uses tools, and loops until a goal is met — not a fixed script. |
| **APScheduler** | Python library for running scheduled background jobs. Used to trigger re-scans every 2 hours. |
| **BeautifulSoup4** | Python HTML parsing library. Extracts structured data from raw HTML using CSS selectors. |
| **Chroma** | Open-source in-process vector database. Stores text as numerical vectors, retrieves by semantic similarity. |
| **Conditional edge** | A LangGraph edge that routes to different nodes based on runtime state. Used for the confidence loop. |
| **Cosine similarity** | Measure of angle between two vectors. Used by Chroma to rank reviews by semantic closeness (0 = perpendicular, 1 = identical direction). |
| **Distress pricing** | A price cut driven by crisis (quality failure, overstock) — not competitive strategy. Signals opportunity. |
| **Embedding** | A numerical vector (list of floats) representing the meaning of text. Similar meaning → vectors point in similar directions. |
| **LangGraph** | Python framework for stateful, cyclic agent workflows as directed graphs. Extends LangChain. |
| **LangSmith** | Observability platform for LangChain/LangGraph. Traces every LLM call and agent step. Free tier. |
| **LLM** | Large Language Model — neural network trained on text that can reason, summarize, generate. GPT-4o-mini and llama3 used here. |
| **Polarity score** | TextBlob's sentiment output per text. Range −1.0 (very negative) to +1.0 (very positive). |
| **ProfitSim** | The optional Node 4 that models ₹ net profit impact of 4 strategies. Skipped if seller cost not provided. |
| **RAG** | Retrieval-Augmented Generation — retrieve relevant documents from Chroma, inject into LLM prompt to ground its reasoning. |
| **SSE** | Server-Sent Events — HTTP streaming protocol. Server pushes events to browser over a persistent connection without polling. |
| **VulnCalc** | Node 3: `(NegSentiment×0.4) + (PriceDropPct×0.3) + (ReviewSpike×0.2) + (RatingDrop×0.1)` = score 0–100. |
| **Vulnerability Score** | ProfitStory's 0–100 health metric for a competitor. >70 = Bleeding, 40–70 = Vulnerable, 20–40 = Stable, <20 = Healthy. |

---

*ProfitStory CI · PS-D3 · CIT M.Sc Data Science Hackathon · March 2026*  
*Stack: React + Vite · FastAPI · LangGraph · BeautifulSoup4 · Chroma · SQLite · TextBlob · LangSmith*
