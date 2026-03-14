# Shadowspy.ai — Presentation Slides

Use this document for your presentation. Each section below is one slide (or slide group). You can copy into Google Slides, PowerPoint, or use a Markdown-to-slides tool (e.g. Marp, reveal.js).

---

## 1. Problem & Solution

### Problem
- **E-commerce sellers** struggle to track competitor prices, reviews, and positioning in real time.
- Manual monitoring does not scale; sellers miss **pricing risks** (matching a competitor’s low price can erode margin).
- Hard to know **when to act** (hold price vs match vs invest in ads) and what the **profit impact** is.
- No single place to get an **actionable strategy memo** based on live data and AI.

### Solution: Shadowspy.ai
- **Competitive intelligence platform** that scrapes your product and competitors, embeds reviews in a vector DB, and runs an **AI agent pipeline** to produce:
  - **Vulnerability scores** (including “bleeding” logic for low-rated competitors).
  - **Profit-at-risk simulation** (Match vs Hold vs Ad Campaign) with bar and pie charts.
  - **Review signals** (e.g. quality issues, distress pricing).
  - **AI Pivot Memo** with recommended actions.
- **Multi-tenant**: each seller has their own products and competitors; scans and results are isolated.
- **Single cloud DB (Neon)** for app data + embeddings to reduce complexity.

---

## 2. Methodology & Implementation

### Methodology
- **Scrape → Embed → Analyze → Score → Simulate → Synthesize**
  1. **Watchman**: Scrape product and competitor pages (Amazon/Flipkart/Snapdeal); save price/review stats; embed reviews into pgvector.
  2. **Detective**: Semantic search over reviews + LLM to extract signals (e.g. distress vs competitive pricing, quality issues).
  3. **Vuln_calc**: Mathematical vulnerability scores; **bleeding logic** for ~2-star competitors (negative impact).
  4. **Profit_sim**: Net impact for Match Price, Hold Price, Ad Campaign using your price/cost and competitor prices.
  5. **Strategist**: LLM-generated Pivot Memo (situation, recommended actions, what not to do).

### Implementation highlights
- **Backend**: FastAPI; JWT auth; product/competitor CRUD; scan trigger; job result and stream endpoints; Neon PostgreSQL (sellers, products, agent_runs, scrape logs, embeddings).
- **Frontend**: React (Vite), tabbed Analysis (Strategy & charts, Competitors & signals, Pivot memo); Chart.js for bar and pie charts.
- **Agent**: LangGraph state machine with conditional edges (e.g. re-scrape if confidence low; run profit_sim when cost/price available).

---

## 3. Technology Used

| Layer | Technology |
|-------|------------|
| **Backend** | Python 3.x, FastAPI, Uvicorn, SQLAlchemy, bcrypt, python-jose |
| **Database** | Neon PostgreSQL (single DB: app + pgvector); SQLite fallback for local dev |
| **Vector / embeddings** | pgvector (1536-d), OpenAI or Gemini embeddings |
| **Agent / LLM** | LangGraph, LangChain, Gemini (e.g. gemini-3.1-flash-lite) or OpenAI |
| **Scraping** | requests, BeautifulSoup, platform-specific scrapers (Amazon, Flipkart, Snapdeal) |
| **Frontend** | React 18, Vite, React Router, Axios, Chart.js, Lucide icons |
| **Auth** | JWT (HS256), bearer token; optional token in query for SSE |
| **DevOps / config** | python-dotenv, .env for DATABASE_URL, API keys |

---

## 4. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SHADOWSPY.AI ARCHITECTURE                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────────────────────┐│
│  │   Browser    │────▶│  Vite/React  │────▶│  FastAPI (Backend)            ││
│  │  (Port 3000) │     │  Frontend    │     │  Auth, Products, Scan, Job     ││
│  └──────────────┘     └──────────────┘     │  Result, Logs, SSE Stream     ││
│         │                      │          └────────────┬───────────────────┘│
│         │                      │                       │                    │
│         │                      │          ┌────────────▼───────────────────┐│
│         │                      │          │  Neon PostgreSQL                ││
│         │                      │          │  • sellers, products,          ││
│         │                      │          │    competitors, agent_runs     ││
│         │                      │          │  • scrape_* tables,            ││
│         │                      │          │    agent_results,               ││
│         │                      │          │  • review_embeddings (pgvector)││
│         │                      │          └────────────┬───────────────────┘│
│         │                      │                       │                    │
│         │                      │          ┌────────────▼───────────────────┐
│         │                      │          │  LangGraph Agent Pipeline       ││
│         │                      │          │  Watchman → Detective →         ││
│         │                      │          │  Vuln_calc → Profit_sim →       ││
│         │                      │          │  Strategist                     ││
│         │                      │          └────────────┬───────────────────┘│
│         │                      │                       │                    │
│         │                      │          ┌────────────▼───────────────────┐
│         │                      │          │  External: Scrapers,             ││
│         │                      │          │  Gemini/OpenAI, Embeddings      ││
│         │                      │          └────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
```

**Data flow (high level)**  
User runs scan → Backend creates `agent_run`, enqueues workflow → Watchman scrapes and embeds → Detective extracts signals → Vuln_calc scores (incl. bleeding) → Profit_sim computes strategies → Strategist writes memo → Backend saves to DB → Frontend fetches result and shows tabs (Strategy charts, Competitors, Memo).

---

## 5. Feasibility

- **Technical**: Built with standard, well-supported stack (FastAPI, React, Neon, LangGraph). Single Neon DB keeps operations and deployment simpler.
- **Resource**: Can run backend and frontend on a single small server or split (e.g. frontend on Vercel, backend on Railway/Fly.io); Neon free tier sufficient for demo.
- **Scalability**: Multi-tenant from day one; scan runs are per-product and can be queued or rate-limited as needed.
- **Maintainability**: Clear separation (api/, agents/, db/, scraper/, frontend/); documentation and slides support onboarding and presentations.

---

## 6. Conclusion

- **Shadowspy.ai** addresses the need for **actionable competitive intelligence** for e-commerce sellers by combining **scraping, vector search, and an LLM-based agent pipeline** to produce vulnerability scores, profit-at-risk simulation, and an AI Pivot Memo.
- **Methodology** is implemented end-to-end: Watchman → Detective → Vuln_calc (with bleeding logic) → Profit_sim → Strategist, with results stored in a **single Neon PostgreSQL** database and surfaced in a **tabbed React UI** with charts.
- **Feasibility** is demonstrated through a working prototype, a clear architecture, and the use of widely adopted technologies.
- **Next steps** could include: more platforms (e.g. Meesho), historical trend charts, alerts, and optional A/B testing suggestions based on the pivot memo.

---

*Shadowspy.ai — Competitive intelligence for e-commerce sellers.*
