# LOCAL-CODER: Change Tracking Ledger

All notable changes, additions, and architectural evolutions of the LOCAL-CODER system are meticulously recorded here.

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
