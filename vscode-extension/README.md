# LOCAL-CODER VS Code Extension

Autonomous AI pair programming inside your editor with **80% to 90% Cursor parity**.

## Features

### 1. In-Editor Inline Editing (`Ctrl+K` / `Cmd+K`)
Select any function, class, or block of code and press `Ctrl+K`. Provide your natural language instructions and review the live inline diff directly inside the editor buffer.
- `Ctrl+Enter`: Accept Diff
- `Escape`: Reject Diff

### 2. Composer Sidebar (`Ctrl+Shift+L`)
Open the Composer sidebar to plan and execute multi-file architectures, scaffold complete applications, and run self-repairing loops across the repository.

### 3. Compiler & LSP Self-Healing Gate
Automatically catches syntax errors, broken imports, and type warnings reported by language servers (Pyright, TSServer, rust-analyzer) and invokes targeted self-repair before code is committed.

### 4. Pluggable Model Tiering
Switch between intelligence tiers directly from the status bar:
- **Local CPU (1.5B Qwen GGUF)**: 100% private, offline, < 1.9 GB RAM.
- **Ollama (Local GPU 7B/14B)**: Connects to your local Ollama server.
- **Frontier (DeepSeek-V3 / OpenAI)**: Frontier intelligence for deep multi-file planning.
- **Hybrid**: Asymmetric routing that uses Frontier for multi-file manifests and Local CPU for AST surgery and micro-repairs.

## Quick Installation

1. Start the LOCAL-CODER backend server:
   ```bash
   python -m uvicorn local_coder.server.api_server:app --host 127.0.0.1 --port 8000
   ```
2. Copy or symlink `vscode-extension/` to your VS Code extensions folder:
   - **Windows**: `%USERPROFILE%\.vscode\extensions\local-coder-vscode`
   - **macOS / Linux**: `~/.vscode/extensions/local-coder-vscode`
3. Restart VS Code or run `Developer: Reload Window`.
