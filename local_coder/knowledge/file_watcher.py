"""Incremental file watcher daemon for sub-2ms symbol and dependency graph updates."""

from dataclasses import dataclass
import logging
import os
from pathlib import Path
import threading
import time
from typing import Callable, Optional

from local_coder.ast_engine.tree_indexer import TreeIndexer
from local_coder.knowledge.dependency_graph import CodebaseDependencyGraph

logger = logging.getLogger("file_watcher")


@dataclass(frozen=True)
class FileUpdateEvent:
    """Telemetry for a single incremental index update."""

    file_path: str
    elapsed_ms: float
    symbols_updated: int
    dependencies_updated: int


class IncrementalFileWatcher:
    """Detects modified files and updates HDC index and dependency graph incrementally."""

    IGNORED_DIRS = {
        ".git",
        "__pycache__",
        ".venv",
        "venv",
        "node_modules",
        ".pytest_cache",
        "build",
        "dist",
        ".idea",
        ".vscode",
        ".localcoder",
    }

    def __init__(
        self,
        root_dir: str | Path,
        tree_indexer: TreeIndexer,
        dependency_graph: CodebaseDependencyGraph,
        on_update_callback: Optional[Callable[[FileUpdateEvent], None]] = None,
    ) -> None:
        self.root_dir = Path(root_dir).resolve()
        self.tree_indexer = tree_indexer
        self.dependency_graph = dependency_graph
        self.on_update_callback = on_update_callback
        self._mtime_cache: dict[str, float] = {}
        self._is_running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._prime_cache()

    def _prime_cache(self) -> None:
        """Records initial file modification timestamps without triggering events."""
        for path in self._walk_tracked_files():
            try:
                self._mtime_cache[str(path)] = path.stat().st_mtime
            except OSError:
                pass

    def _walk_tracked_files(self) -> list[Path]:
        """Collects all trackable code files in workspace."""
        tracked: list[Path] = []
        for dirpath, dirnames, filenames in os.walk(self.root_dir):
            dirnames[:] = [d for d in dirnames if d not in self.IGNORED_DIRS]
            for filename in filenames:
                ext = Path(filename).suffix.lower()
                if ext in (".py", ".js", ".jsx", ".ts", ".tsx", ".json", ".html", ".css"):
                    tracked.append(Path(dirpath) / filename)
        return tracked

    def process_file_change(self, file_path: Path) -> FileUpdateEvent:
        """Incrementally re-indexes a single modified file in sub-2ms."""
        start_t = time.perf_counter()
        sym_count = 0
        dep_count = 0

        # Update symbol graph if Python
        if file_path.suffix.lower() == ".py":
            sym_count = self.tree_indexer.reindex_file(file_path, self.root_dir)

        # Update multi-hop dependency graph
        if file_path.suffix.lower() in (".py", ".js", ".jsx", ".ts", ".tsx"):
            dep_count = self.dependency_graph.update_file(file_path)

        elapsed_ms = (time.perf_counter() - start_t) * 1000.0
        rel_path = str(file_path.relative_to(self.root_dir)).replace("\\", "/")

        event = FileUpdateEvent(
            file_path=rel_path,
            elapsed_ms=elapsed_ms,
            symbols_updated=sym_count,
            dependencies_updated=dep_count,
        )

        if self.on_update_callback:
            try:
                self.on_update_callback(event)
            except Exception as e:
                logger.error("Error in watcher callback: %s", e)

        return event

    def poll_once(self) -> list[FileUpdateEvent]:
        """Performs a single sweep for modified or deleted files."""
        events: list[FileUpdateEvent] = []
        current_files = self._walk_tracked_files()
        current_paths_set = {str(p) for p in current_files}

        with self._lock:
            # Check for modified or new files
            for p in current_files:
                p_str = str(p)
                try:
                    mtime = p.stat().st_mtime
                except OSError:
                    continue

                cached_mtime = self._mtime_cache.get(p_str)
                if cached_mtime is None or mtime > cached_mtime:
                    self._mtime_cache[p_str] = mtime
                    ev = self.process_file_change(p)
                    events.append(ev)

            # Check for deleted files
            deleted = [p_str for p_str in self._mtime_cache if p_str not in current_paths_set]
            for d_str in deleted:
                del self._mtime_cache[d_str]
                ev = self.process_file_change(Path(d_str))
                events.append(ev)

        return events

    def start_background_watcher(self, interval_seconds: float = 0.5) -> None:
        """Starts background daemon thread for continuous file observation."""
        if self._is_running:
            return

        self._is_running = True
        self._thread = threading.Thread(
            target=self._run_loop,
            args=(interval_seconds,),
            daemon=True,
            name="local-coder-file-watcher",
        )
        self._thread.start()

    def _run_loop(self, interval: float) -> None:
        """Internal daemon loop polling workspace filesystem."""
        while self._is_running:
            try:
                self.poll_once()
            except Exception as e:
                logger.error("Watcher polling error: %s", e)
            time.sleep(interval)

    def stop(self) -> None:
        """Stops background watcher gracefully."""
        self._is_running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
