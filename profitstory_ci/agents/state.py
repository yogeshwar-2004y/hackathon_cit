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
    # Multi-tenant / product-scoped (optional; default None)
    seller_id: Optional[int]
    product_id: Optional[int]
    my_price: Optional[float]
    my_cost: Optional[float]
    monthly_units: Optional[int]
    # Multi-platform: which platform per product/competitor (optional)
    product_platform: Optional[str]
    competitor_platforms: Optional[Dict[str, str]]  # platform_id -> platform
