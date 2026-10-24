"""FastAPI server providing OpenAI-compatible endpoints, REST management, and Web UI."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from local_coder.orchestrator import LocalCoderOrchestrator
from local_coder.server.coding_router import coding_router
from local_coder.server.openai_router import openai_router
from local_coder.server.orchestrator_registry import get_orchestrator, set_orchestrator
from local_coder.server.web_ui import get_ui_html
from local_coder.server.workspace_router import workspace_router

orchestrator_instance: Optional[LocalCoderOrchestrator] = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    global orchestrator_instance
    orchestrator_instance = LocalCoderOrchestrator()
    set_orchestrator(orchestrator_instance)
    yield
    active = get_orchestrator()
    if active:
        active.close()
    orchestrator_instance = None
    set_orchestrator(None)


app = FastAPI(title="LOCAL-CODER API Server", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(openai_router)
app.include_router(workspace_router)
app.include_router(coding_router)


@app.get("/", response_class=HTMLResponse)
async def serve_ui() -> HTMLResponse:
    """Renders interactive local developer studio UI."""
    return HTMLResponse(get_ui_html())


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Lightweight health check endpoint."""
    return {"status": "ok", "engine": "local-coder"}
