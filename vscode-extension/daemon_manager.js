/**
 * LOCAL-CODER Daemon Process and Network Telemetry Manager
 */

const vscode = require('vscode');
const http = require('http');
const https = require('https');
const cp = require('child_process');
const path = require('path');
const fs = require('fs');

let cachedActiveUrl = 'http://127.0.0.1:8080';
let isBackendOnline = false;
let spawnedServerProcess = null;

function getBackendState() {
    return {
        isOnline: isBackendOnline,
        activeUrl: cachedActiveUrl,
    };
}

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
                'Content-Length': Buffer.byteLength(data),
            },
            timeout: timeoutMs,
        };

        const client = parsed.protocol === 'https:' ? https : http;
        const req = client.request(options, (res) => {
            let body = '';
            res.on('data', (chunk) => { body += chunk; });
            res.on('end', () => {
                if (res.statusCode >= 200 && res.statusCode < 300) {
                    try {
                        resolve(JSON.parse(body));
                    } catch {
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

function sendGetRequest(targetUrl, timeoutMs = 5000) {
    return new Promise((resolve, reject) => {
        const parsed = new URL(targetUrl);
        const options = {
            hostname: parsed.hostname,
            port: parsed.port || (parsed.protocol === 'https:' ? 443 : 80),
            path: parsed.pathname + parsed.search,
            method: 'GET',
            timeout: timeoutMs,
        };

        const client = parsed.protocol === 'https:' ? https : http;
        const req = client.request(options, (res) => {
            let body = '';
            res.on('data', (chunk) => { body += chunk; });
            res.on('end', () => {
                if (res.statusCode >= 200 && res.statusCode < 300) {
                    try {
                        resolve(JSON.parse(body));
                    } catch {
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

async function checkBackendHealth(statusBarItem) {
    if (!statusBarItem) return;
    const config = vscode.workspace.getConfiguration('localCoder');
    const activeUrl = await getActiveBaseUrl();
    try {
        const statusData = await sendGetRequest(`${activeUrl}/api/v1/status`, 1200);
        const rss = Math.round(statusData.rss_mb || 0);
        const provider = config.get('provider') || 'local';
        cachedActiveUrl = activeUrl;
        isBackendOnline = true;
        statusBarItem.text = `$(sparkle) Local Coder: ${rss}MB [${provider}]`;
        statusBarItem.tooltip = `Status: ${statusData.status} | URL: ${activeUrl} | Staged: ${statusData.staged_files.length}`;
    } catch {
        isBackendOnline = false;
        statusBarItem.text = '$(circle-slash) Local Coder: Offline';
        statusBarItem.tooltip = 'FastAPI server daemon is offline. Click to launch automatic background daemon.';
    }
}

function resolvePythonPath() {
    const wsFolders = vscode.workspace.workspaceFolders;
    if (wsFolders && wsFolders.length > 0) {
        const root = wsFolders[0].uri.fsPath;
        const venvWin = path.join(root, 'venv', 'Scripts', 'python.exe');
        if (fs.existsSync(venvWin)) return venvWin;
        const dotVenvWin = path.join(root, '.venv', 'Scripts', 'python.exe');
        if (fs.existsSync(dotVenvWin)) return dotVenvWin;
        const venvUnix = path.join(root, 'venv', 'bin', 'python');
        if (fs.existsSync(venvUnix)) return venvUnix;
    }

    const defaultProjDir = 'C:\\Deep_Patel_Projects\\OpenSourceProjects\\local_coder';
    const projVenv = path.join(defaultProjDir, 'venv', 'Scripts', 'python.exe');
    if (fs.existsSync(projVenv)) return projVenv;

    return 'python';
}

function resolveServerCwd() {
    const wsFolders = vscode.workspace.workspaceFolders;
    if (wsFolders && wsFolders.length > 0) {
        const root = wsFolders[0].uri.fsPath;
        if (fs.existsSync(path.join(root, 'local_coder'))) {
            return root;
        }
    }
    const defaultProjDir = 'C:\\Deep_Patel_Projects\\OpenSourceProjects\\local_coder';
    if (fs.existsSync(defaultProjDir)) {
        return defaultProjDir;
    }
    return process.cwd();
}

async function startBackendDaemon(statusBarItem) {
    if (isBackendOnline) {
        return;
    }

    const pythonBin = resolvePythonPath();
    const cwd = resolveServerCwd();

    if (statusBarItem) {
        statusBarItem.text = '$(sync~spin) Local Coder: Spawning daemon...';
    }

    try {
        spawnedServerProcess = cp.spawn(
            pythonBin,
            ['-m', 'uvicorn', 'local_coder.server.api_server:app', '--host', '127.0.0.1', '--port', '8080'],
            {
                cwd: cwd,
                detached: true,
                stdio: 'ignore',
                windowsHide: true,
            }
        );
        spawnedServerProcess.unref();

        for (let i = 0; i < 15; i++) {
            await new Promise((r) => setTimeout(r, 600));
            try {
                await sendGetRequest('http://127.0.0.1:8080/health', 600);
                cachedActiveUrl = 'http://127.0.0.1:8080';
                isBackendOnline = true;
                if (statusBarItem) {
                    await checkBackendHealth(statusBarItem);
                }
                vscode.window.showInformationMessage('LOCAL-CODER background daemon started.');
                return;
            } catch {}
        }
    } catch (err) {
        vscode.window.showErrorMessage(`Failed to auto-spawn LOCAL-CODER daemon: ${err.message}`);
    }
}

module.exports = {
    getBackendState,
    sendPostRequest,
    sendGetRequest,
    getActiveBaseUrl,
    checkBackendHealth,
    startBackendDaemon,
};
