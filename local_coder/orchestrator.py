"""Master orchestrator integrating workspace, HDC memory, tools, and ReAct agent."""

from pathlib import Path
from typing import Optional
import json
import os
import re
import time
import uuid

from local_coder.agent.agent_state import AgentSessionState, AgentStep, TaskStatus
from local_coder.agent.compiler_gate import CompilerGate
from local_coder.agent.diagnostic_healer import DiagnosticHealer
from local_coder.agent.execution_loop import AgentExecutionLoop
from local_coder.agent.context_builder import WorkspaceContextBuilder
from local_coder.agent.fast_apply import FastApplyEngine, FastApplyResult
from local_coder.agent.hierarchical_planner import HierarchicalPlanner
from local_coder.agent.manifest_synthesizer import ManifestSynthesizer
from local_coder.agent.session_disk_flusher import SessionDiskFlusher
from local_coder.ast_engine.tree_indexer import TreeIndexer
from local_coder.core.config import CONFIG
from local_coder.core.memory_guard import MemoryGuard
from local_coder.knowledge.ast_compactor import ASTSemanticCompactor
from local_coder.knowledge.coding_knowledge_db import CodingKnowledgeDB
from local_coder.knowledge.dependency_graph import CodebaseDependencyGraph
from local_coder.knowledge.file_watcher import IncrementalFileWatcher
from local_coder.knowledge.hdc_code_index import HDCCodeIndex
from local_coder.knowledge.mmap_symbol_graph import MmapSymbolGraph
from local_coder.memory.episodic_ring import EpisodicRollingHashRing
from local_coder.neural.contract_planner import ContractPlanner
from local_coder.neural.infilling_engine import InfillingEngine
from local_coder.neural.llama_runner import LlamaModelRunner
from local_coder.neural.model_router import ModelRouter, ModelProvider
from local_coder.neural.slot_coder import SlotCoder
from local_coder.neural.speculative_drafter import SpeculativeDraftingEngine
from local_coder.tools.file_tools import FileOutlineTool, ListDirectoryTool, ReadFileTool, WriteFileTool
from local_coder.tools.patch_tools import ApplySearchReplacePatchTool, LibCSTTransformTool
from local_coder.tools.search_tools import LookupSymbolTool, SearchCodeTool
from local_coder.tools.terminal_tools import RunTerminalCommandTool
from local_coder.tools.test_tools import RunAutonomousTestRepairTool
from local_coder.verifier.repair_loop import MicroRepairLoop
from local_coder.verifier.syntax_validator import SyntaxValidator
from local_coder.verifier.test_runner import TestRunner
from local_coder.workspace.git_manager import GitManager
from local_coder.workspace.rules_engine import RulesEngine
from local_coder.workspace.secret_scrubber import SecretScrubber
from local_coder.workspace.shadow_workspace import ShadowWorkspace
from local_coder.workspace.terminal_runner import TerminalRunner
from local_coder.workspace.transaction_manager import WorkspaceTransactionManager


class LocalCoderOrchestrator:
    """The central coordinator managing all autonomous coding capabilities."""

    def __init__(
        self,
        workspace_root: Optional[str | Path] = None,
        model_runner: Optional[LlamaModelRunner | ModelRouter] = None,
    ) -> None:
        self.root_dir = Path(workspace_root or os.getcwd()).resolve()
        self.memory_guard = MemoryGuard()
        self.scrubber = SecretScrubber()
        self.hdc_index = HDCCodeIndex()
        self.coding_knowledge = CodingKnowledgeDB()
        self.runner = model_runner or ModelRouter(memory_guard=self.memory_guard)
        self.contract_planner = ContractPlanner(self.runner)
        self.slot_coder = SlotCoder(self.runner)
        self.speculative_drafter = SpeculativeDraftingEngine()
        self.infilling_engine = InfillingEngine(self.runner, drafter=self.speculative_drafter)
        self.ast_compactor = ASTSemanticCompactor()
        self.syntax_validator = SyntaxValidator()
        self.compiler_gate = CompilerGate()
        self.episodic_ring = EpisodicRollingHashRing(ring_capacity=5)
        self.symbol_graph: Optional[MmapSymbolGraph] = None
        self.file_watcher: Optional[IncrementalFileWatcher] = None
        self._setup_workspace(self.root_dir)

    def _setup_workspace(self, root: Path) -> None:
        self.root_dir = root
        if self.symbol_graph is not None:
            self.symbol_graph.close()
        if self.file_watcher is not None:
            self.file_watcher.stop()

        self.shadow_workspace = ShadowWorkspace(self.root_dir)
        self.transaction_mgr = WorkspaceTransactionManager(self.shadow_workspace)
        self.terminal_runner = TerminalRunner(str(self.root_dir))
        self.git_mgr = GitManager(self.root_dir)
        self.rules_engine = RulesEngine(self.root_dir)
        graph_file = str(self.root_dir / ".localcoder" / "symbols.hkg")
        self.symbol_graph = MmapSymbolGraph(graph_file)
        self.tree_indexer = TreeIndexer(self.hdc_index, self.symbol_graph)
        self.dependency_graph = CodebaseDependencyGraph(self.root_dir)
        self.file_watcher = IncrementalFileWatcher(
            root_dir=self.root_dir,
            tree_indexer=self.tree_indexer,
            dependency_graph=self.dependency_graph,
        )
        self.test_runner = TestRunner(self.terminal_runner)
        self.repair_loop = MicroRepairLoop(
            repair_generator=lambda prompt, ctx: self.runner.generate(prompt=prompt, max_tokens=200).content
        )
        self.tools = [
            ReadFileTool(self.shadow_workspace),
            WriteFileTool(self.shadow_workspace),
            ListDirectoryTool(self.shadow_workspace),
            FileOutlineTool(self.shadow_workspace),
            SearchCodeTool(self.hdc_index),
            LookupSymbolTool(self.symbol_graph),
            ApplySearchReplacePatchTool(self.shadow_workspace),
            LibCSTTransformTool(self.shadow_workspace),
            RunTerminalCommandTool(self.terminal_runner),
            RunAutonomousTestRepairTool(self.runner, self.shadow_workspace, self.terminal_runner),
        ]
        self.agent_loop = AgentExecutionLoop(runner=self.runner, tools=self.tools)
        self.manifest_synthesizer = ManifestSynthesizer(
            runner=self.runner,
            workspace=self.shadow_workspace,
            coding_knowledge=self.coding_knowledge,
        )
        self.hierarchical_planner = HierarchicalPlanner(
            synthesizer=self.manifest_synthesizer,
            workspace=self.shadow_workspace,
            compiler_gate=self.compiler_gate,
            knowledge_db=self.coding_knowledge,
        )
        self.fast_apply = FastApplyEngine(runner=self.runner, workspace=self.shadow_workspace)

    def set_workspace(self, workspace_root: str | Path) -> None:
        """Dynamically re-roots the orchestrator and shadow workspace to a new workspace directory."""
        target = Path(workspace_root).resolve()
        target.mkdir(parents=True, exist_ok=True)
        if target != self.root_dir:
            self._setup_workspace(target)

    def initialize_codebase(self) -> int:
        """Indexes the repository into HDC vector store and symbol graph. Returns symbol count."""
        return self.tree_indexer.index_directory(self.root_dir)

    def run_fast_apply(
        self, file_path: str, instruction: str, output_directory: Optional[str | Path] = None
    ) -> FastApplyResult:
        """Executes single-pass fast apply edit without multi-step loop overhead."""
        if output_directory:
            self.set_workspace(output_directory)
        self.memory_guard.assert_within_budget()
        res = self.fast_apply.apply_update(file_path=file_path, instruction=instruction)
        if res.is_success:
            run_dir = Path(output_directory).resolve() if output_directory else self.root_dir
            target_file = run_dir / file_path
            target_file.parent.mkdir(parents=True, exist_ok=True)
            with open(target_file, "w", encoding="utf-8") as f:
                f.write(res.staged_content)
        return res

    def run_coding_task(
        self,
        user_goal: str,
        output_directory: Optional[str | Path] = None,
        auto_commit: bool = True,
    ) -> AgentSessionState:
        """Executes full autonomous coding task in a dedicated physical run directory."""
        if output_directory:
            self.set_workspace(output_directory)

        self.memory_guard.assert_within_budget()
        rules = self.rules_engine.discover_rules() or ""

        # Step 0: Fast Apply auto-routing for precision edits and targeted creation
        m_file = re.search(
            r"@([a-zA-Z0-9_./\\-]+\.[a-zA-Z0-9]+)|"
            r"(?:in|for|into|modify|update|edit|create|write|add|generate|to)\s+([a-zA-Z0-9_./\\-]+\.[a-zA-Z0-9]+)|"
            r"\b([a-zA-Z0-9_\-]+\.(py|js|ts|jsx|tsx|html|css|json))\b",
            user_goal,
            re.IGNORECASE,
        )
        target_f = (m_file.group(1) or m_file.group(2) or m_file.group(3)) if m_file else None
        goal_lower = user_goal.lower()

        if not target_f:
            m_s = re.search(r"\b(calculator|converter|analyzer|parser|service|helper|scraper|server|script)\b", goal_lower)
            if m_s and any(w in goal_lower for w in ["python", "py", "function", "class", "script"]):
                target_f = f"{m_s.group(1)}.py"

        # Step 0A: Autonomous Diagnostic and Runtime Healer for multi-file repairs
        repair_kws = ["fix", "repair", "debug", "resolve", "make it work", "clean", "broken", "issue", "diagnos"]
        is_repair = any(re.search(rf"\b{kw}\b", goal_lower) for kw in repair_kws)
        if is_repair and not target_f:
            healer = DiagnosticHealer(runner=self.runner, workspace=self.shadow_workspace)
            session = healer.heal_workspace(root_dir=self.root_dir, user_goal=user_goal)
            if session.modified_files and auto_commit:
                self.shadow_workspace.commit_all()
            return session

        if target_f:
            fast_res = self.run_fast_apply(target_f, user_goal, output_directory)
            if fast_res.is_success:
                step = AgentStep(1, f"Fast Apply {target_f}", "fast_apply", {"file_path": target_f}, "Applied.", True, fast_res.elapsed_seconds)
                return AgentSessionState(
                    session_id=str(uuid.uuid4())[:8], user_goal=user_goal, status=TaskStatus.COMPLETED,
                    output_directory=str(self.root_dir), modified_files=[target_f],
                    final_output=f"Fast Apply completed in {fast_res.elapsed_seconds:.2f}s:\n{fast_res.diff}",
                    completed_steps=[step],
                )

        # Step 1: Detect true multi-file scaffold vs targeted coding
        project_scaffold_patterns = [
            r"\b(create|build|scaffold)\s+(a\s+)?(new\s+)?(project|app|application|website|fullstack|react|dashboard|frontend|backend)\b",
            r"\b(react|nextjs|django|flask|fastapi)\s+(app|application|project|dashboard)\b",
        ]
        is_scaffold = any(re.search(p, goal_lower) for p in project_scaffold_patterns)
        if any(kw in goal_lower for kw in ["function", "method", "class", "script", "test", "patch", "modify", "edit", "update"]):
            is_scaffold = False

        if is_scaffold:
            session = AgentSessionState(session_id=str(uuid.uuid4())[:8], user_goal=user_goal, status=TaskStatus.IN_PROGRESS)
            step_idx, start_t = 0, time.perf_counter()

            def on_file(fp: str, idx: int, total: int) -> None:
                nonlocal step_idx
                step_idx += 1
                session.completed_steps.append(
                    AgentStep(step_idx, f"Synthesizing {fp} ({idx}/{total})", "write_file", {"file_path": fp}, "Staged.", True, time.perf_counter() - start_t)
                )

            manifest = self.manifest_synthesizer.generate_manifest(user_goal)
            results = self.hierarchical_planner.synthesize_hierarchy(
                manifest=manifest, user_goal=user_goal, on_file_progress=on_file,
            )
            manifest_files = [r.file_path for r in results]
            session.status = TaskStatus.COMPLETED
            session.final_output = f"Successfully generated full project ({len(manifest_files)} files): {', '.join(manifest_files)}"
        else:
            full_rules = WorkspaceContextBuilder.build_context_rules(
                root_dir=self.root_dir,
                shadow_workspace=self.shadow_workspace,
                ast_compactor=self.ast_compactor,
                base_rules=rules,
            )
            session = self.agent_loop.execute_task(user_goal=user_goal, rules_context=full_rules)

        # Step 2: Determine run directory
        run_dir = Path(output_directory).resolve() if output_directory else (self.root_dir / "workspace_runs" / f"run_{session.session_id}")
        run_dir.mkdir(parents=True, exist_ok=True)
        session.output_directory = str(run_dir)

        # Step 3: Physically write all staged files to disk
        session.modified_files = SessionDiskFlusher.flush_staged_files(
            workspace=self.shadow_workspace,
            root_dir=self.root_dir,
            destination_dir=run_dir,
        )

        # Step 4: Write execution summary to disk (.localcoder subdirectory to avoid project clutter)
        SessionDiskFlusher.write_execution_summary(
            session=session,
            run_dir=run_dir,
            output_directory=output_directory,
        )

        # Step 5: If auto_commit enabled, commit to workspace root as well
        if auto_commit and self.shadow_workspace.has_staged_edits:
            self.commit_changes()

        # Step 6: Record in episodic memory ring
        summary = session.final_output or f"Completed {len(session.completed_steps)} steps."
        self.episodic_ring.add_turn(user_prompt=user_goal, assistant_response=summary)

        return session

    def commit_changes(self) -> list[str]:
        """Applies shadow workspace edits to real disk files."""
        return self.transaction_mgr.commit()

    def commit_file(self, relative_path: str) -> bool:
        """Commits a single staged file to disk."""
        return self.shadow_workspace.commit_file(relative_path)

    def discard_file(self, relative_path: str) -> bool:
        """Discards a single staged file."""
        return self.shadow_workspace.discard_file(relative_path)

    def rollback_changes(self) -> None:
        """Discards all staged edits."""
        self.transaction_mgr.rollback()

    def close(self) -> None:
        """Closes memory-mapped graph and frees neural engine resources."""
        if hasattr(self, "file_watcher") and self.file_watcher is not None:
            self.file_watcher.stop()
        if hasattr(self, "symbol_graph") and self.symbol_graph is not None:
            self.symbol_graph.close()
        if hasattr(self, "runner") and self.runner is not None:
            self.runner.close()
