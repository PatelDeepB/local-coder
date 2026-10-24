/**
 * LOCAL-CODER Composer Stylesheet Provider
 * Returns CSS styles matching native VS Code dark and light themes.
 */

function getComposerStyles() {
    return `
        :root {
            --primary: #38bdf8;
            --primary-glow: rgba(56, 189, 248, 0.4);
            --success: #22c55e;
            --danger: #ef4444;
            --border-subtle: rgba(255, 255, 255, 0.08);
        }
        body {
            font-family: var(--vscode-font-family);
            padding: 10px;
            color: var(--vscode-foreground);
            background-color: var(--vscode-editor-background);
            margin: 0;
            font-size: 12px;
            line-height: 1.4;
        }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
            padding-bottom: 6px;
            border-bottom: 1px solid var(--border-subtle);
        }
        .title {
            font-weight: 600;
            font-size: 13px;
            color: var(--primary);
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .badge {
            font-size: 10px;
            padding: 2px 6px;
            border-radius: 10px;
            background: rgba(56, 189, 248, 0.12);
            color: var(--primary);
            border: 1px solid rgba(56, 189, 248, 0.3);
            cursor: pointer;
        }
        .dir-bar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 5px 8px;
            margin-bottom: 8px;
            background: rgba(56, 189, 248, 0.06);
            border: 1px solid rgba(56, 189, 248, 0.2);
            border-radius: 5px;
            gap: 6px;
        }
        .dir-info {
            display: flex;
            align-items: center;
            gap: 5px;
            overflow: hidden;
            flex: 1;
            cursor: pointer;
        }
        .dir-icon { font-size: 12px; flex-shrink: 0; }
        .dir-label { font-size: 10px; color: var(--vscode-descriptionForeground, #888); font-weight: 600; flex-shrink: 0; }
        .dir-path {
            font-size: 11px;
            color: var(--primary);
            font-family: var(--vscode-editor-font-family);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .btn-xs {
            padding: 2px 6px;
            font-size: 10px;
            border-radius: 3px;
            background: var(--vscode-button-secondaryBackground);
            color: var(--vscode-button-secondaryForeground);
            flex-shrink: 0;
            border: 1px solid var(--border-subtle);
        }
        .btn-xs:hover { background: var(--vscode-button-secondaryHoverBackground); }
        .input-wrap { position: relative; margin-bottom: 6px; }
        textarea {
            width: 100%;
            box-sizing: border-box;
            background: var(--vscode-input-background);
            color: var(--vscode-input-foreground);
            border: 1px solid var(--vscode-input-border);
            border-radius: 6px;
            padding: 8px 10px;
            font-family: inherit;
            font-size: 12px;
            resize: vertical;
            min-height: 85px;
            transition: all 0.2s ease;
        }
        textarea:focus { outline: none; border-color: var(--primary); box-shadow: 0 0 0 1px var(--primary); }
        textarea.locked {
            opacity: 0.75;
            background: rgba(0, 0, 0, 0.2);
            border-color: var(--primary);
            box-shadow: 0 0 12px var(--primary-glow);
            cursor: not-allowed;
            animation: pulse-glow 2s infinite ease-in-out;
        }
        @keyframes pulse-glow {
            0%, 100% { box-shadow: 0 0 6px var(--primary-glow); }
            50% { box-shadow: 0 0 16px rgba(56, 189, 248, 0.7); }
        }
        .chips { display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 8px; }
        .chip {
            background: var(--vscode-badge-background);
            color: var(--vscode-badge-foreground);
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 10px;
            cursor: pointer;
            border: 1px solid transparent;
            user-select: none;
        }
        .chip:hover { border-color: var(--primary); color: var(--primary); }
        .btn-row { display: flex; gap: 6px; align-items: center; }
        button {
            background: var(--vscode-button-background);
            color: var(--vscode-button-foreground);
            border: none;
            border-radius: 4px;
            padding: 6px 12px;
            cursor: pointer;
            font-size: 11px;
            font-weight: 500;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 5px;
            transition: opacity 0.15s;
        }
        button:hover:not(:disabled) { background: var(--vscode-button-hoverBackground); }
        button:disabled { opacity: 0.5; cursor: not-allowed; }
        .btn-sec {
            background: var(--vscode-button-secondaryBackground);
            color: var(--vscode-button-secondaryForeground);
        }
        .btn-sec:hover:not(:disabled) { background: var(--vscode-button-secondaryHoverBackground); }
        .btn-danger { background: var(--danger); color: #fff; }
        .btn-danger:hover:not(:disabled) { background: #dc2626; }
        .btn-sm { padding: 2px 6px; font-size: 10px; border-radius: 3px; }
        .spinner {
            display: inline-block;
            width: 10px;
            height: 10px;
            border: 2px solid rgba(255,255,255,0.3);
            border-radius: 50%;
            border-top-color: #fff;
            animation: spin 0.8s linear infinite;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        .progress-bar {
            height: 3px;
            width: 100%;
            background: rgba(56, 189, 248, 0.15);
            border-radius: 2px;
            overflow: hidden;
            margin-top: 6px;
            display: none;
        }
        .progress-fill {
            height: 100%;
            width: 40%;
            background: var(--primary);
            border-radius: 2px;
            animation: progress-slide 1.4s infinite ease-in-out;
        }
        @keyframes progress-slide {
            0% { transform: translateX(-100%); }
            100% { transform: translateX(350%); }
        }
        .status-box {
            margin-top: 8px;
            padding: 6px 8px;
            border-radius: 4px;
            background: rgba(56, 189, 248, 0.08);
            border-left: 3px solid var(--primary);
            display: none;
            font-size: 11px;
            font-family: var(--vscode-editor-font-family);
        }
        .status-box.success {
            background: rgba(34, 197, 94, 0.08);
            border-left-color: var(--success);
            color: var(--success);
        }
        .status-box.error {
            background: rgba(239, 68, 68, 0.08);
            border-left-color: var(--danger);
            color: var(--danger);
        }
        .staged-card {
            margin-top: 10px;
            border: 1px solid rgba(56, 189, 248, 0.25);
            border-radius: 6px;
            padding: 8px;
            background: rgba(56, 189, 248, 0.03);
            display: none;
        }
        .staged-head {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 6px;
            font-weight: 600;
            font-size: 11px;
        }
        .staged-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 4px 0;
            border-top: 1px solid var(--border-subtle);
            font-size: 11px;
            font-family: var(--vscode-editor-font-family);
        }
        .step-log {
            margin-top: 8px;
            font-family: var(--vscode-editor-font-family);
            font-size: 10.5px;
            max-height: 160px;
            overflow-y: auto;
            background: rgba(0, 0, 0, 0.2);
            padding: 6px;
            border-radius: 4px;
            display: none;
        }
        .step-row {
            padding: 2px 0;
            color: var(--vscode-descriptionForeground);
            border-bottom: 1px solid rgba(255, 255, 255, 0.03);
        }
        .mention-dropdown {
            position: absolute;
            left: 0;
            right: 0;
            bottom: 100%;
            max-height: 140px;
            overflow-y: auto;
            background: var(--vscode-dropdown-background);
            border: 1px solid var(--vscode-dropdown-border);
            border-radius: 4px;
            display: none;
            z-index: 100;
            box-shadow: 0 4px 12px rgba(0,0,0,0.4);
        }
        .mention-item {
            padding: 5px 8px;
            cursor: pointer;
            font-size: 11px;
            font-family: var(--vscode-editor-font-family);
        }
        .mention-item:hover {
            background: var(--vscode-list-hoverBackground);
            color: var(--primary);
        }
    `;
}

module.exports = { getComposerStyles };
