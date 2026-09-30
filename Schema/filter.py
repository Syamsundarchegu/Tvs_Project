"""Builds Azure AI Search OData filters from the LLM's metadata selection."""
from Schema.metadata_schema import NOT_AVAILABLE


def _escape(value: str) -> str:
    # OData string literal escaping + keep '|' free for search.in delimiter
    return value.replace("'", "''").replace("|", " ")


def _search_in(field: str, values: list[str]) -> str:
    joined = "|".join(_escape(v) for v in values)
    return f"search.in({field}, '{joined}', '|')"


def build_odata_filter(entity_names: list[str], filters: list[dict], include_not_available: bool = False) -> str:
    """
    entity_names          -> hard company filter (always applied)
    filters               -> [{"field": "document_subtype", "values": ["Diligence Record"]}, ...]  (AND across fields, OR within)
    include_not_available -> also accept chunks where that field is 'Not Available' (handles missing metadata)
    """
    clauses = [_search_in("entity_name", entity_names)]
    for f in filters:
        values = [v for v in f.get("values", []) if v and v != NOT_AVAILABLE]
        if not values:
            continue
        if include_not_available:
            values = values + [NOT_AVAILABLE]
        clauses.append(_search_in(f["field"], values))
    return " and ".join(clauses)
