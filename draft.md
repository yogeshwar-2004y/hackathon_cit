# Project Directive – Build a 24-Hour Hackathon MVP: ProfitStory Competitive Intelligence Agent (PS-D3)

You are an expert full-stack AI developer and retail strategy specialist. Your mission is to build a complete, demo-ready MVP for a 24-hour hackathon. The project solves "Competitive Intelligence Wall" for e-commerce sellers (Amazon/Flipkart style), aligned perfectly with **ProfitStory.ai** philosophy: prioritize **Net Profit** over Gross Revenue. Never suggest blind price drops — always protect/grow margins while winning market share.

## Core Problem We Are Solving
Sellers face fast-changing competitor prices + review sentiment that humans can't analyze in time. Traditional scrapers show raw data but miss connections (e.g., competitor price drop caused by quality complaints in reviews → opportunity to steal customers without cutting price).

We build an **agentic AI layer** that:
- Monitors competitors autonomously
- Cross-references pricing + reviews + sentiment
- Calculates **Competitor Vulnerability Score**
- Runs **Profit-at-Risk** simulations using seller's cost data
- Outputs **profit-first Pivot Memos** (e.g., "Don't match price — boost quality ads instead → +₹18k net profit")

Key mindset: Think like a "Chief Strategy Officer obsessed with net profit". Use agentic cycles (reason → check data → loop if needed).

## Target Demo Scope (Hackathon MVP – must run locally/demo in <24h)
- Track 1 seller product + 2–3 competitors (use Amazon ASINs)
- Scrape price + recent reviews (mock or real via free tools)
- Compute Vulnerability Score (0–100)
- Simulate profit impact of strategies
- Show clean dashboard with Pivot Memo
- Use LangGraph for agentic reasoning loops

## Tech Stack – Use ONLY these (all free/local for hackathon)
- **Frontend**: Streamlit (Python) → fast dashboard with cards, heatmaps, real-time updates
- **Backend API**: FastAPI → expose endpoints like /run-agent, /get-memo
- **Agent Orchestration**: LangGraph (from LangChain) → MUST use for cycles, stateful memory, tool-calling loops
- **LLM**: Groq (Llama-3.1-70B or Mixtral – fast & free tier) or fallback OpenAI GPT-4o-mini
- **Vector DB**: Chroma (local, embed reviews for semantic search)
- **Normal DB**: SQLite → store product costs, historical prices, scores
- **Scraping**: Playwright (dynamic pages) + Apify free tier actors (Amazon Product Reviews / Pricing)
- **Scheduler**: Simple Python loop / APScheduler for every 2h refresh (or manual trigger for demo)
- **Extras**: LangSmith (free tier) for trace visualization (judges love it)

NO paid infra, NO heavy cloud — everything runs on laptop.

## Architecture & Node Breakdown (LangGraph Graph)
Create a stateful LangGraph with these nodes (cyclic):
1. **Watchman** → Scrape price/reviews → embed into Chroma → save to SQLite
2. **Detective** → LLM reasoning loop:
   - Analyze signals
   - Use tools: semantic search Chroma ("quality complaints"), query SQLite history
   - Loop back if confidence low (e.g., "need more reviews")
3. **Vulnerability Calculator** → Score = (Neg Sentiment*0.4) + (Price Drop %*0.3) + (Review Spike*0.2) + (Rating Drop*0.1)
   - Output 0–100 + label ("Bleeding" >70, "Vulnerable" 40–70, etc.)
4. **Profit ROI Simulator** → Use seller cost data:
   - Calc margin loss if match price
   - Calc gain from alternative (e.g., +ad spend → steal customers)
5. **Strategist** → Generate formatted Pivot Memo:
   - 3 ranked actions
   - Profit impact in ₹
   - Never suggest pure price cut without margin protection

## Key Features to Implement (Killer for Judges)
1. **Competitor Vulnerability Score** + heatmap
2. **Profit-at-Risk Analysis** (exact ₹ loss/gain)
3. **Autonomous Pivot Memo** (one-page strategy card)

## Example Data for Testing
Your product:
- Name: Premium Earphones
- ASIN: B0CXYZ123 (mock)
- Price: ₹999
- Cost: ₹550
- Margin: ₹449/unit

Competitor:
- Name: XYZ Budget Earphones
- ASIN: B0CDEF456
- Price: dropped to ₹699 (was ₹899)
- Recent reviews: 45 new, 38 mention "sound dies", sentiment -0.68, rating 3.1

Expected output:
- Vulnerability: 84/100 ("Bleeding")
- Pivot: "Don't match price (lose ₹14k margin). Boost 'durable earphones' ads +₹3k → +₹18.5k net profit"

## Development Guidelines
- Structure repo:
/profitstory-agent/
├── app.py                # Streamlit frontend
├── api.py                # FastAPI backend
├── agent_graph.py        # LangGraph definition + nodes + tools
├── scraper.py            # Playwright/Apify logic
├── db.py                 # SQLite + Chroma helpers
├── prompts/              # System prompts for each node
├── data/                 # SQLite db + mock data
└── requirements.txt


- Use clean, modular code — docstrings + comments
- Add error handling (scraping fails → graceful fallback)
- Make dashboard beautiful: use st.markdown, st.metric, Altair/Pandas for heatmap
- For demo: include "Run Agent Now" button + scheduled mock trigger
- Final output: After building, explain how to run + demo flow

## First Steps You Should Take Right Now
1. Create the project folder structure above
2. Write requirements.txt with: streamlit, fastapi, uvicorn, langgraph, langchain, langchain-groq (or openai), chromadb, playwright, sqlite3, apscheduler, etc.
3. Implement db.py + scraper.py skeleton first
4. Then build agent_graph.py with LangGraph
5. Connect FastAPI → graph
6. Finish with Streamlit dashboard

Start building now. Ask me clarifying questions only if truly blocked. Output code files one by one when ready, with explanations. Let's win this hackathon — focus on agentic profit intelligence!
