"""Real-world complex task test: Building a multi-file responsive React application."""

from pathlib import Path
import json
import time

from local_coder.orchestrator import LocalCoderOrchestrator


def run_react_scaffold_test() -> None:
    print("\n" + "=" * 70)
    print("STARTING COMPLEX TASK TEST: MULTI-FILE REACT APPLICATION")
    print("=" * 70)

    target_dir = Path("workspace_runs") / "complex_react_app"
    orchestrator = LocalCoderOrchestrator()

    goal = (
        "Create a modern, responsive React web application named 'TaskFlow'. "
        "The project must include: "
        "1. package.json with dependencies (react, react-dom, lucide-react) and dev scripts, "
        "2. index.html entry point, "
        "3. src/App.jsx with an interactive task dashboard supporting task adding, status toggling, and filtering, "
        "4. src/components/TaskCard.jsx component for individual tasks, "
        "5. src/index.css with responsive mobile-first dark styling, and "
        "6. README.md with setup instructions."
    )

    start_time = time.perf_counter()
    session = orchestrator.run_coding_task(
        user_goal=goal,
        output_directory=target_dir,
        auto_commit=True,
    )
    total_elapsed = time.perf_counter() - start_time
    peak_rss = orchestrator.memory_guard.get_resident_memory_mb()

    print("\n" + "-" * 70)
    print(f"Task Completed in {total_elapsed:.2f}s | Peak RSS: {peak_rss:.1f} MB")
    print(f"Session Status: {session.status.value}")
    print(f"Output Directory: {session.output_directory}")
    print(f"Files Modified/Created: {session.modified_files}")
    print(f"ReAct Steps Executed: {len(session.completed_steps)}")
    print("-" * 70)

    for step in session.completed_steps:
        print(f"\n[Step {step.step_number}] Tool: {step.action_tool} ({step.elapsed_seconds:.2f}s)")
        print(f"Thought: {step.thought[:100]}...")
        print(f"Observation: {step.observation[:120]}")

    # Inspect physical files created on disk
    print("\n" + "=" * 70)
    print("PHYSICAL FILE INSPECTION IN workspace_runs/complex_react_app:")
    print("=" * 70)
    all_files = list(target_dir.rglob("*"))
    files_only = [f for f in all_files if f.is_file()]
    for f in sorted(files_only):
        rel = f.relative_to(target_dir)
        size = f.stat().st_size
        print(f"-> {rel} ({size} bytes)")

    # Validate package.json
    pkg_file = target_dir / "package.json"
    if pkg_file.is_file():
        try:
            pkg_data = json.loads(pkg_file.read_text(encoding="utf-8"))
            print(f"\n[Validation] package.json is VALID JSON: name='{pkg_data.get('name')}'")
        except Exception as exc:
            print(f"\n[Validation Error] package.json JSON corrupt: {exc}")
    else:
        print("\n[Validation Warning] package.json not found on disk.")

    orchestrator.close()


if __name__ == "__main__":
    run_react_scaffold_test()
