import * as vscode from 'vscode';

function apiBase(): string {
  return vscode.workspace.getConfiguration('peeknook').get<string>('apiUrl') || 'http://127.0.0.1:5056';
}

function uiUrl(): string {
  return vscode.workspace.getConfiguration('peeknook').get<string>('uiUrl') || 'http://127.0.0.1:5173';
}

async function fetchJson<T>(path: string): Promise<T> {
  const res = await fetch(`${apiBase()}${path}`);
  if (!res.ok) {
    throw new Error(`PeekNook API ${res.status}: ${await res.text()}`);
  }
  return (await res.json()) as T;
}

export function activate(context: vscode.ExtensionContext) {
  context.subscriptions.push(
    vscode.commands.registerCommand('peeknook.status', async () => {
      try {
        const status = await fetchJson<Record<string, unknown>>('/api/peeknook/termitpro/status');
        const msg = [
          `Service: ${status.service}`,
          `Notebooks: ${status.notebook_count}`,
          `Sources: ${status.source_count}`,
        ].join('\n');
        vscode.window.showInformationMessage(msg);
      } catch (err) {
        vscode.window.showErrorMessage(String(err));
      }
    }),
  );

  context.subscriptions.push(
    vscode.commands.registerCommand('peeknook.search', async () => {
      const q = await vscode.window.showInputBox({ prompt: 'Search PeekNook notebooks and sources' });
      if (!q?.trim()) {
        return;
      }
      try {
        const body = await fetchJson<{ results: Array<{ type?: string; name?: string; title?: string }> }>(
          `/api/peeknook/termitpro/search?q=${encodeURIComponent(q.trim())}&limit=10`,
        );
        const hits = body.results || [];
        if (!hits.length) {
          vscode.window.showInformationMessage('No results.');
          return;
        }
        const pick = await vscode.window.showQuickPick(
          hits.map((h, i) => ({
            label: h.name || h.title || `Result ${i + 1}`,
            description: h.type,
            hit: h,
          })),
          { placeHolder: 'PeekNook search results' },
        );
        if (pick) {
          vscode.window.showInformationMessage(JSON.stringify(pick.hit, null, 2));
        }
      } catch (err) {
        vscode.window.showErrorMessage(String(err));
      }
    }),
  );

  context.subscriptions.push(
    vscode.commands.registerCommand('peeknook.openNotebooks', () => {
      vscode.env.openExternal(vscode.Uri.parse(`${uiUrl()}/notebooks`));
    }),
  );
}

export function deactivate() {}
