"""Neural inference and contract planning package."""

from local_coder.neural.contract_planner import CodeContract, ContractPlanner
from local_coder.neural.grammar_engine import build_tool_calling_grammar, parse_tool_call_json
from local_coder.neural.llama_runner import GenerationResult, LlamaModelRunner
from local_coder.neural.model_router import ModelProvider, ModelRouter

__all__ = [
    "LlamaModelRunner",
    "GenerationResult",
    "ModelRouter",
    "ModelProvider",
    "ContractPlanner",
    "CodeContract",
    "build_tool_calling_grammar",
    "parse_tool_call_json",
]
