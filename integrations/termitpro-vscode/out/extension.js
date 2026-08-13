"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = __importStar(require("vscode"));
function apiBase() {
    return vscode.workspace.getConfiguration('peeknook').get('apiUrl') || 'http://127.0.0.1:5056';
}
function uiUrl() {
    return vscode.workspace.getConfiguration('peeknook').get('uiUrl') || 'http://127.0.0.1:5173';
}
async function fetchJson(path) {
    const res = await fetch(`${apiBase()}${path}`);
    if (!res.ok) {
        throw new Error(`PeekNook API ${res.status}: ${await res.text()}`);
    }
    return (await res.json());
}
function activate(context) {
    context.subscriptions.push(vscode.commands.registerCommand('peeknook.status', async () => {
        try {
            const status = await fetchJson('/api/peeknook/termitpro/status');
            const msg = [
                `Service: ${status.service}`,
                `Notebooks: ${status.notebook_count}`,
                `Sources: ${status.source_count}`,
            ].join('\n');
            vscode.window.showInformationMessage(msg);
        }
        catch (err) {
            vscode.window.showErrorMessage(String(err));
        }
    }));
    context.subscriptions.push(vscode.commands.registerCommand('peeknook.search', async () => {
        const q = await vscode.window.showInputBox({ prompt: 'Search PeekNook notebooks and sources' });
        if (!q?.trim()) {
            return;
        }
        try {
            const body = await fetchJson(`/api/peeknook/termitpro/search?q=${encodeURIComponent(q.trim())}&limit=10`);
            const hits = body.results || [];
            if (!hits.length) {
                vscode.window.showInformationMessage('No results.');
                return;
            }
            const pick = await vscode.window.showQuickPick(hits.map((h, i) => ({
                label: h.name || h.title || `Result ${i + 1}`,
                description: h.type,
                hit: h,
            })), { placeHolder: 'PeekNook search results' });
            if (pick) {
                vscode.window.showInformationMessage(JSON.stringify(pick.hit, null, 2));
            }
        }
        catch (err) {
            vscode.window.showErrorMessage(String(err));
        }
    }));
    context.subscriptions.push(vscode.commands.registerCommand('peeknook.openNotebooks', () => {
        vscode.env.openExternal(vscode.Uri.parse(`${uiUrl()}/notebooks`));
    }));
}
function deactivate() { }
//# sourceMappingURL=extension.js.map