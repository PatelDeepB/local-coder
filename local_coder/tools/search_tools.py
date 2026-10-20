"""Hyperdimensional and graph search tools for instant codebase exploration."""

from typing import Any
from local_coder.knowledge.hdc_code_index import HDCCodeIndex
from local_coder.knowledge.mmap_symbol_graph import MmapSymbolGraph
from local_coder.tools.base_tool import BaseAgentTool, ToolResult


class SearchCodeTool(BaseAgentTool):
    """Searches codebase using sub-millisecond hyperdimensional bitwise vector search."""

    def __init__(self, index: HDCCodeIndex) -> None:
        self.index = index

    @property
    def name(self) -> str:
        return "search_code"

    @property
    def description(self) -> str:
        return "Performs fast semantic code search across the codebase using hyperdimensional indexing."

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Semantic search query or symbol intent"},
                "limit": {"type": "integer", "description": "Maximum hits to return", "default": 4},
            },
            "required": ["query"],
        }

    def execute(self, **kwargs: Any) -> ToolResult:
        query = kwargs.get("query", "")
        limit = kwargs.get("limit", 4)
        hits = self.index.search(query, limit=limit)
        if not hits:
            return ToolResult(is_success=True, output="No relevant code symbols found.")

        lines = [f"=== Search Hits for '{query}' ==="]
        for h in hits:
            lines.append(f"- [{h.symbol_type}] {h.symbol_id} (Score: {h.similarity:.2f})")
            lines.append(f"  {h.code_snippet.strip()}")

        return ToolResult(is_success=True, output="\n".join(lines))


class LookupSymbolTool(BaseAgentTool):
    """Looks up exact symbol definition and callers in the binary symbol graph."""

    def __init__(self, graph: MmapSymbolGraph) -> None:
        self.graph = graph

    @property
    def name(self) -> str:
        return "lookup_symbol"

    @property
    def description(self) -> str:
        return "Retrieves the exact signature, file location, and callers of a symbol."

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "symbol_id": {"type": "string", "description": "Exact symbol identifier (e.g. 'main.py:process_data')"}
            },
            "required": ["symbol_id"],
        }

    def execute(self, **kwargs: Any) -> ToolResult:
        sym_id = kwargs.get("symbol_id", "")
        node = self.graph.get_node(sym_id)
        if not node:
            return ToolResult(is_success=False, output="", error_message=f"Symbol '{sym_id}' not found in graph.")

        callers = self.graph.get_callers(sym_id)
        caller_str = ", ".join(c.symbol_id for c in callers) if callers else "None"

        res = (
            f"Symbol: {node.symbol_id}\n"
            f"File: {node.file_path}\n"
            f"Type: {node.symbol_type}\n"
            f"Signature: {node.signature}\n"
            f"Dependencies: {', '.join(node.dependencies) or 'None'}\n"
            f"Callers: {caller_str}"
        )
        return ToolResult(is_success=True, output=res)
