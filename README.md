# LOCAL-CODER: Autonomous In-Editor AI Pair Programmer

An autonomous, production-grade coding copilot engineered to deliver the developer experience, in-editor diff editing, and multi-file architecture of Cursor, operating locally on CPU hardware strictly under a 2.0 GB RAM ceiling.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![VS Code Extension](https://img.shields.io/badge/vscode-extension-green.svg)](vscode-extension/)
[![Tests Passing](https://img.shields.io/badge/tests-59%20passed-brightgreen.svg)](tests/)
[![RAM Ceiling](https://img.shields.io/badge/RAM%20Ceiling-%3C%3D%201900%20MB-orange.svg)](#memory-guard)

---

## Key Capabilities (80% to 90% Cursor Parity)

1. **Native VS Code Extension (`local-coder-vscode`)**:
   - **Inline Edit (`Ctrl+I` / `Alt+K` / `Ctrl+K`)**: Select any code or place your cursor on a line, provide instructions, and review live red/green diff decorations directly in the buffer.
   - **Keyboard Shortcuts**: `Ctrl+Enter` to Accept diff, `Escape` to Reject diff.
   - **Composer Sidebar (`Ctrl+Shift+L`)**: Multi-file autonomous planning, live step-by-step progress logging, and one-click commit or rollback.
   - **Auto-Fix Diagnostics**: Intercepts active red squiggles from your language server (`vscode.languages.getDiagnostics`) and feeds them into the self-repair loop.
   - **Editor Context Menu**: Right-click on any code and select "Local Coder: Inline Edit".

2. **Asymmetric Model Router (`ModelRouter`)**:
   - `local` (default): Qwen2.5-Coder-1.5B GGUF running via llama.cpp (< 1.9 GB RAM, 100% offline & private).
   - `ollama`: Connects to local GPU Ollama instance (`http://localhost:11434/v1`) for 7B/14B/32B models.
   - `openai`: Remote endpoints (DeepSeek-V3, DeepSeek-R1, OpenAI, Claude via router).
   - `hybrid`: Decomposes multi-file architectures using frontier reasoning, while keeping AST diffs and micro-repairs on local CPU.
   - **Resilient Fallback**: Automatically falls back to local CPU if remote endpoints timeout or disconnect.

3. **Active Compiler & Diagnostic Gate (`CompilerGate`)**:
   - Real-time bytecode compilation (`compile()`) and AST syntax checks for Python.
   - Native Node.js syntax checks (`node --check`) for JavaScript/CommonJS/ESM.
   - JSX and TypeScript bracket balancing and tag closure validation.
   - Strict JSON and HTML DOM tree parsers.
   - Cross-file import auto-healing: detects missing `redirect`, `TaskForm`, or model imports and resolves them automatically before disk commits.

4. **Clean Pattern Bank (`CleanPatternBank`)**:
   - Ingests verified, production-grade architectural templates (React 18 hooks, Next.js, layered FastAPI with Pydantic schemas, and Django MVC with ModelForms).
   - Injects structural contracts directly into model prompts, eliminating hallucinations and placeholder comments (`// TODO`).

5. **Multi-Hop Codebase Dependency Graph (`CodebaseDependencyGraph`)**:
   - Scans `import` and `require` statements across Python and JS/TS files.
   - Maps bidirectional dependency trees (imported files vs importing callers).
   - Extracts public function and class signatures to inject type contracts into prompt context.

6. **Sub-Millisecond Code Retrieval (HDC Vector Store)**:
   - 10,240-bit Hyperdimensional Computing vector store performing sub-millisecond similarity search across codebase symbols using CPU SIMD bitwise operations.

7. **Zero-Copy Memory-Mapped Knowledge Graph (`.hkg`)**:
   - Binary symbol dependency graph with zero-RAM overhead via `mmap`.

8. **Deterministic LibCST Surgeries & Shadow Workspace**:
   - LibCST transformers for function body replacement, error wrapping, and async transformation in under 6 milliseconds.
   - In-memory virtual file staging prevents premature disk mutation, supporting atomic commits and instant rollback.

---

## Architecture Overview

```
+-------------------------------------------------------------------------+
|                  VS CODE / CURSOR EDITOR ENVIRONMENT                    |
|       Inline Edit (Ctrl+I)  |  Composer (Ctrl+Shift+L)  |  LSP Sync     |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
|                 LOCAL-CODER FASTAPI SERVER (Port 8080)                  |
+-------------------------------------------------------------------------+
                                    |
          +-------------------------+-------------------------+
          |                                                   |
          v                                                   v
+-------------------+                               +-------------------+
|   Model Router    |                               | Clean Pattern Bank|
| (Local/Ollama/API)|                               | (React/Django/API)|
+-------------------+                               +-------------------+
          |                                                   |
    +-----+-----+-------------------+                         |
    |           |                   |                         |
    v           v                   v                         v
+-------+   +-------+       +---------------+       +-------------------+
| LibCST|   |  HDC  |       | Dependency    |       | Shadow Workspace  |
|Surgery|   | Search|       | Graph (Imports|       | (Atomic Commit)   |
+-------+   +-------+       +---------------+       +-------------------+
          |                         |                         |
          +-------------------------+-------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
|                        Active Compiler Gate                             |
|          (node --check | py_compile | JSX Gate | Import Healer)          |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
|                   Physical Disk Files & Git Repository                  |
+-------------------------------------------------------------------------+
```

---

## Performance Benchmarks

Measured on commodity multi-core CPU hardware (Intel Core i7/AMD Ryzen):

| Metric | Target Ceiling | Achieved Result | Status |
|:---|:---|:---|:---|
| Codebase Indexing (AST + HDC + Mmap Graph) | < 200 ms | **16.38 ms** | PASS |
| HDC Semantic Vector Search | < 5.0 ms | **0.698 ms** | PASS |
| LibCST Deterministic Surgery | < 50.0 ms | **5.66 ms** | PASS |
| Precision Hunk Diff Patching | < 5.0 ms | **0.07 ms** | PASS |
| Compiler Gate Syntax Validation | < 2.0 ms | **0.082 ms** | PASS |
| Full-Stack React Scaffolding (5 files) | < 120 s | **34.80 s** (100% Compiler Clean) | PASS |
| Full Django Application Scaffolding (9 files)| < 180 s | **106.62 s** (100% Clean) | PASS |
| Automated Test Suite (59 tests) | < 15 s | **5.18 s** (100% Passing) | PASS |
| Idle Server RAM Footprint (RSS) | <= 1,900 MB | **1,379.6 MB** | PASS |
| Peak Multi-File RAM Footprint (RSS) | <= 1,900 MB | **1,711.3 MB** | PASS |

---

## Quick Installation & Setup

### 1. Clone & Set Up Environment
```bash
git clone https://github.com/PatelDeepB/local-coder.git
cd local-coder

# On Windows:
setup.bat

# On Linux / macOS:
chmod +x setup.sh && ./setup.sh
```

### 2. Download Model Weights (1.04 GB)
```bash
python scripts/download_model.py
```
This fetches `Qwen2.5-Coder-1.5B-Instruct-Q4_K_M.gguf` into `models/qwen25_coder_15b/`.

### 3. Install the VS Code Extension
```bash
code --install-extension vscode-extension/local-coder-vscode-1.0.1.vsix --force
```

### 4. Start the Backend Daemon
```bash
python -m uvicorn local_coder.server.api_server:app --host 127.0.0.1 --port 8080
```
Verify the daemon is alive: `http://127.0.0.1:8080/health` -> `{"status": "ok", "engine": "local-coder"}`.

---

## In-Editor Usage Guide

1. **Inline Edit (`Ctrl+I` / `Alt+K` / `Ctrl+K`)**:
   - Highlight any block of code (or leave cursor on a single line).
   - Press `Ctrl+I` (Mac: `Cmd+I`) or right-click -> "Local Coder: Inline Edit".
   - Enter your prompt (e.g., *"Add error handling with try-catch and log errors"*).
   - Watch the inline diff render in your buffer.
   - Press **`Ctrl+Enter`** to Accept the diff, or **`Escape`** to Reject.

2. **Composer Sidebar (`Ctrl+Shift+L`)**:
   - Press `Ctrl+Shift+L` or click the Sparkle icon in the top-right of your editor.
   - Enter your project-wide goal (e.g., *"Build a React dashboard with CSS styles and tests"*).
   - Click **Execute Plan** to scaffold, synthesize, and compile all files.
   - Click **Commit** to write to disk, or **Rollback** to discard.

3. **Switch Intelligence Tier**:
   - Click the status bar icon: `$(sparkle) Local Coder: 1380MB [local]`.
   - Select between Local CPU (1.5B), Ollama (Local GPU 7B/14B), Frontier (DeepSeek-V3/R1), or Hybrid.

---

## Running the Automated Test Suite

```bash
pytest
```
Executes all 59 unit and integration tests across 19 modules in under 6 seconds.

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
