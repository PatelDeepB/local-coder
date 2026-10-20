"""FastAPI server providing OpenAI-compatible endpoints, REST management, and Web UI."""

from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Optional
import json
import time
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

from local_coder.ast_engine.diff_patcher import PrecisionPatcher
from local_coder.orchestrator import LocalCoderOrchestrator
from local_coder.server.web_ui import get_ui_html


class OpenAIMessage(BaseModel):
    role: str
    content: str


class OpenAIChatRequest(BaseModel):
    model: str = "local-coder"
    messages: list[OpenAIMessage]
    temperature: Optional[float] = 0.2
    max_tokens: Optional[int] = 1024
    stream: Optional[bool] = False


class OpenAIChoiceMessage(BaseModel):
    role: str = "assistant"
    content: str


class OpenAIChoice(BaseModel):
    index: int = 0
    message: OpenAIChoiceMessage
    finish_reason: str = "stop"


class OpenAIChatResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[OpenAIChoice]


class TaskRequest(BaseModel):
    goal: str


class TerminalRequest(BaseModel):
    command: str


orchestrator_instance: Optional[LocalCoderOrchestrator] = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    global orchestrator_instance
    orchestrator_instance = LocalCoderOrchestrator()
    yield
    if orchestrator_instance:
        orchestrator_instance.close()


app = FastAPI(title="LOCAL-CODER API Server", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_class=HTMLResponse)
async def serve_ui() -> HTMLResponse:
    """Renders interactive local developer studio UI."""
    return HTMLResponse(get_ui_html())


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Lightweight health check endpoint."""
    return {"status": "ok", "engine": "local-coder"}


@app.get("/api/v1/status")
async def get_system_status() -> dict[str, Any]:
    """Provides memory, staged files, and index telemetry."""
    if not orchestrator_instance:
        return {"status": "offline", "rss_mb": 0.0, "max_rss_mb": 1800.0, "staged_files": [], "symbols_count": 0}

    rss = orchestrator_instance.memory_guard.get_resident_memory_mb()
    staged = [
        str(p.relative_to(orchestrator_instance.root_dir))
        for p in orchestrator_instance.shadow_workspace.staged_files
    ]
    return {
        "status": "online",
        "rss_mb": rss,
        "max_rss_mb": orchestrator_instance.memory_guard.budget_mb,
        "workspace_root": str(orchestrator_instance.root_dir),
        "staged_files": staged,
        "symbols_count": len(orchestrator_instance.hdc_index),
    }


@app.post("/api/v1/index")
async def index_repository() -> dict[str, Any]:
    """Triggers repository indexing into HDC and symbol graph."""
    if not orchestrator_instance:
        raise HTTPException(status_code=500, detail="Orchestrator not initialized.")

    start = time.perf_counter()
    count = orchestrator_instance.initialize_codebase()
    elapsed_ms = (time.perf_counter() - start) * 1000
    return {"symbols_indexed": count, "elapsed_ms": elapsed_ms}


@app.post("/api/v1/task")
async def execute_task(req: TaskRequest) -> dict[str, Any]:
    """Executes an autonomous coding task via the ReAct agent loop."""
    if not orchestrator_instance:
        raise HTTPException(status_code=500, detail="Orchestrator not initialized.")

    session = orchestrator_instance.run_coding_task(req.goal)
    steps_data = [
        {
            "step_number": s.step_number,
            "thought": s.thought,
            "action_tool": s.action_tool,
            "action_arguments": s.action_arguments,
            "observation": s.observation,
            "is_successful": s.is_successful,
            "elapsed_seconds": s.elapsed_seconds,
        }
        for s in session.completed_steps
    ]
    return {
        "session_id": session.session_id,
        "status": session.status.value,
        "final_output": session.final_output,
        "output_directory": session.output_directory,
        "modified_files": session.modified_files,
        "steps": steps_data,
    }


@app.get("/api/v1/diff")
async def get_staged_diff() -> dict[str, str]:
    """Returns unified diff of all staged changes in the shadow workspace."""
    if not orchestrator_instance:
        return {"diff": ""}

    patcher = PrecisionPatcher()
    diffs: list[str] = []
    for path, edit in orchestrator_instance.shadow_workspace._staged_edits.items():
        orig = edit.original_content or ""
        new = edit.staged_content
        rel = str(path.relative_to(orchestrator_instance.root_dir))
        diff = patcher.generate_unified_diff(orig, new, file_path=rel)
        if diff:
            diffs.append(diff)

    return {"diff": "\n".join(diffs)}


@app.post("/api/v1/commit")
async def commit_changes() -> dict[str, Any]:
    """Commits staged shadow workspace changes to disk."""
    if not orchestrator_instance:
        raise HTTPException(status_code=500, detail="Orchestrator not initialized.")

    committed = orchestrator_instance.commit_changes()
    return {"status": "ok", "committed_files": committed}


@app.post("/api/v1/rollback")
async def rollback_changes() -> dict[str, str]:
    """Rolls back all staged shadow workspace changes."""
    if not orchestrator_instance:
        raise HTTPException(status_code=500, detail="Orchestrator not initialized.")

    orchestrator_instance.rollback_changes()
    return {"status": "ok", "message": "Shadow workspace rolled back."}


@app.post("/api/v1/terminal")
async def run_terminal(req: TerminalRequest) -> dict[str, Any]:
    """Runs a sandboxed terminal command in the workspace directory."""
    if not orchestrator_instance:
        raise HTTPException(status_code=500, detail="Orchestrator not initialized.")

    res = orchestrator_instance.terminal_runner.run_command(req.command)
    return {
        "exit_code": res.exit_code,
        "stdout": res.stdout,
        "stderr": res.stderr,
        "elapsed_seconds": res.elapsed_seconds,
    }


@app.get("/v1/models")
async def list_models() -> dict[str, Any]:
    """Lists available OpenAI-compatible models."""
    return {
        "object": "list",
        "data": [
            {"id": "local-coder", "object": "model", "owned_by": "local-coder"},
            {"id": "deepseek-r1-distill-1.5b", "object": "model", "owned_by": "local-coder"},
        ],
    }


async def _stream_sse_chunks(prompt: str, model_name: str) -> AsyncGenerator[str, None]:
    req_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
    created = int(time.time())

    if orchestrator_instance:
        for chunk in orchestrator_instance.runner.stream_tokens(prompt):
            payload = {
                "id": req_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": model_name,
                "choices": [{"index": 0, "delta": {"content": chunk}, "finish_reason": None}],
            }
            yield f"data: {json.dumps(payload)}\n\n"

    yield "data: [DONE]\n\n"


@app.post("/v1/chat/completions")
async def chat_completion(request: OpenAIChatRequest) -> Any:
    """OpenAI-compatible chat completions endpoint with streaming support."""
    if not request.messages:
        raise HTTPException(status_code=400, detail="Messages list cannot be empty.")

    user_query = request.messages[-1].content
    req_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
    created = int(time.time())

    if request.stream:
        return StreamingResponse(
            _stream_sse_chunks(user_query, request.model),
            media_type="text/event-stream",
        )

    if orchestrator_instance:
        session = orchestrator_instance.run_coding_task(user_query)
        output_text = session.final_output or "Task finished."
    else:
        output_text = "Orchestrator not initialized."

    return OpenAIChatResponse(
        id=req_id,
        created=created,
        model=request.model,
        choices=[
            OpenAIChoice(
                index=0,
                message=OpenAIChoiceMessage(content=output_text),
                finish_reason="stop",
            )
        ],
    )
