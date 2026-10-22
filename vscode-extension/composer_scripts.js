/**
 * LOCAL-CODER Composer Client Scripts
 * Provides prompt locking, live execution timer, mention autocomplete, and diff review logic.
 */

function getComposerScripts() {
    return `
        const vscode = acquireVsCodeApi();
        const goalInput = document.getElementById('goalInput');
        const mentionBox = document.getElementById('mentionBox');
        const execBtn = document.getElementById('execBtn');
        const stopBtn = document.getElementById('stopBtn');
        const elapsedSec = document.getElementById('elapsedSec');
        const progressBar = document.getElementById('progressBar');
        const statusBox = document.getElementById('statusBox');
        const stagedCard = document.getElementById('stagedCard');
        const stagedList = document.getElementById('stagedList');
        const stagedTitle = document.getElementById('stagedTitle');
        const stepLog = document.getElementById('stepLog');
        const providerBadge = document.getElementById('providerBadge');

        let wsFiles = [];
        let isExecuting = false;
        let timerInterval = null;
        let startTime = 0;

        // Restore saved state from previous view session
        const saved = vscode.getState() || {};
        if (saved.goal && !goalInput.value) {
            goalInput.value = saved.goal;
        }

        vscode.postMessage({ command: 'getTaskState' });
        vscode.postMessage({ command: 'loadWorkspaceFiles' });
        vscode.postMessage({ command: 'loadStagedFiles' });

        function setLockedState(locked, customStart) {
            isExecuting = locked;
            goalInput.disabled = locked;
            execBtn.disabled = locked;
            if (locked) {
                goalInput.classList.add('locked');
                execBtn.style.display = 'none';
                stopBtn.style.display = 'inline-flex';
                progressBar.style.display = 'block';
                startTime = customStart || startTime || Date.now();
                if (timerInterval) clearInterval(timerInterval);
                const tick = () => {
                    const sec = ((Date.now() - startTime) / 1000).toFixed(1);
                    elapsedSec.innerText = sec;
                };
                tick();
                timerInterval = setInterval(tick, 100);
            } else {
                goalInput.classList.remove('locked');
                execBtn.style.display = 'inline-flex';
                stopBtn.style.display = 'none';
                progressBar.style.display = 'none';
                if (timerInterval) {
                    clearInterval(timerInterval);
                    timerInterval = null;
                }
            }
        }

        function triggerExecute() {
            if (isExecuting) return;
            const goal = goalInput.value.trim();
            if (!goal) {
                statusBox.className = 'status-box error';
                statusBox.style.display = 'block';
                statusBox.innerText = 'Please enter a goal or instruction above.';
                goalInput.focus();
                return;
            }
            startTime = Date.now();
            setLockedState(true, startTime);
            vscode.setState({ goal: goal, isExecuting: true, startTime: startTime });
            statusBox.className = 'status-box';
            statusBox.style.display = 'block';
            statusBox.innerText = 'Agent is planning and virtualizing context...';
            stepLog.style.display = 'block';
            stepLog.innerHTML = '';
            vscode.postMessage({ command: 'submitTask', goal: goal });
        }

        function triggerStop() {
            vscode.postMessage({ command: 'abortTask' });
            setLockedState(false);
            vscode.setState({ ...(vscode.getState() || {}), isExecuting: false });
            statusBox.className = 'status-box error';
            statusBox.innerText = 'Task execution stopped by user.';
        }

        window.triggerExecute = triggerExecute;
        window.triggerStop = triggerStop;

        if (execBtn) execBtn.addEventListener('click', triggerExecute);
        if (stopBtn) stopBtn.addEventListener('click', triggerStop);

        goalInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                triggerExecute();
            } else if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                e.preventDefault();
                triggerExecute();
            } else if (e.key === 'Escape') {
                mentionBox.style.display = 'none';
            }
        });

        goalInput.addEventListener('input', () => {
            vscode.setState({ ...(vscode.getState() || {}), goal: goalInput.value });
            vscode.postMessage({ command: 'syncPrompt', goal: goalInput.value });
            const val = goalInput.value;
            const cursorPos = goalInput.selectionStart;
            const textBefore = val.slice(0, cursorPos);
            const atMatch = textBefore.match(/@([a-zA-Z0-9_\\-\\.\\/]*)$/);

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

        document.getElementById('chipCurrentFile').onclick = () => {
            vscode.postMessage({ command: 'insertActiveFile' });
        };
        document.getElementById('chipFixErrors').onclick = () => {
            goalInput.value = (goalInput.value ? goalInput.value + ' ' : '') + 'Inspect and fix all LSP compiler diagnostic errors in current file.';
            goalInput.focus();
        };
        document.getElementById('chipAddTests').onclick = () => {
            goalInput.value = (goalInput.value ? goalInput.value + ' ' : '') + 'Write comprehensive unit tests with full edge-case coverage.';
            goalInput.focus();
        };
        document.getElementById('chipClean').onclick = () => {
            goalInput.value = '';
            vscode.setState({ ...(vscode.getState() || {}), goal: '' });
            goalInput.focus();
        };

        providerBadge.onclick = () => vscode.postMessage({ command: 'switchProvider' });
        document.getElementById('commitBtn').onclick = () => vscode.postMessage({ command: 'commitEdits' });
        document.getElementById('rollbackBtn').onclick = () => vscode.postMessage({ command: 'rollbackEdits' });
        document.getElementById('acceptAllBtn').onclick = () => vscode.postMessage({ command: 'commitEdits' });
        document.getElementById('rejectAllBtn').onclick = () => vscode.postMessage({ command: 'rollbackEdits' });

        function renderTaskComplete(result) {
            setLockedState(false);
            vscode.setState({ ...(vscode.getState() || {}), isExecuting: false });
            const count = result.modified_files ? result.modified_files.length : 0;
            statusBox.className = 'status-box success';
            statusBox.innerText = 'Completed. ' + count + ' file(s) staged for review.';
            if (result.steps && result.steps.length > 0) {
                stepLog.style.display = 'block';
                stepLog.innerHTML = '';
                result.steps.forEach(s => {
                    const row = document.createElement('div');
                    row.className = 'step-row';
                    row.innerText = 'Step ' + s.step_number + ': ' + (s.thought || s.action_tool);
                    stepLog.appendChild(row);
                });
            }
        }

        window.addEventListener('message', (event) => {
            const msg = event.data;
            if (msg.type === 'workspaceFiles') {
                wsFiles = msg.files || [];
            } else if (msg.type === 'activeFileInserted') {
                if (msg.filePath) {
                    goalInput.value = (goalInput.value ? goalInput.value + ' ' : '') + '@' + msg.filePath + ' ';
                    goalInput.focus();
                }
            } else if (msg.type === 'providerUpdated') {
                providerBadge.innerText = msg.provider;
            } else if (msg.type === 'taskStarted') {
                setLockedState(true);
            } else if (msg.type === 'taskRestoreState') {
                const t = msg.task;
                if (!t) return;
                if (t.goal && !goalInput.value) {
                    goalInput.value = t.goal;
                }
                if (t.status === 'running') {
                    setLockedState(true, t.startTime);
                    statusBox.className = 'status-box';
                    statusBox.style.display = 'block';
                    statusBox.innerText = 'Agent is running in background...';
                } else if (t.status === 'completed' && t.result) {
                    renderTaskComplete(t.result);
                } else if (t.status === 'error' && t.error) {
                    setLockedState(false);
                    statusBox.className = 'status-box error';
                    statusBox.innerText = 'Error: ' + t.error;
                }
            } else if (msg.type === 'taskComplete') {
                renderTaskComplete(msg.result);
            } else if (msg.type === 'taskError') {
                setLockedState(false);
                vscode.setState({ ...(vscode.getState() || {}), isExecuting: false });
                statusBox.className = 'status-box error';
                statusBox.innerText = 'Error: ' + msg.error;
            } else if (msg.type === 'stagedFilesData') {
                renderStagedFiles(msg.files || []);
            }
        });

        function renderStagedFiles(files) {
            stagedTitle.innerText = 'Staged Changes (' + files.length + ')';
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
    `;
}

module.exports = { getComposerScripts };
