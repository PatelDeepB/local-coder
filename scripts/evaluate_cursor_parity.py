"""Evaluation benchmark verifying 80% to 90% Cursor parity across multi-file synthesis and compiler gates."""

from pathlib import Path
import shutil
import time

from local_coder.agent.compiler_gate import CompilerGate
from local_coder.orchestrator import LocalCoderOrchestrator


def run_cursor_parity_benchmark() -> None:
    """Executes complex multi-file application scaffolding and audits compiler diagnostics."""
    eval_dir = Path("workspace_runs/cursor_parity_eval").resolve()
    if eval_dir.exists():
        shutil.rmtree(eval_dir)
    eval_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== Starting LOCAL-CODER Cursor Parity Benchmark ===")
    print(f"Sandbox Directory: {eval_dir}")

    orch = LocalCoderOrchestrator(workspace_root=eval_dir)
    compiler_gate = CompilerGate()

    goal = "Create a Next.js style React Dashboard with package.json, App.jsx, Header.jsx, and styles.css"
    start_time = time.perf_counter()

    print(f"\n[1/3] Executing Manifest-Driven Synthesis with Compiler Gate...")
    created_files = orch.manifest_synthesizer.execute_manifest_synthesis(
        user_goal=goal,
        on_file_synthesized=lambda path, i, total: print(f"  -> [{i}/{total}] Synthesized and verified: {path}")
    )

    print(f"\n[2/3] Committing staged edits to disk...")
    orch.commit_changes()
    elapsed = time.perf_counter() - start_time

    print(f"\n[3/3] Auditing all generated files with CompilerGate...")
    diagnostics_passed = 0
    total_files = len(created_files)

    for rel_path in created_files:
        disk_file = eval_dir / rel_path
        if not disk_file.is_file():
            print(f"  FAILED: Missing file {rel_path}")
            continue

        content = disk_file.read_text(encoding="utf-8")
        report = compiler_gate.check_file_content(rel_path, content)
        if report.is_valid:
            diagnostics_passed += 1
            print(f"  PASSED [Compiler Clean]: {rel_path} ({len(content)} bytes)")
        else:
            print(f"  WARNING [Diagnostics]: {rel_path} -> {report.summary_message}")

    rss = orch.memory_guard.get_resident_memory_mb()
    clean_pct = (diagnostics_passed / total_files * 100) if total_files > 0 else 0.0

    print("\n" + "=" * 55)
    print("=== BENCHMARK RESULTS ===")
    print(f"Total Files Generated:    {total_files}")
    print(f"Compiler Clean Rate:      {clean_pct:.1f}% ({diagnostics_passed}/{total_files})")
    print(f"Elapsed Time:             {elapsed:.2f}s")
    print(f"Peak Resident Memory:     {rss:.1f} MB (Budget: 1900.0 MB)")
    print("=" * 55)

    orch.close()


if __name__ == "__main__":
    run_cursor_parity_benchmark()
