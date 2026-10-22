"""Sub-millisecond code index powered by Hyperdimensional Computing (HDC)."""

from dataclasses import dataclass
from typing import Optional
import re
import numpy as np

from local_coder.knowledge.hyper_vector import HyperVector


@dataclass(frozen=True)
class CodeSearchHit:
    """Represents a search hit from the hyperdimensional code index."""

    symbol_id: str
    file_path: str
    symbol_type: str
    code_snippet: str
    similarity: float


class HDCCodeIndex:
    """Stores and queries code symbols using 10,240-bit hypervectors."""

    def __init__(self, dimension: int = 10240) -> None:
        self.dimension = dimension
        self._symbols: list[dict[str, str]] = []
        self._matrix: Optional[np.ndarray] = None  # Shape: (N, dimension)

    def encode_code(self, text: str) -> HyperVector:
        """Encodes code text into a composite hypervector via subword token bundling."""
        words = [w.lower() for w in re.findall(r"[A-Za-z0-9]+", text) if len(w) > 1]
        if not words:
            return HyperVector.from_seed("empty", dimension=self.dimension)

        # Bag-of-symbols unigram vectors
        components = [
            HyperVector.from_seed(f"tok_{w}", dimension=self.dimension)
            for w in words[:128]
        ]
        return HyperVector.bundle(components)

    def add_symbol(
        self,
        symbol_id: str,
        file_path: str,
        symbol_type: str,
        code_snippet: str,
    ) -> None:
        """Adds a code symbol to the hyperdimensional index."""
        vec = self.encode_code(f"{symbol_id} {code_snippet}")
        self._symbols.append(
            {
                "symbol_id": symbol_id,
                "file_path": file_path,
                "symbol_type": symbol_type,
                "code_snippet": code_snippet,
            }
        )

        row = vec.data[np.newaxis, :].astype(np.float32)
        if self._matrix is None:
            self._matrix = row
        else:
            self._matrix = np.vstack([self._matrix, row])

    def remove_file(self, file_path: str) -> int:
        """Removes all symbols belonging to a specific file path from the index."""
        if not self._symbols or self._matrix is None:
            return 0

        keep_indices = [
            i for i, s in enumerate(self._symbols) if s["file_path"] != file_path
        ]
        removed_count = len(self._symbols) - len(keep_indices)
        if removed_count == 0:
            return 0

        if len(keep_indices) == 0:
            self._symbols = []
            self._matrix = None
            return removed_count

        self._symbols = [self._symbols[i] for i in keep_indices]
        self._matrix = self._matrix[keep_indices]
        return removed_count

    def search(self, query: str, limit: int = 5) -> list[CodeSearchHit]:
        """Searches index using single matrix dot product (sub-millisecond)."""
        if self._matrix is None or len(self._symbols) == 0:
            return []

        query_vec = self.encode_code(query).data.astype(np.float32)
        # Vectorized batch dot product across all indexed symbols
        scores = np.dot(self._matrix, query_vec) / float(self.dimension)

        top_indices = np.argsort(scores)[::-1][:limit]
        hits: list[CodeSearchHit] = []

        for idx in top_indices:
            score = float(scores[idx])
            if score > 0.10:  # Valid similarity threshold
                item = self._symbols[idx]
                hits.append(
                    CodeSearchHit(
                        symbol_id=item["symbol_id"],
                        file_path=item["file_path"],
                        symbol_type=item["symbol_type"],
                        code_snippet=item["code_snippet"],
                        similarity=score,
                    )
                )

        return hits

    def __len__(self) -> int:
        return len(self._symbols)
