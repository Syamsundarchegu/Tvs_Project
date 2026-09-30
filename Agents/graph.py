from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from config import COMPANIES
from Agents.nodes import (general_node, irrelevant_node, make_company_node, respond_node,
                  retrieve_node, route_selector, router_node)
from Agents.state import AgentState



@lru_cache(maxsize=1)
def build_graph():
    g = StateGraph(AgentState)

    g.add_node("router", router_node)
    g.add_node("general", general_node)
    g.add_node("irrelevant", irrelevant_node)
    for key in COMPANIES:                       # insurancedekho_node, yubi_node
        g.add_node(f"{key}_node", make_company_node(key))
    g.add_node("retrieve", retrieve_node)
    g.add_node("respond", respond_node)

    g.add_edge(START, "router")
    g.add_conditional_edges(
        "router",
        route_selector,
        {
            "general": "general",
            "irrelevant": "irrelevant",
            "unclassified": "retrieve",          # company unknown -> straight to AI Search, no filters
            **{k: f"{k}_node" for k in COMPANIES},
        },
    )
    for key in COMPANIES:
        g.add_edge(f"{key}_node", "retrieve")
    g.add_edge("retrieve", "respond")
    g.add_edge("respond", END)
    g.add_edge("general", END)
    g.add_edge("irrelevant", END)

    return g.compile()