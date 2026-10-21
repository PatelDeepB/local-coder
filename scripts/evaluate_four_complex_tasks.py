"""4-Task Complex Multi-Domain Evaluation Suite for LOCAL-CODER."""

import json
from pathlib import Path
import shutil
import time

from local_coder.agent.compiler_gate import CompilerGate
from local_coder.orchestrator import LocalCoderOrchestrator


BENCHMARK_TASKS = [
    {
        "id": "task_1_react_dashboard",
        "name": "Modern React 18 Dashboard",
        "domain": "Frontend SPA",
        "goal": "Create a modern React 18 single page dashboard with package.json, App.jsx, index.html, and styles.css",
        "target_dir": "workspace_runs/eval_4tasks/task_1_react",
    },
    {
        "id": "task_2_django_app",
        "name": "Django Production MVC Application",
        "domain": "Fullstack Web",
        "goal": "Create a production Django task management application with manage.py, settings.py, urls.py, models.py, forms.py, views.py, tests.py, and templates",
        "target_dir": "workspace_runs/eval_4tasks/task_2_django",
    },
    {
        "id": "task_3_fastapi_service",
        "name": "FastAPI Layered REST Microservice",
        "domain": "Backend REST API",
        "goal": "Build a production python FastAPI REST service with schemas.py, main.py, and test_main.py",
        "target_dir": "workspace_runs/eval_4tasks/task_3_fastapi",
    },
    {
        "id": "task_4_data_cli",
        "name": "Statistical Data Analysis CLI Tool",
        "domain": "Systems & CLI",
        "goal": "Build a high-performance numerical data analysis CLI with analyzer.py, cli.py, and test_analyzer.py",
        "target_dir": "workspace_runs/eval_4tasks/task_4_cli",
    },
]


def run_single_benchmark_task(task_spec: dict) -> dict:
    """Executes a single benchmark task and measures performance, memory, and diagnostics."""
    target_path = Path(task_spec["target_dir"]).resolve()
    if target_path.exists():
        shutil.rmtree(target_path)
    target_path.mkdir(parents=True, exist_ok=True)

    print(f"\n=======================================================")
    print(f"RUNNING BENCHMARK: {task_spec['name']} ({task_spec['domain']})")
    print(f"Target Directory: {target_path}")

    orch = LocalCoderOrchestrator(workspace_root=target_path)
    compiler_gate = CompilerGate()

    start_time = time.perf_counter()
    created_files = orch.manifest_synthesizer.execute_manifest_synthesis(
        user_goal=task_spec["goal"],
        on_file_synthesized=lambda path, i, total: print(f"  [{i}/{total}] Synthesized: {path}")
    )
    orch.commit_changes()
    elapsed = time.perf_counter() - start_time
    rss = orch.memory_guard.get_resident_memory_mb()

    # Audit all files with CompilerGate
    clean_count = 0
    file_audits = []
    for rel_path in created_files:
        f_path = target_path / rel_path
        if f_path.is_file():
            content = f_path.read_text(encoding="utf-8", errors="ignore")
            report = compiler_gate.check_file_content(rel_path, content)
            if report.is_valid:
                clean_count += 1
            file_audits.append({
                "path": rel_path,
                "bytes": len(content),
                "is_clean": report.is_valid,
                "error": report.summary_message if not report.is_valid else None,
            })

    orch.close()

    clean_rate = (clean_count / len(created_files) * 100) if created_files else 0.0
    print(f"Outcome: {clean_count}/{len(created_files)} Clean ({clean_rate:.1f}%) in {elapsed:.2f}s | RSS: {rss:.1f} MB")

    return {
        "id": task_spec["id"],
        "name": task_spec["name"],
        "domain": task_spec["domain"],
        "elapsed_seconds": elapsed,
        "peak_rss_mb": rss,
        "file_count": len(created_files),
        "clean_count": clean_count,
        "clean_rate": clean_rate,
        "files": file_audits,
    }


def run_full_suite() -> list:
    """Runs all 4 complex evaluation benchmarks and outputs summary."""
    results = []
    total_start = time.perf_counter()

    for task in BENCHMARK_TASKS:
        res = run_single_benchmark_task(task)
        results.append(res)

    total_time = time.perf_counter() - total_start
    print("\n" + "=" * 60)
    print("=== 4-TASK COMPLEX BENCHMARK SUMMARY ===")
    print(f"Total Execution Time: {total_time:.2f}s")
    for r in results:
        print(f"  - {r['name']}: {r['clean_count']}/{r['file_count']} files clean ({r['clean_rate']:.1f}%) in {r['elapsed_seconds']:.2f}s [RSS: {r['peak_rss_mb']:.1f} MB]")
    print("=" * 60)

    # Save summary report
    out_file = Path("workspace_runs/eval_4tasks/summary_report.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(results, indent=2), encoding="utf-8")
    return results


if __name__ == "__main__":
    run_full_suite()
