/**
 * LOCAL-CODER Composer Webview HTML Assembler
 * Assembles styles, semantic layout components, and client-side scripts.
 */

const { getComposerStyles } = require('./composer_styles');
const { getComposerScripts } = require('./composer_scripts');

function getComposerHtml(currentProvider = 'Local (CPU 1.5B)') {
    return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
${getComposerStyles()}
    </style>
</head>
<body>
    <div class="header">
        <div class="title">&#10024; LOCAL-CODER</div>
        <span id="providerBadge" class="badge" title="Click to switch intelligence tier">${currentProvider}</span>
    </div>

    <div class="input-wrap">
        <textarea id="goalInput" placeholder="Describe task (e.g., 'Refactor @app.py to use async'). Press Ctrl+Enter to execute. Type @ to pin files..."></textarea>
        <div id="mentionBox" class="mention-dropdown"></div>
    </div>

    <div class="chips">
        <span id="chipCurrentFile" class="chip" title="Pin active editor file">+ @ Current File</span>
        <span id="chipFixErrors" class="chip" title="Ask agent to fix LSP diagnostics">Fix Errors</span>
        <span id="chipAddTests" class="chip" title="Ask agent to generate unit tests">Add Tests</span>
        <span id="chipClean" class="chip" title="Clear prompt text">Clear</span>
    </div>

    <div class="btn-row">
        <button id="execBtn" type="button" style="flex: 1;" onclick="triggerExecute()">
            <span id="btnIcon">&#9658;</span>
            <span id="btnText">Execute Plan</span>
        </button>
        <button id="stopBtn" type="button" class="btn-danger" style="display: none;" onclick="triggerStop()">
            <span class="spinner"></span>
            <span>Stop (<span id="elapsedSec">0.0</span>s)</span>
        </button>
        <button id="commitBtn" type="button" class="btn-sec" title="Apply all shadow edits to real files">Commit</button>
        <button id="rollbackBtn" type="button" class="btn-sec" title="Discard staged edits">Rollback</button>
    </div>

    <div id="progressBar" class="progress-bar">
        <div class="progress-fill"></div>
    </div>

    <div id="statusBox" class="status-box"></div>

    <div id="stagedCard" class="staged-card">
        <div class="staged-head">
            <span id="stagedTitle">Staged Changes (0)</span>
            <div style="display: flex; gap: 4px;">
                <button id="acceptAllBtn" class="btn-sm">Accept All</button>
                <button id="rejectAllBtn" class="btn-sm btn-sec">Reject</button>
            </div>
        </div>
        <div id="stagedList"></div>
    </div>

    <div id="stepLog" class="step-log"></div>

    <script>
${getComposerScripts()}
    </script>
</body>
</html>`;
}

module.exports = { getComposerHtml };
