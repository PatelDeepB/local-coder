"""Workspace inspection, indexing, diffing, and git transaction endpoints."""

from typing import Any
import time

from fastapi import APIRouter, HTTPException

from local_coder.ast_engine.diff_patcher import PrecisionPatcher
from local_coder.server.orchestrator_registry import get_orchestrator
from local_coder.server.schemas import SingleFileRequest, TerminalRequest

workspace_router = APIRouter()


@workspace_router.get("/api/v1/status")
async def get_system_status() -> dict[str, Any]:
    """Provides memory, staged files, and index telemetry."""
    orchestrator = get_orchestrator()
    if not orchestrator:
        return {"status": "offline", "rss_mb": 0.0, "max_rss_mb": 1800.0, "staged_files": [], "symbols_count": 0}

    rss = orchestrator.memory_guard.get_resident_memory_mb()
    staged = [
        str(p.relative_to(orchestrator.root_dir))
        for p in orchestrator.shadow_workspace.staged_files
    ]
    return {
        "status": "online",
        "rss_mb": rss,
        "max_rss_mb": orchestrator.memory_guard.budget_mb,
        "workspace_root": str(orchestrator.root_dir),
        "staged_files": staged,
        "symbols_count": len(orchestrator.hdc_index),
    }


@workspace_router.post("/api/v1/index")
async def index_repository() -> dict[str, Any]:
    """Triggers repository indexing into HDC and symbol graph."""
    orchestrator = get_orchestrator()
    if not orchestrator:
        raise HTTPException(status_code=500, detail="Orchestrator not initialized.")

    start = time.perf_counter()
    count = orchestrator.initialize_codebase()
    elapsed_ms = (time.perf_counter() - start) * 1000
    return {"symbols_indexed": count, "elapsed_ms": elapsed_ms}


@workspace_router.get("/api/v1/diff")
async def get_staged_diff() -> dict[str, str]:
    """Returns unified diff of all staged changes in the shadow workspace."""
    orchestrator = get_orchestrator()
    if not orchestrator:
        return {"diff": ""}

    patcher = PrecisionPatcher()
    diffs: list[str] = []
    for path, edit in orchestrator.shadow_workspace._staged_edits.items():
        orig = edit.original_content or ""
        new = edit.staged_content
        rel = str(path.relative_to(orchestrator.root_dir))
        diff = patcher.generate_unified_diff(orig, new, file_path=rel)
        if diff:
            diffs.append(diff)

    return {"diff": "\n".join(diffs)}


@workspace_router.get("/api/v1/staged-files")
async def get_staged_files() -> dict[str, Any]:
    """Returns detailed metadata and diffs for all staged files."""
    orchestrator = get_orchestrator()
    if not orchestrator:
        return {"files": []}

    patcher = PrecisionPatcher()
    files_data = []
    for path, edit in orchestrator.shadow_workspace._staged_edits.items():
        orig = edit.original_content or ""
        new = edit.staged_content
        rel = str(path.relative_to(orchestrator.root_dir)).replace("\\", "/")
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


@workspace_router.post("/api/v1/staged-files/commit")
async def commit_single_file(req: SingleFileRequest) -> dict[str, Any]:
    """Commits a single staged file to disk."""
    orchestrator = get_orchestrator()
    if not orchestrator:
        raise HTTPException(status_code=500, detail="Orchestrator not initialized.")

    success = orchestrator.commit_file(req.file_path)
    return {"status": "ok" if success else "not_found", "file_path": req.file_path}


@workspace_router.post("/api/v1/staged-files/discard")
async def discard_single_file(req: SingleFileRequest) -> dict[str, Any]:
    """Discards a single staged file."""
    orchestrator = get_orchestrator()
    if not orchestrator:
        raise HTTPException(status_code=500, detail="Orchestrator not initialized.")

    success = orchestrator.discard_file(req.file_path)
    return {"status": "ok" if success else "not_found", "file_path": req.file_path}


@workspace_router.get("/api/v1/workspace/files")
async def list_workspace_files() -> dict[str, Any]:
    """Returns list of all code file paths in workspace for context mention autocomplete."""
    orchestrator = get_orchestrator()
    if not orchestrator:
        return {"files": []}

    files = []
    ignored = {".git", ".venv", "venv", "node_modules", "__pycache__", ".localcoder"}
    for p in orchestrator.root_dir.rglob("*"):
        if p.is_file() and not any(part in ignored for part in p.parts):
            rel = str(p.relative_to(orchestrator.root_dir)).replace("\\", "/")
            files.append(rel)
    return {"files": sorted(files[:200])}


@workspace_router.post("/api/v1/workspace/set")
async def set_active_workspace(req: dict[str, str]) -> dict[str, str]:
    """Sets the active workspace root directory."""
    orchestrator = get_orchestrator()
    if not orchestrator:
        raise HTTPException(status_code=500, detail="Orchestrator not initialized.")
    ws = req.get("workspace_root")
    if ws:
        orchestrator.set_workspace(ws)
    return {"status": "ok", "workspace_root": str(orchestrator.root_dir)}


@workspace_router.post("/api/v1/commit")
async def commit_changes() -> dict[str, Any]:
    """Commits staged shadow workspace changes to disk."""
    orchestrator = get_orchestrator()
    if not orchestrator:
        raise HTTPException(status_code=500, detail="Orchestrator not initialized.")

    committed = orchestrator.commit_changes()
    return {"status": "ok", "committed_files": committed}


@workspace_router.post("/api/v1/rollback")
async def rollback_changes() -> dict[str, str]:
    """Rolls back all staged shadow workspace changes."""
    orchestrator = get_orchestrator()
    if not orchestrator:
        raise HTTPException(status_code=500, detail="Orchestrator not initialized.")

    orchestrator.rollback_changes()
    return {"status": "ok", "message": "Shadow workspace rolled back."}


@workspace_router.post("/api/v1/terminal")
async def run_terminal(req: TerminalRequest) -> dict[str, Any]:
    """Runs a sandboxed terminal command in the workspace directory."""
    orchestrator = get_orchestrator()
    if not orchestrator:
        raise HTTPException(status_code=500, detail="Orchestrator not initialized.")

    res = orchestrator.terminal_runner.run_command(req.command)
    return {
        "exit_code": res.exit_code,
        "stdout": res.stdout,
        "stderr": res.stderr,
        "elapsed_seconds": res.elapsed_seconds,
    }
