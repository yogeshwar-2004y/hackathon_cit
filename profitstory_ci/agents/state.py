from typing import TypedDict, Optional, List, Dict, Any

class AgentState(TypedDict):
    product_asin: str
    competitor_asins: List[str]
    scraped_data: Dict[str, Any]
    embeddings_done: bool
    signals: List[Dict[str, Any]]
    vuln_scores: Dict[str, Any]
    profit_sims: Dict[str, Any]
    pivot_memo: str
    confidence: float
    loop_count: int
