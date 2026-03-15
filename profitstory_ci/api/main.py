import os
import json
import uuid
import time
import asyncio
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, BackgroundTasks, Depends
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from sqlalchemy.orm import Session

# Load env vars
load_dotenv()

# Disable LangSmith tracing to avoid 403 Forbidden
os.environ["LANGCHAIN_TRACING_V2"] = "false"

from api.db import init_db, get_latest_agent_result, save_agent_result
from api.vector_db import list_embeddings
from api.auth import get_current_seller, get_current_seller_from_token_or_query
from api.auth import router as auth_router
from api.products import router as products_router
from db.database import init_db as init_sqlite_db, get_db, AgentRun, Product
from agents.graph import build_graph

app = FastAPI(title="Shadowspy.ai Dashboard")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes are under /api in frontend; Vite proxy strips /api so backend sees /auth, /products, etc.
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(products_router, prefix="", tags=["products"])

# Initialize DB on startup (single Neon DB: sellers + embeddings + scrape logs)
@app.on_event("startup")
def startup_event():
    init_db()  # Neon: pgvector, scrape_* tables, agent_results, review_embeddings
    init_sqlite_db()  # Same Neon when DATABASE_URL set; else SQLite fallback (sellers, products, agent_runs, etc.)
    if not os.path.exists("agent.log"):
        open("agent.log", "w").close()

agent_graph = build_graph()


def run_agent_workflow(
    job_id: str,
    product_asin: str,
    competitor_asins: list[str],
    seller_id: Optional[int] = None,
    product_id: Optional[int] = None,
    my_price: Optional[float] = None,
    my_cost: Optional[float] = None,
    monthly_units: Optional[int] = None,
    product_platform: Optional[str] = None,
    competitor_platforms: Optional[dict] = None,
):
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
        "loop_count": 0,
        "seller_id": seller_id,
        "product_id": product_id,
        "my_price": my_price,
        "my_cost": my_cost,
        "monthly_units": monthly_units or 40,
        "product_platform": product_platform or "amazon",
        "competitor_platforms": competitor_platforms or {},
    }
    try:
        final_state = agent_graph.invoke(initial_state)
        save_agent_result(
            run_id=job_id,
            product_asin=product_asin,
            result_json=json.dumps(final_state),
            created_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
        )
        # Update agent_runs if product-scoped
        if product_id and seller_id:
            from db.database import SessionLocal
            db = SessionLocal()
            try:
                run = db.query(AgentRun).filter(AgentRun.run_id == job_id).first()
                if run:
                    run.status = "done"
                    run.completed_at = datetime.utcnow()
                    run.vuln_scores = json.dumps(final_state.get("vuln_scores"))
                    run.pivot_memo = final_state.get("pivot_memo")
                    run.profit_sims = json.dumps(final_state.get("profit_sims"))
                    run.signals = json.dumps(final_state.get("signals"))
                    db.commit()
            finally:
                db.close()
        with open("agent.log", "a") as f:
            f.write(json.dumps({"status": "done"}) + "\n")
    except Exception as e:
        if product_id and seller_id:
            from db.database import SessionLocal
            db = SessionLocal()
            try:
                run = db.query(AgentRun).filter(AgentRun.run_id == job_id).first()
                if run:
                    run.status = "error"
                    run.error_msg = str(e)
                    run.completed_at = datetime.utcnow()
                    db.commit()
            finally:
                db.close()
        with open("agent.log", "a") as f:
            f.write(json.dumps({"status": "error", "msg": str(e)}) + "\n")


@app.post("/scan/{product_id}")
async def trigger_scan_product(
    product_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    seller=Depends(get_current_seller),
):
    product = db.query(Product).filter(Product.id == product_id, Product.seller_id == seller.id, Product.is_active == True).first()
    if not product:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Product not found or access denied")
    competitors = [c for c in product.competitors if c.is_active]
    competitor_platform_ids = [c.platform_id for c in competitors]
    competitor_platforms = {c.platform_id: c.platform for c in competitors}
    run_id = str(uuid.uuid4())[:8]
    run = AgentRun(
        seller_id=seller.id,
        product_id=product.id,
        run_id=run_id,
        status="running",
    )
    db.add(run)
    db.commit()
    background_tasks.add_task(
        run_agent_workflow,
        run_id,
        product.platform_id,
        competitor_platform_ids,
        seller_id=seller.id,
        product_id=product.id,
        my_price=product.price,
        my_cost=product.cost,
        monthly_units=getattr(product, "monthly_units", None) or 40,
        product_platform=product.platform,
        competitor_platforms=competitor_platforms,
    )
    return {"run_id": run_id, "status": "started"}


@app.get("/scan/{product_id}/history")
async def scan_history(
    product_id: int,
    limit: int = 10,
    db: Session = Depends(get_db),
    seller=Depends(get_current_seller),
):
    product = db.query(Product).filter(Product.id == product_id, Product.seller_id == seller.id, Product.is_active == True).first()
    if not product:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Product not found or access denied")
    runs = db.query(AgentRun).filter(AgentRun.product_id == product_id, AgentRun.seller_id == seller.id).order_by(AgentRun.created_at.desc()).limit(limit).all()
    return {
        "runs": [
            {
                "run_id": r.run_id,
                "status": r.status,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "vuln_scores": json.loads(r.vuln_scores) if r.vuln_scores else None,
            }
            for r in runs
        ]
    }


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
async def job_stream(job_id: str, seller=Depends(get_current_seller_from_token_or_query)):
    return StreamingResponse(log_reader(), media_type="text/event-stream")


@app.get("/job/{job_id}/result")
async def job_result(job_id: str, db: Session = Depends(get_db), seller=Depends(get_current_seller)):
    """Return result for a run (from agent_runs or legacy agent_results)."""
    run = db.query(AgentRun).filter(AgentRun.run_id == job_id, AgentRun.seller_id == seller.id).first()
    if run:
        has_result = run.status == "done" and (run.vuln_scores or run.profit_sims or (run.pivot_memo and run.pivot_memo.strip()))
        if has_result:
            def _safe_json(val, default):
                if val is None:
                    return default
                if isinstance(val, str):
                    try:
                        return json.loads(val)
                    except (TypeError, ValueError):
                        return default
                return val if isinstance(default, type(val)) or (default == {} and isinstance(val, dict)) or (default == [] and isinstance(val, list)) else default
            profit_sims = _safe_json(run.profit_sims, {})
            vuln_scores = _safe_json(run.vuln_scores, {})
            signals = _safe_json(run.signals, [])
            return {
                "status": "success",
                "job_id": run.run_id,
                "product_asin": None,
                "products": {},
                "vuln_scores": vuln_scores if isinstance(vuln_scores, dict) else {},
                "profit_sims": profit_sims if isinstance(profit_sims, dict) else {},
                "pivot_memo": run.pivot_memo or "",
                "signals": signals if isinstance(signals, list) else [],
            }
        # Run exists but not finished yet (running / error / pending) — return 200 so frontend doesn't get 404
        return {
            "status": run.status or "running",
            "job_id": run.run_id,
            "products": {},
            "vuln_scores": {},
            "profit_sims": {},
            "pivot_memo": "",
            "signals": [],
        }
    doc = get_latest_agent_result()
    if doc and doc.get("run_id") == job_id:
        state = json.loads(doc["result_json"])
        scraped = state.get("scraped_data", {})
        products = {asin: {"name": d.get("name", f"Product {asin}"), "price": d.get("price"), "rating": d.get("rating"), "review_count": d.get("review_count", 0), "fallback_platform": d.get("fallback_platform"), "fallback_source_id": d.get("fallback_source_id")} for asin, d in scraped.items()}
        return {"status": "success", "job_id": doc["run_id"], "product_asin": doc["product_asin"], "products": products, "vuln_scores": state.get("vuln_scores", {}), "profit_sims": state.get("profit_sims", {}), "pivot_memo": state.get("pivot_memo", ""), "signals": state.get("signals", [])}
    return JSONResponse({"status": "no_run", "job_id": job_id}, status_code=404)


# Resolve agent.log relative to project root (parent of api/)
LOG_FILE = os.path.join(os.path.dirname(__file__), "..", "agent.log")
LOG_FILE = os.path.abspath(LOG_FILE)

@app.get("/logs")
async def get_logs(limit: int = 200, seller=Depends(get_current_seller)):
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
async def get_embeddings(asin: Optional[str] = None, limit: int = 500, seller=Depends(get_current_seller)):
    """List review embeddings stored in pgvector (Neon). Optional ?asin= to filter by product."""
    try:
        items = list_embeddings(asin=asin, limit=limit)
        return {"count": len(items), "embeddings": items}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/results/latest")
async def get_latest_result(seller=Depends(get_current_seller)):
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
            "fallback_platform": data.get("fallback_platform"),
            "fallback_source_id": data.get("fallback_source_id"),
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
