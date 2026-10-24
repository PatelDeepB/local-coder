"""OpenAI-compatible chat and models endpoints."""

from typing import Any, AsyncGenerator, Optional
import json
import time
import uuid

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from local_coder.orchestrator import LocalCoderOrchestrator
from local_coder.server.orchestrator_registry import get_orchestrator
from local_coder.server.schemas import (
    OpenAIChatRequest,
    OpenAIChatResponse,
    OpenAIChoice,
    OpenAIChoiceMessage,
)

openai_router = APIRouter()


async def _stream_sse_chunks(
    prompt: str,
    model_name: str,
    orchestrator: Optional[LocalCoderOrchestrator],
) -> AsyncGenerator[str, None]:
    req_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
    created = int(time.time())

    if orchestrator:
        for chunk in orchestrator.runner.stream_tokens(prompt):
            payload = {
                "id": req_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": model_name,
                "choices": [{"index": 0, "delta": {"content": chunk}, "finish_reason": None}],
            }
            yield f"data: {json.dumps(payload)}\n\n"

    yield "data: [DONE]\n\n"


@openai_router.get("/v1/models")
async def list_models() -> dict[str, Any]:
    """Lists available OpenAI-compatible models."""
    return {
        "object": "list",
        "data": [
            {"id": "local-coder", "object": "model", "owned_by": "local-coder"},
            {"id": "deepseek-r1-distill-1.5b", "object": "model", "owned_by": "local-coder"},
        ],
    }


@openai_router.post("/v1/chat/completions")
async def chat_completion(request: OpenAIChatRequest) -> Any:
    """OpenAI-compatible chat completions endpoint with streaming support."""
    if not request.messages:
        raise HTTPException(status_code=400, detail="Messages list cannot be empty.")

    user_query = request.messages[-1].content
    req_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
    created = int(time.time())
    orchestrator = get_orchestrator()

    if request.stream:
        return StreamingResponse(
            _stream_sse_chunks(user_query, request.model, orchestrator),
            media_type="text/event-stream",
        )

    if orchestrator:
        session = orchestrator.run_coding_task(user_query)
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
