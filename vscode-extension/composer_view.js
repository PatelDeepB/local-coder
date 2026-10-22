/**
 * LOCAL-CODER Composer Sidebar Webview Provider
 * Supports multi-file planning, @file context mentions, and interactive diff reviews.
 */

const vscode = require('vscode');
const path = require('path');
const fs = require('fs');
const { getActiveBaseUrl, sendPostRequest, sendGetRequest } = require('./daemon_manager');

class LocalCoderComposerViewProvider {
    constructor(extensionUri) {
        this._extensionUri = extensionUri;
    }

    resolveWebviewView(webviewView) {
        this._view = webviewView;
        webviewView.webview.options = { enableScripts: true };
        webviewView.webview.html = this._getHtmlForWebview();

        webviewView.webview.onDidReceiveMessage(async (message) => {
            const baseUrl = await getActiveBaseUrl();

            if (message.command === 'submitTask') {
                await this._handleSubmitTask(baseUrl, message.goal);
            } else if (message.command === 'loadWorkspaceFiles') {
                await this._handleLoadFiles(baseUrl);
            } else if (message.command === 'loadStagedFiles') {
                await this._handleLoadStaged(baseUrl);
            } else if (message.command === 'viewDiff') {
                await this._handleViewDiff(message.filePath, message.stagedContent);
            } else if (message.command === 'commitSingle') {
                await sendPostRequest(`${baseUrl}/api/v1/staged-files/commit`, { file_path: message.filePath });
                await this._handleLoadStaged(baseUrl);
            } else if (message.command === 'discardSingle') {
                await sendPostRequest(`${baseUrl}/api/v1/staged-files/discard`, { file_path: message.filePath });
                await this._handleLoadStaged(baseUrl);
            } else if (message.command === 'commitEdits') {
                vscode.commands.executeCommand('local-coder.commitChanges');
                await this._handleLoadStaged(baseUrl);
            } else if (message.command === 'rollbackEdits') {
                vscode.commands.executeCommand('local-coder.rollbackChanges');
                await this._handleLoadStaged(baseUrl);
            }
        });
    }

    async _handleSubmitTask(baseUrl, rawGoal) {
        let enrichedGoal = rawGoal;
        const mentions = rawGoal.match(/@([a-zA-Z0-9_\-\.\/]+)/g) || [];
        const wsRoot = vscode.workspace.workspaceFolders ? vscode.workspace.workspaceFolders[0].uri.fsPath : '';

        for (const m of mentions) {
            const relPath = m.substring(1);
            const fullPath = path.join(wsRoot, relPath);
            if (fs.existsSync(fullPath)) {
                try {
                    const content = fs.readFileSync(fullPath, 'utf8');
                    enrichedGoal += `\n\n=== CONTEXT FROM @${relPath} ===\n${content.slice(0, 1500)}`;
                } catch {}
            }
        }

        try {
            this._view.webview.postMessage({ type: 'taskStarted' });
            const res = await sendPostRequest(`${baseUrl}/api/v1/task`, { goal: enrichedGoal });
            this._view.webview.postMessage({ type: 'taskComplete', result: res });
            await this._handleLoadStaged(baseUrl);
        } catch (err) {
            this._view.webview.postMessage({ type: 'taskError', error: err.message });
        }
    }

    async _handleLoadFiles(baseUrl) {
        try {
            const res = await sendGetRequest(`${baseUrl}/api/v1/workspace/files`, 1500);
            this._view.webview.postMessage({ type: 'workspaceFiles', files: res.files || [] });
        } catch {
            this._view.webview.postMessage({ type: 'workspaceFiles', files: [] });
        }
    }

    async _handleLoadStaged(baseUrl) {
        try {
            const res = await sendGetRequest(`${baseUrl}/api/v1/staged-files`, 2000);
            this._view.webview.postMessage({ type: 'stagedFilesData', files: res.files || [] });
        } catch {
            this._view.webview.postMessage({ type: 'stagedFilesData', files: [] });
        }
    }

    async _handleViewDiff(filePath, stagedContent) {
        const wsRoot = vscode.workspace.workspaceFolders ? vscode.workspace.workspaceFolders[0].uri.fsPath : '';
        const origPath = path.join(wsRoot, filePath);
        const tempDir = path.join(wsRoot, '.localcoder', 'staged');
        fs.mkdirSync(tempDir, { recursive: true });

        const tempFile = path.join(tempDir, path.basename(filePath));
        fs.writeFileSync(tempFile, stagedContent || '', 'utf8');

        const leftUri = fs.existsSync(origPath) ? vscode.Uri.file(origPath) : vscode.Uri.file(tempFile);
        const rightUri = vscode.Uri.file(tempFile);
        const title = `${path.basename(filePath)} (Original <-> Staged Changes)`;
        await vscode.commands.executeCommand('vscode.diff', leftUri, rightUri, title);
    }

    _getHtmlForWebview() {
        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: var(--vscode-font-family); padding: 12px; color: var(--vscode-foreground); background-color: var(--vscode-editor-background); margin: 0; font-size: 13px; }
        .title { font-weight: 600; font-size: 14px; margin-bottom: 6px; color: #38bdf8; display: flex; align-items: center; gap: 6px; }
        .sub { font-size: 11px; color: var(--vscode-descriptionForeground); margin: 0 0 8px 0; }
        .input-wrap { position: relative; }
        textarea { width: 100%; box-sizing: border-box; background: var(--vscode-input-background); color: var(--vscode-input-foreground); border: 1px solid var(--vscode-input-border); border-radius: 4px; padding: 8px; font-family: inherit; font-size: 12px; resize: vertical; min-height: 80px; }
        textarea:focus { outline: 1px solid var(--vscode-focusBorder); }
        .mention-dropdown { position: absolute; left: 0; right: 0; bottom: 100%; max-height: 140px; overflow-y: auto; background: var(--vscode-dropdown-background); border: 1px solid var(--vscode-dropdown-border); border-radius: 4px; display: none; z-index: 100; box-shadow: 0 4px 12px rgba(0,0,0,0.4); }
        .mention-item { padding: 6px 10px; cursor: pointer; font-size: 11px; font-family: var(--vscode-editor-font-family); }
        .mention-item:hover { background: var(--vscode-list-hoverBackground); color: #38bdf8; }
        .btn-group { display: flex; gap: 6px; margin-top: 8px; }
        button { background: var(--vscode-button-background); color: var(--vscode-button-foreground); border: none; border-radius: 4px; padding: 6px 12px; cursor: pointer; font-size: 12px; font-weight: 500; }
        button:hover { background: var(--vscode-button-hoverBackground); }
        .btn-sec { background: var(--vscode-button-secondaryBackground); color: var(--vscode-button-secondaryForeground); }
        .btn-sec:hover { background: var(--vscode-button-secondaryHoverBackground); }
        .btn-sm { padding: 2px 8px; font-size: 10px; border-radius: 3px; }
        .staged-card { margin-top: 14px; border: 1px solid rgba(56, 189, 248, 0.2); border-radius: 6px; padding: 8px; background: rgba(56, 189, 248, 0.04); display: none; }
        .staged-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; font-weight: 600; font-size: 11px; }
        .staged-item { display: flex; justify-content: space-between; align-items: center; padding: 4px 0; border-top: 1px solid rgba(255,255,255,0.06); font-size: 11px; font-family: var(--vscode-editor-font-family); }
        .status-box { margin-top: 10px; padding: 6px 8px; border-radius: 4px; background: rgba(56, 189, 248, 0.08); border-left: 3px solid #38bdf8; display: none; font-size: 12px; }
        .step-log { margin-top: 8px; font-family: var(--vscode-editor-font-family); font-size: 11px; max-height: 200px; overflow-y: auto; background: rgba(0,0,0,0.25); padding: 6px; border-radius: 4px; display: none; }
        .step-row { padding: 3px 0; border-bottom: 1px solid rgba(255,255,255,0.04); }
    </style>
</head>
<body>
    <div class="title">&#10024; LOCAL-CODER Composer</div>
    <p class="sub">Multi-file planning with @file mentions and live review diffs.</p>
    <div class="input-wrap">
        <textarea id="goalInput" placeholder="Describe task (e.g., 'Refactor @app.py to use async'). Type @ to pin files..."></textarea>
        <div id="mentionBox" class="mention-dropdown"></div>
    </div>
    <div class="btn-group">
        <button id="sendBtn">Execute Plan</button>
        <button id="commitBtn" class="btn-sec">Commit All</button>
        <button id="rollbackBtn" class="btn-sec">Rollback</button>
    </div>
    <div id="statusBox" class="status-box"></div>
    <div id="stagedCard" class="staged-card">
        <div class="staged-head">
            <span id="stagedTitle">Staged Files (0)</span>
            <div style="display: flex; gap: 4px;">
                <button id="acceptAllBtn" class="btn-sm">Accept All</button>
                <button id="rejectAllBtn" class="btn-sm btn-sec">Reject All</button>
            </div>
        </div>
        <div id="stagedList"></div>
    </div>
    <div id="stepLog" class="step-log"></div>

    <script>
        const vscode = acquireVsCodeApi();
        const goalInput = document.getElementById('goalInput');
        const mentionBox = document.getElementById('mentionBox');
        const sendBtn = document.getElementById('sendBtn');
        const statusBox = document.getElementById('statusBox');
        const stagedCard = document.getElementById('stagedCard');
        const stagedList = document.getElementById('stagedList');
        const stagedTitle = document.getElementById('stagedTitle');
        const stepLog = document.getElementById('stepLog');

        let wsFiles = [];
        let stagedFilesCache = [];

        vscode.postMessage({ command: 'loadWorkspaceFiles' });
        vscode.postMessage({ command: 'loadStagedFiles' });

        goalInput.addEventListener('input', () => {
            const val = goalInput.value;
            const cursorPos = goalInput.selectionStart;
            const textBefore = val.slice(0, cursorPos);
            const atMatch = textBefore.match(/@([a-zA-Z0-9_\-\.\/]*)$/);

            if (atMatch && wsFiles.length > 0) {
                const query = atMatch[1].toLowerCase();
                const filtered = wsFiles.filter(f => f.toLowerCase().includes(query)).slice(0, 8);
                if (filtered.length > 0) {
                    mentionBox.innerHTML = '';
                    filtered.forEach(f => {
                        const div = document.createElement('div');
                        div.className = 'mention-item';
                        div.innerText = '@' + f;
                        div.onclick = () => {
                            const newText = textBefore.slice(0, atMatch.index) + '@' + f + ' ' + val.slice(cursorPos);
                            goalInput.value = newText;
                            mentionBox.style.display = 'none';
                            goalInput.focus();
                        };
                        mentionBox.appendChild(div);
                    });
                    mentionBox.style.display = 'block';
                    return;
                }
            }
            mentionBox.style.display = 'none';
        });

        sendBtn.addEventListener('click', () => {
            const goal = goalInput.value.trim();
            if (!goal) return;
            statusBox.style.display = 'block';
            statusBox.innerText = 'Analyzing codebase and planning files...';
            stepLog.style.display = 'block';
            stepLog.innerHTML = '';
            vscode.postMessage({ command: 'submitTask', goal: goal });
        });

        document.getElementById('commitBtn').onclick = () => vscode.postMessage({ command: 'commitEdits' });
        document.getElementById('rollbackBtn').onclick = () => vscode.postMessage({ command: 'rollbackEdits' });
        document.getElementById('acceptAllBtn').onclick = () => vscode.postMessage({ command: 'commitEdits' });
        document.getElementById('rejectAllBtn').onclick = () => vscode.postMessage({ command: 'rollbackEdits' });

        window.addEventListener('message', (event) => {
            const msg = event.data;
            if (msg.type === 'workspaceFiles') {
                wsFiles = msg.files || [];
            } else if (msg.type === 'taskStarted') {
                statusBox.style.display = 'block';
                statusBox.innerText = 'Executing task...';
            } else if (msg.type === 'taskComplete') {
                statusBox.innerText = 'Task finished. Modified ' + (msg.result.modified_files ? msg.result.modified_files.length : 0) + ' files.';
                if (msg.result.steps) {
                    stepLog.style.display = 'block';
                    stepLog.innerHTML = '';
                    msg.result.steps.forEach(s => {
                        const row = document.createElement('div');
                        row.className = 'step-row';
                        row.innerText = 'Step ' + s.step_number + ': ' + (s.thought || s.action_tool);
                        stepLog.appendChild(row);
                    });
                }
            } else if (msg.type === 'taskError') {
                statusBox.style.display = 'block';
                statusBox.innerText = 'Error: ' + msg.error;
            } else if (msg.type === 'stagedFilesData') {
                renderStagedFiles(msg.files || []);
            }
        });

        function renderStagedFiles(files) {
            stagedFilesCache = files;
            stagedTitle.innerText = 'Staged Files (' + files.length + ')';
            if (files.length === 0) {
                stagedCard.style.display = 'none';
                return;
            }
            stagedCard.style.display = 'block';
            stagedList.innerHTML = '';

            files.forEach(f => {
                const row = document.createElement('div');
                row.className = 'staged-item';

                const nameSpan = document.createElement('span');
                nameSpan.innerText = f.file_path;
                nameSpan.style.cursor = 'pointer';
                nameSpan.style.textDecoration = 'underline';
                nameSpan.onclick = () => vscode.postMessage({ command: 'viewDiff', filePath: f.file_path, stagedContent: f.staged_content });

                const actionDiv = document.createElement('div');
                actionDiv.style.display = 'flex';
                actionDiv.style.gap = '4px';

                const diffBtn = document.createElement('button');
                diffBtn.className = 'btn-sm btn-sec';
                diffBtn.innerText = 'Diff';
                diffBtn.onclick = () => vscode.postMessage({ command: 'viewDiff', filePath: f.file_path, stagedContent: f.staged_content });

                const acceptBtn = document.createElement('button');
                acceptBtn.className = 'btn-sm';
                acceptBtn.innerText = 'Accept';
                acceptBtn.onclick = () => vscode.postMessage({ command: 'commitSingle', filePath: f.file_path });

                const discardBtn = document.createElement('button');
                discardBtn.className = 'btn-sm btn-sec';
                discardBtn.innerText = 'X';
                discardBtn.onclick = () => vscode.postMessage({ command: 'discardSingle', filePath: f.file_path });

                actionDiv.appendChild(diffBtn);
                actionDiv.appendChild(acceptBtn);
                actionDiv.appendChild(discardBtn);

                row.appendChild(nameSpan);
                row.appendChild(actionDiv);
                stagedList.appendChild(row);
            });
        }
    </script>
</body>
</html>`;
    }
}

module.exports = { LocalCoderComposerViewProvider };
