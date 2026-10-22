/**
 * LOCAL-CODER Composer Sidebar Webview Provider
 * Manages task submission, prompt locking, @file mentions, and interactive diff reviews.
 */

const vscode = require('vscode');
const path = require('path');
const fs = require('fs');
const { getActiveBaseUrl, sendPostRequest, sendGetRequest } = require('./daemon_manager');
const { getComposerHtml } = require('./composer_html');

class LocalCoderComposerViewProvider {
    constructor(extensionUri) {
        this._extensionUri = extensionUri;
        this._activeAbortController = null;
        this._taskState = {
            status: 'idle',
            goal: '',
            startTime: 0,
            result: null,
            error: null
        };
    }

    resolveWebviewView(webviewView) {
        this._view = webviewView;
        webviewView.webview.options = {
            enableScripts: true,
            retainContextWhenHidden: true,
        };

        const config = vscode.workspace.getConfiguration('localCoder');
        const providerName = config.get('provider', 'local');
        webviewView.webview.html = getComposerHtml(providerName);

        webviewView.webview.onDidReceiveMessage(async (message) => {
            const baseUrl = getActiveBaseUrl();

            switch (message.command) {
                case 'getTaskState':
                    if (this._view) {
                        this._view.webview.postMessage({ type: 'taskRestoreState', task: this._taskState });
                    }
                    break;
                case 'syncPrompt':
                    this._taskState.goal = message.goal || '';
                    break;
                case 'submitTask':
                    await this._handleSubmitTask(baseUrl, message.goal);
                    break;
                case 'abortTask':
                    this._handleAbortTask();
                    break;
                case 'insertActiveFile':
                    this._handleInsertActiveFile();
                    break;
                case 'switchProvider':
                    await vscode.commands.executeCommand('local-coder.switchProvider');
                    this._updateProviderBadge();
                    break;
                case 'loadWorkspaceFiles':
                    await this._handleLoadFiles(baseUrl);
                    break;
                case 'loadStagedFiles':
                    await this._handleLoadStaged(baseUrl);
                    break;
                case 'viewDiff':
                    await this._handleViewDiff(message.filePath, message.stagedContent);
                    break;
                case 'commitSingle':
                    await sendPostRequest(`${baseUrl}/api/v1/staged-files/commit`, { file_path: message.filePath });
                    await this._handleLoadStaged(baseUrl);
                    break;
                case 'discardSingle':
                    await sendPostRequest(`${baseUrl}/api/v1/staged-files/discard`, { file_path: message.filePath });
                    await this._handleLoadStaged(baseUrl);
                    break;
                case 'commitEdits':
                    await vscode.commands.executeCommand('local-coder.commitChanges');
                    await this._handleLoadStaged(baseUrl);
                    break;
                case 'rollbackEdits':
                    await vscode.commands.executeCommand('local-coder.rollbackChanges');
                    await this._handleLoadStaged(baseUrl);
                    break;
            }
        });
    }

    _updateProviderBadge() {
        const config = vscode.workspace.getConfiguration('localCoder');
        const p = config.get('provider', 'local');
        if (this._view) {
            this._view.webview.postMessage({ type: 'providerUpdated', provider: p });
        }
    }

    _handleInsertActiveFile() {
        const editor = vscode.window.activeTextEditor;
        if (!editor) return;
        const wsRoot = vscode.workspace.workspaceFolders ? vscode.workspace.workspaceFolders[0].uri.fsPath : '';
        const relPath = path.relative(wsRoot, editor.document.fileName).replace(/\\/g, '/');
        if (this._view) {
            this._view.webview.postMessage({ type: 'activeFileInserted', filePath: relPath });
        }
    }

    _handleAbortTask() {
        this._taskState.status = 'idle';
        this._taskState.error = 'Task execution stopped by user.';
        if (this._activeAbortController) {
            this._activeAbortController.abort();
            this._activeAbortController = null;
        }
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

        const controller = new AbortController();
        this._activeAbortController = controller;
        this._taskState = {
            status: 'running',
            goal: rawGoal,
            startTime: Date.now(),
            result: null,
            error: null
        };

        try {
            if (this._view) this._view.webview.postMessage({ type: 'taskStarted' });
            vscode.commands.executeCommand('local-coder.notifyTaskState', 'running');

            const payload = {
                goal: enrichedGoal,
                output_directory: wsRoot || undefined,
            };
            const res = await sendPostRequest(`${baseUrl}/api/v1/task`, payload, 300000, controller.signal);
            this._taskState.status = 'completed';
            this._taskState.result = res;
            if (this._view) this._view.webview.postMessage({ type: 'taskComplete', result: res });
            vscode.commands.executeCommand('local-coder.notifyTaskState', 'completed');
            await this._handleLoadStaged(baseUrl);
        } catch (err) {
            this._taskState.status = 'error';
            this._taskState.error = err.message;
            if (err.message && err.message.includes('ECONNREFUSED')) {
                vscode.commands.executeCommand('local-coder.startDaemon');
                if (this._view) this._view.webview.postMessage({
                    type: 'taskError',
                    error: 'Local Coder daemon was offline. Automatically launched daemon on port 8080. Please retry in 5 seconds.'
                });
            } else {
                if (this._view) this._view.webview.postMessage({ type: 'taskError', error: err.message });
            }
            vscode.commands.executeCommand('local-coder.notifyTaskState', 'error');
        } finally {
            this._activeAbortController = null;
        }
    }

    async _handleLoadFiles(baseUrl) {
        try {
            const res = await sendGetRequest(`${baseUrl}/api/v1/workspace/files`, 2000);
            if (this._view) this._view.webview.postMessage({ type: 'workspaceFiles', files: res.files || [] });
        } catch {
            if (this._view) this._view.webview.postMessage({ type: 'workspaceFiles', files: [] });
        }
    }

    async _handleLoadStaged(baseUrl) {
        try {
            const res = await sendGetRequest(`${baseUrl}/api/v1/staged-files`, 2000);
            if (this._view) this._view.webview.postMessage({ type: 'stagedFilesData', files: res.files || [] });
        } catch {
            if (this._view) this._view.webview.postMessage({ type: 'stagedFilesData', files: [] });
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
        const title = `${path.basename(filePath)} (Original <-> Staged)`;
        await vscode.commands.executeCommand('vscode.diff', leftUri, rightUri, title);
    }
}

module.exports = { LocalCoderComposerViewProvider };
