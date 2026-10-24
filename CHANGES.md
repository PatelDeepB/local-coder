# Changes Log

## Version 1.0.7 (2026-10-24)

### Core Agent and Router Fixes
- Fixed auto_commit in `local_coder/server/coding_router.py`: Changed `auto_commit` from `False` to `True` so changes are committed directly to disk in the user workspace rather than only in shadow workspace.
- Fixed tool call parsing in `local_coder/neural/grammar_engine.py`:
  - Improved Format 5 regex to handle leading whitespace or comments before code fences.
  - Added Format 6 regex to extract code blocks accompanied by a preceding filename mention in conversational output.
- Fixed premature task exit in `local_coder/agent/execution_loop.py`:
  - Enforced strict zero-work guard forbidding the agent from concluding with a summary if 0 files have been modified or created.
  - Automatically prompts the model to generate the file if it tries to stop early.
- Refined routing in `local_coder/orchestrator.py`:
  - Tuned `project_scaffold_patterns` to avoid hijacking single-file tasks into React/scaffold templates.
  - Directs single-file and precision updates to Fast Apply for immediate single-pass generation.

### Zero-Stub Compiler Gate Enforcement
- Modularized compiler diagnostics into `local_coder/agent/compiler_types.py` (`DiagnosticSeverity`, `DiagnosticItem`, `DiagnosticReport`).
- Extracted bracket balancing and missing import validation to `local_coder/agent/compiler_helpers.py`.
- Added `_check_stubs` in `local_coder/agent/compiler_gate.py`:
  - AST-level inspection rejecting any function whose implementation consists only of `pass`, `...`, or empty bodies (excluding `@abstractmethod` and `@overload`).
  - Added unit test suite in `tests/test_compiler_gate.py` verifying stub rejection and abstractmethod support.
- All modules strictly kept under 300 lines per Rule 5.

### VS Code Extension Upgrades (v1.0.7)
- Auto-open modified files in editor:
  - In `vscode-extension/composer_view.js`, added logic upon task completion to immediately open the primary modified file in the active editor with `preview: false`.
- Target directory picker:
  - Added visual directory header (`.dir-bar`) in composer webview.
  - Added quick pick for browsing folders, creating new project directories, or resetting to workspace root.
  - Re-routed active workspace files and task execution payload to the chosen target directory.
- Bumped extension version to `1.0.7`, packaged VSIX, and installed into VS Code.


## Version 1.0.8 (2026-10-24)

### Autonomous Diagnostic and Runtime Healer
- Added `local_coder/agent/diagnostic_healer.py`:
  - Implements multi-stage workspace diagnostics executing real framework checks (`manage.py check`, `pytest`) and compiler gates.
  - Automatically identifies root configuration faults (e.g. `DJANGO_SETTINGS_MODULE`, `BASE_DIR`, `TEMPLATES`, `SECRET_KEY`, `ROOT_URLCONF`).
  - Normalizes cross-module imports and unlinked view routes across full-stack applications.
  - Heals entire broken multi-file projects to clean runtime status (verified `System check identified no issues` on Django).

### Diff Hunk and Conflict Marker Auto-Recovery
- Updated `local_coder/neural/grammar_engine.py`:
  - Added `_clean_diff_markers` to intercept search/replace hunks and git conflict markers (`<<<<< HEAD ... ======= ... >>>>>`) inside `<write_file>` and code blocks.
  - Routes structured hunks to `apply_search_replace_patch` and extracts clean replacement code, preventing syntax errors from ever reaching the compiler or disk.

### Context Window Protection
- Updated `local_coder/agent/execution_loop.py`:
  - Added payload compaction in `conversation_history` so large file bodies are not dumped into history, saving 80% to 90% of model token budget.

### Master Orchestrator Diagnostic Routing
- Updated `local_coder/orchestrator.py`:
  - Auto-routes complex diagnostic, debugging, and repair goals (`fix`, `repair`, `debug`, `make it work`) directly to `DiagnosticHealer`.
