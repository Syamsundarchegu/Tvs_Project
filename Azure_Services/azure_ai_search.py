"""Azure AI Search access: hybrid (BM25 + vector) retrieval and live metadata value discovery via facets."""
from functools import lru_cache

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery

import config
from logger import log
from Schema.filter import build_odata_filter
from Azure_Services.azure_openai import get_embeddings
from Schema.metadata_schema import ALL_METADATA_FIELDS, FILTERABLE_FIELDS, METADATA_SCHEMA, NOT_AVAILABLE

_FACET_CACHE: dict[str, dict[str, list[str]]] = {}


@lru_cache(maxsize=1)
def get_search_client() -> SearchClient:
    return SearchClient(
        endpoint=config.SEARCH_ENDPOINT,
        index_name=config.SEARCH_INDEX_NAME,
        credential=AzureKeyCredential(config.SEARCH_API_KEY),
    )


def hybrid_search(query: str, odata_filter: str | None, top: int) -> list[dict]:
    client = get_search_client()
    vector = get_embeddings().embed_query(query)
    vq = VectorizedQuery(vector=vector, k_nearest_neighbors=config.KNN_NEIGHBOURS, fields=config.VECTOR_FIELD)

    kwargs = dict(
        search_text=query,
        vector_queries=[vq],
        filter=odata_filter,
        top=top,
        select=[config.ID_FIELD, config.CONTENT_FIELD] + ALL_METADATA_FIELDS,
    )
    if config.SEMANTIC_CONFIG_NAME:
        kwargs.update(query_type="semantic", semantic_configuration_name=config.SEMANTIC_CONFIG_NAME)

    hits = []
    for r in client.search(**kwargs):
        hits.append({
            "id": r.get(config.ID_FIELD),
            "content": r.get(config.CONTENT_FIELD) or "",
            "score": r.get("@search.score"),
            "reranker_score": r.get("@search.reranker_score"),
            "metadata": {f: r.get(f) for f in ALL_METADATA_FIELDS},
        })
    return hits


def get_available_values(company_key: str) -> dict[str, list[str]]:
    """
    Distinct metadata values that actually exist for this company (via facets).
    Requires the fields to be 'facetable' in the index; falls back to schema examples otherwise.
    Cached per company for the lifetime of the process.
    """
    if company_key in _FACET_CACHE:
        return _FACET_CACHE[company_key]

    cfg = config.COMPANIES[company_key]
    company_filter = build_odata_filter(cfg["entity_names"], [])
    client = get_search_client()
    values: dict[str, list[str]] = {}

    for field in FILTERABLE_FIELDS:
        try:
            res = client.search(
                search_text="*",
                filter=company_filter,
                facets=[f"{field},count:{config.FACET_MAX_VALUES}"],
                top=0,
            )
            facets = res.get_facets() or {}
            values[field] = [f["value"] for f in facets.get(field, []) if f.get("value") and f["value"] != NOT_AVAILABLE]
        except Exception as e:  # field not facetable / missing
            log.warn(f"facet lookup failed for '{field}' ({type(e).__name__}); using schema examples")
            values[field] = METADATA_SCHEMA[field].get("examples", [])

    _FACET_CACHE[company_key] = values
    log.ok(f"loaded live metadata values for {cfg['display_name']}")
    return values


def clear_facet_cache():
    _FACET_CACHE.clear()