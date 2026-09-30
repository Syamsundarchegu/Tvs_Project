# from typing import Optional, TypedDict


# class AgentState(TypedDict, total=False):
#     # inputs
#     session_id: str
#     query: str
#     history: list[dict]

#     # router
#     route: str                    # insurancedekho | yubi | unclassified | general | irrelevant
#     standalone_query: str
#     company: Optional[str]        # None when unclassified -> search across whole index

#     # company filter node
#     selected_filters: list[dict]  # [{"field": ..., "values": [...]}]
#     dropped_filters: list[dict]
#     search_query: str

#     # retrieval
#     chunks: list[dict]
#     retrieval_trace: list[dict]

#     # output
#     answer: str
#     citations: list[dict]
#     filters_used: dict



from typing import Optional, TypedDict


class AgentState(TypedDict, total=False):
    # inputs
    session_id: str
    query: str
    history: list[dict]

    # router
    route: str                    # insurancedekho | yubi | unclassified | general | irrelevant
    standalone_query: str
    company: Optional[str]        # None when unclassified -> search across whole index

    # company filter node
    selected_filters: list[dict]  # [{"field": ..., "values": [...]}]
    dropped_filters: list[dict]
    search_query: str             # router writes it; company filter node refines it

    # retrieval
    chunks: list[dict]
    retrieval_trace: list[dict]

    # output
    answer: str
    citations: list[dict]
    metadata_summary: dict
    filters_used: dict