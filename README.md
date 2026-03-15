# Shadowspy.ai

> **Competitive intelligence for e-commerce sellers** — track competitors, run AI-powered scans, and instantly get vulnerability scores, profit-at-risk simulations, and an AI-generated pivot strategy memo.

---

## What it does

E-commerce sellers face a competitive intelligence wall — prices shift multiple times a day, and review sentiment nuances (a competitor's quality crisis vs. genuine pricing pressure) require completely different responses. Shadowspy.ai closes that gap.

```
Competitor drops price 22%  →  Traditional tool: "Lower your price"  ✗
                            →  Shadowspy.ai:
                               • 38/45 reviews confirm audio driver failure
                               • Rating velocity: −0.06★/day (accelerating)
                               • Distress pricing confirmed (not competitive)
                               • Action: Ad campaign targeting displaced buyers
                               • Net impact: +₹8,225/month vs price-matching (−₹10,659)  ✓
```

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    BROWSER (React SPA)                       │
│   Dashboard │ Competitors │ Reviews │ Signals │ Pivot Memo   │
└─────────────────────────┬────────────────────────────────────┘
                          │  REST + SSE
┌─────────────────────────▼────────────────────────────────────┐
│                  FastAPI  (port 8000)                        │
│  /scan → BackgroundTask → job_id                             │
│  /job/{id}/stream → SSE live logs                            │
└─────────────────────────┬────────────────────────────────────┘
                          │
┌─────────────────────────▼────────────────────────────────────┐
│               LangGraph Agent Pipeline                       │
│                                                              │
│  Watchman → Detective → Vuln_calc → Profit_sim → Strategist  │
└──────────────┬───────────────────────────────────────────────┘
               │
   ┌───────────▼───────────┐
   │  Neon PostgreSQL       │
   │  • sellers / products  │
   │  • agent_runs / logs   │
   │  • review_embeddings   │
   │    (pgvector 1536-d)   │
   └───────────────────────┘
```

### The 5-node agent loop

| Node | Job |
|------|-----|
| **Watchman** | Scrapes Amazon/Flipkart/Snapdeal, embeds reviews into pgvector, saves price history |
| **Detective** | Semantic search over reviews + LLM reasoning to distinguish *distress* vs *competitive* pricing |
| **Vuln_calc** | Weighted formula → 0–100 vulnerability score (`Bleeding / Vulnerable / Stable / Healthy`) |
| **Profit_sim** | ₹ net impact for 4 strategies: Match Price, Hold Price, Ad Campaign, Bundle |
| **Strategist** | LLM-generated Pivot Memo — 3 ranked actions, margin-protected, never recommends blind price cuts |

---

## Tech stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.11, FastAPI, Uvicorn, SQLAlchemy, JWT auth |
| **Database** | Neon PostgreSQL + pgvector (1536-d embeddings) |
| **Agent / LLM** | LangGraph, LangChain, Gemini (`gemini-3.1-flash-lite`) or OpenAI |
| **Embeddings** | Gemini `gemini-embedding-2-preview` or OpenAI `text-embedding-3-small` |
| **Scraping** | requests + BeautifulSoup4 (Amazon, Flipkart, Snapdeal) |
| **Frontend** | React 18, Vite, React Router, Axios, Chart.js, Lucide |
| **Deployment** | Docker + docker-compose, nginx reverse proxy |

---

## Project structure

```
profitstory_ci/
├── api/              # FastAPI — endpoints, auth, DB, vector_db
├── agents/           # LangGraph 5-node pipeline
├── scraper/          # Platform scrapers (Amazon, Flipkart, Snapdeal)
├── db/               # SQLAlchemy models & migrations
├── frontend/         # React + Vite SPA
├── docker/           # nginx.conf
├── Dockerfile.backend
├── Dockerfile.frontend
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

---

## Running locally

### Prerequisites
- Python 3.11+, Node.js 18+
- A [Neon](https://neon.tech) PostgreSQL database (free tier works)
- Gemini or OpenAI API key

### 1. Clone & configure

```bash
git clone <repo-url>
cd profitstory_ci
cp .env.example .env
# Edit .env — set DATABASE_URL, GOOGLE_API_KEY (or OPENAI_API_KEY), JWT_SECRET
```

### 2. Backend

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn api.main:app --reload --port 8000
# Swagger: http://localhost:8000/docs
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
# App: http://localhost:3000
```

---

## Running with Docker

```bash
# Build and start both services
docker compose up --build -d

# Logs
docker compose logs -f

# Stop
docker compose down
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| Swagger docs | http://localhost:8000/docs |

> `.env` is baked into the backend image at build time — all keys are picked up automatically.

---

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | ✅ | Neon PostgreSQL connection string |
| `GOOGLE_API_KEY` | ✅* | Gemini LLM + embeddings |
| `OPENAI_API_KEY` | ✅* | OpenAI LLM + embeddings (alternative) |
| `JWT_SECRET` | ✅ | Secret for JWT auth tokens |
| `LLM_PROVIDER` | — | `gemini` (default) or `openai` |
| `GEMINI_MODEL` | — | e.g. `gemini-3.1-flash-lite-preview` |
| `SCRAPERAPI_KEY` | — | ScraperAPI key for anti-bot scraping |
| `LANGSMITH_API_KEY` | — | LangSmith observability (optional) |

*One of `GOOGLE_API_KEY` or `OPENAI_API_KEY` is required.

---

## Key features

- **Multi-tenant** — each seller has isolated products, competitors, and scan history
- **Live scan logs** — SSE stream shows agent progress in real time as it runs
- **Bleeding logic** — competitors with ~2★ ratings scored negatively (opportunity, not threat)
- **Profit simulation** — exact ₹ net impact for each strategy when cost data is provided
- **Margin-protected advice** — Strategist node never recommends price cuts without margin analysis
- **Fallback scraping** — mock data used when Amazon blocks requests so demo never breaks

---

*Shadowspy.ai · CIT M.Sc Data Science Hackathon 2026 · Stack: React · FastAPI · LangGraph · pgvector · Neon · Gemini*
