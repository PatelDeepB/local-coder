"""Benchmark comparing LOCAL-CODER generated Django application against a gold standard reference."""

import json
from pathlib import Path
import shutil
import time

from local_coder.agent.compiler_gate import CompilerGate
from local_coder.orchestrator import LocalCoderOrchestrator


def run_local_coder_django_synthesis() -> dict:
    """Invokes LOCAL-CODER to scaffold a full Django application."""
    target_dir = Path("workspace_runs/local_coder_django_app").resolve()
    if target_dir.exists():
        shutil.rmtree(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    print("=== Step 1: Synthesizing Django App with LOCAL-CODER ===")
    orch = LocalCoderOrchestrator(workspace_root=target_dir)
    compiler_gate = CompilerGate()

    goal = (
        "Create a complete production Django task management application with manage.py, "
        "settings.py, urls.py, models.py, views.py, forms.py, admin.py, tests.py, and HTML templates."
    )

    start_time = time.perf_counter()
    created_files = orch.manifest_synthesizer.execute_manifest_synthesis(
        user_goal=goal,
        on_file_synthesized=lambda path, i, total: print(f"  -> [{i}/{total}] Local Coder created: {path}")
    )

    orch.commit_changes()
    elapsed = time.perf_counter() - start_time
    rss = orch.memory_guard.get_resident_memory_mb()

    # Audit each generated file
    compiler_clean_count = 0
    file_details = []
    for rel_path in created_files:
        f_path = target_dir / rel_path
        if f_path.is_file():
            content = f_path.read_text(encoding="utf-8", errors="ignore")
            report = compiler_gate.check_file_content(rel_path, content)
            is_clean = report.is_valid
            if is_clean:
                compiler_clean_count += 1
            file_details.append({
                "file_path": rel_path,
                "bytes": len(content),
                "is_clean": is_clean,
                "error": report.summary_message if not is_clean else None,
            })

    orch.close()

    result = {
        "generator": "LOCAL-CODER (Autonomous Agent)",
        "output_dir": str(target_dir),
        "total_files": len(created_files),
        "compiler_clean_count": compiler_clean_count,
        "clean_percentage": (compiler_clean_count / len(created_files) * 100) if created_files else 0.0,
        "elapsed_seconds": elapsed,
        "peak_rss_mb": rss,
        "files": file_details,
    }

    return result


if __name__ == "__main__":
    res = run_local_coder_django_synthesis()
    print("\nLocal Coder Result:")
    print(json.dumps(res, indent=2))
