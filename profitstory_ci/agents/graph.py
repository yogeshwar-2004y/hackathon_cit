from langgraph.graph import StateGraph, END  # type: ignore[reportMissingImports]
from agents.state import AgentState
from agents.nodes import (
    watchman_node, 
    detective_node, 
    vuln_calc_node, 
    profit_sim_node, 
    strategist_node
)

def detective_should_loop(state: AgentState) -> str:
    # Loop max 2 times
    if state.get("confidence", 1.0) < 0.7 and state.get("loop_count", 0) < 2:
        return "watchman"
    return "vuln_calc"

def should_run_profit_sim(state: AgentState) -> str:
    # Run profit sim when we have seller-set cost/price (my_cost, my_price) or scraped product data with price.
    # Cost is from the product form (my_cost), not from scrapers, so check state first.
    if state.get("my_cost") is not None or state.get("my_price") is not None:
        return "profit_sim"
    product_data = state.get("scraped_data", {}).get(state.get("product_asin"), {})
    if product_data.get("price") is not None or product_data.get("cost"):
        return "profit_sim"
    return "strategist"

def build_graph():
    builder = StateGraph(AgentState)

    # Register nodes
    builder.add_node("watchman", watchman_node)
    builder.add_node("detective", detective_node)
    builder.add_node("vuln_calc", vuln_calc_node)
    builder.add_node("profit_sim", profit_sim_node)
    builder.add_node("strategist", strategist_node)

    # Entry point
    builder.set_entry_point("watchman")

    # Edges
    builder.add_edge("watchman", "detective")
    
    builder.add_conditional_edges(
        "detective",
        detective_should_loop,
        {"watchman": "watchman", "vuln_calc": "vuln_calc"}
    )
    
    builder.add_conditional_edges(
        "vuln_calc",
        should_run_profit_sim,
        {"profit_sim": "profit_sim", "strategist": "strategist"}
    )
    
    builder.add_edge("profit_sim", "strategist")
    builder.add_edge("strategist", END)

    return builder.compile()
