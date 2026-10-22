/**
 * LOCAL-CODER VS Code Extension
 * Brings Cursor-grade inline editing (Ctrl+K), Composer sidebar (Ctrl+Shift+L),
 * compiler gate diagnostics healing, and local/frontier tiering directly into VS Code.
 */

const vscode = require('vscode');
const http = require('http');
const https = require('https');
const url = require('url');

let activeDiffState = null;
let statusBarItem = null;
let cachedActiveUrl = 'http://127.0.0.1:8080';
let isBackendOnline = false;

// Text Editor Decorations for inline diff highlighting
const additionDecorationType = vscode.window.createTextEditorDecorationType({
    backgroundColor: 'rgba(34, 197, 94, 0.20)',
    isWholeLine: true,
    overviewRulerColor: '#22c55e',
    overviewRulerLane: vscode.OverviewRulerLane.Left
});

const deletionDecorationType = vscode.window.createTextEditorDecorationType({
    backgroundColor: 'rgba(239, 68, 68, 0.20)',
    textDecoration: 'line-through',
    isWholeLine: true,
    overviewRulerColor: '#ef4444',
    overviewRulerLane: vscode.OverviewRulerLane.Left
});

/**
 * Activates the Local Coder extension.
 * @param {vscode.ExtensionContext} context
 */
function activate(context) {
    vscode.commands.executeCommand('setContext', 'localCoderDiffActive', false);

    // Initialize Status Bar item
    statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
    statusBarItem.command = 'local-coder.switchProvider';
    statusBarItem.text = '$(sparkle) Local Coder: Initializing...';
    statusBarItem.tooltip = 'Click to switch between Local, Ollama, and Frontier models';
    statusBarItem.show();
    context.subscriptions.push(statusBarItem);

    // Register Status Check Loop
    checkBackendHealth();
    const interval = setInterval(checkBackendHealth, 5000);
    context.subscriptions.push({ dispose: () => clearInterval(interval) });

    // Register Inline Edit (Ctrl+K / Ctrl+I / Alt+K)
    const inlineEditCmd = vscode.commands.registerCommand('local-coder.inlineEdit', async () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showWarningMessage('No active editor open.');
            return;
        }

        let targetRange = editor.selection;
        let selectedText = '';
        let isFullLine = false;

        if (targetRange.isEmpty) {
            const line = editor.document.lineAt(targetRange.active.line);
            targetRange = line.rangeIncludingLineBreak;
            selectedText = line.text;
            isFullLine = true;
        } else {
            selectedText = editor.document.getText(targetRange);
        }

        const instruction = await vscode.window.showInputBox({
            prompt: 'How would you like Local Coder to modify this code?',
            placeHolder: "e.g., 'Add type annotations, validate input, or implement function'"
        });

        if (!instruction) {
            return;
        }

        await executeInlineEdit(editor, targetRange, selectedText || ' ', instruction, isFullLine);
    });

    // Register Accept Diff (Ctrl+Enter)
    const acceptDiffCmd = vscode.commands.registerCommand('local-coder.acceptDiff', async () => {
        if (!activeDiffState) {
            return;
        }
        const { editor, range, replacementCode } = activeDiffState;
        await editor.edit(editBuilder => {
            editBuilder.replace(range, replacementCode);
        });
        clearActiveDiff(editor);
        vscode.window.showInformationMessage('Diff accepted.');
    });

    // Register Reject Diff (Escape)
    const rejectDiffCmd = vscode.commands.registerCommand('local-coder.rejectDiff', async () => {
        if (!activeDiffState) {
            return;
        }
        const { editor } = activeDiffState;
        clearActiveDiff(editor);
        vscode.window.showInformationMessage('Diff rejected.');
    });

    // Register Auto-Fix Diagnostics with Compiler Gate
    const fixDiagnosticsCmd = vscode.commands.registerCommand('local-coder.fixDiagnostics', async () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            return;
        }

        const diags = vscode.languages.getDiagnostics(editor.document.uri);
        if (!diags || diags.length === 0) {
            vscode.window.showInformationMessage('No active compiler or LSP diagnostics on current file.');
            return;
        }

        const rawDiags = diags.map(d => ({
            file: editor.document.fileName,
            line: d.range.start.line + 1,
            column: d.range.start.character + 1,
            message: d.message,
            severity: d.severity === 0 ? 'error' : 'warning'
        }));

        vscode.window.withProgress({
            location: vscode.ProgressLocation.Notification,
            title: 'Local Coder: Repairing compiler errors...',
            cancellable: false
        }, async () => {
            const config = vscode.workspace.getConfiguration('localCoder');
            const baseUrl = config.get('apiUrl') || 'http://127.0.0.1:8000';
            try {
                const res = await sendPostRequest(`${baseUrl}/api/v1/diagnostics/heal`, {
                    file_path: editor.document.fileName,
                    content: editor.document.getText(),
                    diagnostics: rawDiags
                });

                if (res.is_repaired && res.repaired_code) {
                    const fullRange = new vscode.Range(
                        editor.document.positionAt(0),
                        editor.document.positionAt(editor.document.getText().length)
                    );
                    await editor.edit(editBuilder => {
                        editBuilder.replace(fullRange, res.repaired_code);
                    });
                    vscode.window.showInformationMessage('Compiler diagnostics resolved and file updated.');
                } else {
                    vscode.window.showWarningMessage('Could not automatically resolve all compiler diagnostics.');
                }
            } catch (err) {
                vscode.window.showErrorMessage(`Diagnostics repair failed: ${err.message}`);
            }
        });
    });

    // Register Provider Switcher
    const switchProviderCmd = vscode.commands.registerCommand('local-coder.switchProvider', async () => {
        const items = [
            { label: 'Local CPU (1.5B Qwen)', description: 'Default offline model, < 1.9 GB RAM, fast AST surgery', id: 'local' },
            { label: 'Ollama (Local GPU 7B/14B)', description: 'Runs against local Ollama instance (localhost:11434)', id: 'ollama' },
            { label: 'Frontier (DeepSeek-V3 / OpenAI)', description: 'Highest multi-file reasoning capability', id: 'openai' },
            { label: 'Hybrid (Frontier Plan + Local Edits)', description: 'Best of both worlds: deep architecture + fast local diffs', id: 'hybrid' }
        ];

        const selected = await vscode.window.showQuickPick(items, {
            placeHolder: 'Select intelligence backend tier for Local Coder'
        });

        if (!selected) {
            return;
        }

        const config = vscode.workspace.getConfiguration('localCoder');
        const baseUrl = config.get('apiUrl') || 'http://127.0.0.1:8000';

        try {
            await sendPostRequest(`${baseUrl}/api/v1/provider/set`, { provider: selected.id });
            await config.update('provider', selected.id, vscode.ConfigurationTarget.Global);
            vscode.window.showInformationMessage(`Local Coder switched to: ${selected.label}`);
            checkBackendHealth();
        } catch (err) {
            vscode.window.showErrorMessage(`Failed to switch provider: ${err.message}`);
        }
    });

    // Register Composer Sidebar Provider
    const composerProvider = new LocalCoderComposerViewProvider(context.extensionUri);
    context.subscriptions.push(
        vscode.window.registerWebviewViewProvider('local-coder.chatView', composerProvider)
    );

    // Register Composer open shortcut (Ctrl+Shift+L)
    const openComposerCmd = vscode.commands.registerCommand('local-coder.openComposer', () => {
        vscode.commands.executeCommand('local-coder.chatView.focus');
    });

    // Register Commit / Rollback commands
    const commitCmd = vscode.commands.registerCommand('local-coder.commitChanges', async () => {
        const config = vscode.workspace.getConfiguration('localCoder');
        const baseUrl = config.get('apiUrl') || 'http://127.0.0.1:8000';
        try {
            const res = await sendPostRequest(`${baseUrl}/api/v1/commit`, {});
            vscode.window.showInformationMessage(`Committed ${res.committed_files.length} files to disk.`);
        } catch (err) {
            vscode.window.showErrorMessage(`Commit failed: ${err.message}`);
        }
    });

    const rollbackCmd = vscode.commands.registerCommand('local-coder.rollbackChanges', async () => {
        const config = vscode.workspace.getConfiguration('localCoder');
        const baseUrl = config.get('apiUrl') || 'http://127.0.0.1:8000';
        try {
            await sendPostRequest(`${baseUrl}/api/v1/rollback`, {});
            vscode.window.showInformationMessage('Staged changes rolled back.');
        } catch (err) {
            vscode.window.showErrorMessage(`Rollback failed: ${err.message}`);
        }
    });

    // Register Autonomous Test and Repair Loop
    const testAndRepairCmd = vscode.commands.registerCommand('local-coder.testAndRepair', async () => {
        const testPath = await vscode.window.showInputBox({
            prompt: 'Test path or directory to run and repair:',
            value: 'tests'
        });
        if (!testPath) {
            return;
        }

        await vscode.window.withProgress({
            location: vscode.ProgressLocation.Notification,
            title: 'Local Coder: Executing autonomous test-repair loop...',
            cancellable: false
        }, async () => {
            const activeUrl = await getActiveBaseUrl();
            try {
                const res = await sendPostRequest(`${activeUrl}/api/v1/test-and-repair`, {
                    test_path: testPath,
                    max_iterations: 3
                });
                if (res.is_successful) {
                    vscode.window.showInformationMessage(`All tests PASSED (${res.passed_count} passed, ${res.iterations_used} iterations)!`);
                } else {
                    vscode.window.showWarningMessage(`Test repair ended: ${res.passed_count} passed, ${res.failed_count} failed.`);
                }
            } catch (err) {
                vscode.window.showErrorMessage(`Test-repair loop failed: ${err.message}`);
            }
        });
    });

    // Register Predictive Tab Autocomplete (Copilot++ Speculative Infilling)
    const inlineCompletionProvider = {
        async provideInlineCompletionItems(document, position, context, token) {
            const config = vscode.workspace.getConfiguration('localCoder');
            const autocompleteEnabled = config.get('enableAutocomplete', true);
            if (!autocompleteEnabled || !isBackendOnline) {
                return { items: [] };
            }

            const lineText = document.lineAt(position.line).text;
            const linePrefix = lineText.substring(0, position.character);
            if (!linePrefix.trim()) {
                return { items: [] };
            }

            // 150ms typing debounce to avoid flooding model on rapid typing
            await new Promise(resolve => setTimeout(resolve, 150));
            if (token.isCancellationRequested) {
                return { items: [] };
            }

            try {
                const textBefore = document.getText(new vscode.Range(new vscode.Position(0, 0), position));
                const textAfter = document.getText(new vscode.Range(position, document.lineAt(document.lineCount - 1).range.end));

                const payload = {
                    prefix: textBefore.slice(-800),
                    suffix: textAfter.slice(0, 400),
                    max_tokens: 24,
                    single_line_only: true
                };

                const res = await sendPostRequest(`${cachedActiveUrl}/api/v1/autocomplete`, payload, 2500);
                if (token.isCancellationRequested || !res || !res.completion) {
                    return { items: [] };
                }

                const completionText = res.completion;
                if (!completionText.trim()) {
                    return { items: [] };
                }

                const item = new vscode.InlineCompletionItem(completionText, new vscode.Range(position, position));
                return { items: [item] };
            } catch {
                return { items: [] };
            }
        }
    };

    const autocompleteDisposable = vscode.languages.registerInlineCompletionItemProvider(
        { pattern: '**' },
        inlineCompletionProvider
    );

    context.subscriptions.push(
        inlineEditCmd,
        acceptDiffCmd,
        rejectDiffCmd,
        fixDiagnosticsCmd,
        switchProviderCmd,
        openComposerCmd,
        commitCmd,
        rollbackCmd,
        testAndRepairCmd,
        autocompleteDisposable
    );
}

/**
 * Executes inline edit request and renders diff overlay.
 */
async function executeInlineEdit(editor, selection, selectedText, instruction, isFullLine = false) {
    const baseUrl = await getActiveBaseUrl();

    const document = editor.document;
    const startLine = selection.start.line;
    const endLine = selection.end.line;

    const prefix = document.getText(new vscode.Range(0, 0, startLine, 0));
    const suffix = document.getText(new vscode.Range(endLine + 1, 0, document.lineCount, 0));

    await vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: 'Local Coder: Generating inline edit...',
        cancellable: false
    }, async () => {
        try {
            const response = await sendPostRequest(`${baseUrl}/api/v1/inline-edit`, {
                file_path: document.fileName,
                selected_code: selectedText,
                instruction: instruction,
                prefix_context: prefix,
                suffix_context: suffix
            });

            let replacementCode = response.replacement_code || '';
            if (isFullLine && !replacementCode.endsWith('\n')) {
                replacementCode += '\n';
            }

            activeDiffState = {
                editor: editor,
                range: selection,
                originalCode: selectedText,
                replacementCode: replacementCode
            };

            // Apply decorations
            editor.setDecorations(deletionDecorationType, [selection]);
            vscode.commands.executeCommand('setContext', 'localCoderDiffActive', true);

            vscode.window.showInformationMessage(
                'Inline diff ready. Press Ctrl+Enter to Accept, or Esc to Reject.',
                'Accept',
                'Reject'
            ).then(choice => {
                if (choice === 'Accept') {
                    vscode.commands.executeCommand('local-coder.acceptDiff');
                } else if (choice === 'Reject') {
                    vscode.commands.executeCommand('local-coder.rejectDiff');
                }
            });
        } catch (err) {
            vscode.window.showErrorMessage(`Inline edit error: ${err.message}`);
        }
    });
}

/**
 * Clears active diff decorations and resets context.
 */
function clearActiveDiff(editor) {
    if (editor) {
        editor.setDecorations(additionDecorationType, []);
        editor.setDecorations(deletionDecorationType, []);
    }
    activeDiffState = null;
    vscode.commands.executeCommand('setContext', 'localCoderDiffActive', false);
}

/**
 * Resolves active backend URL with automatic fallback to port 8080 if 8000 is occupied.
 */
async function getActiveBaseUrl() {
    if (isBackendOnline && cachedActiveUrl) {
        return cachedActiveUrl;
    }
    const config = vscode.workspace.getConfiguration('localCoder');
    const configured = config.get('apiUrl') || 'http://127.0.0.1:8080';
    try {
        await sendGetRequest(`${configured}/health`, 800);
        cachedActiveUrl = configured;
        isBackendOnline = true;
        return configured;
    } catch {
        const altUrl = configured.includes('8080') ? 'http://127.0.0.1:8000' : 'http://127.0.0.1:8080';
        try {
            await sendGetRequest(`${altUrl}/health`, 800);
            cachedActiveUrl = altUrl;
            isBackendOnline = true;
            return altUrl;
        } catch {
            isBackendOnline = false;
            return configured;
        }
    }
}

/**
 * Queries server telemetry and updates status bar.
 */
async function checkBackendHealth() {
    if (!statusBarItem) {
        return;
    }
    const config = vscode.workspace.getConfiguration('localCoder');
    const activeUrl = await getActiveBaseUrl();
    try {
        const statusData = await sendGetRequest(`${activeUrl}/api/v1/status`, 1200);
        const rss = Math.round(statusData.rss_mb || 0);
        const provider = config.get('provider') || 'local';
        cachedActiveUrl = activeUrl;
        isBackendOnline = true;
        statusBarItem.text = `$(sparkle) Local Coder: ${rss}MB [${provider}]`;
        statusBarItem.tooltip = `Status: ${statusData.status} | URL: ${activeUrl} | Staged: ${statusData.staged_files.length} | Click to switch`;
    } catch {
        isBackendOnline = false;
        statusBarItem.text = '$(circle-slash) Local Coder: Offline';
        statusBarItem.tooltip = 'FastAPI server daemon is not running on 127.0.0.1:8080 or 8000. Start via: python -m uvicorn local_coder.server.api_server:app --port 8080';
    }
}

/**
 * Webview provider for Composer sidebar.
 */
class LocalCoderComposerViewProvider {
    constructor(extensionUri) {
        this._extensionUri = extensionUri;
    }

    resolveWebviewView(webviewView) {
        this._view = webviewView;
        webviewView.webview.options = {
            enableScripts: true
        };

        webviewView.webview.html = this._getHtmlForWebview();

        webviewView.webview.onDidReceiveMessage(async (message) => {
            const baseUrl = await getActiveBaseUrl();

            if (message.command === 'submitTask') {
                try {
                    this._view.webview.postMessage({ type: 'taskStarted' });
                    const res = await sendPostRequest(`${baseUrl}/api/v1/task`, { goal: message.goal });
                    this._view.webview.postMessage({ type: 'taskComplete', result: res });
                } catch (err) {
                    this._view.webview.postMessage({ type: 'taskError', error: err.message });
                }
            } else if (message.command === 'commitEdits') {
                vscode.commands.executeCommand('local-coder.commitChanges');
            } else if (message.command === 'rollbackEdits') {
                vscode.commands.executeCommand('local-coder.rollbackChanges');
            }
        });
    }

    _getHtmlForWebview() {
        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: var(--vscode-font-family); padding: 12px; color: var(--vscode-foreground); background-color: var(--vscode-editor-background); margin: 0; font-size: 13px; }
        .composer-title { font-weight: 600; font-size: 14px; margin-bottom: 8px; color: #38bdf8; display: flex; align-items: center; gap: 6px; }
        textarea { width: 100%; box-sizing: border-box; background: var(--vscode-input-background); color: var(--vscode-input-foreground); border: 1px solid var(--vscode-input-border); border-radius: 4px; padding: 8px; font-family: inherit; font-size: 12px; resize: vertical; min-height: 80px; }
        textarea:focus { outline: 1px solid var(--vscode-focusBorder); }
        .btn-group { display: flex; gap: 6px; margin-top: 8px; }
        button { background: var(--vscode-button-background); color: var(--vscode-button-foreground); border: none; border-radius: 4px; padding: 6px 12px; cursor: pointer; font-size: 12px; font-weight: 500; }
        button:hover { background: var(--vscode-button-hoverBackground); }
        .btn-secondary { background: var(--vscode-button-secondaryBackground); color: var(--vscode-button-secondaryForeground); }
        .btn-secondary:hover { background: var(--vscode-button-secondaryHoverBackground); }
        .status-box { margin-top: 12px; padding: 8px; border-radius: 4px; background: rgba(56, 189, 248, 0.08); border-left: 3px solid #38bdf8; display: none; }
        .step-log { margin-top: 10px; font-family: var(--vscode-editor-font-family); font-size: 11px; max-height: 250px; overflow-y: auto; background: rgba(0,0,0,0.2); padding: 6px; border-radius: 4px; }
        .step-item { padding: 4px 0; border-bottom: 1px solid rgba(255,255,255,0.05); }
    </style>
</head>
<body>
    <div class="composer-title">&#10024; LOCAL-CODER Composer</div>
    <p style="font-size: 11px; color: var(--vscode-descriptionForeground); margin-top: 0;">Multi-file autonomous planning, synthesis, and compiler self-healing.</p>
    <textarea id="goalInput" placeholder="Describe coding task (e.g., 'Build React counter component with CSS and test suite')..."></textarea>
    <div class="btn-group">
        <button id="sendBtn">Execute Plan</button>
        <button id="commitBtn" class="btn-secondary">Commit</button>
        <button id="rollbackBtn" class="btn-secondary">Rollback</button>
    </div>
    <div id="statusBox" class="status-box">Processing task...</div>
    <div id="logBox" class="step-log" style="display: none;"></div>

    <script>
        const vscode = acquireVsCodeApi();
        const goalInput = document.getElementById('goalInput');
        const sendBtn = document.getElementById('sendBtn');
        const commitBtn = document.getElementById('commitBtn');
        const rollbackBtn = document.getElementById('rollbackBtn');
        const statusBox = document.getElementById('statusBox');
        const logBox = document.getElementById('logBox');

        sendBtn.addEventListener('click', () => {
            const goal = goalInput.value.trim();
            if (!goal) return;
            statusBox.style.display = 'block';
            statusBox.innerText = 'Analyzing codebase and planning files...';
            logBox.style.display = 'block';
            logBox.innerHTML = '';
            vscode.postMessage({ command: 'submitTask', goal: goal });
        });

        commitBtn.addEventListener('click', () => {
            vscode.postMessage({ command: 'commitEdits' });
        });

        rollbackBtn.addEventListener('click', () => {
            vscode.postMessage({ command: 'rollbackEdits' });
        });

        window.addEventListener('message', event => {
            const msg = event.data;
            if (msg.type === 'taskStarted') {
                statusBox.innerText = 'Executing task...';
            } else if (msg.type === 'taskComplete') {
                statusBox.innerText = 'Completed. ' + (msg.result.modified_files ? msg.result.modified_files.length : 0) + ' files staged.';
                if (msg.result.steps) {
                    msg.result.steps.forEach(s => {
                        const div = document.createElement('div');
                        div.className = 'step-item';
                        div.innerText = 'Step ' + s.step_number + ': ' + (s.thought || s.action_tool);
                        logBox.appendChild(div);
                    });
                }
            } else if (msg.type === 'taskError') {
                statusBox.innerText = 'Error: ' + msg.error;
            }
        });
    </script>
</body>
</html>`;
    }
}

/**
 * Performs an HTTP POST request.
 */
function sendPostRequest(targetUrl, payload, timeoutMs = 60000) {
    return new Promise((resolve, reject) => {
        const parsed = new URL(targetUrl);
        const data = JSON.stringify(payload);
        const options = {
            hostname: parsed.hostname,
            port: parsed.port || (parsed.protocol === 'https:' ? 443 : 80),
            path: parsed.pathname + parsed.search,
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Content-Length': Buffer.byteLength(data)
            },
            timeout: timeoutMs
        };

        const client = parsed.protocol === 'https:' ? https : http;
        const req = client.request(options, res => {
            let body = '';
            res.on('data', chunk => { body += chunk; });
            res.on('end', () => {
                if (res.statusCode >= 200 && res.statusCode < 300) {
                    try {
                        resolve(JSON.parse(body));
                    } catch (e) {
                        resolve(body);
                    }
                } else {
                    reject(new Error(`HTTP ${res.statusCode}: ${body}`));
                }
            });
        });

        req.on('error', reject);
        req.on('timeout', () => {
            req.destroy();
            reject(new Error('Request timed out'));
        });
        req.write(data);
        req.end();
    });
}

/**
 * Performs an HTTP GET request.
 */
function sendGetRequest(targetUrl, timeoutMs = 5000) {
    return new Promise((resolve, reject) => {
        const parsed = new URL(targetUrl);
        const options = {
            hostname: parsed.hostname,
            port: parsed.port || (parsed.protocol === 'https:' ? 443 : 80),
            path: parsed.pathname + parsed.search,
            method: 'GET',
            timeout: timeoutMs
        };

        const client = parsed.protocol === 'https:' ? https : http;
        const req = client.request(options, res => {
            let body = '';
            res.on('data', chunk => { body += chunk; });
            res.on('end', () => {
                if (res.statusCode >= 200 && res.statusCode < 300) {
                    try {
                        resolve(JSON.parse(body));
                    } catch (e) {
                        resolve(body);
                    }
                } else {
                    reject(new Error(`HTTP ${res.statusCode}: ${body}`));
                }
            });
        });

        req.on('error', reject);
        req.on('timeout', () => {
            req.destroy();
            reject(new Error('Request timed out'));
        });
        req.end();
    });
}

function deactivate() {
    if (statusBarItem) {
        statusBarItem.dispose();
    }
}

module.exports = {
    activate,
    deactivate
};
