"""Master orchestrator integrating workspace, HDC memory, tools, and ReAct agent."""

from pathlib import Path
from typing import Optional
import json
import os
import time
import uuid

from local_coder.agent.execution_loop import AgentExecutionLoop
from local_coder.agent.agent_state import AgentSessionState, AgentStep, TaskStatus
from local_coder.agent.manifest_synthesizer import ManifestSynthesizer
from local_coder.ast_engine.tree_indexer import TreeIndexer
from local_coder.core.config import CONFIG
from local_coder.core.memory_guard import MemoryGuard
from local_coder.knowledge.hdc_code_index import HDCCodeIndex
from local_coder.knowledge.mmap_symbol_graph import MmapSymbolGraph
from local_coder.memory.episodic_ring import EpisodicRollingHashRing
from local_coder.neural.contract_planner import ContractPlanner
from local_coder.neural.llama_runner import LlamaModelRunner
from local_coder.neural.model_router import ModelRouter, ModelProvider
from local_coder.neural.slot_coder import SlotCoder
from local_coder.tools.file_tools import (
    FileOutlineTool,
    ListDirectoryTool,
    ReadFileTool,
    WriteFileTool,
)
from local_coder.tools.patch_tools import ApplySearchReplacePatchTool, LibCSTTransformTool
from local_coder.tools.search_tools import LookupSymbolTool, SearchCodeTool
from local_coder.tools.terminal_tools import RunTerminalCommandTool
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

        # Workspace & Execution Infrastructure
        self.shadow_workspace = ShadowWorkspace(self.root_dir)
        self.transaction_mgr = WorkspaceTransactionManager(self.shadow_workspace)
        self.terminal_runner = TerminalRunner(str(self.root_dir))
        self.git_mgr = GitManager(self.root_dir)
        self.rules_engine = RulesEngine(self.root_dir)
        self.scrubber = SecretScrubber()

        # Knowledge & Zero-RAM Substrates
        self.hdc_index = HDCCodeIndex()
        graph_file = str(self.root_dir / ".localcoder" / "symbols.hkg")
        self.symbol_graph = MmapSymbolGraph(graph_file)
        self.episodic_ring = EpisodicRollingHashRing(ring_capacity=5)
        self.tree_indexer = TreeIndexer(self.hdc_index, self.symbol_graph)

        # Neural Engine
        self.runner = model_runner or ModelRouter(memory_guard=self.memory_guard)
        self.contract_planner = ContractPlanner(self.runner)
        self.slot_coder = SlotCoder(self.runner)

        # Verifier Gate
        self.syntax_validator = SyntaxValidator()
        self.test_runner = TestRunner(self.terminal_runner)
        self.repair_loop = MicroRepairLoop(
            repair_generator=lambda prompt, ctx: self.runner.generate(prompt=prompt, max_tokens=200).content
        )

        # Register Tools
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
        ]

        # Agent Loop & Manifest Synthesizer
        self.agent_loop = AgentExecutionLoop(runner=self.runner, tools=self.tools)
        self.manifest_synthesizer = ManifestSynthesizer(runner=self.runner, workspace=self.shadow_workspace)

    def initialize_codebase(self) -> int:
        """Indexes the repository into HDC vector store and symbol graph. Returns symbol count."""
        return self.tree_indexer.index_directory(self.root_dir)

    def run_coding_task(
        self,
        user_goal: str,
        output_directory: Optional[str | Path] = None,
        auto_commit: bool = True,
    ) -> AgentSessionState:
        """Executes full autonomous coding task in a dedicated physical run directory."""
        self.memory_guard.assert_within_budget()
        rules = self.rules_engine.discover_rules() or ""

        # Step 1: Execute synthesis engine
        goal_lower = user_goal.lower()
        is_scaffold = any(kw in goal_lower for kw in ["create", "build", "scaffold", "react", "website", "next", "app", "application"])

        if is_scaffold:
            session = AgentSessionState(
                session_id=str(uuid.uuid4())[:8],
                user_goal=user_goal,
                status=TaskStatus.IN_PROGRESS,
            )
            step_idx = 0
            start_t = time.perf_counter()

            def on_file(fp: str, idx: int, total: int) -> None:
                nonlocal step_idx
                step_idx += 1
                session.completed_steps.append(
                    AgentStep(
                        step_number=step_idx,
                        thought=f"Synthesizing manifest file {idx}/{total}: {fp}",
                        action_tool="write_file",
                        action_arguments={"file_path": fp},
                        observation=f"Successfully synthesized and staged {fp} in shadow workspace.",
                        is_successful=True,
                        elapsed_seconds=time.perf_counter() - start_t,
                    )
                )

            manifest_files = self.manifest_synthesizer.execute_manifest_synthesis(
                user_goal=user_goal,
                on_file_synthesized=on_file,
            )
            session.status = TaskStatus.COMPLETED
            session.final_output = f"Successfully generated full project ({len(manifest_files)} files): {', '.join(manifest_files)}"
        else:
            session = self.agent_loop.execute_task(user_goal=user_goal, rules_context=rules)

        # Step 2: Create physical directory on disk for this run
        run_dir = (
            Path(output_directory).resolve()
            if output_directory
            else (self.root_dir / "workspace_runs" / f"run_{session.session_id}")
        )
        run_dir.mkdir(parents=True, exist_ok=True)
        session.output_directory = str(run_dir)

        # Step 3: Physically write all staged files to the run directory
        saved_files: list[str] = []
        for p, edit in list(self.shadow_workspace._staged_edits.items()):
            try:
                rel = p.relative_to(self.root_dir)
            except ValueError:
                rel = Path(str(p).replace(str(self.root_dir), "").lstrip("/\\"))

            target_file = run_dir / rel
            target_file.parent.mkdir(parents=True, exist_ok=True)
            with open(target_file, "w", encoding="utf-8") as f:
                f.write(edit.staged_content)
            saved_files.append(str(rel))

        session.modified_files = saved_files

        # Step 4: Write execution summary report to disk
        summary_payload = {
            "session_id": session.session_id,
            "user_goal": session.user_goal,
            "status": session.status.value,
            "output_directory": session.output_directory,
            "modified_files": session.modified_files,
            "final_output": session.final_output,
            "steps": [
                {
                    "step_number": s.step_number,
                    "action_tool": s.action_tool,
                    "action_arguments": s.action_arguments,
                    "observation": s.observation,
                    "elapsed_seconds": s.elapsed_seconds,
                }
                for s in session.completed_steps
            ],
        }
        with open(run_dir / "execution_summary.json", "w", encoding="utf-8") as f:
            json.dump(summary_payload, f, indent=2)

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

    def rollback_changes(self) -> None:
        """Discards all staged edits."""
        self.transaction_mgr.rollback()

    def close(self) -> None:
        """Closes memory-mapped graph and frees neural engine resources."""
        if hasattr(self, "symbol_graph") and self.symbol_graph is not None:
            self.symbol_graph.close()
        if hasattr(self, "runner") and self.runner is not None:
            self.runner.close()
