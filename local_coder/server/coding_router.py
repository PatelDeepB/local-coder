"""Coding agent task execution, fast apply, inline edits, and code healing endpoints."""

from typing import Any
import asyncio
import re
import time

from fastapi import APIRouter, HTTPException

from local_coder.ast_engine.diff_patcher import PrecisionPatcher
from local_coder.server.orchestrator_registry import get_orchestrator
from local_coder.server.schemas import (
    AutocompleteRequest,
    DiagnosticsHealRequest,
    FastApplyRequest,
    InlineEditRequest,
    ProviderChangeRequest,
    TaskRequest,
    TestRepairRequest,
)

coding_router = APIRouter()


@coding_router.post("/api/v1/task")
async def execute_task(req: TaskRequest) -> dict[str, Any]:
    """Executes an autonomous coding task via the ReAct agent loop."""
    orchestrator = get_orchestrator()
    if not orchestrator:
        raise HTTPException(status_code=500, detail="Orchestrator not initialized.")

    if req.output_directory:
        orchestrator.set_workspace(req.output_directory)

    try:
        session = await asyncio.to_thread(
            orchestrator.run_coding_task,
            user_goal=req.goal,
            output_directory=req.output_directory,
            auto_commit=True,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Task execution error: {str(exc)}")

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


@coding_router.post("/api/v1/fast-apply")
async def execute_fast_apply(req: FastApplyRequest) -> dict[str, Any]:
    """Applies single-pass precision update to target file."""
    orchestrator = get_orchestrator()
    if not orchestrator:
        raise HTTPException(status_code=500, detail="Orchestrator not initialized.")

    result = await asyncio.to_thread(
        orchestrator.run_fast_apply,
        file_path=req.file_path,
        instruction=req.instruction,
        output_directory=req.output_directory,
    )
    return {
        "file_path": result.file_path,
        "is_success": result.is_success,
        "diff": result.diff,
        "error_message": result.error_message,
        "elapsed_seconds": result.elapsed_seconds,
    }


@coding_router.post("/api/v1/inline-edit")
async def inline_edit(req: InlineEditRequest) -> dict[str, Any]:
    """Provides fast scoped inline code replacement for VS Code Ctrl+K."""
    orchestrator = get_orchestrator()
    if not orchestrator:
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
    res = orchestrator.runner.generate(prompt=prompt, max_tokens=1024, temperature=0.1)
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


@coding_router.post("/api/v1/autocomplete")
async def autocomplete(req: AutocompleteRequest) -> dict[str, Any]:
    """Generates speculative tab completion ahead of cursor."""
    orchestrator = get_orchestrator()
    if not orchestrator:
        raise HTTPException(status_code=500, detail="Orchestrator not initialized.")

    from local_coder.neural.infilling_engine import InfillingEngine

    if (
        hasattr(orchestrator, "infilling_engine")
        and isinstance(orchestrator.infilling_engine, InfillingEngine)
    ):
        engine = orchestrator.infilling_engine
    else:
        engine = InfillingEngine(orchestrator.runner)

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


@coding_router.post("/api/v1/test-and-repair")
async def test_and_repair(req: TestRepairRequest) -> dict[str, Any]:
    """Runs test suite and autonomously heals code on failure."""
    orchestrator = get_orchestrator()
    if not orchestrator:
        raise HTTPException(status_code=500, detail="Orchestrator not initialized.")

    from local_coder.agent.autonomous_test_healer import AutonomousTestHealer
    healer = AutonomousTestHealer(
        runner=orchestrator.runner,
        workspace=orchestrator.shadow_workspace,
        terminal=orchestrator.terminal_runner,
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


@coding_router.post("/api/v1/diagnostics/heal")
async def heal_diagnostics(req: DiagnosticsHealRequest) -> dict[str, Any]:
    """Ingests LSP or compiler diagnostics and attempts targeted self-repair."""
    orchestrator = get_orchestrator()
    if not orchestrator:
        raise HTTPException(status_code=500, detail="Orchestrator not initialized.")

    from local_coder.agent.compiler_gate import CompilerGate
    gate = CompilerGate()
    diag_report = gate.ingest_lsp_diagnostics(req.diagnostics)
    if diag_report.is_valid:
        diag_report = gate.check_file_content(req.file_path, req.content)

    if diag_report.is_valid:
        return {"is_repaired": False, "repaired_code": req.content, "message": "No errors found."}

    repair_prompt = gate.format_repair_prompt(diag_report, req.content, req.file_path)
    res = orchestrator.runner.generate(prompt=repair_prompt, max_tokens=1500, temperature=0.1)
    raw = res.content.strip()
    m = re.search(r"```(?:[a-zA-Z0-9_-]+)?\s*\n(.*?)\n```", raw, flags=re.DOTALL)
    repaired = m.group(1) if m else raw.replace("```", "").strip()

    check_res = gate.check_file_content(req.file_path, repaired)
    return {
        "is_repaired": check_res.is_valid,
        "repaired_code": repaired,
        "remaining_errors": [e.message for e in check_res.errors],
    }


@coding_router.post("/api/v1/provider/set")
async def set_model_provider(req: ProviderChangeRequest) -> dict[str, Any]:
    """Switches active model provider dynamically."""
    orchestrator = get_orchestrator()
    if not orchestrator:
        raise HTTPException(status_code=500, detail="Orchestrator not initialized.")

    from local_coder.neural.model_router import ModelRouter, ModelProvider
    if isinstance(orchestrator.runner, ModelRouter):
        orchestrator.runner.provider = ModelProvider(req.provider.lower())
        if req.model:
            if req.provider == "ollama":
                orchestrator.runner.ollama_model = req.model
            elif req.provider == "openai":
                orchestrator.runner.openai_model = req.model
        if req.base_url:
            if req.provider == "ollama":
                orchestrator.runner.ollama_base_url = req.base_url.rstrip("/")
            elif req.provider == "openai":
                orchestrator.runner.openai_base_url = req.base_url.rstrip("/")
        if req.api_key:
            orchestrator.runner.openai_api_key = req.api_key
        return {"status": "ok", "provider": orchestrator.runner.provider.value}

    return {"status": "error", "message": "Runner is not a ModelRouter instance"}
