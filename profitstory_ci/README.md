# Shadowspy.ai

Competitive intelligence for e-commerce sellers: track competitors, run AI-powered scans, and get vulnerability scores, profit-at-risk simulation, and an AI pivot memo.

## Quick links

- **[Presentation (slides)](docs/PRESENTATION.md)** — Problem & Solution, Methodology & Implementation, Technology Used, Architecture Diagram, Feasibility, Conclusion.
- **[Detailed documentation](docs/DOCUMENTATION.md)** — Full technical docs: architecture, database, agent pipeline, API, setup.
- [Gemini setup](docs/GEMINI_SETUP.md) — LLM and embedding configuration.
- [Sample input](SAMPLE_INPUT.md) — Example scan input.

## Run locally

```bash
# Backend (from project root)
python -m venv venv && source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
# Set .env (see .env.example), including DATABASE_URL for Neon
uvicorn api.main:app --reload --port 8000

# Frontend
cd frontend && npm install && npm run dev -- --host
# Open http://localhost:3000
```

## Tech overview

- **Backend**: FastAPI, SQLAlchemy, Neon PostgreSQL (or SQLite fallback), JWT auth.
- **Agent**: LangGraph pipeline (Watchman → Detective → Vuln_calc → Profit_sim → Strategist); Gemini or OpenAI.
- **Frontend**: React (Vite), Chart.js, tabbed Analysis (Strategy charts, Competitors & signals, Pivot memo).
