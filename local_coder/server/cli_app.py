"""Interactive terminal application for LOCAL-CODER."""

import sys
from pathlib import Path

from local_coder.orchestrator import LocalCoderOrchestrator


def main() -> None:
    """Launches interactive CLI session."""
    print("=" * 60)
    print("  LOCAL-CODER: Frontier-Grade Autonomous Coding Agent")
    print("  RAM Ceiling: Strictly < 2.0 GB | CPU SIMD Optimized")
    print("=" * 60)

    workspace = sys.argv[1] if len(sys.argv) > 1 else "."
    orch = LocalCoderOrchestrator(workspace_root=workspace)

    print(f"\nScanning and indexing workspace at '{orch.root_dir}'...")
    count = orch.initialize_codebase()
    print(f"Indexed {count} symbols into on-disk HDC and graph substrates.")

    print("\nReady! Enter coding requests (or 'exit' to quit):")
    while True:
        try:
            goal = input("\nlocal-coder> ").strip()
            if not goal:
                continue
            if goal.lower() in {"exit", "quit", "q"}:
                print("Exiting LOCAL-CODER.")
                break

            print("\nPlanning and executing...")
            session = orch.run_coding_task(goal)

            print("\n=== Execution Summary ===")
            for step in session.completed_steps:
                status_icon = "[OK]" if step.is_successful else "[ERR]"
                print(f"{status_icon} Step {step.step_number}: {step.action_tool} ({step.elapsed_seconds:.2f}s)")

            if orch.shadow_workspace.has_staged_edits:
                print(f"\nPending edits in {len(orch.shadow_workspace.staged_files)} files.")
                choice = input("Commit changes to disk? [y/N]: ").strip().lower()
                if choice == "y":
                    applied = orch.commit_changes()
                    print(f"Applied changes to: {', '.join(applied)}")
                else:
                    orch.rollback_changes()
                    print("Changes discarded.")
            else:
                if session.final_output:
                    print(f"\nResponse:\n{session.final_output}")

        except KeyboardInterrupt:
            print("\nAborted.")
            break
        except Exception as exc:
            print(f"Error: {exc}")


if __name__ == "__main__":
    main()
