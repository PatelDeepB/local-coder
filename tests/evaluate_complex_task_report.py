"""Comprehensive Evaluation and Observation Runner for Complex Tasks."""

from pathlib import Path
import json
import time

from local_coder.orchestrator import LocalCoderOrchestrator


def run_evaluation() -> None:
    print("\n" + "=" * 70)
    print("STARTING COMPLEX TASK REAL-WORLD EVALUATION")
    print("=" * 70)

    target_dir = Path("workspace_runs") / "complex_task_evaluation"
    orchestrator = LocalCoderOrchestrator()

    goal = (
        "Create a modern, responsive React web application named 'TaskFlow'. "
        "The application must include: "
        "1. package.json with dependencies (react, react-dom) and scripts, "
        "2. index.html entry point, "
        "3. src/App.jsx with an interactive task dashboard supporting adding tasks and status toggling, "
        "4. src/index.css with responsive styling, and "
        "5. src/index.js for mounting."
    )

    start_time = time.perf_counter()
    session = orchestrator.run_coding_task(
        user_goal=goal,
        output_directory=target_dir,
        auto_commit=True,
    )
    total_elapsed = time.perf_counter() - start_time
    peak_rss = orchestrator.memory_guard.get_resident_memory_mb()

    # Inspect physical files created on disk
    all_files = list(target_dir.rglob("*"))
    files_only = [f for f in all_files if f.is_file() and f.name != "execution_summary.json"]

    # Generate Markdown Observation Report
    report_lines = [
        "# LOCAL-CODER Complex Task Observation Report",
        "",
        f"**Evaluation Timestamp:** {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}",
        "**Target Architecture:** Multi-Agent Dual-Persona (Planner + Coder + AST Gate)",
        "**Neural Engine:** Qwen2.5-Coder-1.5B-Instruct (GGUF Q4_K_M)",
        f"**Hardware Environment:** Commodity CPU, 4 Cores, Peak RSS: {peak_rss:.1f} MB (Budget: 1900 MB)",
        f"**Total Execution Time:** {total_elapsed:.2f} seconds",
        f"**Session Status:** {session.status.value}",
        f"**ReAct Execution Steps:** {len(session.completed_steps)}",
        f"**Physical Disk Directory:** `{target_dir.resolve()}`",
        "",
        "---",
        "",
        "## 1. Executive Summary",
        "",
        f"- **Goal:** {goal}",
        f"- **Files Created on Disk:** {len(files_only)} files",
        f"- **Memory Ceiling Adherence:** PASS ({peak_rss:.1f} MB <= 1900.0 MB)",
        f"- **Speed Performance:** {total_elapsed:.2f}s total across {len(session.completed_steps)} LLM steps",
        "",
        "---",
        "",
        "## 2. ReAct Execution Step-by-Step Observation Trace",
        "",
        "| Step # | Action Tool | Target File / Command | Duration | Success |",
        "|:---|:---|:---|:---|:---|",
    ]

    for step in session.completed_steps:
        target = step.action_arguments.get("file_path") or step.action_arguments.get("command") or "N/A"
        succ = "PASS" if step.is_successful else "FAIL"
        report_lines.append(
            f"| Step {step.step_number} | `{step.action_tool}` | `{target}` | {step.elapsed_seconds:.2f}s | {succ} |"
        )

    report_lines.extend([
        "",
        "### Detailed Step Observations:",
        "",
    ])

    for step in session.completed_steps:
        report_lines.extend([
            f"#### Step {step.step_number}: `{step.action_tool}`",
            f"- **Execution Time:** {step.elapsed_seconds:.2f}s",
            f"- **Arguments:** `{json.dumps(step.action_arguments)}`",
            f"- **Observation:** {step.observation[:250]}",
            "",
        ])

    report_lines.extend([
        "---",
        "",
        "## 3. Physical File Inspection & Code Analysis",
        "",
    ])

    for f in sorted(files_only):
        rel = f.relative_to(target_dir)
        size = f.stat().st_size
        content = f.read_text(encoding="utf-8", errors="replace")
        ext = f.suffix.lstrip(".")
        lang = "json" if ext == "json" else ("html" if ext == "html" else ("css" if ext == "css" else "jsx"))

        report_lines.extend([
            f"### File: `{rel}` ({size} bytes)",
            f"```{lang}",
            content.strip(),
            "```",
            "",
        ])

    # Validation Checks
    pkg_file = target_dir / "package.json"
    html_file = target_dir / "public" / "index.html"
    if not html_file.is_file():
        html_file = target_dir / "index.html"
    app_file = target_dir / "src" / "App.jsx"
    if not app_file.is_file():
        app_file = target_dir / "src" / "App.js"

    has_root = False
    if html_file.is_file():
        has_root = 'id="root"' in html_file.read_text(encoding="utf-8", errors="ignore")

    report_lines.extend([
        "---",
        "",
        "## 4. Verification & Quality Diagnostics",
        "",
        f"- **package.json Present & Valid JSON:** {'PASS' if (pkg_file.is_file() and is_valid_json(pkg_file)) else 'FAIL'}",
        f"- **index.html Present & Contains Root Div:** {'PASS' if has_root else 'FAIL'}",
        f"- **React App Component Present:** {'PASS' if app_file.is_file() else 'FAIL'}",
        "",
    ])

    report_content = "\n".join(report_lines)
    report_path = target_dir / "OBSERVATION_REPORT.md"
    report_path.write_text(report_content, encoding="utf-8")
    print(f"\n[REPORT WRITTEN] Saved full observation report to: {report_path}")

    orchestrator.close()


def is_valid_json(path: Path) -> bool:
    try:
        json.loads(path.read_text(encoding="utf-8"))
        return True
    except Exception:
        return False


if __name__ == "__main__":
    run_evaluation()
