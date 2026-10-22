"""FastAPI server providing OpenAI-compatible endpoints, REST management, and Web UI."""

from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Optional
import json
import re
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


class InlineEditRequest(BaseModel):
    file_path: str
    selected_code: str
    instruction: str
    prefix_context: str = ""
    suffix_context: str = ""


class AutocompleteRequest(BaseModel):
    prefix: str
    suffix: str = ""
    max_tokens: int = 32
    single_line_only: bool = True


class DiagnosticsHealRequest(BaseModel):
    file_path: str
    content: str
    diagnostics: list[dict] = []


class TestRepairRequest(BaseModel):
    test_path: str = "tests"
    target_file: Optional[str] = None
    max_iterations: int = 3


class SingleFileRequest(BaseModel):
    file_path: str


class ProviderChangeRequest(BaseModel):
    provider: str
    model: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None


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


@app.get("/api/v1/staged-files")
async def get_staged_files() -> dict[str, Any]:
    """Returns detailed metadata and diffs for all staged files."""
    if not orchestrator_instance:
        return {"files": []}

    patcher = PrecisionPatcher()
    files_data = []
    for path, edit in orchestrator_instance.shadow_workspace._staged_edits.items():
        orig = edit.original_content or ""
        new = edit.staged_content
        rel = str(path.relative_to(orchestrator_instance.root_dir)).replace("\\", "/")
        diff = patcher.generate_unified_diff(orig, new, file_path=rel)
        files_data.append(
            {
                "file_path": rel,
                "original_content": orig,
                "staged_content": new,
                "diff": diff,
                "is_deletion": edit.is_deletion,
            }
        )
    return {"files": files_data}


@app.post("/api/v1/staged-files/commit")
async def commit_single_file(req: SingleFileRequest) -> dict[str, Any]:
    """Commits a single staged file to disk."""
    if not orchestrator_instance:
        raise HTTPException(status_code=500, detail="Orchestrator not initialized.")

    success = orchestrator_instance.commit_file(req.file_path)
    return {"status": "ok" if success else "not_found", "file_path": req.file_path}


@app.post("/api/v1/staged-files/discard")
async def discard_single_file(req: SingleFileRequest) -> dict[str, Any]:
    """Discards a single staged file."""
    if not orchestrator_instance:
        raise HTTPException(status_code=500, detail="Orchestrator not initialized.")

    success = orchestrator_instance.discard_file(req.file_path)
    return {"status": "ok" if success else "not_found", "file_path": req.file_path}


@app.get("/api/v1/workspace/files")
async def list_workspace_files() -> dict[str, Any]:
    """Returns list of all code file paths in workspace for context mention autocomplete."""
    if not orchestrator_instance:
        return {"files": []}

    files = []
    ignored = {".git", ".venv", "venv", "node_modules", "__pycache__", ".localcoder"}
    for p in orchestrator_instance.root_dir.rglob("*"):
        if p.is_file() and not any(part in ignored for part in p.parts):
            rel = str(p.relative_to(orchestrator_instance.root_dir)).replace("\\", "/")
            files.append(rel)
    return {"files": sorted(files[:200])}


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


@app.post("/api/v1/inline-edit")
async def inline_edit(req: InlineEditRequest) -> dict[str, Any]:
    """Provides fast scoped inline code replacement for VS Code Ctrl+K."""
    if not orchestrator_instance:
        raise HTTPException(status_code=500, detail="Orchestrator not initialized.")

    start = time.perf_counter()
    prompt = (
        f"File: {req.file_path}\n"
        f"Prefix Context:\n{req.prefix_context[-300:]}\n"
        f"Selected Code to Modify:\n```\n{req.selected_code}\n```\n"
        f"Suffix Context:\n{req.suffix_context[:300]}\n"
        f"Edit Instruction: {req.instruction}\n\n"
        f"Output ONLY the replacement code for the selected block inside a code fence."
    )
    res = orchestrator_instance.runner.generate(prompt=prompt, max_tokens=1024, temperature=0.1)
    raw = res.content.strip()
    m = re.search(r"```(?:[a-zA-Z0-9_-]+)?\s*\n(.*?)\n```", raw, flags=re.DOTALL)
    replacement = m.group(1) if m else raw.replace("```", "").strip()

    patcher = PrecisionPatcher()
    diff = patcher.generate_unified_diff(req.selected_code, replacement, file_path=req.file_path)
    elapsed = time.perf_counter() - start

    return {
        "file_path": req.file_path,
        "replacement_code": replacement,
        "diff": diff,
        "elapsed_seconds": elapsed,
    }


@app.post("/api/v1/autocomplete")
async def autocomplete(req: AutocompleteRequest) -> dict[str, Any]:
    """Generates speculative tab completion ahead of cursor."""
    if not orchestrator_instance:
        raise HTTPException(status_code=500, detail="Orchestrator not initialized.")

    from local_coder.neural.infilling_engine import InfillingEngine
    engine = InfillingEngine(orchestrator_instance.runner)
    result = engine.complete(
        prefix=req.prefix,
        suffix=req.suffix,
        max_tokens=req.max_tokens,
        single_line_only=req.single_line_only,
    )
    return {
        "completion": result.completion,
        "elapsed_ms": result.elapsed_ms,
        "token_count": result.token_count,
    }


@app.post("/api/v1/test-and-repair")
async def test_and_repair(req: TestRepairRequest) -> dict[str, Any]:
    """Runs test suite and autonomously heals code on failure."""
    if not orchestrator_instance:
        raise HTTPException(status_code=500, detail="Orchestrator not initialized.")

    from local_coder.agent.autonomous_test_healer import AutonomousTestHealer
    healer = AutonomousTestHealer(
        runner=orchestrator_instance.runner,
        workspace=orchestrator_instance.shadow_workspace,
        terminal=orchestrator_instance.terminal_runner,
        max_iterations=req.max_iterations,
    )
    result = healer.run_and_repair(test_path=req.test_path, target_file=req.target_file)
    return {
        "is_successful": result.is_successful,
        "iterations_used": result.iterations_used,
        "passed_count": result.passed_count,
        "failed_count": result.failed_count,
        "repaired_files": result.repaired_files,
        "final_output": result.final_output,
    }


@app.post("/api/v1/diagnostics/heal")
async def heal_diagnostics(req: DiagnosticsHealRequest) -> dict[str, Any]:
    """Ingests LSP or compiler diagnostics and attempts targeted self-repair."""
    if not orchestrator_instance:
        raise HTTPException(status_code=500, detail="Orchestrator not initialized.")

    from local_coder.agent.compiler_gate import CompilerGate
    gate = CompilerGate()
    diag_report = gate.ingest_lsp_diagnostics(req.diagnostics)
    if diag_report.is_valid:
        diag_report = gate.check_file_content(req.file_path, req.content)

    if diag_report.is_valid:
        return {"is_repaired": False, "repaired_code": req.content, "message": "No errors found."}

    repair_prompt = gate.format_repair_prompt(diag_report, req.content, req.file_path)
    res = orchestrator_instance.runner.generate(prompt=repair_prompt, max_tokens=1500, temperature=0.1)
    raw = res.content.strip()
    m = re.search(r"```(?:[a-zA-Z0-9_-]+)?\s*\n(.*?)\n```", raw, flags=re.DOTALL)
    repaired = m.group(1) if m else raw.replace("```", "").strip()

    check_res = gate.check_file_content(req.file_path, repaired)
    return {
        "is_repaired": check_res.is_valid,
        "repaired_code": repaired,
        "remaining_errors": [e.message for e in check_res.errors],
    }


@app.post("/api/v1/provider/set")
async def set_model_provider(req: ProviderChangeRequest) -> dict[str, Any]:
    """Switches active model provider dynamically."""
    if not orchestrator_instance:
        raise HTTPException(status_code=500, detail="Orchestrator not initialized.")

    from local_coder.neural.model_router import ModelRouter, ModelProvider
    if isinstance(orchestrator_instance.runner, ModelRouter):
        orchestrator_instance.runner.provider = ModelProvider(req.provider.lower())
        if req.model:
            if req.provider == "ollama":
                orchestrator_instance.runner.ollama_model = req.model
            elif req.provider == "openai":
                orchestrator_instance.runner.openai_model = req.model
        if req.base_url:
            if req.provider == "ollama":
                orchestrator_instance.runner.ollama_base_url = req.base_url.rstrip("/")
            elif req.provider == "openai":
                orchestrator_instance.runner.openai_base_url = req.base_url.rstrip("/")
        if req.api_key:
            orchestrator_instance.runner.openai_api_key = req.api_key
        return {"status": "ok", "provider": orchestrator_instance.runner.provider.value}

    return {"status": "error", "message": "Runner is not a ModelRouter instance"}


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
