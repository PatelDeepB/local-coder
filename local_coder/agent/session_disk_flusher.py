"""Utility module to write shadow workspace edits and agent session summaries to disk."""

from pathlib import Path
from typing import Optional
import json

from local_coder.agent.agent_state import AgentSessionState
from local_coder.workspace.shadow_workspace import ShadowWorkspace


class SessionDiskFlusher:
    """Handles flushing staged workspace edits and execution summaries to the disk."""

    @staticmethod
    def flush_staged_files(
        workspace: ShadowWorkspace,
        root_dir: Path,
        destination_dir: Path,
    ) -> list[str]:
        """Physically writes all staged files from the shadow workspace to destination_dir."""
        saved_files: list[str] = []
        for p, edit in list(workspace._staged_edits.items()):
            try:
                rel = p.relative_to(root_dir)
            except ValueError:
                rel = Path(str(p).replace(str(root_dir), "").lstrip("/\\"))

            target_file = destination_dir / rel
            target_file.parent.mkdir(parents=True, exist_ok=True)
            with open(target_file, "w", encoding="utf-8") as f:
                f.write(edit.staged_content)
            saved_files.append(str(rel).replace("\\", "/"))

        return saved_files

    @staticmethod
    def write_execution_summary(
        session: AgentSessionState,
        run_dir: Path,
        output_directory: Optional[str | Path],
    ) -> None:
        """Writes execution_summary.json into the target run directory."""
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
        summary_dir = run_dir / ".localcoder" if output_directory else run_dir
        summary_dir.mkdir(parents=True, exist_ok=True)
        with open(summary_dir / "execution_summary.json", "w", encoding="utf-8") as f:
            json.dump(summary_payload, f, indent=2)
