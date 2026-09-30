# """LangGraph nodes: router -> (general | irrelevant | company filter node -> retrieve | unclassified -> retrieve) -> respond."""
# import re
# from typing import Literal

# from langchain_core.messages import HumanMessage, SystemMessage
# from pydantic import BaseModel, Field

# import config
# from logger import log
# from Schema.filter import build_odata_filter
# from Chat_History.history import history_as_text
# from Azure_Services.azure_openai import get_llm
# from Schema.metadata_schema import CITATION_FIELDS, FILTERABLE_FIELDS, METADATA_SCHEMA, NOT_AVAILABLE
# from Agents.prompts import (FILTER_PROMPT_TEMPLATE, GENERAL_PROMPT, IRRELEVANT_PROMPT,
#                      RESPONSE_PROMPT, ROUTER_PROMPT)
# from Azure_Services.azure_ai_search import get_available_values, hybrid_search
# from Agents.state import AgentState


# # ═════════════════════════════ structured outputs ═════════════════════════════
# class RouteDecision(BaseModel):
#     route: Literal["insurancedekho", "yubi", "unclassified", "general", "irrelevant"] = Field(description="Chosen route")
#     standalone_query: str = Field(description="Self-contained rewrite of the user's message")
#     reasoning: str = Field(description="One short sentence explaining the choice (logged only)")


# class FilterSpec(BaseModel):
#     field: str = Field(description="Metadata field name exactly as in the schema")
#     values: list[str] = Field(description="Allowed values for this field (OR-ed), copied exactly from the schema")


# class FilterDecision(BaseModel):
#     filters: list[FilterSpec] = Field(default_factory=list, description="Metadata filters; empty list if none apply")
#     search_query: str = Field(description="Concise keyword-rich query for hybrid search")
#     reasoning: str = Field(description="Why these filters (or none) were chosen (logged only)")


# def _user_block(state: AgentState, query: str) -> str:
#     return f"Chat history (most recent last):\n{history_as_text(state.get('history', []))}\n\nCurrent user message:\n{query}"


# # ═════════════════════════════ router ═════════════════════════════
# def router_node(state: AgentState) -> dict:
#     log.node("router")
#     log.data("query", state["query"])
#     log.info(f"history turns in context: {len(state.get('history', []))}")

#     llm = get_llm().with_structured_output(RouteDecision, method="function_calling")
#     try:
#         d: RouteDecision = llm.invoke([SystemMessage(ROUTER_PROMPT), HumanMessage(_user_block(state, state["query"]))])
#     except Exception as e:
#         log.err(f"router failed ({e}); defaulting to unclassified (search whole index)")
#         d = RouteDecision(route="unclassified", standalone_query=state["query"], reasoning="router error fallback")

#     log.ok(f"route = {d.route}")
#     log.data("standalone_query", d.standalone_query)
#     log.data("reasoning", d.reasoning)
#     return {
#         "route": d.route,
#         "standalone_query": d.standalone_query,
#         "company": d.route if d.route in config.COMPANIES else None,
#     }


# def route_selector(state: AgentState) -> str:
#     return state["route"]


# # ═════════════════════════════ general / irrelevant ═════════════════════════════
# def _simple_answer(state: AgentState, system_prompt: str, name: str) -> dict:
#     log.node(name)
#     resp = get_llm().invoke([SystemMessage(system_prompt), HumanMessage(_user_block(state, state["query"]))])
#     log.ok("answer generated")
#     return {"answer": resp.content, "citations": [], "filters_used": {}}


# def general_node(state: AgentState) -> dict:
#     return _simple_answer(state, GENERAL_PROMPT, "general")


# def irrelevant_node(state: AgentState) -> dict:
#     return _simple_answer(state, IRRELEVANT_PROMPT, "irrelevant")


# # ═════════════════════════════ company filter nodes ═════════════════════════════
# def _render_schema(available: dict[str, list[str]]) -> str:
#     lines = []
#     for field in FILTERABLE_FIELDS:
#         vals = available.get(field) or []
#         shown = ", ".join(f'"{v}"' for v in vals) if vals else "(no known values)"
#         lines.append(f"- {field}: {METADATA_SCHEMA[field]['description']}\n    values: {shown}")
#     return "\n".join(lines)


# def _validate_filters(filters: list[FilterSpec], available: dict[str, list[str]]) -> tuple[list[dict], list[dict]]:
#     """Drop unknown fields / hallucinated values; map values to their canonical casing."""
#     kept, dropped = [], []
#     for f in filters:
#         if f.field not in FILTERABLE_FIELDS:
#             dropped.append({"field": f.field, "values": f.values, "reason": "unknown field"})
#             continue
#         known = available.get(f.field) or []
#         if known:
#             lookup = {v.lower(): v for v in known}
#             good = [lookup[v.lower()] for v in f.values if v.lower() in lookup]
#             bad = [v for v in f.values if v.lower() not in lookup]
#             if bad:
#                 dropped.append({"field": f.field, "values": bad, "reason": "value not present in index"})
#         else:
#             good = [v for v in f.values if v and v != NOT_AVAILABLE]
#         if good:
#             kept.append({"field": f.field, "values": good})
#     return kept, dropped


# def make_company_node(company_key: str):
#     cfg = config.COMPANIES[company_key]

#     def company_node(state: AgentState) -> dict:
#         log.node(f"{company_key}_node  ({cfg['display_name']})")
#         available = get_available_values(company_key)
#         prompt = FILTER_PROMPT_TEMPLATE.format(company=cfg["display_name"], schema=_render_schema(available))

#         llm = get_llm().with_structured_output(FilterDecision, method="function_calling")
#         try:
#             d: FilterDecision = llm.invoke([SystemMessage(prompt), HumanMessage(state["standalone_query"])])
#         except Exception as e:
#             log.err(f"filter selection failed ({e}); searching without metadata filters")
#             d = FilterDecision(filters=[], search_query=state["standalone_query"], reasoning="filter LLM error fallback")

#         kept, dropped = _validate_filters(d.filters, available)
#         log.data("llm filters (validated)", kept or "none")
#         if dropped:
#             log.warn(f"dropped filters: {dropped}")
#         log.data("search_query", d.search_query)
#         log.data("reasoning", d.reasoning)
#         return {
#             "selected_filters": kept,
#             "dropped_filters": dropped,
#             "search_query": d.search_query or state["standalone_query"],
#         }

#     company_node.__name__ = f"{company_key}_node"
#     return company_node


# # ═════════════════════════════ retrieval ═════════════════════════════
# def _build_stages(state: AgentState) -> list[tuple[str, str | None]]:
#     # unclassified: company unknown -> search the whole index, no filters at all
#     if not state.get("company"):
#         return [("whole_index", None)]

#     cfg = config.COMPANIES[state["company"]]
#     filters = state.get("selected_filters", [])
#     stages = []
#     if filters:
#         stages.append(("strict", build_odata_filter(cfg["entity_names"], filters)))
#         stages.append(("strict_or_not_available", build_odata_filter(cfg["entity_names"], filters, include_not_available=True)))
#     stages.append(("entity_only", build_odata_filter(cfg["entity_names"], [])))
#     return stages


# def retrieve_node(state: AgentState) -> dict:
#     """
#     Company routes use staged retrieval to cope with missing metadata:
#       strict -> strict_or_not_available -> entity_only  (stops once MIN_RESULTS chunks are found)
#     Unclassified route: one hybrid search over the whole index with no filter.
#     """
#     log.node("retrieve" + ("" if state.get("company") else "  (unclassified -> whole index)"))
#     query = state.get("search_query") or state["standalone_query"]

#     collected, seen, trace = [], set(), []
#     for stage, odata in _build_stages(state):
#         log.info(f"stage '{stage}' -> filter: {odata or '(none)'}")
#         try:
#             hits = hybrid_search(query, odata, config.TOP_K)
#         except Exception as e:
#             log.err(f"search failed at stage '{stage}': {e}")
#             hits = []
#         new = 0
#         for h in hits:
#             if h["id"] in seen or len(collected) >= config.TOP_K:
#                 continue
#             seen.add(h["id"])
#             collected.append({**h, "retrieval_stage": stage})
#             new += 1
#         trace.append({"stage": stage, "odata_filter": odata, "hits": len(hits), "new_chunks": new})
#         log.info(f"   hits={len(hits)} new={new} total={len(collected)}")
#         if len(collected) >= config.MIN_RESULTS:
#             break

#     if collected:
#         companies = sorted({c["metadata"].get("entity_name") or "?" for c in collected})
#         log.ok(f"{len(collected)} chunks retrieved (final stage: {trace[-1]['stage']}, entities: {companies})")
#     else:
#         log.warn("no chunks retrieved")
#     return {"chunks": collected, "retrieval_trace": trace}


# # ═════════════════════════════ response ═════════════════════════════
# def _format_context(chunks: list[dict]) -> str:
#     blocks = []
#     for i, c in enumerate(chunks, 1):
#         m = c["metadata"]
#         meta = " | ".join(f"{k}: {v}" for k, v in m.items()
#                           if k != "current_path" and v and v != NOT_AVAILABLE)
#         blocks.append(f"[{i}] {meta}\n{c['content'][:config.MAX_CHARS_PER_CHUNK]}")
#     return "\n\n---\n\n".join(blocks)


# def respond_node(state: AgentState) -> dict:
#     log.node("respond")
#     chunks = state.get("chunks", [])
#     company_key = state.get("company")
#     cfg = config.COMPANIES.get(company_key) if company_key else None
#     company_label = cfg["display_name"] if cfg else "All companies (unclassified)"

#     filters_used = {
#         "company": company_label,
#         "entity_filter": cfg["entity_names"] if cfg else [],
#         "llm_selected_filters": state.get("selected_filters", []),
#         "dropped_filters": state.get("dropped_filters", []),
#         "search_query": state.get("search_query") or state.get("standalone_query", ""),
#         "retrieval_trace": state.get("retrieval_trace", []),
#         "final_stage": (state.get("retrieval_trace") or [{}])[-1].get("stage"),
#     }

#     if not chunks:
#         return {
#             "answer": "I couldn't find any documents relevant to that question. "
#                       "Could you rephrase or add detail (company, document type, period, advisor)?",
#             "citations": [],
#             "filters_used": filters_used,
#         }

#     prompt = RESPONSE_PROMPT.format(history=history_as_text(state.get("history", [])), context=_format_context(chunks))
#     resp = get_llm().invoke([SystemMessage(prompt), HumanMessage(state["standalone_query"])])
#     answer = resp.content

#     # keep only chunks the model actually cited
#     cited_nums = sorted({int(n) for n in re.findall(r"\[(\d+)\]", answer) if 1 <= int(n) <= len(chunks)})
#     citations = []
#     for n in cited_nums:
#         c = chunks[n - 1]
#         m = c["metadata"]
#         citations.append({
#             "ref": n,
#             "file_name": m.get("file_name"),
#             "current_path": m.get("current_path"),
#             "entity_name": m.get("entity_name"),
#             "chunk_id": c["id"],
#             "retrieval_stage": c["retrieval_stage"],
#             "score": c["score"],
#             "metadata": {k: v for k, v in m.items() if k not in CITATION_FIELDS},
#         })
#     log.ok(f"answer generated, {len(citations)} citations")
#     log.data("cited files", sorted({c['file_name'] for c in citations if c.get('file_name')}))
#     return {"answer": answer, "citations": citations, "filters_used": filters_used}



"""LangGraph nodes: router -> (general | irrelevant | company filter node -> retrieve | unclassified -> retrieve) -> respond."""

import re
from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

import config
from logger import log
from Schema.filter import build_odata_filter
from Chat_History.history import history_as_text
from Azure_Services.azure_openai import get_llm
from Schema.metadata_schema import CITATION_FIELDS, FILTERABLE_FIELDS, METADATA_SCHEMA, NOT_AVAILABLE
from Agents.prompts import (FILTER_PROMPT_TEMPLATE, GENERAL_PROMPT, IRRELEVANT_PROMPT,
                     RESPONSE_PROMPT, ROUTER_PROMPT)
from Azure_Services.azure_ai_search import get_available_values, hybrid_search
from Agents.state import AgentState



# ═════════════════════════════ structured outputs ═════════════════════════════
class RouteDecision(BaseModel):
    route: Literal["insurancedekho", "yubi", "unclassified", "general", "irrelevant"] = Field(description="Chosen route")
    standalone_query: str = Field(description="Self-contained rewrite of the user's message")
    search_query: str = Field(description="Short keyword query for document search: company names, document types, "
                                          "periods, topics only. No filler, no references to the conversation.")


class FilterSpec(BaseModel):
    field: str = Field(description="Metadata field name exactly as in the schema")
    values: list[str] = Field(description="Allowed values for this field (OR-ed), copied exactly from the schema")


class FilterDecision(BaseModel):
    filters: list[FilterSpec] = Field(default_factory=list, description="Metadata filters; empty list if none apply")
    search_query: str = Field(description="Concise keyword-rich query for hybrid search")


def _user_block(state: AgentState, query: str) -> str:
    return f"Chat history (most recent last):\n{history_as_text(state.get('history', []))}\n\nCurrent user message:\n{query}"


# ═════════════════════════════ router ═════════════════════════════
def router_node(state: AgentState) -> dict:
    log.node("router")
    log.data("query", state["query"])
    log.info(f"history turns in context: {len(state.get('history', []))}")

    llm = get_llm().with_structured_output(RouteDecision, method="function_calling")
    try:
        d: RouteDecision = llm.invoke([SystemMessage(ROUTER_PROMPT), HumanMessage(_user_block(state, state["query"]))])
    except Exception as e:
        log.err(f"router failed ({e}); defaulting to unclassified (search whole index)")
        d = RouteDecision(route="unclassified", standalone_query=state["query"],
                          search_query=state["query"])

    log.ok(f"route = {d.route}")
    log.data("standalone_query", d.standalone_query)
    log.data("search_query", d.search_query)
    return {
        "route": d.route,
        "standalone_query": d.standalone_query,
        "search_query": d.search_query,
        "company": d.route if d.route in config.COMPANIES else None,
    }


def route_selector(state: AgentState) -> str:
    return state["route"]


# ═════════════════════════════ general / irrelevant ═════════════════════════════
def _simple_answer(state: AgentState, system_prompt: str, name: str) -> dict:
    log.node(name)
    resp = get_llm().invoke([SystemMessage(system_prompt), HumanMessage(_user_block(state, state["query"]))])
    log.ok("answer generated")
    return {"answer": resp.content, "citations": [], "metadata_summary": {}, "filters_used": {}}


def general_node(state: AgentState) -> dict:
    return _simple_answer(state, GENERAL_PROMPT, "general")


def irrelevant_node(state: AgentState) -> dict:
    return _simple_answer(state, IRRELEVANT_PROMPT, "irrelevant")


# ═════════════════════════════ company filter nodes ═════════════════════════════
def _render_schema(available: dict[str, list[str]]) -> str:
    lines = []
    for field in FILTERABLE_FIELDS:
        vals = available.get(field) or []
        shown = ", ".join(f'"{v}"' for v in vals) if vals else "(no known values)"
        lines.append(f"- {field}: {METADATA_SCHEMA[field]['description']}\n    values: {shown}")
    return "\n".join(lines)


def _validate_filters(filters: list[FilterSpec], available: dict[str, list[str]]) -> tuple[list[dict], list[dict]]:
    """Drop unknown fields / hallucinated values; map values to their canonical casing."""
    kept, dropped = [], []
    for f in filters:
        if f.field not in FILTERABLE_FIELDS:
            dropped.append({"field": f.field, "values": f.values, "reason": "unknown field"})
            continue
        known = available.get(f.field) or []
        if known:
            lookup = {v.lower(): v for v in known}
            good = [lookup[v.lower()] for v in f.values if v.lower() in lookup]
            bad = [v for v in f.values if v.lower() not in lookup]
            if bad:
                dropped.append({"field": f.field, "values": bad, "reason": "value not present in index"})
        else:
            good = [v for v in f.values if v and v != NOT_AVAILABLE]
        if good:
            kept.append({"field": f.field, "values": good})
    return kept, dropped


def make_company_node(company_key: str):
    cfg = config.COMPANIES[company_key]

    def company_node(state: AgentState) -> dict:
        log.node(f"{company_key}_node  ({cfg['display_name']})")
        available = get_available_values(company_key)
        prompt = FILTER_PROMPT_TEMPLATE.format(company=cfg["display_name"], schema=_render_schema(available))

        llm = get_llm().with_structured_output(FilterDecision, method="function_calling")
        try:
            d: FilterDecision = llm.invoke([SystemMessage(prompt), HumanMessage(state["standalone_query"])])
        except Exception as e:
            log.err(f"filter selection failed ({e}); searching without metadata filters")
            d = FilterDecision(filters=[], search_query=state["standalone_query"])

        kept, dropped = _validate_filters(d.filters, available)
        log.data("llm filters (validated)", kept or "none")
        if dropped:
            log.warn(f"dropped filters: {dropped}")
        log.data("search_query", d.search_query)
        return {
            "selected_filters": kept,
            "dropped_filters": dropped,
            "search_query": d.search_query or state["standalone_query"],
        }

    company_node.__name__ = f"{company_key}_node"
    return company_node


# ═════════════════════════════ retrieval ═════════════════════════════
def _build_stages(state: AgentState) -> list[tuple[str, str | None]]:
    # unclassified: company unknown -> search the whole index, no filters at all
    if not state.get("company"):
        return [("whole_index", None)]

    cfg = config.COMPANIES[state["company"]]
    filters = state.get("selected_filters", [])
    stages = []
    if filters:
        stages.append(("strict", build_odata_filter(cfg["entity_names"], filters)))
        stages.append(("strict_or_not_available", build_odata_filter(cfg["entity_names"], filters, include_not_available=True)))
    stages.append(("entity_only", build_odata_filter(cfg["entity_names"], [])))
    return stages


def retrieve_node(state: AgentState) -> dict:
    """
    Company routes use staged retrieval to cope with missing metadata:
      strict -> strict_or_not_available -> entity_only  (stops once MIN_RESULTS chunks are found)
    Unclassified route: one hybrid search over the whole index with no filter.
    """
    log.node("retrieve" + ("" if state.get("company") else "  (unclassified -> whole index)"))
    query = state.get("search_query") or state["standalone_query"]

    collected, seen, trace = [], set(), []
    for stage, odata in _build_stages(state):
        log.info(f"stage '{stage}' -> filter: {odata or '(none)'}")
        try:
            hits = hybrid_search(query, odata, config.TOP_K)
        except Exception as e:
            log.err(f"search failed at stage '{stage}': {e}")
            hits = []
        new = 0
        for h in hits:
            if h["id"] in seen or len(collected) >= config.TOP_K:
                continue
            seen.add(h["id"])
            collected.append({**h, "retrieval_stage": stage})
            new += 1
        trace.append({"stage": stage, "odata_filter": odata, "hits": len(hits), "new_chunks": new})
        log.info(f"   hits={len(hits)} new={new} total={len(collected)}")
        if len(collected) >= config.MIN_RESULTS:
            break

    if collected:
        companies = sorted({c["metadata"].get("entity_name") or "?" for c in collected})
        log.ok(f"{len(collected)} chunks retrieved (final stage: {trace[-1]['stage']}, entities: {companies})")
    else:
        log.warn("no chunks retrieved")
    return {"chunks": collected, "retrieval_trace": trace}


# ═════════════════════════════ response ═════════════════════════════
def _format_context(chunks: list[dict]) -> str:
    blocks = []
    for i, c in enumerate(chunks, 1):
        m = c["metadata"]
        meta = " | ".join(f"{k}: {v}" for k, v in m.items()
                          if k != "current_path" and v and v != NOT_AVAILABLE)
        blocks.append(f"[{i}] {meta}\n{c['content'][:config.MAX_CHARS_PER_CHUNK]}")
    return "\n\n---\n\n".join(blocks)


def _merge_metadata(chunks: list[dict]) -> dict:
    """Unique metadata across a file's chunks: single value -> str, differing values -> list."""
    merged: dict[str, list] = {}
    for c in chunks:
        for k, v in c["metadata"].items():
            if k in ("file_name", "current_path") or v in (None, ""):
                continue
            vals = merged.setdefault(k, [])
            if v not in vals:
                vals.append(v)
    return {k: v[0] if len(v) == 1 else v for k, v in merged.items()}


def _group_by_file(used: list[tuple[int, dict]]) -> list[dict]:
    """[(ref_no, chunk), ...] -> one entry per file with its refs, chunk ids and unique metadata."""
    groups: dict[str, dict] = {}
    for n, c in used:
        m = c["metadata"]
        key = m.get("current_path") or m.get("file_name") or c["id"]
        g = groups.setdefault(key, {
            "file_name": m.get("file_name"),
            "current_path": m.get("current_path"),
            "refs": [],
            "_chunks": [],
        })
        g["refs"].append(n)
        g["_chunks"].append(c)

    sources = []
    for g in groups.values():
        g["metadata"] = _merge_metadata(g.pop("_chunks"))
        sources.append(g)
    return sources


def _build_summary(used: list[tuple[int, dict]]) -> dict:
    """Overall summary of the used chunks: file names + paths as lists, other metadata unique-merged."""
    if not used:
        return {}
    chunks = [c for _, c in used]
    file_names, paths = [], []
    for c in chunks:
        fn, cp = c["metadata"].get("file_name"), c["metadata"].get("current_path")
        if fn and fn not in file_names:
            file_names.append(fn)
        if cp and cp not in paths:
            paths.append(cp)
    return {"file_name": file_names, "current_path": paths, **_merge_metadata(chunks)}


def respond_node(state: AgentState) -> dict:
    log.node("respond")
    chunks = state.get("chunks", [])
    company_key = state.get("company")
    cfg = config.COMPANIES.get(company_key) if company_key else None

    filters_used = {
        "company": cfg["display_name"] if cfg else "All companies (unclassified)",
        "entity_filter": cfg["entity_names"] if cfg else [],
        "llm_selected_filters": state.get("selected_filters", []),
        "dropped_filters": state.get("dropped_filters", []),
        "search_query": state.get("search_query") or state.get("standalone_query", ""),
        "retrieval_trace": state.get("retrieval_trace", []),
        "final_stage": (state.get("retrieval_trace") or [{}])[-1].get("stage"),
    }

    if not chunks:
        return {
            "answer": "I couldn't find any documents relevant to that question. "
                      "Could you rephrase or add detail (company, document type, period, advisor)?",
            "citations": [],
            "metadata_summary": {},
            "filters_used": filters_used,
        }

    prompt = RESPONSE_PROMPT.format(history=history_as_text(state.get("history", [])), context=_format_context(chunks))
    answer = get_llm().invoke([SystemMessage(prompt), HumanMessage(state["standalone_query"])]).content

    # only the chunks the LLM actually cited (e.g. 4 of the 8 passed in), grouped per file
    cited_nums = sorted({int(n) for n in re.findall(r"\[(\d+)\]", answer) if 1 <= int(n) <= len(chunks)})
    used = [(n, chunks[n - 1]) for n in cited_nums]
    sources = _group_by_file(used)
    metadata_summary = _build_summary(used)

    log.ok(f"answer generated: {len(chunks)} chunks given, {len(used)} used, from {len(sources)} file(s)")
    for s in sources:
        log.data(s["file_name"], {"refs": s["refs"]})
    return {"answer": answer, "citations": sources, "metadata_summary": metadata_summary,
            "filters_used": filters_used}