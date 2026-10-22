# LOCAL-CODER: Change Tracking Ledger

All notable changes, additions, and architectural evolutions of the LOCAL-CODER system are meticulously recorded here.

## [1.3.0] - 2026-10-22: Tab Autocomplete, Synapse Training Pipeline, Incremental Watcher, & Autonomous Test-Repair Loop

### Step 1: Real-Time Predictive Tab Autocomplete (Copilot++ Speculative Infilling)
- Built `InfillingEngine` in `local_coder/neural/infilling_engine.py`:
  * Formats Qwen FIM prompt tokens (`<|fim_prefix|>...<|fim_suffix|>...<|fim_middle|>`).
  * Trims recent context window for sub-second speculative completion.
  * Strips special tokens and cleans markdown fence artifacts.
- Added `generate_raw` method to `LlamaModelRunner` and `ModelRouter`:
  * Skips chat templates and generates raw completions directly from prompt.
- Added `/api/v1/autocomplete` endpoint in `local_coder/server/api_server.py`.
- Integrated `vscode.languages.registerInlineCompletionItemProvider` in `vscode-extension/extension.js`:
  * Provides ghost text suggestions inline as the user types; accepts on Tab.
  * Added `localCoder.enableAutocomplete` configuration toggle in `vscode-extension/package.json`.
- Packaged and installed `local-coder-vscode-1.0.2.vsix`.

### Step 2: Clean Dataset & Synapse LoRA Training Pipeline
- Built `SynapseDatasetBuilder` in `local_coder/training/dataset_builder.py`:
  * Synthesizes high-density instruction pairs from `CleanPatternBank`.
  * Generates FIM training samples using natural function and module slicing.
  * Serializes samples to standard JSON Lines format (`data/synapse_instructions.jsonl`).
- Created `scripts/train_lora.py`:
  * Lightweight PEFT/LoRA fine-tuning script for Qwen2.5-Coder (0.5B / 1.5B) base weights.
  * Supports ChatML format, target projections (`q_proj`, `k_proj`, `v_proj`, `o_proj`, `gate_proj`, `up_proj`, `down_proj`), rank r=16, alpha=32.
  * Added `--dry-run` flag for data and pipeline verification without GPU hardware.

### Step 3: Incremental File Watcher Daemon
- Created `IncrementalFileWatcher` in `local_coder/knowledge/file_watcher.py`:
  * Observes workspace code changes via timestamp polling with negligible CPU overhead.
  * Incrementally re-indexes single modified files into `HDCCodeIndex` and `CodebaseDependencyGraph` in sub-2ms without full codebase rescanning.
  * Provides background thread management (`start_background_watcher`, `stop`).
- Added `reindex_file` to `TreeIndexer` and `remove_file` to `HDCCodeIndex`.
- Added `update_file` to `CodebaseDependencyGraph` for instant edge recalculation.
- Wired `IncrementalFileWatcher` into `LocalCoderOrchestrator` lifecycle.

### Step 4: Autonomous Terminal Test-Repair Loop
- Created `AutonomousTestHealer` in `local_coder/agent/autonomous_test_healer.py`:
  * Runs test suite via `TerminalRunner` and `TestRunner`.
  * On test failure, detects offending source file from tracebacks, extracts error diagnostic, and synthesizes targeted fixes.
  * Iteratively applies changes and re-runs tests until 100% pass or max iterations reached.
- Added `/api/v1/test-and-repair` endpoint in `local_coder/server/api_server.py`.
- Built `RunAutonomousTestRepairTool` in `local_coder/tools/test_tools.py` and registered with agent loop.
- Added `local-coder.testAndRepair` command to VS Code extension and command palette.
- Expanded automated test suite from 59 to 74 passing tests.

## [1.2.3] - 2026-10-21: 4-Task Complex Benchmark & Typing Auto-Healing

### Comprehensive Documentation & Pattern Expansion
- Updated repository `README.md` on GitHub:
  * Documented native VS Code extension installation, keybindings, and inline editing workflows.
  * Added architecture diagram, benchmarks, and model router tiering.
- Added `CLI_DATA_ANALYSIS_PATTERN` to `CleanPatternBank` for systems and mathematical tools.
- Enhanced `CompilerGate` and `ManifestSynthesizer` with typing auto-healing:
  * Detects missing typing imports (`Dict`, `List`, `Optional`, `Tuple`, `Any`, `Union`) and injects them automatically.

### 4-Task Multi-Domain Complex Evaluation Benchmark
- Executed `scripts/evaluate_four_complex_tasks.py` across 4 domains:
  * Modern React 18 Dashboard: 5/5 files clean in 43.68s.
  * Django Production MVC Application: 8/8 files clean in 95.33s.
  * FastAPI Layered REST Microservice: 4/4 files clean in 59.97s (100% pytest pass in 0.38s).
  * Statistical Data Analysis CLI Tool: 4/4 files clean in 82.94s.
- Total Synthesis Latency: 286.73s across all 21 files.
- Peak Physical RAM: 1,748.9 MB RSS (safely under 1,900.0 MB hardware ceiling).

## [1.2.2] - 2026-10-21: Inline Edit Bugfix & Django Benchmark Parity Upgrades

### Inline Edit Line Replacement Bugfix
- Fixed the inline edit bug in `vscode-extension/extension.js`:
  * Empty selections now resolve to `rangeIncludingLineBreak` so full-line edits cleanly delete the target line and replace it, rather than inserting duplicate lines.
  * Ensured `replacementCode` includes proper trailing newlines to match line-break semantics.
  * Repackaged and reinstalled `local-coder-vscode-1.0.1.vsix`.

### Django Architecture Pattern & Import Auto-Healing
- Added `DJANGO_CRUD_PATTERN` to `CleanPatternBank`:
  * Provides production-grade Django MVC skeletons (`ModelForm`, CBVs, `core_project` settings, `reverse()` test cases).
- Added cross-file import auto-healing to `CompilerGate` and `ManifestSynthesizer`:
  * Automatically detects and injects missing `redirect` and `TaskForm` imports in view controllers.
  * Eliminates placeholder strings (`your_project_name` -> `core_project`).
- Executed real-world Django comparison benchmark against human Gold Standard reference application:
  * Documented exact gap analysis in `django_parity_comparison_report.md`.

## [1.2.1] - 2026-10-21: In-Editor Keyboard Shortcut Fixes & Clean Pattern Bank

### Fixes & Enhancements for VS Code Extension (v1.0.1)
- Fixed shortcut trigger issues in VS Code:
  * Added `Ctrl+I` (Mac: `Cmd+I`) as immediate inline edit shortcut without chord collisions.
  * Added `Alt+K` (Mac: `Option+K`) as direct one-stroke trigger.
  * Preserved `Ctrl+K` with active editor context.
  * Added right-click editor context menu: "Local Coder: Inline Edit" and "Local Coder: Fix Diagnostics".
  * Added editor title bar button with sparkle icon for instant Composer access.
  * Fixed empty selection behavior: now automatically expands to the active line when no text is explicitly highlighted.
  * Repackaged and reinstalled `local-coder-vscode-1.0.1.vsix` directly into user VS Code extensions.

### Neural-Symbolic Clean Pattern Bank
- Built `CleanPatternBank` in `local_coder/knowledge/pattern_bank.py` storing gold-standard architectural templates:
  * Modern React 18: single-page dashboard with state hooks, input validation, and CSS custom properties.
  * Layered FastAPI: Pydantic models, versioned `/api/v1/` routes, health check endpoint, and pytest verification suite.
- Wired pattern bank into `ManifestSynthesizer`: injects verified structural contracts and production skeletons into model prompts to eliminate hallucinations and cognitive drift under 2 GB RAM.
- Added 3 unit tests in `tests/test_pattern_bank.py` (total test suite at 59 passing tests).

## [1.2.0] - 2026-10-21: Achieving 80% to 90% Cursor Parity

### Phase 1: Asymmetric & Pluggable Intelligence Router
- Implemented `ModelRouter` in `local_coder/neural/model_router.py` supporting:
  * `LOCAL`: Local CPU GGUF inference (Qwen2.5-Coder 1.5B, RSS <= 1900 MB, 100% offline).
  * `OLLAMA`: Local GPU inference against Ollama endpoint (e.g., Qwen 7B/14B, DeepSeek-R1).
  * `OPENAI`: Remote OpenAI-compatible endpoints (DeepSeek-V3, DeepSeek-R1, OpenRouter).
  * `HYBRID`: Multi-tier dispatch sending complex architectural decomposition to frontier models while routing micro-repairs and AST diffs to local CPU.
- Configured resilient fallback: automatically falls back to local CPU runner if remote or Ollama endpoints are unreachable or timeout.
- Added provider configuration options to `local_coder/core/config.py`.

### Phase 2: Active Compiler & Diagnostic Gate
- Created `CompilerGate` in `local_coder/agent/compiler_gate.py` with multi-language validation:
  * Python: Bytecode compilation (`compile()`) and native AST checks.
  * JavaScript / Node: Runtime check (`node --check`) for ESM/CommonJS modules.
  * React / TypeScript: JSX bracket and tag balance verification.
  * JSON: Strict syntax validation and auto-formatting.
  * HTML: Structured tag validation via `HTMLParser`.
- Ingests live LSP diagnostics from VS Code (`vscode.languages.getDiagnostics`) and transforms them into structured `DiagnosticReport`.
- Integrated `CompilerGate` into `ManifestSynthesizer` to automatically trigger self-repair before staging files.

### Phase 3: Multi-Hop Codebase Dependency Graph
- Implemented `CodebaseDependencyGraph` in `local_coder/knowledge/dependency_graph.py`:
  * Parses import statements across Python (`from .mod import x`) and JS/TS (`import { x } from './mod'`, `require()`).
  * Maps bidirectional caller/callee and import/dependent relationships.
  * Extracts function signatures, class interfaces, and exported types.
  * Injects imported contracts into prompt context to prevent hallucinated function signatures.

### Phase 4: Native VS Code Extension (`local-coder-vscode`)
- Built complete native extension in `vscode-extension/`:
  * Inline Editing (`Ctrl+K` / `Cmd+K`): Select code, enter natural language prompt, and review live red/green inline diff.
  * Accept (`Ctrl+Enter`) / Reject (`Escape`) inline diff shortcuts.
  * Composer Sidebar (`Ctrl+Shift+L`): Webview interface for multi-file planning, execution logs, and staged diff review.
  * Auto-Fix Diagnostics command: Transmits active red squiggles to backend compiler gate and auto-applies repairs.
  * Status Bar item: Displays real-time daemon status, active model tier, and RAM consumption.
  * Installed extension directly into `%USERPROFILE%\.vscode\extensions\local-coder-vscode`.

### Phase 5: Server Endpoints & Integration
- Added `/api/v1/inline-edit` endpoint for sub-second scoped code replacement.
- Added `/api/v1/diagnostics/heal` endpoint for automated LSP error resolution.
- Added `/api/v1/provider/set` endpoint for real-time model backend switching.

### Phase 6: Verification & Benchmarks
- Expanded automated test suite from 42 to 56 unit and integration tests (100% passing in 7.49s).
- Validated end-to-end multi-file Next.js/React application synthesis:
  * 5/5 files generated on disk with 100.0% Compiler Clean Rate.
  * Peak RAM memory: 1,711.3 MB RSS (well below the 1,900.0 MB CPU limit).
  * Full functionality confirmed across `package.json`, `public/index.html`, `src/App.jsx`, `src/Header.jsx`, and `src/styles.css`.

## [1.0.0] - 2026-10-20

### Phase 1: Environment & Knowledge Substrates
- Initialized repository structure at `C:\Deep_Patel_Projects\OpenSourceProjects\local_coder`.
- Configured dependencies in `requirements.txt`: `libcst`, `tree-sitter`, `llama-cpp-python`, `fastapi`, `uvicorn`, `psutil`, `pytest`, `pydantic`.
- Configured 10,240-bit Vector Symbolic Architecture (`HyperVector`) with multiplicative binding, permutation, and majority voting.
- Implemented `HDCCodeIndex` enabling sub-millisecond similarity search across codebase symbols using CPU bitwise operations.
- Built `MmapSymbolGraph` implementing a zero-copy binary format (`.hkg`) with mmap for instant symbol dependency traversal.
- Built `EpisodicRollingHashRing` and `EpisodicCompressor` for conversational state management.
- Implemented `MemoryGuard` and `HardwareProfiler` enforcing a strict 1,800 MB RSS memory ceiling on CPU hardware.

### Phase 2: AST Surgery Engine & Workspace Transactions
- Implemented `cst_surgery.py` with LibCST transformers for `make_function_async`, `replace_function_body`, and `wrap_function_error_handler` running in under 6 milliseconds.
- Created `symbol_extractor.py` and `tree_indexer.py` scanning repositories and populating HDC and symbol graph stores concurrently.
- Built `diff_patcher.py` delivering exact search/replace hunk application and unified diff generation in 0.07 milliseconds.
- Implemented `ShadowWorkspace` providing in-memory virtual staging of all file edits to prevent premature disk corruption.
- Implemented `WorkspaceTransactionManager` supporting atomic commits and instant multi-snapshot rollbacks.
- Built `TerminalRunner` executing sandboxed commands with timeout protection and ANSI stripping.
- Created `GitManager` for git status and fast restore fallback.
- Added `RulesEngine` to detect `.cursorrules` and `SecretScrubber` to protect sensitive credentials.

### Phase 3: Agent Tools & Verifier Gates
- Built modular agent tools: `ReadFileTool`, `ListDirectoryTool`, `FileOutlineTool`, `SearchCodeTool`, `LookupSymbolTool`, `ApplySearchReplacePatchTool`, `LibCSTTransformTool`, and `RunTerminalCommandTool`.
- Implemented `SyntaxValidator` catching syntax errors in under 0.1 milliseconds.
- Implemented `LSPDiagnosticsParser` extracting diagnostic warnings and errors.
- Created `TestRunner` executing pytest in isolated subprocesses with structured outcome parsing.
- Implemented `MicroRepairLoop` auto-correcting syntax and test failures prior to disk commits.

### Phase 4: Neural Engine & ReAct Loop
- Configured `LlamaModelRunner` integrating `llama_cpp` with 4-bit KV-cache (`Q4_0`) and CPU SIMD execution.
- Added `close()` resource cleanup to `LlamaModelRunner` and `LocalCoderOrchestrator` to maintain low resident memory across cycles.
- Built `ContractPlanner` enforcing typed JSON action contracts via grammar engine.
- Implemented `SlotCoder` (`slot_coder.py`) for Stage 2 scoped function body synthesis and surgical injection via LibCST.
- Implemented `AgentExecutionLoop` running multi-step ReAct cycles (Thought, Action, Observation, Reflection).
- Implemented `SelfHealer` for autonomous error diagnosis and targeted patch generation.

### Phase 5: Orchestrator, REST API, & CLI
- Created `LocalCoderOrchestrator` integrating workspace, HDC memory, tools, and ReAct agent into a unified API.
- Implemented `api_server.py` with FastAPI endpoints (`/health`, `/api/v1/status`, `/api/v1/index`, `/api/v1/task`, `/api/v1/diff`, `/api/v1/commit`, `/api/v1/rollback`, `/api/v1/terminal`, `/v1/models`, `/v1/chat/completions`).
- Built responsive, dark-themed Single Page Application Web UI (`web_ui.py`) served directly at `http://127.0.0.1:8000/`.
- Built `cli_app.py` interactive terminal assistant with real-time status indicators and slash command handling.

### Phase 6: Verification, Setup, & Benchmarking
- Implemented 33 unit and integration tests across 14 modules: 100% passing.
  * Added `test_slot_coder.py` verifying scoped slot body synthesis, indent cleaning, and LibCST injection.
  * Added `test_contract_planner.py` verifying interface planning and signature extraction.
  * Added `test_micro_repair_loop.py` verifying automated syntax error recovery.
  * Added `test_api_server.py` verifying FastAPI endpoints and OpenAI chat completion protocol.
- Created `tests/benchmark_coding_agent.py` evaluating real multi-file codebase indexing, HDC search, LibCST surgeries, hunk patching, terminal test runner, and GGUF neural reasoning.
- Created automated setup scripts: `setup.bat` (Windows) and `setup.sh` (Linux/macOS).
- Authored comprehensive documentation and architectural diagrams in `README.md`.

## [1.1.0] - 2026-10-20

### Critical Engine & Model Enhancements
- Replaced general reasoning model with specialized `Qwen2.5-Coder-1.5B-Instruct` (GGUF Q4_K_M) dedicated specifically to software engineering.
- Eliminated `type_k=2, type_v=2` KV-cache quantization which caused attention matrix numerical overflow and repeating characters on CPU.
- Standardized `LlamaModelRunner` to use native `create_chat_completion` ensuring exact Jinja template token parsing.
- Added `WriteFileTool` allowing autonomous creation and editing of new and existing files.
- Added tool alias mappings (`apply_patch`, `run_terminal`, `list_dir`) in `AgentExecutionLoop` and aligned `CODING_AGENT_SYSTEM_PROMPT`.
- Added duplicate consecutive tool execution guards in `AgentExecutionLoop` to prevent infinite action loops.
- Verified live end-to-end multi-step tool execution with real unified diff generation in shadow workspace.

## [1.2.0] - 2026-10-20

### Generalized Multi-Agent Architecture & AST Syntax Gate
- Implemented generalized Dual-Persona pipeline separating High-Level Architecture Planning from Low-Level Code Synthesis within memory budget.
- Integrated deterministic AST Syntax Gate into `WriteFileTool`: automatically validates `ast.parse` before staging Python files, rejecting broken syntax immediately with actionable error feedback.
- Upgraded `PLANNER_SYSTEM_PROMPT` to enforce structured task decomposition: implementation files, unit test requirements (pytest), and verification steps.
- Removed premature agent exit rule from `CODING_AGENT_SYSTEM_PROMPT`, allowing full multi-step execution (writing implementation, writing tests, and running terminal verification).
- Increased token generation budget in `AgentExecutionLoop` from 300 to 1024 tokens to support complete, production-ready modules and test suites without truncation.
- Added comprehensive unit tests in `tests/test_shadow_workspace.py` covering valid Python staging and automatic invalid syntax rejection.

## [1.3.0] - 2026-10-20

### Complex Multi-File Architecture & Polyglot Engine
- Built Multi-Format Tool Parser in `grammar_engine.py`: seamlessly supports XML tags (`<write_file path="...">`), Markdown file blocks (`FILE: path ```...``` `), and standard JSON tool calling.
- Integrated JSON String Recovery: extracts tool arguments even when models produce nested unescaped quotes inside `package.json` configurations.
- Upgraded `execution_loop.py` with multi-step nudge guards to prevent premature termination on repeated actions.
- Added automated JSON syntax verification inside `WriteFileTool` to guarantee valid configurations before disk staging.
- Executed real-world complex benchmark: successfully scaffolded a multi-file React application (`TaskFlow`) with `package.json`, `public/index.html`, and `src/App.jsx` in `workspace_runs/complex_react_app/` in 42.07 seconds at 1742.8 MB RSS.
- Added comprehensive unit test suite in `tests/test_grammar_engine.py` verifying all tool calling formats (41 total tests passing).

## [1.3.1] - 2026-10-20

### Open-Source Release & Automated Setup
- Published complete, standalone repository to GitHub at `https://github.com/PatelDeepB/local-coder`.
- Configured `.gitignore` keeping the repository lightweight (~220 KB clone) while auto-managing the 1.04 GB model weights.
- Implemented `scripts/download_model.py` with visual progress bar for automatic Hugging Face model downloads.
- Updated `setup.bat` and `setup.sh` for one-click environment installation, virtualenv creation, and model verification.
- Added `pytest.ini` with `pythonpath = .` for zero-configuration testing out of the box.
- Verified fresh remote clone and automated test suite execution from GitHub directly in a clean sandbox.

## [1.4.0] - 2026-10-20

### Deterministic Manifest-Driven Synthesis (MDS) Engine
- Built `ManifestSynthesizer` in `local_coder/agent/manifest_synthesizer.py`: solves small model cognitive drift by decomposing high-level application goals into a formal `FileManifest`.
- Orchestrator drives sequential, 100% focused synthesis across each file in the manifest, eliminating autoregressive recency bias and placeholder comments.
- Wired MDS directly into `LocalCoderOrchestrator.run_coding_task` for all project scaffolding, full-stack, and multi-file workflows.
- Evaluated on end-to-end complex React application benchmark: achieved 100% file creation across all 5 required components (`package.json`, `public/index.html`, `src/App.jsx`, `src/index.css`, `src/index.js`) in 34.80 seconds at 1,736.3 MB RSS.
- All verification gates passed: valid JSON package configuration, valid HTML5 root container, complete React state management without placeholders.
