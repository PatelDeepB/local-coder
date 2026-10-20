"""AST manipulation, LibCST surgery, and codebase indexing package."""

from local_coder.ast_engine.cst_surgery import (
    make_function_async,
    replace_function_body,
    wrap_function_error_handler,
)
from local_coder.ast_engine.diff_patcher import PatchResult, PrecisionPatcher
from local_coder.ast_engine.symbol_extractor import ExtractedSymbol, SymbolExtractor
from local_coder.ast_engine.tree_indexer import TreeIndexer

__all__ = [
    "make_function_async",
    "replace_function_body",
    "wrap_function_error_handler",
    "PrecisionPatcher",
    "PatchResult",
    "SymbolExtractor",
    "ExtractedSymbol",
    "TreeIndexer",
]
