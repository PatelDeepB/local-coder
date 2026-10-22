/**
 * LOCAL-CODER VS Code Extension
 * Entry point orchestrating inline editing, tab completions, Composer, and daemon lifecycle.
 */

const vscode = require('vscode');
const {
    getBackendState,
    sendPostRequest,
    getActiveBaseUrl,
    checkBackendHealth,
    startBackendDaemon,
} = require('./daemon_manager');
const { LocalCoderComposerViewProvider } = require('./composer_view');

let activeDiffState = null;
let statusBarItem = null;

const additionDecorationType = vscode.window.createTextEditorDecorationType({
    backgroundColor: 'rgba(34, 197, 94, 0.20)', isWholeLine: true, overviewRulerColor: '#22c55e',
});

const deletionDecorationType = vscode.window.createTextEditorDecorationType({
    backgroundColor: 'rgba(239, 68, 68, 0.20)', textDecoration: 'line-through', isWholeLine: true, overviewRulerColor: '#ef4444',
});

function activate(context) {
    vscode.commands.executeCommand('setContext', 'localCoderDiffActive', false);

    // Status Bar Telemetry
    statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
    statusBarItem.command = 'local-coder.switchProvider';
    statusBarItem.text = '$(sparkle) Local Coder: Initializing...';
    statusBarItem.show();
    context.subscriptions.push(statusBarItem);

    // Initial check & auto-spawn daemon if offline
    checkBackendHealth(statusBarItem).then(() => {
        if (!getBackendState().isOnline) {
            startBackendDaemon(statusBarItem);
        }
    });

    const interval = setInterval(() => checkBackendHealth(statusBarItem), 5000);
    context.subscriptions.push({ dispose: () => clearInterval(interval) });

    // Commands
    const inlineEditCmd = vscode.commands.registerCommand('local-coder.inlineEdit', async () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor) return;

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
            placeHolder: "e.g., 'Add validation, convert to async, or fix types'",
        });
        if (!instruction) return;

        await executeInlineEdit(editor, targetRange, selectedText || ' ', instruction, isFullLine);
    });

    const acceptDiffCmd = vscode.commands.registerCommand('local-coder.acceptDiff', async () => {
        if (!activeDiffState) return;
        const { editor, range, replacementCode } = activeDiffState;
        await editor.edit((eb) => { eb.replace(range, replacementCode); });
        clearActiveDiff(editor);
        vscode.window.showInformationMessage('Diff accepted.');
    });

    const rejectDiffCmd = vscode.commands.registerCommand('local-coder.rejectDiff', async () => {
        if (!activeDiffState) return;
        clearActiveDiff(activeDiffState.editor);
        vscode.window.showInformationMessage('Diff rejected.');
    });

    const fixDiagnosticsCmd = vscode.commands.registerCommand('local-coder.fixDiagnostics', async () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor) return;

        const diags = vscode.languages.getDiagnostics(editor.document.uri);
        if (!diags || diags.length === 0) {
            vscode.window.showInformationMessage('No active compiler or LSP diagnostics on file.');
            return;
        }

        const rawDiags = diags.map((d) => ({
            file: editor.document.fileName,
            line: d.range.start.line + 1,
            column: d.range.start.character + 1,
            message: d.message,
            severity: d.severity === 0 ? 'error' : 'warning',
        }));

        const baseUrl = await getActiveBaseUrl();
        const res = await sendPostRequest(`${baseUrl}/api/v1/diagnostics/heal`, {
            file_path: editor.document.fileName,
            content: editor.document.getText(),
            diagnostics: rawDiags,
        });

        if (res.is_repaired) {
            await editor.edit((eb) => {
                const fullRange = new vscode.Range(0, 0, editor.document.lineCount, 0);
                eb.replace(fullRange, res.repaired_code);
            });
            vscode.window.showInformationMessage('Errors repaired by Compiler Gate.');
        } else {
            vscode.window.showWarningMessage('Compiler Gate could not fully resolve diagnostics.');
        }
    });

    const switchProviderCmd = vscode.commands.registerCommand('local-coder.switchProvider', async () => {
        const choice = await vscode.window.showQuickPick(
            ['Local (CPU Qwen 1.5B)', 'Ollama (Local GPU)', 'OpenAI / DeepSeek (Remote API)', 'Hybrid (Frontier + Local)'],
            { placeHolder: 'Select intelligence tier:' }
        );
        if (!choice) return;

        let provider = 'local';
        if (choice.includes('Ollama')) provider = 'ollama';
        else if (choice.includes('OpenAI')) provider = 'openai';
        else if (choice.includes('Hybrid')) provider = 'hybrid';

        const baseUrl = await getActiveBaseUrl();
        await sendPostRequest(`${baseUrl}/api/v1/provider/set`, { provider: provider });
        vscode.workspace.getConfiguration('localCoder').update('provider', provider, true);
        await checkBackendHealth(statusBarItem);
    });

    const openComposerCmd = vscode.commands.registerCommand('local-coder.openComposer', async () => {
        await vscode.commands.executeCommand('workbench.view.extension.local-coder-sidebar');
    });

    const commitCmd = vscode.commands.registerCommand('local-coder.commitChanges', async () => {
        const baseUrl = await getActiveBaseUrl();
        const res = await sendPostRequest(`${baseUrl}/api/v1/commit`, {});
        vscode.window.showInformationMessage(`Committed ${res.committed_files.length} staged files.`);
    });

    const rollbackCmd = vscode.commands.registerCommand('local-coder.rollbackChanges', async () => {
        const baseUrl = await getActiveBaseUrl();
        await sendPostRequest(`${baseUrl}/api/v1/rollback`, {});
        vscode.window.showInformationMessage('Staged changes rolled back.');
    });

    const testAndRepairCmd = vscode.commands.registerCommand('local-coder.testAndRepair', async () => {
        const testPath = await vscode.window.showInputBox({ prompt: 'Test path or directory to run:', value: 'tests' });
        if (!testPath) return;

        const baseUrl = await getActiveBaseUrl();
        const res = await sendPostRequest(`${baseUrl}/api/v1/test-and-repair`, { test_path: testPath, max_iterations: 3 });
        if (res.is_successful) {
            vscode.window.showInformationMessage(`All tests PASSED (${res.passed_count} passed, ${res.iterations_used} iterations)!`);
        } else {
            vscode.window.showWarningMessage(`Test repair ended: ${res.passed_count} passed, ${res.failed_count} failed.`);
        }
    });

    const startDaemonCmd = vscode.commands.registerCommand('local-coder.startDaemon', () => startBackendDaemon(statusBarItem));

    const notifyTaskStateCmd = vscode.commands.registerCommand('local-coder.notifyTaskState', (state) => {
        if (!statusBarItem) return;
        if (state === 'running') {
            statusBarItem.text = '$(sync~spin) Local Coder: Synthesizing...';
        } else if (state === 'completed') {
            statusBarItem.text = '$(check) Local Coder: Done';
            setTimeout(() => checkBackendHealth(statusBarItem), 3000);
        } else if (state === 'error') {
            statusBarItem.text = '$(error) Local Coder: Error';
            setTimeout(() => checkBackendHealth(statusBarItem), 3000);
        }
    });

    // Inline Completion Provider (Tab Autocomplete)
    const inlineCompletionProvider = {
        async provideInlineCompletionItems(document, position, context, token) {
            const config = vscode.workspace.getConfiguration('localCoder');
            if (!config.get('enableAutocomplete', true) || !getBackendState().isOnline) {
                return { items: [] };
            }

            const linePrefix = document.lineAt(position.line).text.substring(0, position.character);
            if (!linePrefix.trim()) return { items: [] };

            await new Promise((r) => setTimeout(r, 150));
            if (token.isCancellationRequested) return { items: [] };

            try {
                const textBefore = document.getText(new vscode.Range(new vscode.Position(0, 0), position));
                const textAfter = document.getText(new vscode.Range(position, document.lineAt(document.lineCount - 1).range.end));

                const payload = {
                    prefix: textBefore.slice(-800),
                    suffix: textAfter.slice(0, 400),
                    max_tokens: 24,
                    single_line_only: true,
                };

                const res = await sendPostRequest(`${getBackendState().activeUrl}/api/v1/autocomplete`, payload, 2500);
                if (token.isCancellationRequested || !res || !res.completion || !res.completion.trim()) {
                    return { items: [] };
                }

                const item = new vscode.InlineCompletionItem(res.completion, new vscode.Range(position, position));
                return { items: [item] };
            } catch {
                return { items: [] };
            }
        },
    };

    const autocompleteDisposable = vscode.languages.registerInlineCompletionItemProvider({ pattern: '**' }, inlineCompletionProvider);

    // Register Composer Sidebar Provider
    const composerProvider = new LocalCoderComposerViewProvider(context.extensionUri);
    const composerDisposable = vscode.window.registerWebviewViewProvider('local-coder.chatView', composerProvider);

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
        startDaemonCmd,
        notifyTaskStateCmd,
        autocompleteDisposable,
        composerDisposable
    );
}

async function executeInlineEdit(editor, selection, selectedText, instruction, isFullLine) {
    const baseUrl = await getActiveBaseUrl();
    const doc = editor.document;
    const prefix = doc.getText(new vscode.Range(0, 0, selection.start.line, 0));
    const suffix = doc.getText(new vscode.Range(selection.end.line + 1, 0, doc.lineCount, 0));

    await vscode.window.withProgress(
        { location: vscode.ProgressLocation.Notification, title: 'Local Coder: Generating edit...' },
        async () => {
            const res = await sendPostRequest(`${baseUrl}/api/v1/inline-edit`, {
                file_path: doc.fileName,
                selected_code: selectedText,
                instruction: instruction,
                prefix_context: prefix,
                suffix_context: suffix,
            });

            let repl = res.replacement_code || '';
            if (isFullLine && !repl.endsWith('\n')) repl += '\n';

            activeDiffState = { editor, range: selection, originalCode: selectedText, replacementCode: repl };
            editor.setDecorations(deletionDecorationType, [selection]);
            vscode.commands.executeCommand('setContext', 'localCoderDiffActive', true);

            vscode.window.showInformationMessage('Diff ready: Ctrl+Enter to Accept, Esc to Reject.', 'Accept', 'Reject')
                .then((c) => {
                    if (c === 'Accept') vscode.commands.executeCommand('local-coder.acceptDiff');
                    else if (c === 'Reject') vscode.commands.executeCommand('local-coder.rejectDiff');
                });
        }
    );
}

function clearActiveDiff(editor) {
    if (editor) {
        editor.setDecorations(additionDecorationType, []);
        editor.setDecorations(deletionDecorationType, []);
    }
    activeDiffState = null;
    vscode.commands.executeCommand('setContext', 'localCoderDiffActive', false);
}

function deactivate() {
    if (statusBarItem) statusBarItem.dispose();
}

module.exports = { activate, deactivate };
