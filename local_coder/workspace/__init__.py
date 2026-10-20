"""Workspace management, terminal execution, and git operations package."""

from local_coder.workspace.git_manager import GitManager
from local_coder.workspace.rules_engine import RulesEngine
from local_coder.workspace.secret_scrubber import SecretScrubber
from local_coder.workspace.shadow_workspace import ShadowWorkspace, StagedFileEdit
from local_coder.workspace.terminal_runner import TerminalExecutionResult, TerminalRunner
from local_coder.workspace.transaction_manager import WorkspaceTransactionManager

__all__ = [
    "TerminalRunner",
    "TerminalExecutionResult",
    "ShadowWorkspace",
    "StagedFileEdit",
    "WorkspaceTransactionManager",
    "GitManager",
    "RulesEngine",
    "SecretScrubber",
]
