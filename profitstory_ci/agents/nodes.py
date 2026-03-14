import json
import re
import os
import datetime
from agents.state import AgentState
from agents.llm_config import get_llm, get_llm_json
from scraper.amazon_scraper import scrape_product
from scraper.outliers import clean_product_outliers, clean_cross_asin_price_outliers
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
    product_asin = state["product_asin"]
    competitor_asins = state["competitor_asins"]
    asins_to_scrape = [product_asin] + competitor_asins
    product_platform = (state.get("product_platform") or "amazon").strip().lower()
    competitor_platforms = state.get("competitor_platforms") or {}
    total_reviews = 0
    for asin in asins_to_scrape:
        if asin not in scraped_data:
            platform = product_platform if asin == product_asin else competitor_platforms.get(asin, "amazon")
            if isinstance(platform, str):
                platform = platform.strip().lower() or "amazon"
            _emit_log(f"[WATCHMAN] Scraping {asin}...")
            data = scrape_product(platform, asin)
            # Outlier detection and removal
            data, single_changes = clean_product_outliers(data, asin)
            for field, old_val, new_val, action in single_changes:
                _emit_log(f"[WATCHMAN] Outlier {asin} {field}: {old_val} -> {new_val} ({action})")
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

    # Cross-ASIN price outlier detection (IQR) and cap
    scraped_data, cross_changes = clean_cross_asin_price_outliers(scraped_data)
    for asin, field, old_val, new_val, action in cross_changes:
        _emit_log(f"[WATCHMAN] Outlier {asin} {field}: {old_val} -> {new_val} ({action})")

    _emit_log(f"[WATCHMAN] Embedded {total_reviews} reviews into pgvector.")
    _emit_log(f"[WATCHMAN] Outlier detection/removal complete (per-product + cross-ASIN price IQR).")

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
            raw = res.content if hasattr(res, "content") else res
            # Gemini can return content as list of parts [{type, text}]; normalize to string
            if isinstance(raw, list):
                content_str = "".join(
                    (p.get("text", "") if isinstance(p, dict) else str(p))
                    for p in raw
                )
            elif isinstance(raw, dict):
                content_str = raw.get("text", json.dumps(raw))
            else:
                content_str = str(raw) if raw is not None else ""
            analysis = _parse_json_from_response(content_str) if _use_gemini else json.loads(content_str)
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


# Competitors with overall rating <= this are treated as "bleeding" (negative impact).
BLEEDING_RATING_THRESHOLD = 2.5


def vuln_calc_node(state: AgentState) -> dict:
    _emit_log("[VULN_CALC] Calculating mathematical vulnerability scores...")
    scraped_data = state["scraped_data"]
    competitors = state["competitor_asins"]
    
    vuln_scores = {}
    for asin in competitors:
        data = scraped_data.get(asin, {})
        
        # Actual rating from scraped data (e.g. 1–5 stars). Low rating = bleeding.
        try:
            rating = float(data.get("rating") or 0)
        except (TypeError, ValueError):
            rating = 0.0
        is_low_rating = rating > 0 and rating <= BLEEDING_RATING_THRESHOLD
        
        neg_sentiment = max(0, -data.get("avg_sentiment", 0))
        neg_score = min(neg_sentiment * 100, 100) * 0.4
        
        # Simulate price drop pct. In a real scenario, compare to history DB.
        price_drop_pct = 20.0
        price_drop_score = min(price_drop_pct * 3, 100) * 0.3
        
        review_spike_score = min(data.get("review_spike", 0) * 2, 100) * 0.2
        
        # Rating drop: use actual low rating as strong signal; else small default.
        if is_low_rating:
            # 2-star (~2.0) or below = max contribution to vulnerability (bleeding).
            rating_drop_score = 100 * 0.1  # full 10% component
        else:
            rating_drop = 0.5
            rating_drop_score = min(rating_drop * 25, 100) * 0.1
        
        # Bleeding logic: low overall star rating = negative impact → force into Bleeding.
        low_rating_bleed_score = 0.0
        if is_low_rating:
            # Add a large component so total pushes into Bleeding (score > 70) and we mark explicitly.
            low_rating_bleed_score = min((BLEEDING_RATING_THRESHOLD - rating) * 40, 55)  # up to ~55 points
        
        total_score = neg_score + price_drop_score + review_spike_score + rating_drop_score + low_rating_bleed_score
        
        label = "Healthy"
        bleeding = False
        bleeding_reason = None
        if is_low_rating:
            label = "Bleeding"
            bleeding = True
            bleeding_reason = "low_rating"
        elif total_score > 70:
            label = "Bleeding"
            bleeding = True
            bleeding_reason = "high_vulnerability"
        elif total_score > 40:
            label = "Vulnerable"
        elif total_score > 20:
            label = "Stable"
            
        vuln_scores[asin] = {
            "score": round(total_score, 2),
            "label": label,
            "bleeding": bleeding,
            "bleeding_reason": bleeding_reason,
            "rating": round(rating, 1) if rating else None,
            "components": {
                "neg_sentiment": round(neg_score, 2),
                "price_drop": round(price_drop_score, 2),
                "review_spike": round(review_spike_score, 2),
                "rating_drop": round(rating_drop_score, 2),
                "low_rating_bleed": round(low_rating_bleed_score, 2),
            }
        }
        _emit_log(f"[VULN_CALC] {asin} Score = {total_score:.2f} → {label}" + (" (low rating)" if is_low_rating else ""))
        
    return {"vuln_scores": vuln_scores}


def profit_sim_node(state: AgentState) -> dict:
    _emit_log("[PROFIT_SIM] Simulating net ROI across strategies...")
    scraped_data = state["scraped_data"]
    product_data = scraped_data.get(state["product_asin"], {})
    # Use seller-editable price/cost/units from state when set (multi-tenant product-scoped run)
    cost = state.get("my_cost") if state.get("my_cost") is not None else product_data.get("cost") or 550.0
    my_price = state.get("my_price") if state.get("my_price") is not None else product_data.get("price") or 999.0
    baseline_units = state.get("monthly_units") if state.get("monthly_units") is not None else 40
    cost = float(cost)
    my_price = float(my_price)
    baseline_units = max(1, int(baseline_units))
    margin = my_price - cost
    baseline_profit = margin * baseline_units

    # Match price = lowest competitor price from scraped data (risk if we match)
    competitor_prices = []
    for asin in state.get("competitor_asins", []):
        d = scraped_data.get(asin, {})
        p = d.get("price")
        if p is not None:
            try:
                competitor_prices.append(float(p))
            except (TypeError, ValueError):
                pass
    if competitor_prices:
        match_price = min(competitor_prices)
    else:
        match_price = round(my_price * 0.85, 0)  # assume 15% undercut if no competitor data
    match_price = max(match_price, cost + 1)
    match_margin = match_price - cost
    # If we match competitor price: assume some volume gain but margin drop
    est_units_match = min(baseline_units + int(baseline_units * 0.25), baseline_units + 20)
    net_match = (match_margin * est_units_match) - baseline_profit
    match_vol_pct = round((est_units_match - baseline_units) / baseline_units * 100) if baseline_units else 0

    sims = {}

    # Strategy A - Match (competitor) price — profit at risk
    sims["match"] = {
        "label": "Match Price",
        "net_profit": round(net_match, 0),
        "verdict": "AVOID" if net_match < 0 else "RISKY",
        "verdictColor": "#E24B4A",
        "rows": [
            {"label": "Match at", "color": "#E24B4A", "val": f"₹{match_price:,.0f}"},
            {"label": "Margin/unit", "color": "#E24B4A", "val": f"₹{match_margin:,.0f}"},
            {"label": "Volume est.", "color": "#185FA5", "val": f"+{match_vol_pct}%"},
        ]
    }

    # Strategy B - Hold current price
    sims["hold"] = {
        "label": "Hold Price",
        "net_profit": 0,
        "verdict": "SAFE",
        "verdictColor": "#BA7517",
        "rows": [
            {"label": "Your price", "color": "#12B76A", "val": f"₹{my_price:,.0f}"},
            {"label": "Margin/unit", "color": "#12B76A", "val": f"₹{margin:,.0f}"},
            {"label": "Baseline", "color": "#BA7517", "val": f"{baseline_units} units/mo"},
        ]
    }

    # Strategy C - Ad campaign (hold price + spend for volume)
    ad_spend = max(2000, int(baseline_profit * 0.15))
    est_units_ad = baseline_units + int(baseline_units * 0.5)
    net_ad = (margin * est_units_ad) - ad_spend - baseline_profit
    ad_vol_pct = round((est_units_ad - baseline_units) / baseline_units * 100) if baseline_units else 50
    sims["ads"] = {
        "label": "Ad Campaign",
        "net_profit": round(net_ad, 0),
        "verdict": "RECOMMENDED" if net_ad > 0 else "OPTIONAL",
        "verdictColor": "#12B76A",
        "rows": [
            {"label": "Margin/unit", "color": "#12B76A", "val": f"₹{margin:,.0f}"},
            {"label": "Volume est.", "color": "#12B76A", "val": f"+{ad_vol_pct}%"},
            {"label": "Ad Spend", "color": "#E24B4A", "val": f"₹{ad_spend:,}"},
        ]
    }

    _emit_log(f"[PROFIT_SIM] Match: ₹{net_match:,.0f} | Hold: ₹0 | Ad campaign: ₹{net_ad:,.0f}")
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
    
    Important: Competitors with "bleeding": true or "bleeding_reason": "low_rating" have overall ~2-star (or very low) ratings — treat them as negative impact / bleeding; recommend capitalizing on their weakness (e.g. quality messaging, trust) rather than chasing their price.
    
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
    raw = res.content if hasattr(res, "content") else res
    # Gemini can return content as list of parts [{type, text, extras}]; normalize to string
    if isinstance(raw, list):
        content = "".join(
            (p.get("text", "") if isinstance(p, dict) else str(p))
            for p in raw
        )
    elif isinstance(raw, dict):
        content = raw.get("text", json.dumps(raw))
    else:
        content = str(raw) if raw is not None else ""
    return {"pivot_memo": content}
