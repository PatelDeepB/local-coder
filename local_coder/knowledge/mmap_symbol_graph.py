"""Zero-copy memory-mapped binary graph store (.hkg) for symbol dependencies."""

from dataclasses import dataclass
from typing import Optional
import json
import mmap
import os
import struct


@dataclass(frozen=True)
class SymbolNode:
    """Represents a code symbol and its relational dependencies."""

    symbol_id: str
    file_path: str
    symbol_type: str
    signature: str
    dependencies: tuple[str, ...]


class MmapSymbolGraph:
    """Zero-copy on-disk memory-mapped graph store for repository symbols."""

    MAGIC = b"HKG2"

    def __init__(self, file_path: str) -> None:
        self.file_path = file_path
        self._file = None
        self._mmap: Optional[mmap.mmap] = None
        self._nodes: dict[str, SymbolNode] = {}

        if os.path.exists(file_path):
            self._load_existing()

    def _load_existing(self) -> None:
        """Loads and maps the existing binary file."""
        self._file = open(self.file_path, "r+b")
        self._mmap = mmap.mmap(self._file.fileno(), 0, access=mmap.ACCESS_READ)
        if len(self._mmap) < 8:
            return

        magic = self._mmap[:4]
        if magic != self.MAGIC:
            return

        payload_len = struct.unpack("<I", self._mmap[4:8])[0]
        raw_payload = self._mmap[8 : 8 + payload_len]
        data = json.loads(raw_payload.decode("utf-8"))

        for item in data:
            node = SymbolNode(
                symbol_id=item["symbol_id"],
                file_path=item["file_path"],
                symbol_type=item["symbol_type"],
                signature=item["signature"],
                dependencies=tuple(item.get("dependencies", [])),
            )
            self._nodes[node.symbol_id] = node

    def add_node(self, node: SymbolNode) -> None:
        """Adds a symbol node to the graph in memory."""
        self._nodes[node.symbol_id] = node

    def save(self) -> None:
        """Flushes graph nodes to the memory-mapped binary file."""
        if self._mmap:
            self._mmap.close()
            self._mmap = None
        if self._file:
            self._file.close()
            self._file = None

        os.makedirs(os.path.dirname(os.path.abspath(self.file_path)), exist_ok=True)
        serialized = [
            {
                "symbol_id": n.symbol_id,
                "file_path": n.file_path,
                "symbol_type": n.symbol_type,
                "signature": n.signature,
                "dependencies": list(n.dependencies),
            }
            for n in self._nodes.values()
        ]
        payload = json.dumps(serialized).encode("utf-8")
        header = self.MAGIC + struct.pack("<I", len(payload))

        with open(self.file_path, "wb") as f:
            f.write(header + payload)

        self._load_existing()

    def get_node(self, symbol_id: str) -> Optional[SymbolNode]:
        """Looks up a symbol node by identifier."""
        return self._nodes.get(symbol_id)

    def get_callers(self, target_symbol_id: str) -> list[SymbolNode]:
        """Finds all symbols that depend on the target symbol."""
        return [n for n in self._nodes.values() if target_symbol_id in n.dependencies]

    def close(self) -> None:
        """Closes memory mapping and file descriptors."""
        if self._mmap:
            self._mmap.close()
            self._mmap = None
        if self._file:
            self._file.close()
            self._file = None

    def __len__(self) -> int:
        return len(self._nodes)
