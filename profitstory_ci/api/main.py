import os
import json
import uuid
import time
import asyncio
from typing import Optional
from fastapi import FastAPI, BackgroundTasks, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load env vars
load_dotenv()

# Disable LangSmith tracing to avoid 403 Forbidden (comment out next line and set a valid LANGSMITH_API_KEY to re-enable)
os.environ["LANGCHAIN_TRACING_V2"] = "false"

from api.db import init_db, get_latest_agent_result, save_agent_result
from api.vector_db import list_embeddings
from agents.graph import build_graph

app = FastAPI(title="ProfitStory CI Dashboard")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize DB on startup
@app.on_event("startup")
def startup_event():
    init_db()
    # Create an empty agent.log if it doesn't exist
    if not os.path.exists("agent.log"):
        open("agent.log", "w").close()

# The global agent graph
agent_graph = build_graph()

def run_agent_workflow(job_id: str, product_asin: str, competitor_asins: list[str]):
    # Clear log file for new run
    with open("agent.log", "w") as f:
        f.write("")
        
    initial_state = {
        "product_asin": product_asin,
        "competitor_asins": competitor_asins,
        "scraped_data": {},
        "embeddings_done": False,
        "signals": [],
        "vuln_scores": {},
        "profit_sims": {},
        "pivot_memo": "",
        "confidence": 1.0,
        "loop_count": 0
    }
    
    # We optionally can pass config or just run
    try:
        final_state = agent_graph.invoke(initial_state)
        # Save exact result to SQLite
        save_agent_result(
            run_id=job_id,
            product_asin=product_asin,
            result_json=json.dumps(final_state),
            created_at=time.strftime("%Y-%m-%dT%H:%M:%S")
        )
        
        # Write "done" message to SSE log
        with open("agent.log", "a") as f:
            f.write(json.dumps({"status": "done"}) + "\n")
            
    except Exception as e:
        with open("agent.log", "a") as f:
            f.write(json.dumps({"status": "error", "msg": str(e)}) + "\n")


@app.post("/scan")
async def trigger_scan(
    background_tasks: BackgroundTasks,
    product_asin: str = "B0CP54XBWN",
    competitor_asins: str = "B0F7LY85KB"
):
    job_id = str(uuid.uuid4())[:8]
    comp_asins_list = [c.strip() for c in competitor_asins.split(",") if c.strip()]
    
    background_tasks.add_task(run_agent_workflow, job_id, product_asin, comp_asins_list)
    return {"job_id": job_id, "status": "started"}


async def log_reader():
    # Tail the agent.log file to push SSE
    filename = "agent.log"
    with open(filename, "r") as f:
        f.seek(0, 2) # Move to end (since it resets on /scan)
        
        # Actually wait, if the endpoint is hit slightly after /scan, the file might have already been reset.
        # So we should read from the beginning. Let's just read from 0.
        f.seek(0, 0)
        
        while True:
            line = f.readline()
            if not line:
                await asyncio.sleep(0.5)
                continue
            
            data = json.loads(line)
            yield f"data: {json.dumps(data)}\n\n"
            
            if data.get("status") in ["done", "error"]:
                break

@app.get("/job/{job_id}/stream")
async def job_stream(job_id: str):
    return StreamingResponse(log_reader(), media_type="text/event-stream")


# Resolve agent.log relative to project root (parent of api/)
LOG_FILE = os.path.join(os.path.dirname(__file__), "..", "agent.log")
LOG_FILE = os.path.abspath(LOG_FILE)

@app.get("/logs")
async def get_logs(limit: int = 200):
    """Return recent backend/agent log lines (from agent.log)."""
    if not os.path.exists(LOG_FILE):
        return {"lines": [], "message": "No logs yet."}
    try:
        with open(LOG_FILE, "r") as f:
            lines = f.readlines()
        # Each line is JSON: {"time": "...", "msg": "..."} or {"status": "done"}
        parsed = []
        for line in lines[-limit:] if limit else lines:
            line = line.strip()
            if not line:
                continue
            try:
                parsed.append(json.loads(line))
            except json.JSONDecodeError:
                parsed.append({"msg": line, "raw": True})
        return {"lines": parsed}
    except Exception as e:
        return JSONResponse({"lines": [], "error": str(e)}, status_code=500)


@app.get("/embeddings")
async def get_embeddings(asin: Optional[str] = None, limit: int = 500):
    """List review embeddings stored in pgvector (Neon). Optional ?asin=B0863TXGM3 to filter by product."""
    try:
        items = list_embeddings(asin=asin, limit=limit)
        return {"count": len(items), "embeddings": items}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/results/latest")
async def get_latest_result():
    doc = get_latest_agent_result()
    if not doc:
        return JSONResponse({"status": "no_runs_yet"})
        
    state = json.loads(doc["result_json"])
    scraped = state.get("scraped_data", {})
    # Slim product info for frontend (name, price, rating) — no full review text
    products = {
        asin: {
            "name": data.get("name", f"Product {asin}"),
            "price": data.get("price"),
            "rating": data.get("rating"),
            "review_count": data.get("review_count", 0),
        }
        for asin, data in scraped.items()
    }
    
    return {
        "status": "success",
        "job_id": doc["run_id"],
        "product_asin": doc["product_asin"],
        "products": products,
        "vuln_scores": state.get("vuln_scores", {}),
        "profit_sims": state.get("profit_sims", {}),
        "pivot_memo": state.get("pivot_memo", ""),
        "signals": state.get("signals", []),
    }
