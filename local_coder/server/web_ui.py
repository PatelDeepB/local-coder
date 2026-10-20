"""Self-contained responsive Web UI for LOCAL-CODER interactive testing."""

def get_ui_html() -> str:
    """Returns the complete single-page application HTML string."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>LOCAL-CODER: Autonomous Local Coding Studio</title>
  <style>
    :root {
      --bg-base: #0f1117;
      --bg-surface: #181b24;
      --bg-card: #202430;
      --border: #2c3242;
      --text-main: #f3f4f6;
      --text-muted: #9ca3af;
      --accent: #3b82f6;
      --accent-hover: #2563eb;
      --success: #10b981;
      --danger: #ef4444;
      --warning: #f59e0b;
      --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      --font-mono: "Fira Code", Consolas, Monaco, "Courier New", monospace;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background-color: var(--bg-base);
      color: var(--text-main);
      font-family: var(--font-sans);
      display: flex;
      flex-direction: column;
      height: 100vh;
      overflow: hidden;
    }

    header {
      background-color: var(--bg-surface);
      border-bottom: 1px solid var(--border);
      padding: 0.75rem 1.5rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-shrink: 0;
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }

    .brand h1 {
      font-size: 1.15rem;
      font-weight: 700;
      letter-spacing: 0.5px;
    }

    .brand .tag {
      background-color: #1e3a8a;
      color: #93c5fd;
      font-size: 0.75rem;
      padding: 0.2rem 0.5rem;
      border-radius: 4px;
      font-weight: 600;
    }

    .telemetry {
      display: flex;
      align-items: center;
      gap: 1rem;
      font-size: 0.85rem;
    }

    .badge {
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
      background-color: var(--bg-card);
      border: 1px solid var(--border);
      padding: 0.3rem 0.75rem;
      border-radius: 9999px;
    }

    .dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background-color: var(--success);
    }

    main {
      flex: 1;
      display: grid;
      grid-template-columns: 280px 1fr 420px;
      height: calc(100vh - 57px);
      overflow: hidden;
    }

    @media (max-width: 1024px) {
      main { grid-template-columns: 240px 1fr; }
      .right-panel { display: none; }
    }

    @media (max-width: 768px) {
      main { grid-template-columns: 1fr; }
      .sidebar { display: none; }
    }

    /* Sidebar */
    .sidebar {
      background-color: var(--bg-surface);
      border-right: 1px solid var(--border);
      padding: 1rem;
      display: flex;
      flex-direction: column;
      gap: 1.25rem;
      overflow-y: auto;
    }

    .section-title {
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--text-muted);
      font-weight: 700;
      margin-bottom: 0.5rem;
    }

    .btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 0.5rem;
      background-color: var(--accent);
      color: white;
      border: none;
      padding: 0.6rem 1rem;
      border-radius: 6px;
      font-size: 0.875rem;
      font-weight: 600;
      cursor: pointer;
      transition: background 0.15s ease;
      width: 100%;
    }

    .btn:hover { background-color: var(--accent-hover); }
    .btn:focus { outline: 2px solid var(--accent); outline-offset: 2px; }

    .btn-secondary {
      background-color: var(--bg-card);
      border: 1px solid var(--border);
      color: var(--text-main);
    }
    .btn-secondary:hover { background-color: #2b3140; }

    .btn-success { background-color: var(--success); }
    .btn-success:hover { background-color: #059669; }

    .btn-danger { background-color: var(--danger); }
    .btn-danger:hover { background-color: #dc2626; }

    .template-chips {
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
    }

    .chip {
      background-color: var(--bg-card);
      border: 1px solid var(--border);
      padding: 0.5rem 0.75rem;
      border-radius: 6px;
      font-size: 0.8rem;
      color: var(--text-main);
      cursor: pointer;
      text-align: left;
      transition: border-color 0.15s ease;
    }
    .chip:hover { border-color: var(--accent); }

    /* Center Chat / Plan Area */
    .center-panel {
      display: flex;
      flex-direction: column;
      height: 100%;
      background-color: var(--bg-base);
      overflow: hidden;
    }

    .chat-history {
      flex: 1;
      padding: 1.5rem;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 1.25rem;
    }

    .message {
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
      max-width: 85%;
    }

    .message.user {
      align-self: flex-end;
      background-color: #1e293b;
      border: 1px solid #334155;
      padding: 0.85rem 1.15rem;
      border-radius: 12px 12px 2px 12px;
    }

    .message.assistant {
      align-self: flex-start;
      background-color: var(--bg-surface);
      border: 1px solid var(--border);
      padding: 1rem 1.25rem;
      border-radius: 12px 12px 12px 2px;
      width: 100%;
    }

    .step-card {
      background-color: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 0.75rem;
      margin-top: 0.5rem;
      font-size: 0.85rem;
    }

    .step-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-weight: 600;
      color: var(--accent);
      margin-bottom: 0.35rem;
    }

    .step-body {
      font-family: var(--font-mono);
      font-size: 0.8rem;
      color: var(--text-muted);
      white-space: pre-wrap;
      word-break: break-word;
      max-height: 180px;
      overflow-y: auto;
      background-color: #111318;
      padding: 0.5rem;
      border-radius: 4px;
    }

    .input-box-container {
      padding: 1rem 1.5rem;
      background-color: var(--bg-surface);
      border-top: 1px solid var(--border);
      display: flex;
      gap: 0.75rem;
    }

    .input-box {
      flex: 1;
      background-color: var(--bg-card);
      border: 1px solid var(--border);
      color: var(--text-main);
      padding: 0.75rem 1rem;
      border-radius: 6px;
      font-size: 0.9rem;
      font-family: inherit;
      resize: none;
      height: 48px;
    }
    .input-box:focus { outline: 2px solid var(--accent); }

    /* Right Panel (Diff & Terminal) */
    .right-panel {
      background-color: var(--bg-surface);
      border-left: 1px solid var(--border);
      display: flex;
      flex-direction: column;
      height: 100%;
      overflow: hidden;
    }

    .tabs {
      display: flex;
      border-bottom: 1px solid var(--border);
      background-color: var(--bg-surface);
    }

    .tab-btn {
      flex: 1;
      padding: 0.75rem;
      background: none;
      border: none;
      color: var(--text-muted);
      font-weight: 600;
      font-size: 0.85rem;
      cursor: pointer;
      text-align: center;
      border-bottom: 2px solid transparent;
    }

    .tab-btn.active {
      color: var(--text-main);
      border-bottom-color: var(--accent);
      background-color: var(--bg-card);
    }

    .tab-content {
      flex: 1;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      padding: 1rem;
    }

    .diff-viewer {
      flex: 1;
      font-family: var(--font-mono);
      font-size: 0.8rem;
      background-color: #0b0d12;
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 0.75rem;
      overflow: auto;
      white-space: pre;
    }

    .diff-add { color: #34d399; background-color: rgba(16, 185, 129, 0.1); display: block; }
    .diff-del { color: #f87171; background-color: rgba(239, 68, 68, 0.1); display: block; }
    .diff-hunk { color: #60a5fa; font-weight: bold; display: block; }

    .action-bar {
      display: flex;
      gap: 0.75rem;
      margin-top: 1rem;
    }

    .terminal-box {
      flex: 1;
      background-color: #0b0d12;
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 0.75rem;
      font-family: var(--font-mono);
      font-size: 0.8rem;
      color: #10b981;
      overflow: auto;
      white-space: pre-wrap;
    }
  </style>
</head>
<body>
  <header>
    <div class="brand">
      <h1>LOCAL-CODER</h1>
      <span class="tag">Zero-Cloud / 2GB RAM</span>
    </div>
    <div class="telemetry">
      <div class="badge">
        <span class="dot" id="statusDot"></span>
        <span id="ramUsage">Memory: Loading...</span>
      </div>
      <div class="badge">
        <span id="symbolCount">Symbols: 0</span>
      </div>
    </div>
  </header>

  <main>
    <!-- Left Sidebar -->
    <aside class="sidebar">
      <div>
        <div class="section-title">Knowledge & AST</div>
        <button class="btn btn-secondary" onclick="indexCodebase()">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>
          Index Repository (HDC)
        </button>
      </div>

      <div>
        <div class="section-title">Quick Action Templates</div>
        <div class="template-chips">
          <div class="chip" onclick="applyTemplate('Refactor synchronous fetch functions to async def')">
            Make Functions Async
          </div>
          <div class="chip" onclick="applyTemplate('Wrap database operations in structured try-except error handlers')">
            Wrap in Error Handlers
          </div>
          <div class="chip" onclick="applyTemplate('Run test suite using pytest and summarize results')">
            Run Pytest Verification
          </div>
          <div class="chip" onclick="applyTemplate('Inspect git status and check modified files')">
            Check Git Status
          </div>
        </div>
      </div>

      <div>
        <div class="section-title">Staged Files (<span id="stagedCount">0</span>)</div>
        <div id="stagedList" style="font-size: 0.8rem; color: var(--text-muted); font-family: var(--font-mono);">
          No staged edits.
        </div>
      </div>
    </aside>

    <!-- Center Chat & Plan Execution -->
    <section class="center-panel">
      <div class="chat-history" id="chatHistory">
        <div class="message assistant">
          <strong>LOCAL-CODER Agent Ready</strong>
          <p style="margin-top: 0.25rem; font-size: 0.9rem; color: var(--text-muted);">
            Welcome! I am your autonomous local coding agent running strictly on commodity CPU under 1.8 GB RAM.
            Enter a task below, or click any template on the left to start.
          </p>
        </div>
      </div>

      <div class="input-box-container">
        <textarea id="taskInput" class="input-box" placeholder="Ask to refactor code, add a feature, or fix tests (Press Enter to submit)..." onkeydown="handleKeyDown(event)"></textarea>
        <button class="btn" style="width: auto; padding: 0 1.25rem;" onclick="submitTask()">Send</button>
      </div>
    </section>

    <!-- Right Panel: Diff & Terminal -->
    <aside class="right-panel">
      <div class="tabs">
        <button class="tab-btn active" id="diffTabBtn" onclick="switchTab('diff')">Staged Diff</button>
        <button class="tab-btn" id="termTabBtn" onclick="switchTab('term')">Terminal Runner</button>
      </div>

      <!-- Diff Tab -->
      <div class="tab-content" id="diffTabContent">
        <div class="diff-viewer" id="diffViewer">No changes staged in shadow workspace.</div>
        <div class="action-bar">
          <button class="btn btn-success" onclick="commitChanges()">Commit to Disk</button>
          <button class="btn btn-danger" onclick="rollbackChanges()">Rollback</button>
        </div>
      </div>

      <!-- Terminal Tab -->
      <div class="tab-content" id="termTabContent" style="display: none;">
        <div class="terminal-box" id="terminalOutput">Terminal runner ready.</div>
        <div style="display: flex; gap: 0.5rem; margin-top: 0.75rem;">
          <input type="text" id="termCmdInput" class="input-box" style="height: 38px;" placeholder="e.g. pytest tests -v" onkeydown="if(event.key==='Enter') runTerminalCommand()">
          <button class="btn btn-secondary" style="width: auto;" onclick="runTerminalCommand()">Run</button>
        </div>
      </div>
    </aside>
  </main>

  <script>
    async function fetchStatus() {
      try {
        const res = await fetch('/api/v1/status');
        const data = await res.json();
        document.getElementById('ramUsage').innerText = `RSS: ${data.rss_mb.toFixed(1)} MB / ${data.max_rss_mb} MB`;
        document.getElementById('symbolCount').innerText = `Symbols: ${data.symbols_count}`;
        document.getElementById('stagedCount').innerText = data.staged_files.length;
        
        const listDiv = document.getElementById('stagedList');
        if (data.staged_files.length === 0) {
          listDiv.innerText = 'No staged edits.';
        } else {
          listDiv.innerHTML = data.staged_files.map(f => `<div>* ${f}</div>`).join('');
        }
        refreshDiff();
      } catch (e) {
        console.error('Failed to fetch status:', e);
      }
    }

    async function refreshDiff() {
      try {
        const res = await fetch('/api/v1/diff');
        const data = await res.json();
        const viewer = document.getElementById('diffViewer');
        if (!data.diff || data.diff.trim() === '') {
          viewer.innerText = 'No changes staged in shadow workspace.';
          return;
        }
        const lines = data.diff.split('\\n');
        viewer.innerHTML = lines.map(line => {
          if (line.startsWith('+') && !line.startsWith('+++')) return `<span class="diff-add">${escapeHtml(line)}</span>`;
          if (line.startsWith('-') && !line.startsWith('---')) return `<span class="diff-del">${escapeHtml(line)}</span>`;
          if (line.startsWith('@@')) return `<span class="diff-hunk">${escapeHtml(line)}</span>`;
          return escapeHtml(line);
        }).join('\\n');
      } catch (e) {
        console.error('Failed to fetch diff:', e);
      }
    }

    async function indexCodebase() {
      appendUserMessage('Request: Index repository into HDC vector store and symbol graph.');
      try {
        const res = await fetch('/api/v1/index', { method: 'POST' });
        const data = await res.json();
        appendAssistantMessage(`Indexed ${data.symbols_indexed} symbols in ${data.elapsed_ms.toFixed(2)} ms. Zero-copy binary graph updated.`);
        fetchStatus();
      } catch (e) {
        appendAssistantMessage(`Indexing error: ${e.message}`);
      }
    }

    async function submitTask() {
      const input = document.getElementById('taskInput');
      const goal = input.value.trim();
      if (!goal) return;
      input.value = '';

      appendUserMessage(goal);
      const loadingMsg = appendAssistantMessage('Analyzing codebase and executing autonomous ReAct steps...');

      try {
        const res = await fetch('/api/v1/task', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ goal })
        });
        const data = await res.json();
        renderTaskSteps(loadingMsg, data);
        fetchStatus();
      } catch (e) {
        loadingMsg.innerHTML = `<span style="color: var(--danger)">Execution error: ${e.message}</span>`;
      }
    }

    async function commitChanges() {
      try {
        const res = await fetch('/api/v1/commit', { method: 'POST' });
        const data = await res.json();
        alert(`Committed ${data.committed_files.length} file(s) to disk.`);
        fetchStatus();
      } catch (e) {
        alert(`Commit failed: ${e.message}`);
      }
    }

    async function rollbackChanges() {
      try {
        await fetch('/api/v1/rollback', { method: 'POST' });
        alert('All shadow workspace changes rolled back.');
        fetchStatus();
      } catch (e) {
        alert(`Rollback failed: ${e.message}`);
      }
    }

    async function runTerminalCommand() {
      const input = document.getElementById('termCmdInput');
      const cmd = input.value.trim();
      if (!cmd) return;
      const termBox = document.getElementById('terminalOutput');
      termBox.innerText += `\\n$ ${cmd}\\nExecuting...`;

      try {
        const res = await fetch('/api/v1/terminal', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ command: cmd })
        });
        const data = await res.json();
        termBox.innerText += `\\n${data.stdout || ''}${data.stderr || ''}\\n[Exit Code: ${data.exit_code}]\\n`;
        termBox.scrollTop = termBox.scrollHeight;
      } catch (e) {
        termBox.innerText += `\\nError: ${e.message}\\n`;
      }
    }

    function applyTemplate(text) {
      document.getElementById('taskInput').value = text;
      document.getElementById('taskInput').focus();
    }

    function handleKeyDown(e) {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        submitTask();
      }
    }

    function switchTab(tab) {
      document.getElementById('diffTabBtn').classList.toggle('active', tab === 'diff');
      document.getElementById('termTabBtn').classList.toggle('active', tab === 'term');
      document.getElementById('diffTabContent').style.display = tab === 'diff' ? 'flex' : 'none';
      document.getElementById('termTabContent').style.display = tab === 'term' ? 'flex' : 'none';
    }

    function appendUserMessage(text) {
      const container = document.getElementById('chatHistory');
      const div = document.createElement('div');
      div.className = 'message user';
      div.innerText = text;
      container.appendChild(div);
      container.scrollTop = container.scrollHeight;
    }

    function appendAssistantMessage(text) {
      const container = document.getElementById('chatHistory');
      const div = document.createElement('div');
      div.className = 'message assistant';
      div.innerHTML = `<p>${escapeHtml(text)}</p>`;
      container.appendChild(div);
      container.scrollTop = container.scrollHeight;
      return div;
    }

    function renderTaskSteps(targetDiv, data) {
      let html = `<strong>Goal Result: ${escapeHtml(data.status)}</strong>`;
      if (data.output_directory) {
        html += `<div style="margin: 0.5rem 0; padding: 0.5rem 0.75rem; background-color: #1e3a5f; border-left: 3px solid var(--accent); border-radius: 4px; font-size: 0.85rem;">
          <div><strong>Disk Directory:</strong> <code>${escapeHtml(data.output_directory)}</code></div>
          ${data.modified_files && data.modified_files.length > 0 ? `<div style="margin-top: 0.25rem;"><strong>Files Created:</strong> <code>${escapeHtml(data.modified_files.join(', '))}</code></div>` : ''}
        </div>`;
      }
      if (data.final_output) {
        html += `<div style="margin: 0.75rem 0; font-size: 0.9rem; line-height: 1.5; white-space: pre-wrap; background-color: var(--bg-card); padding: 0.85rem; border-radius: 6px; border: 1px solid var(--border); font-family: var(--font-mono);">${escapeHtml(data.final_output)}</div>`;
      }
      if (data.steps && data.steps.length > 0) {
        html += `<div style="margin-top: 0.75rem;"><strong>ReAct Execution Steps (${data.steps.length}):</strong>`;
        data.steps.forEach(s => {
          html += `
            <div class="step-card">
              <div class="step-header">
                <span>Step ${s.step_number}: ${escapeHtml(s.action_tool)}</span>
                <span style="font-size: 0.75rem; color: var(--text-muted);">${s.elapsed_seconds.toFixed(2)}s</span>
              </div>
              <div class="step-body">${escapeHtml(s.thought || '')}\\n-> Action: ${escapeHtml(JSON.stringify(s.action_arguments || {}))}\\n<- Observation: ${escapeHtml(s.observation || '')}</div>
            </div>`;
        });
        html += `</div>`;
      }
      targetDiv.innerHTML = html;
    }

    function escapeHtml(str) {
      if (!str) return '';
      return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    // Initialize
    fetchStatus();
    setInterval(fetchStatus, 3000);
  </script>
</body>
</html>"""
