# """API endpoints."""
# import time

# from fastapi import APIRouter, HTTPException

# import config
# from logger import log
# from Agents.graph import build_graph
# from Chat_History.history import clear_history, get_full_history, load_history, save_turn
# from Router.model import ChatRequest, ChatResponse
# from Azure_Services.azure_ai_search import clear_facet_cache, get_available_values

# router = APIRouter()


# @router.get("/health")
# def health():
#     return {"status": "ok", "index": config.SEARCH_INDEX_NAME, "companies": list(config.COMPANIES)}


# @router.post("/chat", response_model=ChatResponse)
# def chat(req: ChatRequest):
#     log.banner(f"session={req.session_id} | {req.query}")
#     t0 = time.perf_counter()
#     history = load_history(req.session_id, config.HISTORY_TURNS_USED)

#     try:
#         result = build_graph().invoke({"session_id": req.session_id, "query": req.query, "history": history})
#     except Exception as e:
#         log.err(f"graph failed: {e}")
#         raise HTTPException(status_code=500, detail=str(e))

#     route = result.get("route", "")
#     company_key = result.get("company")
#     save_turn(
#         req.session_id,
#         user=req.query,
#         assistant=result.get("answer", ""),
#         company=config.COMPANIES[company_key]["display_name"] if company_key else None,
#         question_type="company_query" if route in config.COMPANIES else route,
#     )

#     latency = round(time.perf_counter() - t0, 2)
#     log.ok(f"done in {latency}s")
#     return ChatResponse(
#         session_id=req.session_id,
#         route=route,
#         company=company_key,
#         standalone_query=result.get("standalone_query", req.query),
#         answer=result.get("answer", ""),
#         citations=result.get("citations", []),
#         filters_used=result.get("filters_used", {}),
#         latency_seconds=latency,
#     )


# @router.get("/history/{session_id}")
# def history(session_id: str):
#     return {"session_id": session_id, "turns": get_full_history(session_id)}


# @router.delete("/history/{session_id}")
# def delete_history(session_id: str):
#     return {"session_id": session_id, "deleted": clear_history(session_id)}


# @router.post("/admin/refresh-metadata")
# def refresh_metadata():
#     """Re-pull distinct metadata values after re-indexing."""
#     clear_facet_cache()
#     return {k: {f: len(v) for f, v in get_available_values(k).items()} for k in config.COMPANIES}




"""API endpoints."""

import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import config
from logger import log
from Agents.graph import build_graph
from Chat_History.history import clear_history, get_full_history, load_history, save_turn
from Router.model import ChatRequest, ChatResponse
from Azure_Services.azure_ai_search import clear_facet_cache, get_available_values
from Azure_Services.blob_storage import create_blob_read_url

router = APIRouter()

class BlobOpenRequest(BaseModel):
    blob_path: str = Field(min_length=1, max_length=2048)


@router.get("/health")
def health():
    return {"status": "ok", "index": config.SEARCH_INDEX_NAME, "companies": list(config.COMPANIES)}


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    log.banner(f"session={req.session_id} | {req.query}")
    t0 = time.perf_counter()
    history = load_history(req.session_id, config.HISTORY_TURNS_USED)

    try:
        result = build_graph().invoke({"session_id": req.session_id, "query": req.query, "history": history})
    except Exception as e:
        log.err(f"graph failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    route = result.get("route", "")
    company_key = result.get("company")
    save_turn(
        req.session_id,
        user=req.query,
        assistant=result.get("answer", ""),
        company=config.COMPANIES[company_key]["display_name"] if company_key else None,
        question_type="company_query" if route in config.COMPANIES else route,
    )

    latency = round(time.perf_counter() - t0, 2)
    log.ok(f"done in {latency}s")
    return ChatResponse(
        session_id=req.session_id,
        route=route,
        company=company_key,
        standalone_query=result.get("standalone_query", req.query),
        answer=result.get("answer", ""),
        citations=result.get("citations", []),
        metadata_summary=result.get("metadata_summary", {}),
        filters_used=result.get("filters_used", {}),
        latency_seconds=latency,
    )


@router.post("/documents/sas-url")
def document_sas_url(req: BlobOpenRequest):
    """Return a short-lived read-only SAS URL for a cited blob."""
    try:
        url = create_blob_read_url(req.blob_path)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        log.err(f"blob SAS generation failed: {e}")
        raise HTTPException(status_code=500, detail="Unable to create document access URL")

    return {"url": url, "expires_in_minutes": 10}



@router.get("/history/{session_id}")
def history(session_id: str):
    return {"session_id": session_id, "turns": get_full_history(session_id)}


@router.delete("/history/{session_id}")
def delete_history(session_id: str):
    return {"session_id": session_id, "deleted": clear_history(session_id)}


@router.post("/admin/refresh-metadata")
def refresh_metadata():
    """Re-pull distinct metadata values after re-indexing."""
    clear_facet_cache()
    return {k: {f: len(v) for f, v in get_available_values(k).items()} for k in config.COMPANIES}