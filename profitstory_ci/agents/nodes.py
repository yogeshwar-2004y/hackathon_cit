import json
import re
import os
import datetime
from agents.state import AgentState
from agents.llm_config import get_llm, get_llm_json
from scraper.amazon_scraper import scrape_product
from api.db import save_price_to_db, save_review_stats
from api.vector_db import embed_reviews, search_reviews

def _emit_log(msg: str):
    print(f"[{datetime.datetime.now().isoformat()}] {msg}")
    with open("agent.log", "a") as f:
        f.write(json.dumps({"time": datetime.datetime.now().isoformat(), "msg": msg}) + "\n")

_llm = get_llm()
_llm_json = get_llm_json()
_use_gemini = (os.environ.get("LLM_PROVIDER") or "").strip().lower() == "gemini"

def _parse_json_from_response(content: str) -> dict:
    """Extract JSON from LLM response (handles Gemini markdown code blocks)."""
    text = (content or "").strip()
    # Strip ```json ... ``` or ``` ... ```
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if m:
        text = m.group(1).strip()
    return json.loads(text)

def watchman_node(state: AgentState) -> dict:
    _emit_log("[WATCHMAN] Starting scrape and embed phase...")
    scraped_data = state.get("scraped_data", {})
    asins_to_scrape = [state["product_asin"]] + state["competitor_asins"]
    
    total_reviews = 0
    for asin in asins_to_scrape:
        if asin not in scraped_data:
            _emit_log(f"[WATCHMAN] Scraping {asin}...")
            data = scrape_product(asin)
            scraped_data[asin] = data
            
            # Save to SQLite
            today = datetime.datetime.now().strftime("%Y-%m-%d")
            save_price_to_db(asin, data["price"], today)
            save_review_stats(
                asin=asin,
                avg_sentiment=data["avg_sentiment"],
                review_count=data["review_count"],
                rating=data["rating"],
                review_spike=data["review_spike"],
                scraped_at=datetime.datetime.now().isoformat()
            )
            
            # Embed to pgvector (Neon DB)
            if data["reviews"]:
                embed_reviews(asin, data["reviews"], today)
                total_reviews += len(data["reviews"])
                
    _emit_log(f"[WATCHMAN] Embedded {total_reviews} reviews into pgvector.")
    
    return {
        "scraped_data": scraped_data,
        "embeddings_done": True,
        "loop_count": state.get("loop_count", 0) + 1
    }

def detective_node(state: AgentState) -> dict:
    _emit_log("[DETECTIVE] Analyzing signals and building case...")
    scraped_data = state["scraped_data"]
    competitors = state["competitor_asins"]
    
    signals = []
    overall_confidence = 1.0 # default
    
    for asin in competitors:
        comp_data = scraped_data.get(asin, {})
        # Tool: Semantic Search
        search_res = search_reviews("quality issues sound problems broken defective", asin)
        matched_reviews = search_res.get("documents", [[]])[0]
        
        # Build prompt for JSON output
        prompt = f"""
        Analyze this competitor data to determine if their recent behavior is competitive pricing or distress pricing.
        Product: {comp_data.get('name')}
        Price: {comp_data.get('price')}
        Rating: {comp_data.get('rating')}
        Avg Sentiment: {comp_data.get('avg_sentiment')}
        Recent critical reviews: {json.dumps(matched_reviews[:5])}
        
        Return ONLY a valid JSON object with these keys (no other text):
        "problem_pattern": string (summary of issue),
        "price_drop_reason": string ("distress" or "competitive"),
        "buyer_intent_shift": string (opportunity),
        "confidence": float between 0 and 1,
        "signals": array of objects {{"type": "critical"|"medium"|"low", "text": "description"}}
        """
        
        try:
            res = _llm_json.invoke(prompt)
            raw = res.content if hasattr(res, "content") else str(res)
            analysis = _parse_json_from_response(raw) if _use_gemini else json.loads(raw)
            analysis["asin"] = asin
            signals.append(analysis)
            # Find minimum confidence among all competitors
            overall_confidence = min(overall_confidence, analysis.get("confidence", 0.8))
        except Exception as e:
            _emit_log(f"[DETECTIVE] Error reasoning for {asin}: {e}")
            signals.append({"asin": asin, "confidence": 0.5, "signals": []})
            overall_confidence = 0.5
            
    _emit_log(f"[DETECTIVE] Signal extraction complete with confidence {overall_confidence:.2f}")
    return {"signals": signals, "confidence": overall_confidence}


def vuln_calc_node(state: AgentState) -> dict:
    _emit_log("[VULN_CALC] Calculating mathematical vulnerability scores...")
    scraped_data = state["scraped_data"]
    competitors = state["competitor_asins"]
    
    vuln_scores = {}
    for asin in competitors:
        data = scraped_data.get(asin, {})
        
        neg_sentiment = max(0, -data.get("avg_sentiment", 0))
        neg_score = min(neg_sentiment * 100, 100) * 0.4
        
        # Simulate price drop pct. In a real scenario, compare to history DB.
        # We will use 0.2 (20% drop) as a dummy for the hackathon MVP if not in DB, 
        # but realistically, you query DB. Here we just hardcode an approximation.
        price_drop_pct = 20.0 
        price_drop_score = min(price_drop_pct * 3, 100) * 0.3
        
        review_spike_score = min(data.get("review_spike", 0) * 2, 100) * 0.2
        
        # Simulate rating drop.
        rating_drop = 0.5
        rating_drop_score = min(rating_drop * 25, 100) * 0.1
        
        total_score = neg_score + price_drop_score + review_spike_score + rating_drop_score
        
        label = "Healthy"
        if total_score > 70:
            label = "Bleeding"
        elif total_score > 40:
            label = "Vulnerable"
        elif total_score > 20:
            label = "Stable"
            
        vuln_scores[asin] = {
            "score": round(total_score, 2),
            "label": label,
            "components": {
                "neg_sentiment": round(neg_score, 2),
                "price_drop": round(price_drop_score, 2),
                "review_spike": round(review_spike_score, 2),
                "rating_drop": round(rating_drop_score, 2)
            }
        }
        _emit_log(f"[VULN_CALC] {asin} Score = {total_score:.2f} → {label}")
        
    return {"vuln_scores": vuln_scores}


def profit_sim_node(state: AgentState) -> dict:
    _emit_log("[PROFIT_SIM] Simulating net ROI across strategies...")
    product_data = state["scraped_data"].get(state["product_asin"], {})
    
    cost = product_data.get("cost", 550)
    my_price = product_data.get("price", 999)
    margin = my_price - cost
    baseline_units = 40
    baseline_profit = margin * baseline_units
    
    sims = {}
    
    # Strategy A - Match
    match_price = 699
    match_margin = match_price - cost
    est_units_match = 50
    net_match = (match_margin * est_units_match) - baseline_profit
    sims["match"] = {
        "label": "Match Price",
        "net_profit": net_match,
        "verdict": "AVOID",
        "verdictColor": "#E24B4A",
        "rows": [
            {"label": "Margin Impact", "pct": max(0, match_margin/margin*100), "color": "#E24B4A", "val": f"₹{match_margin}/unit"},
            {"label": "Volume Impact", "pct": 100, "color": "#185FA5", "val": "+25%"},
        ]
    }
    
    # Strategy B - Hold
    sims["hold"] = {
        "label": "Hold Price",
        "net_profit": 0,
        "verdict": "SAFE",
        "verdictColor": "#BA7517",
        "rows": [
            {"label": "Margin Impact", "pct": 100, "color": "#12B76A", "val": f"₹{margin}/unit"},
            {"label": "Volume Impact", "pct": 80, "color": "#BA7517", "val": "0%"},
        ]
    }
    
    # Strategy C - Ad Campaign
    ad_spend = 3000
    est_units_ad = 65
    net_ad = (margin * est_units_ad) - ad_spend - baseline_profit
    sims["ads"] = {
        "label": "Ad Campaign",
        "net_profit": net_ad,
        "verdict": "RECOMMENDED",
        "verdictColor": "#12B76A",
        "rows": [
            {"label": "Margin Impact", "pct": 100, "color": "#12B76A", "val": f"₹{margin}/unit"},
            {"label": "Volume Impact", "pct": 100, "color": "#12B76A", "val": "+62%"},
            {"label": "Ad Spend", "pct": 30, "color": "#E24B4A", "val": "₹3,000"},
        ]
    }
    
    _emit_log(f"[PROFIT_SIM] ad_campaign: +₹{net_ad} net (RECOMMENDED)")
    return {"profit_sims": sims}


def strategist_node(state: AgentState) -> dict:
    _emit_log("[STRATEGIST] Synthesizing final pivot memo...")
    vuln_scores = state["vuln_scores"]
    signals = state["signals"]
    profit_sims = state.get("profit_sims", {})
    
    prompt = f"""
    You are an expert Chief Strategy Officer for an e-commerce brand.
    Write a clear, concise Pivot Memo based on this data.
    Vulnerabilities: {json.dumps(vuln_scores)}
    Signals: {json.dumps(signals)}
    Simulations: {json.dumps(profit_sims)}
    
    Format requirements: Markdown text.
    Sections:
    ## PIVOT MEMO — [Today's Date]
    SITUATION: (2 sentences)
    ACTION 1 (RECOMMENDED) — Net impact: [X]
    ACTION 2 (ALTERNATIVE) — Net impact: [Y]
    ACTION 3 (DEFENSIVE)
    WHAT NOT TO DO:
    """
    
    res = _llm.invoke(prompt)
    _emit_log("[STRATEGIST] Memo generated. Workflow complete.")
    content = res.content if hasattr(res, "content") else str(res)
    return {"pivot_memo": content}
