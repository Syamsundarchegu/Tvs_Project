# """FastAPI entrypoint.  Run:  uvicorn app:app --reload --port 8000"""
# from contextlib import asynccontextmanager

# from fastapi import FastAPI

# import config
# from logger import log
# from Agents.graph import build_graph
# from Router import backend_router as b
# from Azure_Services.azure_ai_search import get_available_values


# @asynccontextmanager
# async def lifespan(_: FastAPI):
#     log.banner("TVS Capital agent starting")
#     # build_graph()
#     build_graph().get_graph().draw_mermaid_png(output_file_path="agent_flow.png")
    
#     for key in config.COMPANIES:          # warm metadata-value cache so the first query is fast
#         try:
#             get_available_values(key)
#         except Exception as e:
#             log.warn(f"could not warm facets for {key}: {e}")
#     log.ok("ready")
#     yield


# app = FastAPI(title="TVS Capital Portfolio RAG Agent", version="1.0.0", lifespan=lifespan)
# app.include_router(b.router)


# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)



"""FastAPI entrypoint.  Run:  uvicorn app:app --reload --port 8000"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import config
from logger import log
from Frontend import ui_config
from Agents.graph import build_graph
from Router.backend_router import router as router
from Azure_Services.azure_ai_search import get_available_values

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / "Frontend"
STATIC_DIR = FRONTEND_DIR / "Static"
IMAGES_DIR = FRONTEND_DIR / "images"
TEMPLATES_DIR = FRONTEND_DIR / "Templates"


@asynccontextmanager
async def lifespan(_: FastAPI):
    log.banner("TVS Capital agent starting")
    build_graph()
    for key in config.COMPANIES:          # warm metadata-value cache so the first query is fast
        try:
            get_available_values(key)
        except Exception as e:
            log.warn(f"could not warm facets for {key}: {e}")
    log.ok("ready")
    yield


app = FastAPI(title="TVS Capital Portfolio RAG Agent", version="1.0.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/images", StaticFiles(directory=IMAGES_DIR), name="images")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

app.include_router(router)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def index(request: Request):
    logo_exists = (IMAGES_DIR / ui_config.LOGO_FILE).exists()
    if not logo_exists:
        log.warn(f"logo not found at {IMAGES_DIR / ui_config.LOGO_FILE}")
    return templates.TemplateResponse(request, "index.html", {
        "app_name": ui_config.APP_NAME,
        "logo_file": ui_config.LOGO_FILE,
        "logo_url": request.url_for("images", path=ui_config.LOGO_FILE) if logo_exists else None,
        "companies": [c["display_name"] for c in config.COMPANIES.values()],
        "index_name": config.SEARCH_INDEX_NAME,
        "prompts": ui_config.PROMPTS,
        "icons": ui_config.ICONS,
    })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)