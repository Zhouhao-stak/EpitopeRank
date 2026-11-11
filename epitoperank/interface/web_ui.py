"""EpitopeRank web UI - Modern AI Scientific Workspace.

Redesigned as an interactive multi-agent analysis platform with:
- 仪表盘 with real-time project status
- AI 流水线 visualization with agent workflow
- Results 探索r with filtering and search
- Independent chart management
- 基因-level exploration

Backend API remains unchanged (FastAPI endpoints in epitoperank/api/app.py).
Frontend uses vanilla JS SPA architecture for zero-build deployment.
"""

from __future__ import annotations

from fastapi.responses import HTMLResponse

_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<link rel="icon" type="image/svg+xml" href="/favicon.ico">
<style>
/* Ocean lab theme: data-dense, calm, and unmistakably scientific. */
:root {
  --black: #06131b;
  --gray-900: #e8f5f4;
  --gray-700: #b0c8cc;
  --gray-500: #76929d;
  --gray-300: #284653;
  --gray-100: #102733;
  --white: #f3fbf8;
  --bg: #07151e;
  --surface: #0c202b;
  --surface-2: #112b36;
  --surface-3: #173944;
  --text: #e8f5f4;
  --text-secondary: #a6c1c5;
  --text-muted: #718e99;
  --accent: #5eead4;
  --secondary: #b7e36a;
  --warning: #f3bd72;
  --danger: #fb7185;
  --border: #244957;
  /* 字体策略：只引用系统已安装字体，不打包、不加载任何字体文件。
     因此项目不携带字体二进制，无需分发 OFL/Apache 字体授权文本；
     Segoe UI / Roboto / Consolas 等为各自平台自带字体，仅按名称引用。
     如需引入 Web 字体，请同步在 NOTICE 中注明授权。 */
  --font-sans: system-ui, ui-sans-serif, -apple-system, "Segoe UI", "Microsoft YaHei", Arial, sans-serif;
  --font-mono: ui-monospace, "SF Mono", Monaco, "Cascadia Code", Consolas, monospace;
  --space-1: 4px; --space-2: 8px; --space-3: 12px; --space-4: 16px;
  --space-5: 24px; --space-6: 32px; --space-7: 48px; --space-8: 64px;
  --shadow-sm: 0 4px 16px rgba(0, 0, 0, .18);
  --shadow: 0 12px 30px rgba(0, 0, 0, .24);
  --shadow-lg: 0 22px 70px rgba(0, 0, 0, .32);
  --radius: 12px;
}

* { box-sizing: border-box; margin: 0; padding: 0; }
html { background: var(--bg); }
body { font-family: var(--font-sans); background: var(--bg); color: var(--text); line-height: 1.6; font-size: 14px; -webkit-font-smoothing: antialiased; }
body::before { content: ""; position: fixed; inset: 0; pointer-events: none; z-index: -1; background: radial-gradient(circle at 82% -8%, rgba(94,234,212,.14), transparent 32%), radial-gradient(circle at 5% 100%, rgba(183,227,106,.08), transparent 28%), linear-gradient(120deg, rgba(255,255,255,.015) 1px, transparent 1px); background-size: auto, auto, 34px 34px; }
.app { display: flex; min-height: 100vh; }
.sidebar { width: 264px; background: rgba(7, 21, 30, .88); border-right: 1px solid var(--border); position: fixed; top: 0; left: 0; bottom: 0; overflow-y: auto; z-index: 100; backdrop-filter: blur(18px); }
.main { margin-left: 264px; flex: 1; min-height: 100vh; background: transparent; }
.topbar { height: 72px; background: rgba(7, 21, 30, .72); border-bottom: 1px solid rgba(36,73,87,.8); display: flex; align-items: center; justify-content: space-between; padding: 0 var(--space-6); position: sticky; top: 0; z-index: 50; backdrop-filter: blur(18px); }
.content { padding: 30px 34px 60px; max-width: 1600px; margin: 0 auto; }

.brand { padding: 28px 22px 24px; border-bottom: 1px solid var(--border); position: relative; }
.brand::before { content: ""; display: block; width: 34px; height: 34px; margin-bottom: 16px; border-radius: var(--radius); background: radial-gradient(circle at 30% 25%, #e7fff8 0 8%, var(--accent) 9% 35%, #157f83 36% 70%, #0b303a 71%); box-shadow: 0 0 0 5px rgba(94,234,212,.08), 0 0 32px rgba(94,234,212,.23); }
.brand-name { font-size: 20px; font-weight: 600; color: var(--white); letter-spacing: -.4px; }
.brand-tagline { font-size: 12px; color: var(--accent); margin-top: 4px; text-transform: uppercase; letter-spacing: 1.7px; font-weight: 600; }
.nav-section { padding: 22px 0 0; }
.nav-label { font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 1.7px; color: var(--text-muted); padding: 0 22px; margin-bottom: 9px; }
.nav-item { display: flex; align-items: center; gap: 11px; padding: 11px 20px; margin: 3px 12px 3px 0; color: var(--text-secondary); cursor: pointer; transition: all .2s ease; font-size: 14px; font-weight: 600; border-left: 1px solid transparent; border-radius: 0 var(--radius) var(--radius) 0; }
.nav-item:hover { background: rgba(94,234,212,.07); color: var(--white); }
.nav-item.active { background: linear-gradient(90deg, rgba(94,234,212,.16), rgba(94,234,212,.04)); color: var(--white); border-left-color: var(--accent); box-shadow: inset 0 0 24px rgba(94,234,212,.04); }

.card, .chart-container, .filters { background: linear-gradient(145deg, rgba(17,43,54,.92), rgba(10,29,39,.92)); border: 1px solid var(--border); border-radius: var(--radius); padding: var(--space-5); box-shadow: var(--shadow-sm); }
.card { transition: border-color .2s ease, transform .2s ease, box-shadow .2s ease; }
.card:hover { border-color: rgba(94,234,212,.48); transform: translateY(-1px); box-shadow: var(--shadow); }
.card-title { font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: .9px; color: var(--text-secondary); }
.grid { display: grid; gap: 18px; }
.grid-2 { grid-template-columns: repeat(2, 1fr); }
.grid-3 { grid-template-columns: repeat(3, 1fr); }
.grid-4 { grid-template-columns: repeat(4, 1fr); }

.status { display: inline-flex; align-items: center; gap: 8px; font-size: 12px; font-weight: 600; padding: 5px 10px; border-radius: 999px; border: 1px solid transparent; }
.status-running { background: rgba(94,234,212,.12); color: var(--accent); border-color: rgba(94,234,212,.22); }
.status-completed { background: rgba(183,227,106,.12); color: var(--secondary); border-color: rgba(183,227,106,.22); }
.status-waiting { background: rgba(118,146,157,.12); color: var(--text-secondary); border-color: rgba(118,146,157,.2); }
.status-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--text-muted); box-shadow: 0 0 0 3px rgba(118,146,157,.12); }
.status-running .status-dot { background: var(--accent); box-shadow: 0 0 0 3px rgba(94,234,212,.12), 0 0 12px var(--accent); }
.status-completed .status-dot { background: var(--secondary); box-shadow: 0 0 0 3px rgba(183,227,106,.12); }

.btn { display: inline-flex; align-items: center; justify-content: center; gap: var(--space-2); padding: 10px 18px; font-size: 13px; font-weight: 600; border-radius: var(--radius); border: 1px solid transparent; cursor: pointer; transition: all .2s ease; font-family: var(--font-sans); }
.btn:focus-visible, input:focus-visible, select:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.btn-primary { background: linear-gradient(135deg, #6af3d9, #34bdb2); color: #062027; border-color: #6af3d9; box-shadow: 0 6px 20px rgba(94,234,212,.18); }
.btn-primary:hover { filter: brightness(1.08); transform: translateY(-1px); box-shadow: 0 9px 25px rgba(94,234,212,.28); }
.btn-secondary { background: rgba(17,43,54,.55); color: var(--text-secondary); border-color: var(--border); }
.btn-secondary:hover { color: var(--white); border-color: var(--accent); background: rgba(94,234,212,.08); }
.btn-sm { padding: 7px 13px; font-size: 12px; }

.neo-tabs { display: flex; gap: 8px; flex-wrap: wrap; margin: 16px 0 12px; }

.neo-result-body { max-height: 58vh; overflow: auto; border: 1px solid var(--border); border-radius: var(--radius); background: rgba(8,25,34,.6); }
.neo-result-body table { font-size: 12px; }
.neo-result-body th { position: sticky; top: 0; z-index: 1; background: #0d2430; white-space: nowrap; }
.neo-result-body td { white-space: nowrap; font-family: var(--font-mono); font-size: 12px; padding: 8px 12px; }
.neo-result-body pre { margin: 0; padding: 16px; font-size: 12px; line-height: 1.6; white-space: pre; color: var(--text-secondary); font-family: var(--font-mono); }
.neo-path { font-family: var(--font-mono); font-size: 12px; color: var(--text-muted); word-break: break-all; margin-top: 10px; }

.table-container { overflow-x: auto; border: 1px solid var(--border); border-radius: var(--radius); }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
thead { background: rgba(94,234,212,.06); }
th { text-align: left; padding: 11px 14px; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: .7px; color: var(--text-secondary); border-bottom: 1px solid var(--border); }
td { padding: 11px 14px; border-bottom: 1px solid rgba(36,73,87,.65); color: var(--text-secondary); }
tr:last-child td { border-bottom: none; }
tr:hover { background: rgba(94,234,212,.045); }

.pipeline { display: flex; flex-direction: column; gap: 12px; }
.pipeline-step { display: flex; align-items: center; gap: var(--space-4); padding: var(--space-4); background: rgba(12,32,43,.78); border: 1px solid var(--border); border-radius: var(--radius); cursor: pointer; transition: all .2s ease; }
.pipeline-step:hover { border-color: var(--accent); transform: translateX(2px); }
.pipeline-step.active { border-color: var(--accent); background: linear-gradient(90deg, rgba(94,234,212,.13), rgba(94,234,212,.03)); }
.pipeline-step.completed { border-color: rgba(183,227,106,.46); }
.step-number { width: 36px; height: 36px; border-radius: var(--radius); background: var(--surface-3); display: flex; align-items: center; justify-content: center; font-size: 14px; font-weight: 600; color: var(--text-secondary); flex-shrink: 0; }
.pipeline-step.active .step-number { background: var(--accent); color: #062027; }
.pipeline-step.completed .step-number { background: rgba(183,227,106,.18); color: var(--secondary); }
.step-info { flex: 1; }
.step-name { font-weight: 600; font-size: 14px; margin-bottom: var(--space-1); }
.step-desc { font-size: 13px; color: var(--text-muted); line-height: 1.5; }

.filters { display: flex; gap: var(--space-4); flex-wrap: wrap; margin-bottom: var(--space-5); }
.filter-group { display: flex; align-items: center; gap: var(--space-2); }
.filter-label { font-size: 12px; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: .5px; }
.checkbox-group { display: flex; gap: var(--space-3); flex-wrap: wrap; }
.checkbox-label { display: flex; align-items: center; gap: var(--space-2); font-size: 13px; cursor: pointer; padding: 4px 8px; border-radius: var(--radius-sm); color: var(--text-secondary); }
.checkbox-label:hover { background: rgba(94,234,212,.08); color: var(--white); }
input[type="checkbox"] { width: 16px; height: 16px; accent-color: var(--accent); cursor: pointer; }
.search-bar { display: flex; gap: var(--space-3); margin-bottom: var(--space-5); }
.search-input, input, select, textarea { flex: 1; padding: 10px 13px; border: 1px solid var(--border); border-radius: var(--radius); font-size: 14px; font-family: var(--font-sans); color: var(--text); background: rgba(8,25,34,.78); }
.search-input::placeholder, input::placeholder, textarea::placeholder { color: var(--text-muted); }
.search-input:focus, input:focus, select:focus, textarea:focus { outline: none; border-color: var(--accent); box-shadow: 0 0 0 3px rgba(94,234,212,.1); }
#upload-modal input, #project-name, #analysis-query { color: var(--text) !important; background: rgba(8,25,34,.9) !important; border-color: var(--border) !important; }
#upload-modal input::placeholder, #project-name::placeholder, #analysis-query::placeholder { color: var(--text-muted) !important; opacity: 1; }
select option { color: var(--text); background: var(--surface); }
input:-webkit-autofill, input:-webkit-autofill:hover, input:-webkit-autofill:focus { -webkit-text-fill-color: var(--text); -webkit-box-shadow: 0 0 0 1000px rgba(8,25,34,.9) inset; transition: background-color 9999s ease-out; }
.chart-container { margin-bottom: var(--space-5); }

.page { display: none; }
.page.active { display: block; animation: pageIn .24s ease-out; }
.hero-chip { padding: 7px 10px; border: 1px solid rgba(94,234,212,.26); border-radius: 999px; color: var(--text-secondary); background: rgba(94,234,212,.07); font-size: 12px; font-weight: 600; white-space: nowrap; }
.model-config-body { display: flex; flex-direction: column; gap: 10px; padding: 0 14px 14px; }
.model-config-body .cfg-row { display: flex; align-items: center; gap: 10px; }
.model-config-body .cfg-row label { flex: none; width: 88px; font-size: 12px; font-weight: 600; color: var(--text-secondary); }
.model-config-body .cfg-row input { flex: 1; padding: 8px 10px; font-size: 13px; }
.model-config-body .cfg-hint, .model-config-body .cfg-msg { font-size: 12px; line-height: 1.6; color: var(--text-muted); }
.model-config-body .cfg-msg.ok { color: var(--secondary); }
.model-config-body .cfg-msg.err { color: var(--danger); }

/* Smart-ingestion review dialog */
#ingest-modal { display: none; position: fixed; inset: 0; z-index: 1200; padding: 24px; background: rgba(3,12,17,.84); backdrop-filter: blur(10px); align-items: center; justify-content: center; }
#ingest-modal.open { display: flex; }
.ingest-panel { width: min(980px, 96vw); max-height: 90vh; display: flex; flex-direction: column; background: linear-gradient(160deg, var(--surface), #091b25); border: 1px solid var(--border); border-radius: var(--radius); box-shadow: var(--shadow-lg); overflow: hidden; }
.ingest-head { display: flex; align-items: flex-start; gap: 12px; padding: 20px 24px 16px; border-bottom: 1px solid var(--border); background: rgba(7,21,30,.72); }
.ingest-head .ingest-title { font-size: 20px; font-weight: 600; color: var(--white); letter-spacing: -.3px; }
.ingest-head .ingest-sub { margin-top: 4px; font-size: 12px; color: var(--text-muted); }
.ingest-close { margin-left: auto; flex: none; width: 32px; height: 32px; border-radius: var(--radius); border: 1px solid var(--border); background: rgba(8,25,34,.7); color: var(--text-secondary); font-size: 16px; line-height: 1; cursor: pointer; }
.ingest-close:hover { color: var(--white); border-color: var(--accent); }
.ingest-body { padding: 18px 24px 22px; overflow-y: auto; display: flex; flex-direction: column; gap: 16px; }
.ingest-trace { display: flex; gap: 8px; flex-wrap: wrap; }
.ingest-step { display: inline-flex; align-items: center; gap: 7px; padding: 6px 10px; border: 1px solid var(--border); border-radius: 999px; background: rgba(8,25,34,.55); font-size: 12px; font-weight: 600; color: var(--text-secondary); }
.ingest-step .dot { width: 7px; height: 7px; border-radius: 50%; background: var(--text-muted); }
.ingest-step.ok .dot { background: var(--secondary); box-shadow: 0 0 8px rgba(183,227,106,.5); }
.ingest-step.warn .dot { background: var(--warning); }
.ingest-step.error .dot { background: var(--danger); }
.ingest-step.running .dot { background: var(--accent); box-shadow: 0 0 8px rgba(94,234,212,.6); }
.ingest-step.skip { opacity: .62; }
.ingest-source { font-size: 12px; color: var(--text-muted); }
.ingest-stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
.ingest-stat { padding: 12px 14px; border: 1px solid var(--border); border-radius: var(--radius); background: rgba(8,25,34,.52); }
.ingest-stat .v { font-size: 20px; font-weight: 600; color: var(--white); line-height: 1.2; }
.ingest-stat .k { font-size: 12px; letter-spacing: .8px; text-transform: uppercase; color: var(--text-muted); margin-top: 3px; }
.ingest-files { font-size: 12px; color: var(--text-muted); line-height: 1.85; }
.ingest-files code { font-family: var(--font-mono); color: var(--text-secondary); background: rgba(94,234,212,.06); padding: 1px 5px; border-radius: var(--radius-sm); }
.ingest-section-title { font-size: 12px; font-weight: 600; letter-spacing: 1.3px; text-transform: uppercase; color: var(--text-muted); margin-bottom: 8px; }
.ingest-map-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 9px 16px; }
.ingest-map-row { display: flex; align-items: center; gap: 9px; }
.ingest-map-row label { flex: none; width: 132px; font-size: 12px; font-weight: 600; color: var(--text-secondary); }
.ingest-map-row select { flex: 1; min-width: 0; padding: 7px 9px; font-size: 12px; border-radius: var(--radius); }
.ingest-map-row select.missing { border-color: rgba(243,189,114,.55); }
.ingest-issues { display: flex; flex-direction: column; gap: 6px; }
.ingest-issue { display: flex; gap: 8px; padding: 8px 10px; border-radius: var(--radius); font-size: 12px; line-height: 1.55; border: 1px solid var(--border); background: rgba(8,25,34,.45); color: var(--text-secondary); }
.ingest-issue .tag { flex: none; font-weight: 600; font-size: 12px; letter-spacing: .6px; padding: 2px 6px; border-radius: var(--radius-sm); height: fit-content; }
.ingest-issue.error { border-color: rgba(251,113,133,.3); }
.ingest-issue.error .tag { background: rgba(251,113,133,.14); color: var(--danger); }
.ingest-issue.warning .tag { background: rgba(243,189,114,.14); color: var(--warning); }
.ingest-issue.info .tag { background: rgba(94,234,212,.12); color: var(--accent); }
.ingest-preview-table { max-height: 260px; overflow: auto; border: 1px solid var(--border); border-radius: var(--radius); }
.ingest-preview-table table { min-width: 620px; }
.ingest-privacy { font-size: 12px; color: var(--text-muted); line-height: 1.6; }
.ingest-footer { display: flex; align-items: center; gap: 12px; padding: 14px 24px; border-top: 1px solid var(--border); background: rgba(7,21,30,.9); }
.ingest-footer .ingest-error { color: var(--danger); font-size: 12px; margin-right: auto; }
@media (max-width: 760px) { .ingest-stats { grid-template-columns: repeat(2, 1fr); } .ingest-map-grid { grid-template-columns: 1fr; } .ingest-map-row label { width: 112px; } }
#stat-samples, #stat-events, #stat-significant { color: var(--white) !important; text-shadow: 0 0 20px rgba(94,234,212,.16); }
#progress-bar { background: linear-gradient(90deg, var(--accent), var(--secondary)) !important; }
#upload-modal { background: rgba(3,12,17,.75) !important; }
#upload-modal > div { background: var(--surface) !important; border-color: var(--border) !important; color: var(--text) !important; }
#event-detail-modal { background: rgba(3,12,17,.78) !important; backdrop-filter: blur(8px); }
#event-detail-modal > div { background: var(--surface) !important; border-color: var(--border) !important; color: var(--text) !important; box-shadow: var(--shadow-lg); }
#event-detail-modal > div > div:first-child { background: linear-gradient(135deg, #0d4d56, #102a39) !important; }
#event-detail-modal [style*="font-size: 28px"] { color: var(--accent) !important; }

/* MCP tool console */
.mcp-panel { margin-top: 22px; padding-top: 18px; border-top: 1px solid var(--border); display: flex; flex-direction: column; gap: 12px; }
.mcp-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
.mcp-title { font-size: 16px; font-weight: 600; color: var(--white); letter-spacing: -.2px; }
.mcp-sub { font-size: 12px; color: var(--text-muted); margin-top: 3px; letter-spacing: .4px; }
.mcp-badge { padding: 4px 9px; border-radius: 999px; font-size: 12px; font-weight: 600; border: 1px solid var(--border); color: var(--text-secondary); background: rgba(8,25,34,.6); white-space: nowrap; }
.mcp-badge.ok { color: var(--secondary); border-color: rgba(183,227,106,.35); background: rgba(183,227,106,.08); }
.mcp-badge.err { color: var(--danger); border-color: rgba(251,113,133,.35); background: rgba(251,113,133,.08); }
.mcp-field { display: flex; flex-direction: column; gap: 6px; }
.mcp-field > label { font-size: 12px; font-weight: 600; letter-spacing: .8px; text-transform: uppercase; color: var(--text-muted); }
.mcp-inline { display: flex; gap: 8px; align-items: center; }
.mcp-inline select { flex: 1; min-width: 0; }
.mcp-panel select, .mcp-panel textarea, .mcp-panel input[type="text"] { width: 100%; padding: 9px 11px; border: 1px solid var(--border); border-radius: var(--radius); background: rgba(8,25,34,.9); color: var(--text); font-family: inherit; font-size: 13px; }
.mcp-panel input[type="text"]::placeholder { color: var(--text-muted); }
.mcp-panel textarea { font-family: var(--font-mono); font-size: 12px; line-height: 1.55; resize: vertical; min-height: 86px; }
.mcp-desc { font-size: 12px; line-height: 1.6; color: var(--text-secondary); min-height: 18px; }
.mcp-hint { font-size: 12px; line-height: 1.5; color: var(--text-muted); word-break: break-all; }
.mcp-actions { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.mcp-result { margin: 0; padding: 12px; max-height: 300px; overflow: auto; border: 1px solid var(--border); border-radius: var(--radius); background: rgba(3,12,17,.75); color: var(--text-secondary); font-family: var(--font-mono); font-size: 12px; line-height: 1.55; white-space: pre-wrap; word-break: break-word; }
.mcp-result.err { color: var(--danger); }

@keyframes pageIn { from { opacity: .25; transform: translateY(4px); } to { opacity: 1; transform: translateY(0); } }
@keyframes fadeIn { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: translateY(0); } }
@media (max-width: 1100px) { .sidebar { width: 236px; } .main { margin-left: 236px; } .grid-4 { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 768px) { .sidebar { display: none; } .main { margin-left: 0; } .grid-2, .grid-3, .grid-4 { grid-template-columns: 1fr; } .content { padding: 20px 16px 40px; } .topbar { padding: 0 16px; } }
.lang-toggle { display: inline-flex; align-items: center; gap: 2px; padding: 3px; background: rgba(8, 25, 34, .06); border: 1px solid var(--border); border-radius: 999px; }
.lang-toggle button { border: 0; background: transparent; color: var(--text-secondary); font-family: inherit; font-size: 12px; font-weight: 600; line-height: 1; padding: 6px 10px; border-radius: 999px; cursor: pointer; transition: background .18s ease, color .18s ease; }
.lang-toggle button:hover { color: var(--text); }
.lang-toggle button.active { background: var(--black); color: var(--white); box-shadow: 0 1px 3px rgba(0,0,0,.18); }
@media (max-width: 520px) { .lang-toggle button { padding: 5px 7px; font-size: 12px; } }

/* Task-oriented peptide workspace. Shared application colors remain authoritative. */
.pep-workspace { max-width:1280px; margin:auto; }
.pep-header { display:flex; align-items:center; justify-content:space-between; gap:24px; margin-bottom:28px; }
.pep-header h2 { font-size:28px; letter-spacing:-.025em; margin-bottom:8px; }
.pep-header p,.pep-help { color:var(--text-secondary); font-size:14px; }
.pep-steps { list-style:none; display:flex; gap:32px; padding:18px 0; margin-bottom:28px; border-block:1px solid var(--border); }
.pep-steps li { display:flex; align-items:center; gap:10px; color:var(--text-secondary); font-size:14px; }
.pep-steps b { color:var(--accent); font-variant-numeric:tabular-nums; }
.pep-layout { display:grid; grid-template-columns:minmax(0,1fr) 330px; gap:32px; align-items:start; }
.pep-inputs { background:var(--surface); border:1px solid var(--border); border-radius:var(--radius); padding:0 28px; }
.pep-section { padding:24px 0; }
.pep-inputs .pep-section + .pep-section { border-top:1px solid var(--border); }
.pep-workspace h3 { font-size:16px; font-weight:600; margin-bottom:10px; }
.pep-options { padding:0 24px; background:var(--surface-2); border-radius:var(--radius); }
.pep-options .btn-primary { width:100%; min-height:46px; }
.pep-guide { border-top:1px solid var(--border); padding:22px 0; }
.pep-guide h3 { font-size:14px; }
.pep-guide p { font-size:13px; color:var(--text-secondary); margin-top:10px; }
#pep-sequences { min-height:220px; padding:16px !important; background:var(--bg) !important; }
#page-peptide input,#page-peptide select { min-height:42px; }
#page-peptide input[type=checkbox] { width:16px; height:16px; flex:0 0 16px; min-height:auto; accent-color:var(--accent); }
#page-peptide select option { background:var(--surface); color:var(--text); }
.pep-output { margin-top:32px; padding:24px 0; border-block:1px solid var(--border); min-width:0; }
#pep-results { overflow-x:auto; }
#pep-results:empty::before { content:'完成序列与 HLA 设置后，点击「预测并排序」。结果将在这里显示。'; display:block; padding:26px 0; color:var(--text-secondary); font-size:14px; }
.pep-project { margin-top:24px; padding:20px 24px; background:var(--surface); border-radius:var(--radius); border:1px solid var(--border); }
.pep-project summary { cursor:pointer; font-weight:600; }
.pep-project[open] summary { margin-bottom:16px; }
:focus-visible { outline:2px solid var(--accent); outline-offset:4px; }
.btn:disabled { cursor:not-allowed; opacity:.55; }
@media(max-width:1100px) { .pep-layout { grid-template-columns:1fr; } .pep-header { align-items:flex-start; } }
@media(max-width:600px) { .pep-header { flex-direction:column; } .pep-header h2 { font-size:28px; } .pep-steps { gap:12px; flex-wrap:wrap; } .pep-steps li { font-size:12px; } .pep-inputs { padding:0 16px; } }
@media(prefers-reduced-motion:reduce) { *,*::before,*::after { scroll-behavior:auto !important; transition:none !important; animation:none !important; } }

/* EpitopeRank research workspace: daylight surfaces, restrained teal, readable evidence. */
:root { --black:#172f39; --gray-900:#172f39; --gray-700:#445b65; --gray-500:#60737c; --gray-300:#d6e0e3; --gray-100:#f0f4f5; --white:#fff; --bg:#f5f7f8; --surface:#fff; --surface-2:#edf4f3; --surface-3:#e3efec; --text:#172f39; --text-secondary:#455f69; --text-muted:#60737c; --accent:#087e72; --secondary:#367344; --warning:#986015; --danger:#b33449; --border:#d9e3e6; --shadow-sm:none; --shadow:none; --shadow-lg:0 20px 60px #162f3920; --radius:12px; }
body { font-size:14px; } body::before { display:none; }
::selection { background:#c4e9e1; color:#173c36; }
* { scrollbar-width:thin; scrollbar-color:#b7c8cd transparent; }
.sidebar { width:232px; background:#142e38; backdrop-filter:none; border:0; padding-bottom:24px; }
.brand { padding:30px 24px; border-color:#ffffff16; }
.brand::before { display:none; }.brand-name { color:#f6fbfa; font-size:20px; letter-spacing:-.7px; }.brand-tagline { color:#a8c4ca; font-size:12px; letter-spacing:1px; margin-top:8px; }
.nav-section { padding-top:24px; }.nav-label { color:#90aeb7; font-size:12px; letter-spacing:.6px; padding-inline:24px; }
.nav-item { width:calc(100% - 24px); margin:4px 12px; padding:12px; color:#c4d5db; border:0; border-radius:var(--radius-sm); background:transparent; text-align:left; font:400 14px var(--font-sans); }
.nav-item::before { display:none !important; }.nav-item svg { width:19px; height:19px; fill:none; stroke:currentColor; stroke-width:1.6; stroke-linecap:round; stroke-linejoin:round; flex-shrink:0; }
.nav-item:hover { background:#ffffff0c; color:#fff; }.nav-item.active { background:#284b53; box-shadow:none; color:#a5f0dc; }
.main { margin-left:232px; min-width:0; }.topbar { height:74px; background:#ffffffed; border-bottom:1px solid var(--border); padding:0 36px; backdrop-filter:none; gap:16px; }
#current-project { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.content { padding:32px 36px 64px; max-width:1560px; }.content:focus { outline:none; }
.workspace-heading { display:flex; justify-content:space-between; align-items:center; gap:20px; margin-bottom:28px; }.workspace-heading h1,.pep-header h2 { font-size:28px; letter-spacing:-.7px; font-weight:600; line-height:1.3; }.workspace-heading p { margin-top:9px; color:var(--text-secondary); max-width:74ch; font-size:14px; }
.workspace-tag { border:1px solid var(--border); border-radius:var(--radius-sm); padding:6px 11px; color:var(--text-secondary); white-space:nowrap; font-size:12px; background:#fff; }
.start-guide { display:grid; grid-template-columns:1.3fr 1fr; gap:40px; background:#eaf3f0; padding:30px; border-radius:var(--radius); margin-bottom:28px; }.start-guide h2 { font-size:20px; font-weight:600; }.start-guide p { margin:10px 0 22px; color:var(--text-secondary); max-width:52ch; }.start-guide .btn { margin:0 8px 8px 0; }.start-guide ol { list-style:none; display:grid; gap:16px; }.start-guide li { display:flex; gap:16px; font-size:12px; color:var(--text-secondary); }.start-guide li b { font-size:13px; color:var(--accent); padding-top:2px; font-variant-numeric:tabular-nums; }.start-guide strong { display:block; font-size:14px; color:var(--text); margin-bottom:3px; }
.card,.chart-container,.filters { background:var(--surface); box-shadow:none; border:1px solid var(--border); padding:24px; }.card:hover { transform:none; box-shadow:none; border-color:var(--border); }
.card-title { text-transform:none; letter-spacing:0; font-size:14px; }.grid { gap:24px; }.grid > * { min-width:0; }
#page-dashboard > .grid-4 { gap:0; background:#fff; border:1px solid var(--border); border-radius:var(--radius); overflow:hidden; }#page-dashboard > .grid-4 > .card { border:0; border-right:1px solid var(--border); border-radius:0; }#page-dashboard > .grid-4 > .card:last-child { border-right:0; }
.btn { border-radius:var(--radius-sm); font-weight:600; min-height:40px; transition:background .15s,border-color .15s; }.btn-sm { min-height:34px; }.btn-primary { background:var(--accent); color:#fff; border-color:var(--accent); box-shadow:none; }.btn-primary:hover { background:#09685f; color:#fff; box-shadow:none; transform:none; filter:none; }.btn-secondary { background:#fff; color:var(--text); border-color:#cbd8dc; }.btn-secondary:hover { background:#edf5f2; color:#12675c; border-color:#8bb9ae; }.btn-danger { background:#fff3f4; border-color:#e8b5be; }.btn:disabled { opacity:.5; cursor:not-allowed; transform:none; }
input,select,textarea,.search-input { background:#fff; color:var(--text); min-width:0; border-color:#c6d5da; border-radius:var(--radius-sm); caret-color:var(--accent); }
input[type=checkbox] { flex:0 0 16px; }.checkbox-label:hover { color:var(--text); background:#eef5f3; }input::placeholder,textarea::placeholder { color:#677b84; }
#upload-modal input,#project-name,#analysis-query { background:#fff !important; }.search-input:focus,input:focus,select:focus,textarea:focus { box-shadow:0 0 0 3px #087e7214; }
:focus-visible { outline:2px solid var(--accent); outline-offset:3px; }.sidebar :focus-visible { outline-color:#a5f0dc; }
.lang-toggle { background:#f5f7f8; border-color:var(--border); border-radius:var(--radius-sm); }.lang-toggle button { color:var(--text-secondary); white-space:nowrap; }.lang-toggle button.active { color:var(--accent); background:#dfeee9; border-radius:var(--radius-sm); }
.status { font-weight:600; }.status-dot { box-shadow:none !important; }.status-running { background:#e5f4ef; border-color:#bddfd4; }.status-completed { background:#eef5e9; border-color:#ccdfbf; }
.pipeline-step { background:#fff; border-color:var(--border); padding:20px; cursor:default; }.pipeline-step:hover { transform:none; border-color:var(--border); }.pipeline-step.active { background:#eff8f5; border-color:#80bbaa; }.pipeline-step.active .step-number { color:#fff; }.step-number { border-radius:50%; font-variant-numeric:tabular-nums; }#progress-bar { background:var(--accent) !important; box-shadow:none !important; }
#page-pipeline > .card:last-child { padding:28px; }.pipeline { gap:0; }.pipeline-step { border:0; border-radius:0; border-bottom:1px solid var(--border); }.pipeline-step:last-child { border-bottom:0; }
#page-explorer .filters { border:0; border-radius:0; padding:0; box-shadow:none; gap:22px; }.filter-group { align-items:flex-start; flex-direction:column; }.filter-label { font-size:12px; }.table-container { background:white; }table { font-variant-numeric:tabular-nums; }th { background:#eff4f5; letter-spacing:0; font-size:12px; padding:13px 16px; }td { border-bottom:1px solid #e8eef0; padding:14px 16px; }tr:hover { background:#f5faf8; }
#page-visualization > .grid { grid-template-columns:320px minmax(0,1fr); }#page-visualization .card { padding:20px; }#page-visualization .card .btn { border-color:#bfdcff26; border-radius:var(--radius-sm); background:#162d42; color:#eaf4ff; }#page-visualization .card .btn:hover { background:#23465a; border-color:#82eed866; color:#f1fffb; }#chart-display { min-height:560px !important; display:flex; flex-direction:column; justify-content:center; }#chart-display img { max-width:100%; height:auto; }
#page-gene .search-bar { max-width:800px; }#page-gene > div:nth-of-type(2) { border-left:0 !important; }#page-gene #gene-details .card { min-height:300px; display:grid; align-content:center; }
#page-report > .card { padding:32px; }#report-output { background:#f7f9fa; border-radius:var(--radius); border:1px dashed #c6d5da; min-height:240px; display:grid; align-content:center; }#page-report .card > div:last-child { border-left:0 !important; }
#page-settings > .grid { grid-template-columns:minmax(300px,.8fr) minmax(0,1.2fr); align-items:start; }.cfg-row { flex-wrap:wrap; gap:10px; margin-bottom:16px; }.cfg-row label { color:var(--text-secondary); }.mcp-panel { background:transparent; border:0; padding:0; }.mcp-result { background:#f3f6f7; color:var(--text); border-color:var(--border); }.mcp-badge { color:var(--text-secondary); background:#edf3f3; }
#page-neoantigen > .card:first-of-type { max-width:none !important; padding:28px !important; }#page-neoantigen > .card:first-of-type > h2 { display:none; }#page-neoantigen > .card:first-of-type > div[style*='padding:16px'] { border:0 !important; border-top:1px solid var(--border) !important; border-radius:0 !important; padding:24px 0 !important; }#page-neoantigen p { color:var(--text-secondary); max-width:85ch; }#page-neoantigen details { padding:22px; background:#f2f6f7; border-radius:var(--radius); }#page-neoantigen details h3 { margin:24px 0 8px; font-size:16px; }.neo-result-body,.neo-result-body th { background:#f6f9fa; }#neo-result-title { color:var(--text) !important; }
.pep-options { background:#eaf3f0; }.pep-header { margin-bottom:28px; }.pep-section { padding:26px 0; }.pep-steps { margin-bottom:24px; }.pep-output { background:#fff; padding:24px; border:1px solid var(--border); border-radius:var(--radius); }#pep-results:empty::before { color:var(--text-secondary); }#pep-sequences { background:#f8fafb !important; }
#upload-modal { background:#112b3866 !important; backdrop-filter:blur(3px); }#upload-modal > div { box-shadow:var(--shadow-lg); border:0 !important; }#drop-zone { background:#f3f8f6 !important; }#ingest-modal { background:#112b3866; }.ingest-panel { background:#fff; }.ingest-head,.ingest-footer { background:#f7f9fa; }
.mobile-menu { display:none; }.skip-link { position:fixed; left:250px; top:-70px; z-index:2000; padding:12px; background:white; color:var(--accent); }.skip-link:focus { top:12px; }
@media(min-width:1600px) { .content { padding-top:40px; } }
@media(max-width:1100px) { .sidebar { width:216px; }.main { margin-left:216px; }.content { padding:26px 24px 48px; }.topbar { padding:0 24px; }.start-guide { grid-template-columns:1fr; gap:24px; }.start-guide ol { grid-template-columns:repeat(3,1fr); }.start-guide li { gap:10px; }#page-visualization > .grid { grid-template-columns:260px minmax(0,1fr); }#page-settings > .grid { grid-template-columns:1fr; } }
@media(max-width:768px) { .mobile-menu { display:inline-flex; }.sidebar { display:none; width:232px; top:74px; box-shadow:12px 0 35px #142e3833; }.navigation-open .sidebar { display:block; }.main { margin-left:0; }.topbar { gap:10px; padding:12px 16px; height:auto; min-height:74px; flex-wrap:wrap; }.topbar > div:last-child { gap:8px !important; flex-wrap:wrap; }.topbar #current-project { flex:1; }.content { padding:24px 16px 48px; }.workspace-heading { align-items:flex-start; }.workspace-heading h1,.pep-header h2 { font-size:28px; }.workspace-tag { display:none; }.start-guide { padding:24px; }.start-guide ol { grid-template-columns:1fr; }.grid-2,.grid-3,.grid-4,#page-visualization > .grid { grid-template-columns:1fr; }#page-dashboard > .grid-4 { grid-template-columns:repeat(2,1fr); }#page-dashboard > .grid-4 > .card { padding:18px; border-bottom:1px solid var(--border); }#chart-display { position:static !important; min-height:320px !important; }.search-bar { flex-wrap:wrap; }.search-bar input { flex-basis:100%; }.pipeline-step { padding:18px 0; flex-wrap:wrap; }.step-info { min-width:150px; }.card { padding:20px; }#page-report > .card { padding:20px; }#page-report .card > div:first-child { flex-wrap:wrap; gap:20px; }#page-report .card > div:first-child > div:last-child { flex-wrap:wrap; }.mcp-inline { flex-wrap:wrap; }.cfg-row { display:flex; flex-direction:column; align-items:stretch; }.cfg-row label { width:auto; }#neo-mapping-fields { grid-template-columns:1fr !important; }.skip-link { left:16px; }.pep-header { gap:18px; } }
@media(prefers-reduced-motion:reduce) { *,*::before,*::after { animation:none !important; transition:none !important; scroll-behavior:auto !important; } }

#stat-samples,#stat-events,#stat-significant { color:var(--text) !important; text-shadow:none; }
.mcp-title,.ingest-head .ingest-title,.ingest-stat .v { color:var(--text); }
.mcp-panel { margin-top:0; }.mcp-panel select,.mcp-panel textarea,.mcp-panel input[type="text"] { background:#fff; }
.ingest-close,.ingest-step,.ingest-stat,.ingest-issue { background:#f1f6f5; }.ingest-close:hover { color:var(--accent); }
#event-detail-modal > div > div:first-child { background:#edf5f3 !important; }
@media(max-width:768px) { .sidebar { top:110px; }.ingest-footer { flex-wrap:wrap; } }

.mobile-chart-select { display:none; }
#page-visualization > .grid > div:first-child { max-height:560px; overflow-y:auto; padding-right:8px; }
#page-explorer .table-container table { min-width:650px; }
#page-explorer .table-container th { white-space:nowrap; }
@media(max-width:768px) {
 .mobile-chart-select { display:flex; flex-direction:column; gap:8px; margin-bottom:20px; }
 #page-visualization > .grid > div:first-child { display:none; }
 .model-config-body { padding:0; }
 .model-config-body .cfg-row { align-items:stretch; }
 .model-config-body .cfg-row label { width:auto; }
 .model-config-body .cfg-row input { width:100%; }
}

@media(max-width:768px) {
 #events-table td[colspan] { text-align:left !important; padding:32px 16px !important; }
 #events-table td[colspan] > div { width:calc(100vw - 68px); text-align:center; white-space:normal; }
}

/* Fluid interaction layer: bounded effects, no ambient animation loop. */
:root { --motion-ease:cubic-bezier(.16,1,.3,1); }
.page.active { animation:none; }
.topbar { background:rgba(255,255,255,.87); backdrop-filter:blur(16px); }
.start-guide { position:relative; isolation:isolate; overflow:hidden; background:#e6f2ec; border:1px solid #d1e7df; }
.start-guide::before { content:''; position:absolute; z-index:-1; width:460px; height:460px; left:var(--light-x,65%); top:var(--light-y,30%); transform:translate(-50%,-50%); border-radius:50%; background:radial-gradient(ellipse at 40% 35%,#ffffffcf, #b9e7d788 44%, #a3d6e222 67%,transparent 72%); pointer-events:none; transition:border-radius .6s var(--motion-ease); }
.start-guide:hover::before { border-radius:50%; }
.start-guide::after { content:''; position:absolute; z-index:-1; right:-60px; bottom:-120px; width:360px; height:300px; border:1px solid #9bcab766; border-radius:50%; transform:rotate(-28deg); pointer-events:none; }
.start-guide ol { background:#ffffff70; border:1px solid #ffffffa8; border-radius:var(--radius); padding:20px 24px; backdrop-filter:blur(8px); }
.sidebar { isolation:isolate; }
.nav-item { position:relative; z-index:1; transition:color .18s,background .18s; }
.nav-item.active { background:transparent; }
.nav-fluid-marker { position:absolute; left:12px; top:0; width:calc(100% - 24px); height:46px; border-radius:var(--radius); background:linear-gradient(115deg,#365e66,#244a53); border:1px solid #7ea7ab45; box-shadow:0 5px 14px #071d2426; pointer-events:none; z-index:0; transition:transform .42s var(--motion-ease),height .25s var(--motion-ease),border-radius .3s; }
.nav-fluid-marker::after { content:''; position:absolute; inset:0; border-radius:inherit; background:linear-gradient(110deg,#a8eee512,transparent 65%); }
.nav-item:hover svg { transform:translateX(2px); }.nav-item svg { transition:transform .2s var(--motion-ease); }
.btn { position:relative; isolation:isolate; overflow:hidden; transition:background .18s,border-color .18s,box-shadow .18s,transform .18s var(--motion-ease); }
.btn:active:not(:disabled) { transform:scale(.975); }
.btn-primary:hover { box-shadow:0 5px 14px #087e7226; }
.press-wave { position:absolute; pointer-events:none; width:160px; height:160px; border-radius:50%; background:currentColor; opacity:.12; transform:translate(-50%,-50%) scale(0); animation:pressWave .48s var(--motion-ease) forwards; z-index:-1; }
@keyframes pressWave { to { transform:translate(-50%,-50%) scale(2); opacity:0; } }
#page-visualization .card .btn[aria-pressed=true] { background:#214c50; border-color:#82eed8; color:#effff9; }
#page-visualization .card .btn:focus-visible { outline:2px solid #82eed8; outline-offset:3px; }
#chart-display { transition:border-color .2s; }
details[open] > :not(summary) { animation:detailReveal .22s var(--motion-ease); }
@keyframes detailReveal { from { opacity:.4; transform:translateY(-3px); } to { opacity:1; transform:translateY(0); } }
.quick-switch { padding-inline:12px; gap:10px; }.quick-switch kbd { border:1px solid var(--border); border-radius:var(--radius-sm); padding:1px 4px; font:10px var(--font-sans); color:var(--text-secondary); }
.quick-dialog { border:1px solid #dce8e5; border-radius:var(--radius); padding:0; width:min(540px,calc(100vw - 32px)); max-height:80vh; margin:12vh auto auto; color:var(--text); background:#ffffffed; box-shadow:0 24px 80px #142e3838; backdrop-filter:blur(18px); }
.quick-dialog::backdrop { background:#102e3d66; backdrop-filter:blur(5px); }
.quick-dialog[open] { animation:quickOpen .24s var(--motion-ease); }
@keyframes quickOpen { from { opacity:0; transform:translateY(-10px) scale(.98); } to { opacity:1; transform:none; } }
.quick-head { display:flex; gap:16px; align-items:center; justify-content:space-between; padding:20px 22px 8px; }.quick-head h2 { font-size:16px; }.quick-search { padding:12px 22px; }.quick-search input { width:100%; background:#f1f6f5; }.quick-results { display:grid; gap:4px; padding:0 12px 16px; overflow:auto; max-height:48vh; }.quick-result { text-align:left; padding:12px 14px; border:0; border-radius:var(--radius); background:transparent; font:14px var(--font-sans); color:var(--text); cursor:pointer; }.quick-result:hover,.quick-result:focus-visible { background:#e5f2ec; }.quick-result[aria-current=page] { color:var(--accent); background:#f0f7f4; }.quick-result[hidden] { display:none; }.quick-empty { padding:20px 14px; color:var(--text-secondary); font-size:13px; }
.nav-scrim { display:none; }
body.motion-paused *,body.motion-paused *::before,body.motion-paused *::after { animation:none !important; transition:none !important; scroll-behavior:auto !important; }
body.motion-paused .start-guide::before { left:65% !important; top:30% !important; }
@media(max-width:1100px) { .quick-switch kbd { display:none; }.topbar { flex-wrap:wrap; height:auto; min-height:74px; padding-block:12px; } }
@media(max-width:768px) {
 .start-guide ol { padding:18px; }.start-guide { gap:18px; }
 .sidebar { display:block; top:0; width:min(280px,85vw); z-index:120; transform:translateX(-105%); visibility:hidden; transition:transform .32s var(--motion-ease),visibility .32s; }
 .navigation-open .sidebar { visibility:visible; transform:translateX(0); }
 .nav-scrim { display:block; position:fixed; inset:0; z-index:110; border:0; background:#102e3d70; opacity:0; visibility:hidden; transition:opacity .25s,visibility .25s; }
 .navigation-open .nav-scrim { opacity:1; visibility:visible; }
 .quick-switch kbd { display:none; }.quick-dialog { margin-top:8vh; }
}
@media(prefers-reduced-motion:reduce) { *,*::before,*::after { animation:none !important; transition:none !important; scroll-behavior:auto !important; } .start-guide::before { left:65% !important; top:30% !important; } }
.drawer-close { display:none; }
@media(max-width:768px) { body.navigation-open { overflow:hidden; } }
@media(max-width:768px) { .drawer-close { display:flex; margin:16px 12px 0 auto; } }

/* ---- Unified in-app notifications: replaces every native alert/confirm ---- */
#toast-stack { position:fixed; top:86px; right:24px; z-index:3000; display:flex; flex-direction:column; gap:10px; width:min(382px, calc(100vw - 32px)); pointer-events:none; }
.app-toast { pointer-events:auto; position:relative; display:flex; gap:12px; align-items:flex-start; padding:14px 12px 14px 16px; background:#fff; border:1px solid var(--border); border-left:1px solid var(--accent); border-radius:var(--radius); box-shadow:0 14px 38px #142e3826; animation:toastIn .26s cubic-bezier(.16,1,.3,1); overflow:hidden; }
.app-toast.leaving { animation:toastOut .22s ease forwards; }
.app-toast-icon { flex:none; width:24px; height:24px; border-radius:50%; display:grid; place-items:center; color:#fff; background:var(--accent); margin-top:1px; }
.app-toast-icon svg { width:14px; height:14px; }
.app-toast-body { flex:1; min-width:0; }
.app-toast-title { font-size:13px; font-weight:600; color:var(--text); line-height:1.45; }
.app-toast-msg { font-size:13px; color:var(--text-secondary); line-height:1.6; margin-top:3px; white-space:pre-line; word-break:break-word; }
.app-toast-close { flex:none; width:22px; height:22px; border:0; border-radius:var(--radius-sm); background:transparent; color:var(--text-muted); font-size:14px; line-height:1; cursor:pointer; display:grid; place-items:center; }
.app-toast-close:hover { color:var(--text); background:#eef5f3; }
.app-toast::after { content:''; position:absolute; left:0; bottom:0; height:2px; width:100%; background:currentColor; opacity:.18; transform-origin:left; animation:toastLife var(--toast-life,5.2s) linear forwards; }
.app-toast.paused::after { animation-play-state:paused; }
.app-toast.success { border-left-color:var(--secondary); color:var(--secondary); }
.app-toast.success .app-toast-icon { background:var(--secondary); }
.app-toast.error { border-left-color:var(--danger); color:var(--danger); }
.app-toast.error .app-toast-icon { background:var(--danger); }
.app-toast.warning { border-left-color:var(--warning); color:var(--warning); }
.app-toast.warning .app-toast-icon { background:var(--warning); }
@keyframes toastIn { from { opacity:0; transform:translateY(-10px) scale(.985); } to { opacity:1; transform:none; } }
@keyframes toastOut { to { opacity:0; transform:translateX(14px); } }
@keyframes toastLife { from { transform:scaleX(1); } to { transform:scaleX(0); } }

.app-dialog { border:1px solid var(--border); border-radius:var(--radius); padding:0; width:min(524px, calc(100vw - 32px)); margin:auto; color:var(--text); background:#fff; box-shadow:0 26px 90px #142e3840; overflow:hidden; }
.app-dialog::backdrop { background:#102e3d5c; backdrop-filter:blur(5px); }
.app-dialog[open] { animation:appDialogIn .26s cubic-bezier(.16,1,.3,1); }
@keyframes appDialogIn { from { opacity:0; transform:translateY(12px) scale(.975); } to { opacity:1; transform:none; } }
.app-dialog-head { display:flex; gap:14px; align-items:flex-start; padding:24px 24px 0; }
.app-dialog-mark { flex:none; width:42px; height:42px; border-radius:var(--radius); display:grid; place-items:center; background:#e8f2ef; color:var(--accent); }
.app-dialog-mark svg { width:20px; height:20px; }
.app-dialog.success .app-dialog-mark { background:#eaf3e6; color:#367344; }
.app-dialog.error .app-dialog-mark { background:#fdeff1; color:var(--danger); }
.app-dialog.warning .app-dialog-mark { background:#fbf2e4; color:#986015; }
.app-dialog-titles { flex:1; min-width:0; padding-top:2px; }
.app-dialog-title { font-size:16px; font-weight:600; letter-spacing:-.2px; color:var(--text); }
.app-dialog-sub { font-size:12px; color:var(--text-muted); margin-top:4px; letter-spacing:.3px; }
.app-dialog-close { flex:none; width:30px; height:30px; border-radius:var(--radius); border:1px solid var(--border); background:#f7f9fa; color:var(--text-muted); font-size:16px; line-height:1; cursor:pointer; display:grid; place-items:center; }
.app-dialog-close:hover { color:var(--text); border-color:#b9cdd2; background:#eef5f3; }
.app-dialog-body { padding:16px 24px 4px; font-size:14px; line-height:1.72; color:var(--text-secondary); white-space:pre-line; word-break:break-word; }
.app-dialog-body strong { color:var(--text); font-weight:600; }
.app-dialog-detail { margin-top:14px; padding:12px 14px; border:1px solid var(--border); border-radius:var(--radius); background:#f6f9fa; font-family:var(--font-mono); font-size:12px; line-height:1.6; color:var(--text-secondary); max-height:150px; overflow:auto; white-space:pre-wrap; }
.app-dialog-list { margin:14px 0 0; padding:0; list-style:none; display:flex; flex-direction:column; gap:7px; }
.app-dialog-list li { position:relative; padding-left:18px; font-size:13px; color:var(--text-secondary); }
.app-dialog-list li::before { content:''; position:absolute; left:4px; top:9px; width:5px; height:5px; border-radius:50%; background:#9fb6bd; }
.app-dialog-foot { display:flex; align-items:center; justify-content:flex-end; gap:10px; padding:18px 24px 22px; flex-wrap:wrap; }
.app-dialog-foot .btn { min-height:38px; }
.app-dialog-foot .btn-danger { background:var(--danger); color:#fff; border-color:var(--danger); }
.app-dialog-foot .btn-danger:hover { background:#9c2c3e; border-color:#9c2c3e; color:#fff; }
@media(max-width:768px) { #toast-stack { top:14px; right:14px; left:14px; width:auto; } .app-dialog-foot { flex-direction:column-reverse; align-items:stretch; } }

/* Presentation glass: a luminous showcase above a daylight research workspace. */
body { background:radial-gradient(ellipse at 90% 0%,#cce7e5,transparent 45%),#f0f4f5; }
.sidebar { background:linear-gradient(165deg,#102e38,#071a26); box-shadow:10px 0 40px #143b4410; }
.topbar { background:#ffffffb3; backdrop-filter:blur(24px) saturate(150%); }
.workspace-heading h1 { font-size:28px; letter-spacing:-.03em; }
.start-guide { min-height:360px; padding:44px; gap:36px; align-items:center; background:linear-gradient(125deg,#102c3d,#123e49 65%,#19574f); border:0; box-shadow:0 22px 44px #163c4426; color:#f1fffc; }
.start-guide h2 { font-size:var(--fs-xl); line-height:1.24; letter-spacing:-.03em; max-width:13em; font-weight:600; }
.start-guide p { color:#c4dedf; font-size:14px; line-height:1.85; }
.start-guide::before { width:650px; height:650px; background:radial-gradient(ellipse,#5fe6cc35,transparent 65%); }
.start-guide::after { display:none; }
.start-guide > div,.start-guide ol { position:relative; z-index:1; }
.start-guide ol { background:linear-gradient(135deg,#ffffff20,#ffffff07); border:1px solid #ffffff30; box-shadow:0 16px 38px #00151f35,inset 0 1px #ffffff25; backdrop-filter:blur(18px); padding:28px; gap:26px; }
.start-guide li { color:#c1d9dc; }.start-guide strong { color:#f0fffc; font-size:14px; }.start-guide li b { color:#7ce9ce; }
.start-guide .btn-primary { background:#9af2d7; border-color:transparent; color:#10392f; }
.start-guide .btn-primary:hover { background:#c4ffe9; box-shadow:0 8px 22px #001b2655; }
.start-guide .btn-secondary { background:#ffffff0d; color:#e1f8f3; border-color:#ffffff40; backdrop-filter:blur(10px); }
.start-guide .btn-secondary:hover { background:#ffffff22; }
.splice-art { position:absolute; inset:0; width:100%; height:100%; pointer-events:none; opacity:.45; }
.splice-art path { fill:none; stroke:#7de9d0; stroke-width:1; }
.splice-art .signal { stroke:#dcfff5; stroke-width:2; stroke-dasharray:12 700; animation:spliceFlow 8s linear infinite; }
@keyframes spliceFlow { to { stroke-dashoffset:-1424; } }
.card { background:#ffffffda; }
.btn:hover { transform:translateY(-2px); }.btn:active { transform:translateY(1px) scale(.98); }
.btn[aria-busy="true"] { cursor:progress; padding-right:36px; }
.btn[aria-busy="true"]::after { content:''; position:absolute; right:12px; top:calc(50% - 6px); width:12px; height:12px; border:2px solid currentColor; border-right-color:transparent; border-radius:50%; animation:requestSpin .7s linear infinite; }
@keyframes requestSpin { to { transform:rotate(360deg); } }
#request-indicator { position:fixed; top:0; left:0; right:0; height:3px; z-index:4000; overflow:hidden; pointer-events:none; background:#69cdbd33; }
#request-indicator[hidden] { display:none; }
#request-indicator::after { content:''; display:block; width:35%; height:100%; background:#087e72; animation:requestSweep 1.2s ease-in-out infinite alternate; }
@keyframes requestSweep { to { transform:translateX(190%); } }
@media(max-width:1000px) { .start-guide { padding:30px; grid-template-columns:1fr; }.start-guide h2 { max-width:20em; } }
@media(max-width:768px) { .start-guide { padding:26px 22px; gap:24px; }.start-guide ol { padding:22px; }.workspace-heading h1 { font-size:28px; } }
@media(prefers-reduced-motion:reduce) { .splice-art .signal,#request-indicator::after,.btn[aria-busy="true"]::after { animation:none; } }


/* P0 presentation normalization */
:root { --fs-xs:12px; --fs-sm:13px; --fs-base:14px; --fs-md:16px; --fs-lg:20px; --fs-xl:28px; --fs-display:36px; --radius-sm:6px; --radius:10px; --radius-pill:999px; }
body { font-size:var(--fs-base); }
strong,b { font-weight:600; }
table { font-variant-numeric:tabular-nums; font-feature-settings:"tnum" 1; }
th { padding:9px 12px; font-size:var(--fs-xs); }
td { padding:7px 12px; font-size:var(--fs-sm); }
th.num,td.num { text-align:right; }
td.mono { font-family:var(--font-mono); font-size:var(--fs-xs); color:var(--text-muted); }
.dpsi-cell { display:flex; align-items:center; justify-content:flex-end; gap:8px; }
.dpsi-value.up { color:var(--danger); }.dpsi-value.down { color:var(--secondary); }
.dpsi-bar { position:relative; flex:none; width:44px; height:4px; background:#e6eef0; border-radius:999px; }
.dpsi-bar::after { content:''; position:absolute; left:50%; top:-2px; bottom:-2px; width:1px; background:#c3d5da; }
.dpsi-bar > span { position:absolute; top:0; bottom:0; }
.dpsi-bar > .up { left:50%; background:var(--danger); border-radius:0 999px 999px 0; }
.dpsi-bar > .down { right:50%; background:var(--secondary); border-radius:999px 0 0 999px; }
#events-table .event-row { cursor:pointer; }#events-table .event-row:hover { background:#f1f8f5; }
#events-table .event-row:focus-visible { outline:2px solid var(--accent); outline-offset:-2px; }
.row-go { display:inline-flex; opacity:0; transform:translateX(-4px); transition:opacity .15s,transform .15s; color:var(--accent); }
.event-row:hover .row-go,.event-row:focus-visible .row-go { opacity:1; transform:none; }
.start-guide { min-height:0; padding:18px 28px; gap:24px; align-items:center; }
.start-guide h2 { font-size:var(--fs-xl); line-height:1.32; letter-spacing:-.025em; max-width:20em; }
.start-guide p { font-size:var(--fs-sm); line-height:1.65; margin:8px 0 14px; }
.start-guide ol { padding:12px 18px; gap:8px; }.start-guide li { line-height:1.4; }.start-guide strong { font-size:var(--fs-base); }
.start-guide::before { width:380px; height:380px; opacity:.55; }.start-guide .splice-art { opacity:.26; }.start-guide .btn { min-height:36px; }
.sk { display:block; height:9px; border-radius:999px; background:linear-gradient(105deg,#e9f1f2 28%,#f7fbfb 46%,#e9f1f2 64%); background-size:220% 100%; animation:skSweep 1.1s linear infinite; }
@keyframes skSweep { from { background-position:120% 0; } to { background-position:-120% 0; } }
.skeleton-row td { padding:10px 12px; }
@media(prefers-reduced-motion:reduce) { .sk { animation:none; } }

/* Visualization: keep the sidebar compact and show a whole chart on one screen. */
#page-visualization > .grid { align-items:start; }
#page-visualization > .grid > div:first-child {
  align-self:start; position:sticky; top:88px;
  max-height:min(62vh, 520px); overflow-y:auto; padding-right:8px;
}
#page-visualization > .grid > div:first-child > .card { margin-bottom:14px; }
#page-visualization .card .btn { padding:10px 14px; }
#chart-display { min-height:0 !important; justify-content:flex-start !important; }
#chart-display img {
  display:block; width:auto; max-width:100%; height:auto;
  max-height:min(72vh, 680px); object-fit:contain; margin:0 auto;
}

/* Project detail becomes a side drawer opened from the sidebar. */
.detail-drawer-backdrop { position:fixed; inset:0; z-index:1500; background:#030b14b8; backdrop-filter:blur(3px); opacity:0; visibility:hidden; transition:opacity .22s,visibility .22s; }
body.detail-open .detail-drawer-backdrop { opacity:1; visibility:visible; }
#project-detail.detail-drawer {
  position:fixed; z-index:1501; top:0; right:0; bottom:0;
  width:min(920px,92vw); margin:0; padding:28px; border-radius:0;
  border:0; border-left:1px solid #ffffff26;
  background:linear-gradient(160deg,#152a3f,#0b1728);
  box-shadow:-24px 0 70px #0009; overflow-y:auto;
  transform:translateX(102%); visibility:hidden;
  transition:transform .28s ease,visibility .28s;
}
body.detail-open #project-detail.detail-drawer { transform:translateX(0); visibility:visible; }
@media(max-width:768px) { #project-detail.detail-drawer { width:100vw; padding:20px; } }

/* Dala / constellation on a black canvas. */
:root { color-scheme:dark; --bg:#000000; --surface:#000000; --surface-2:#000000; --surface-3:#151019; --text:#ffffff; --text-secondary:#bdbdbd; --text-muted:#9a9a9a; --black:#ffffff; --gray-900:#ffffff; --gray-700:#bdbdbd; --gray-500:#9a9a9a; --gray-300:#28242e; --gray-100:#000000; --accent:#a98aff; --secondary:#9ddecf; --danger:#f3b7c4; --border:#ffffff19; --radius:16px; --radius-sm:6px; --shadow-sm:none; --shadow:none; --shadow-lg:none; }
html,body { background:var(--bg); }
body::before,.splice-art,.start-guide::before,.start-guide::after,.btn-primary::before { display:none; }
* { scrollbar-color:#514760 #000000; }
::selection { background:#a98aff; color:#000000; }
input,textarea { caret-color:#a98aff; }
.sidebar { background:#000000; box-shadow:none; backdrop-filter:none; }
.brand { padding:32px 24px; }.brand::before { background:#a98aff; width:24px; height:24px; border-radius:50%; box-shadow:none; }
.brand-name { font-size:26px; font-weight:500; letter-spacing:-.03em; }.brand-tagline { color:#bdbdbd; font-weight:400; letter-spacing:.08em; }
.nav-label { color:#9a9a9a; font-weight:400; letter-spacing:.1em; }.nav-item { font-weight:400; color:#bdbdbd; border-left:0; }.nav-item:hover { background:#ffffff08; color:#fff; }.nav-item.active { background:transparent; color:#fff; box-shadow:none; }
.nav-fluid-marker { background:#000000; border:1px solid #ffffff12; box-shadow:none; border-radius:6px; }
.topbar { background:#000000f5; border-color:#ffffff12; backdrop-filter:none; }
.content { max-width:1440px; padding-top:36px; }.workspace-heading { margin-bottom:32px; }.workspace-heading h1 { color:#fff; font-size:32px; font-weight:500; letter-spacing:-.03em; }.workspace-heading p { color:#bdbdbd; }
.workspace-tag { background:transparent; color:#bdbdbd; border-color:#ffffff20; border-radius:6px; }
.card,.chart-container,.filters,.pep-output { background:#000000; border:1px solid #ffffff12; box-shadow:none; backdrop-filter:none; }.card:hover { background:#000000; transform:none; box-shadow:none; border-color:#ffffff26; }
#page-dashboard > .grid-4 { background:#000000; border:1px solid #ffffff12; box-shadow:none; border-radius:16px; }
#page-dashboard > .grid-4 > .card { background:transparent; box-shadow:none; border-color:#ffffff12; border-radius:0; }
#stat-samples,#stat-events,#stat-significant { color:#ffb829 !important; font-weight:500 !important; font-size:42px !important; letter-spacing:-.035em; }
.start-guide { position:relative; isolation:isolate; min-height:304px; padding:36px; gap:36px; background:#000000; border:1px solid #ffffff12; border-radius:16px; box-shadow:none; overflow:hidden; }
.start-guide h2 { color:#fff; font-size:clamp(26px,2.7vw,40px); font-weight:500; line-height:1.15; letter-spacing:-.035em; max-width:14em; text-wrap:balance; }
.start-guide p { color:#bdbdbd; max-width:34em; line-height:1.6; margin:18px 0 24px; }
.start-guide ol { background:transparent; border:0; border-radius:0; box-shadow:none; backdrop-filter:none; padding:12px 0 12px 24px; gap:22px; border-left:1px solid #ffffff20; }
.start-guide li { color:#bdbdbd; }.start-guide strong { color:#ffffff; font-weight:500; }.start-guide li b { color:#a98aff; font-weight:400; }

.btn { font-weight:500; border-radius:6px; box-shadow:none; }.btn:hover { transform:none; box-shadow:none; }.btn-primary,.start-guide .btn-primary { color:#000000; background:linear-gradient(90deg,#a98aff 0%,#ffffff 26%,#fffdfa 48%,#fad1ff 100%); border:1px solid transparent; box-shadow:none; }
.btn-primary:hover,.start-guide .btn-primary:hover { background:linear-gradient(90deg,#e0fffd,#ffb829); color:#000000; box-shadow:none; transform:none; }
.btn-secondary,.start-guide .btn-secondary { background:#000000; border:1px solid #ffffff24; color:#ffffff; backdrop-filter:none; }.btn-secondary:hover,.start-guide .btn-secondary:hover { background:#151019; border-color:#bdbdbd; }
input,select,textarea,.search-input,#upload-modal input,#project-name,#analysis-query,#pep-sequences { background:#000000 !important; color:#ffffff !important; border-color:#ffffff26 !important; border-radius:6px; }
input::placeholder,textarea::placeholder { color:#9a9a9a; opacity:1; }input:focus,select:focus,textarea:focus { box-shadow:none; outline:2px solid #a98aff; outline-offset:2px; }
:focus-visible { outline:2px solid #a98aff; outline-offset:3px; }
.lang-toggle { background:#000000; border-color:#ffffff20; }.lang-toggle button.active { background:#000000; color:#a98aff; }
.table-container,.neo-result-body,.neo-result-body th,.neo-result-body td,#page-neoantigen details,#page-neoantigen details pre { background:#000000; color:#ffffff; }
th,.card table th,.neo-result-body th { background:#000000; color:#bdbdbd; }td,.card table td,.neo-result-body td { color:#ffffff; border-color:#ffffff12; }
tr:hover,#events-table .event-row:hover,.neo-result-body tr:hover td { background:#ffffff06; }
.pipeline-step { background:#000000; border-color:#ffffff20; }.pipeline-step.active { background:#000000; border-color:#a98aff; }.pipeline-step:hover { transform:none; }
.app-dialog,.quick-dialog,.app-toast,.ingest-panel,#upload-modal > div,#project-detail.detail-drawer { background:#000000 !important; color:#ffffff; border-color:#ffffff26 !important; box-shadow:none; }
.app-dialog-detail,.app-dialog-close,.quick-result:hover,.quick-result[aria-selected="true"],.ingest-head,.ingest-footer,.ingest-close,.ingest-step,.ingest-stat,.ingest-issue,.pep-options { background:#000000; }
#drop-zone { background:#000000 !important; }#event-detail-modal > div > div:first-child { background:#000000 !important; }
.sk { background:#28242e; animation:none; }.dpsi-bar { background:#28242e; }.dpsi-bar::after { background:#bdbdbd; }
.status-waiting { background:#ffffff08; color:#bdbdbd; }.status-dot { box-shadow:none; }
@media(max-width:1000px) { .start-guide { padding:28px; }.start-guide ol { border-left:0; border-top:1px solid #ffffff20; padding:24px 0 0; } }
@media(max-width:768px) { .sidebar { background:#000000; }.content { padding-top:24px; }.workspace-heading h1 { font-size:26px; }.start-guide { padding:24px; }.start-guide h2 { font-size:28px; } }


/* Typography and open composition: scale carries hierarchy. */
:root { --accent:#a98aff; --radius:24px; --radius-sm:12px; }
body { font-weight:400; }
h1,h2,h3,.workspace-heading h1,.start-guide h2,.brand-name { font-weight:400; }
.brand::before { display:block; background:#8052ff; border-radius:0; clip-path:polygon(50% 0,100% 100%,0 100%); }
.brand-tagline { color:#9a9a9a; }
.sidebar { border-right:1px solid #ffffff0d; }
.nav-fluid-marker { background:#8052ff12; border-color:transparent; border-radius:24px; }
.nav-item.active { color:#c8b7ff; }.nav-item:hover { border-radius:24px; }
.topbar { background:#000; border-bottom:0; }
.content { max-width:1280px; padding-top:42px; }
.workspace-heading h1 { font-size:40px; letter-spacing:-.04em; }.workspace-heading p { font-weight:200; font-size:15px; }
.workspace-tag { border:0; color:#ffb829; }
.card,.card:hover,.chart-container,.filters,.pep-output { background:#000; border-color:transparent; box-shadow:none; }
#page-dashboard > .grid-4 { background:#000; border:0; border-radius:0; }
#page-dashboard > .grid-4 > .card { border:0; border-right:1px solid #ffffff12; }
#page-dashboard > .grid-4 > .card:last-child { border-right:0; }
#stat-samples,#stat-events,#stat-significant { font-weight:400 !important; color:#fff !important; }
.start-guide { display:grid; grid-template-columns:1.3fr 1fr; padding:48px 24px; min-height:380px; background:#000; border:0; border-radius:0; overflow:hidden; margin:12px 0 48px; }
.start-guide h2 { font-size:clamp(32px,3.8vw,54px); line-height:1.15; letter-spacing:-.04em; max-width:10em; }
.start-guide p { font-size:16px; font-weight:200; max-width:29em; line-height:1.7; }
.start-guide ol { align-self:end; border:0; padding:0 0 0 30px; gap:18px; }
.start-guide li { font-weight:200; }.start-guide strong { font-weight:400; }.start-guide li b { color:#ffb829; }
.constellation-art { position:absolute; right:-6px; top:-30px; width:48%; height:220px; z-index:-1; pointer-events:none; opacity:.85; }
.btn,.btn-primary,.start-guide .btn-primary { border-radius:24px; }
.btn-primary,.start-guide .btn-primary { background:#8052ff; color:#fff; border:1px solid transparent; }
.btn-primary:hover,.start-guide .btn-primary:hover { background:#9169ff; color:#fff; }
.btn-secondary,.start-guide .btn-secondary { background:transparent; border-color:#ffffff24; color:#bdbdbd; }
.btn-secondary:hover,.start-guide .btn-secondary:hover { background:#ffffff08; color:#fff; border-color:#ffffff55; }
.start-guide .btn-secondary { border:0; text-decoration:underline; text-underline-offset:5px; }
#page-dashboard #current-agent .btn-primary { background:transparent; border-color:#a98aff; color:#c8b7ff; }
#page-dashboard > .grid-2 > .card { border-top:1px solid #ffffff1c; border-radius:0; padding-top:30px; }
input,select,textarea,.search-input,#upload-modal input,#project-name,#analysis-query,#pep-sequences { background:#000 !important; border-color:#ffffff30 !important; border-radius:12px; }
input:focus,select:focus,textarea:focus { outline-color:#a98aff; }
.table-container { border-color:#ffffff1c; border-radius:12px; }th,.card table th,.neo-result-body th { background:#000; color:#bdbdbd; border-bottom:1px solid #ffffff30; }
.pipeline-step { border-radius:24px; }.pipeline-step.active { border-color:#a98aff; background:#8052ff0c; }
.app-dialog,.quick-dialog,.app-toast,.ingest-panel,#upload-modal > div,#project-detail.detail-drawer { background:#000 !important; border:1px solid #ffffff30 !important; border-radius:24px; }
.lang-toggle button.active { color:#c8b7ff; }
::selection { background:#8052ff; color:#fff; }
a { color:#ffb829; }
@media(max-width:1000px) { .start-guide { grid-template-columns:1fr; padding:36px 12px; }.start-guide h2 { max-width:12em; }.start-guide ol { padding:24px 0 0; }.constellation-art { right:-50px; width:52%; opacity:.45; } }
@media(max-width:768px) { .workspace-heading h1 { font-size:32px; }.start-guide h2 { font-size:36px; }.start-guide { margin-bottom:30px; }.constellation-art { width:85%; right:-100px; top:30px; opacity:.25; } }

.trace-badge { display:inline-block; padding:2px 8px; border-radius:999px; font-size:11px; font-weight:500; border:1px solid rgba(140,160,200,.28); }
.trace-llm { background:rgba(90,140,255,.16); color:#8fb4ff; }
.trace-rule { background:rgba(140,150,170,.14); color:var(--text-secondary); }
.trace-reflection { background:rgba(240,170,60,.16); color:#f0b44a; }
.trace-episodic { background:rgba(150,100,220,.16); color:#c3a0ff; }
.trace-replay { background:rgba(60,190,150,.16); color:#6fd6b0; }
.mission-banner { padding:14px 16px; border-radius:12px; border:1px solid; margin-bottom:12px; font-size:13px; line-height:1.6; }
.mission-banner-failed { background:rgba(226,75,74,.12); border-color:rgba(226,75,74,.45); color:var(--danger); }
.mission-banner-partial { background:rgba(239,159,39,.12); border-color:rgba(239,159,39,.45); color:#efb45a; }
.mission-banner-succeeded { background:rgba(94,234,212,.10); border-color:rgba(94,234,212,.38); color:var(--accent); }
.mission-banner-running { background:var(--surface-2); border-color:var(--border); color:var(--text-secondary); }
.mission-hint { font-size:12px; color:var(--text-muted); margin-top:6px; line-height:1.6; }
.mission-path { font-family:var(--font-mono,monospace); font-size:12px; word-break:break-all; color:var(--text-secondary); }
.mission-actions { display:flex; gap:8px; flex-wrap:wrap; margin-top:12px; }
.mission-code { white-space:nowrap; overflow-x:auto; font-family:var(--font-mono,monospace); font-size:12px; }
.pep-tier { display:inline-block; margin-left:6px; padding:1px 7px; border-radius:999px; font-size:11px; border:1px solid; }
.pep-tier-strong { color:#6fd6b0; border-color:rgba(111,214,176,.5); background:rgba(111,214,176,.12); }
.pep-tier-weak { color:#efb45a; border-color:rgba(239,180,90,.5); background:rgba(239,180,90,.12); }
.pep-tier-none { color:var(--text-muted); border-color:var(--border); }
.pep-tier-unknown { color:var(--text-muted); border-color:var(--border); opacity:.75; }
.trace-step { border-left:2px solid rgba(140,160,200,.25); padding:6px 0 12px 14px; margin-left:6px; position:relative; }
.trace-step::before { content:''; position:absolute; left:-5px; top:13px; width:8px; height:8px; border-radius:50%; background:var(--text-secondary); }
.trace-step-title { font-size:13px; font-weight:500; display:flex; gap:8px; align-items:center; flex-wrap:wrap; }
.trace-meta { font-size:12px; color:var(--text-secondary); margin-top:4px; line-height:1.55; word-break:break-word; }
.trace-call { border:1px solid rgba(140,160,200,.18); border-radius:8px; padding:10px; margin-bottom:8px; font-size:12px; }
.trace-bar { height:6px; border-radius:4px; background:rgba(140,160,200,.18); overflow:hidden; margin-top:8px; }
.trace-bar > span { display:block; height:100%; background:#6f9bff; }
.trace-metric { font-size:24px; font-weight:500; margin-top:4px; }
.trace-control { background:rgba(14,27,43,.7); color:var(--text-primary); border:1px solid rgba(140,160,200,.28); border-radius:8px; padding:8px 10px; font-size:13px; }
</style>
</head>
<body>
<div class="app">
  <button class="nav-scrim" tabindex="-1" aria-label="关闭导航" onclick="toggleNavigation(false)"></button><aside class="sidebar" id="app-navigation" aria-label="主导航"><div class="nav-fluid-marker" aria-hidden="true"></div><button class="drawer-close btn btn-secondary" type="button" onclick="toggleNavigation(false)">关闭菜单</button>
    <div class="brand"><div class="brand-name">EpitopeRank</div><div class="brand-tagline">剪接事件与候选肽分析</div></div>
    <div class="nav-section"><div class="nav-label">主菜单</div>
      <button type="button" class="nav-item active" data-page="dashboard" aria-current="page"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z"/></svg>仪表盘</button>
      <button type="button" class="nav-item" data-page="pipeline"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 5h16 M4 12h16 M4 19h16 M8 3v4 M16 10v4 M10 17v4"/></svg>AI 流水线</button>
      <button type="button" class="nav-item" data-page="explorer"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 4h16v16H4z M4 10h16 M10 4v16"/></svg>事件浏览器</button>
    </div>
    <div class="nav-section"><div class="nav-label">分析工具</div>
      <button type="button" class="nav-item" data-page="visualization"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 3v17h17 M8 16v-5 M13 16V7 M18 16V4"/></svg>可视化</button>
      <button type="button" class="nav-item" data-page="gene"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 3c0 9 12 9 12 18 M18 3C18 12 6 12 6 21 M7 6h10 M8 18h8"/></svg>基因浏览器</button>
      <button type="button" class="nav-item" data-page="report"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 3h9l4 4v14H6z M14 3v5h5 M9 12h7 M9 16h7"/></svg>报告</button>
      <button type="button" class="nav-item" data-page="neoantigen"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 12h5l3-8 4 16 3-8h3"/></svg>剪接候选新抗原</button>
      <button type="button" class="nav-item" data-page="peptide"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 6h5v5H5z M14 13h5v5h-5z M10 8h7v5 M7 11v5h7"/></svg>肽预测</button>
    </div>
    <div class="nav-section"><div class="nav-label">工作区</div>
      <button type="button" class="nav-item" data-detail="1" onclick="openProjectDetail()"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 4h16v16H4z M4 9h16 M9 9v11 M14 4v5"/></svg>项目详情</button>
      <button type="button" class="nav-item" data-page="trace"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 5h16 M4 12h10 M4 19h7 M17 12l3 3-3 3"/></svg>决策轨迹</button>
      <button type="button" class="nav-item" data-page="mission"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3l2.5 5.5L20 9l-4 4 1 6-5-3-5 3 1-6-4-4 5.5-.5z"/></svg>自主任务</button>
      <button type="button" class="nav-item" data-page="settings"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3v3 M12 18v3 M3 12h3 M18 12h3 M6 6l2 2 M16 16l2 2 M6 18l2-2 M16 8l2-2 M8 12a4 4 0 1 0 8 0a4 4 0 1 0-8 0"/></svg>设置</button>
    </div>
  </aside>
  <a class="skip-link" href="#workspace-content">跳到工作区</a><main class="main">
    <div class="topbar"><button class="btn btn-secondary mobile-menu" type="button" aria-controls="app-navigation" aria-expanded="false" onclick="toggleNavigation()">菜单</button>
      <div style="font-size: 14px; color: var(--text-secondary);" id="current-project">未加载项目</div>
      <div style="display: flex; gap: 12px; align-items: center;">
        <button type="button" class="btn btn-secondary btn-sm quick-switch" onclick="openQuickSwitch()">快捷跳转 <kbd>Ctrl K</kbd></button>
        <button type="button" id="motion-toggle" class="btn btn-secondary btn-sm" aria-pressed="false" onclick="toggleMotion()">动态：开</button>
        <div class="lang-toggle" role="group" aria-label="Language" data-no-i18n>
          <button type="button" data-lang="zh" class="active" aria-pressed="true">简体中文</button>
          <button type="button" data-lang="zh-Hant" aria-pressed="false">繁體中文</button>
          <button type="button" data-lang="en" aria-pressed="false">EN</button>
        </div>
        <button class="btn btn-secondary btn-sm" onclick="refreshData()">刷新</button>
        <button class="btn btn-primary btn-sm" onclick="showUploadModal()">+ 新建分析</button>
      </div>
    </div>
    <div class="content" id="workspace-content" tabindex="-1">
      <div class="page active" id="page-dashboard">
        <header class="workspace-heading"><div><h1>项目工作台</h1><p>管理剪接分析项目，追踪进度，回到每一次研究的结果。</p></div><span class="workspace-tag">研究工作区</span></header>
        
        <div class="grid grid-4" style="margin-bottom: 32px;">
          <div class="card">
            <div style="font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.8px; color: var(--gray-500); margin-bottom: 12px;">总样本数</div>
            <div style="font-size: 36px; font-weight: 600; color: var(--black);" id="stat-samples">-</div>
            <div style="font-size: 12px; margin-top: 8px; color: var(--gray-500);">RNA-seq 样本</div>
          </div>
          <div class="card">
            <div style="font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.8px; color: var(--gray-500); margin-bottom: 12px;">剪接事件</div>
            <div style="font-size: 36px; font-weight: 600; color: var(--black);" id="stat-events">-</div>
            <div style="font-size: 12px; margin-top: 8px; color: var(--gray-500);">检测到的事件总数</div>
          </div>
          <div class="card">
            <div style="font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.8px; color: var(--gray-500); margin-bottom: 12px;">显著事件</div>
            <div style="font-size: 36px; font-weight: 600; color: var(--black);" id="stat-significant">-</div>
            <div style="font-size: 12px; margin-top: 8px; color: var(--gray-500);">FDR < 0.05 & |ΔPSI| > 0.1</div>
          </div>
          <div class="card">
            <div style="font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.8px; color: var(--gray-500); margin-bottom: 12px;">系统状态</div>
            <div style="margin-top: 8px;" id="stat-status"><span class="status status-waiting"><span class="status-dot"></span>空闲</span></div>
          </div>
        </div>
<section class="start-guide" aria-label="开始使用"><svg class="constellation-art" viewBox="0 0 500 300" aria-hidden="true"><path d="M273.1 260.1l3.1 5.6h-6.2z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.57"/><path d="M223.9 252.7l1.6 2.8h-3.1z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.60"/><path d="M264.2 258.5l2.2 3.9h-4.4z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.53"/><path d="M279.8 260.4l2.1 3.7h-4.1z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.61"/><path d="M205.3 239.1l3.3 6.0h-6.7z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.57"/><path d="M292.9 257.4l3.2 5.7h-6.4z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.54"/><path d="M227.7 250.6l3.7 6.7h-7.5z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.64"/><path d="M218.3 247.3l1.7 3.1h-3.4z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.51"/><path d="M304.6 254.8l2.6 4.6h-5.1z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.60"/><path d="M193.7 233.0l1.6 2.8h-3.1z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.61"/><path d="M283.3 257.7l2.0 3.7h-4.1z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.50"/><path d="M277.7 256.6l2.8 5.0h-5.5z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.66"/><path d="M190.6 230.7l1.6 2.8h-3.1z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.53"/><path d="M317.5 251.4l2.0 3.6h-4.0z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.55"/><path d="M204.2 235.0l3.1 5.6h-6.2z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.66"/><path d="M230.2 249.2l2.9 5.2h-5.7z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.47"/><path d="M309.8 251.6l2.1 3.7h-4.1z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.64"/><path d="M173.8 224.4l3.0 5.4h-5.9z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.58"/><path d="M308.7 249.6l3.5 6.3h-7.0z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.49"/><path d="M234.9 250.9l1.5 2.7h-3.0z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.69"/><path d="M193.7 227.2l3.5 6.3h-7.0z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.48"/><path d="M332.0 246.4l3.2 5.8h-6.5z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.59"/><path d="M178.9 223.6l2.4 4.2h-4.7z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.65"/><path d="M278.1 253.0l1.9 3.4h-3.8z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.45"/><path d="M299.2 248.8l3.9 7.0h-7.8z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.69"/><path d="M165.5 223.7l2.3 4.2h-4.7z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.53"/><path d="M332.3 246.2l1.7 3.1h-3.5z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.52"/><path d="M207.6 233.4l1.7 3.1h-3.5z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.70"/><path d="M211.0 233.1l3.6 6.5h-7.2z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.44"/><path d="M333.7 244.0l3.0 5.4h-6.0z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.64"/><path d="M158.6 223.4l3.5 6.3h-7.0z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.61"/><path d="M307.0 245.5l3.3 6.0h-6.6z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.45"/><path d="M276.3 248.6l2.8 5.1h-5.7z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.72"/><path d="M170.6 218.7l3.9 7.1h-7.9z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.48"/><path d="M347.9 243.6l2.4 4.4h-4.9z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.56"/><path d="M178.8 218.7l2.9 5.2h-5.8z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.69"/><path d="M262.4 243.6l3.6 6.4h-7.1z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.42"/><path d="M321.8 241.7l3.0 5.5h-6.1z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.69"/><path d="M148.6 226.6l3.7 6.6h-7.3z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.56"/><path d="M334.2 240.7l2.9 5.3h-5.9z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.48"/><path d="M221.6 234.8l3.3 5.9h-6.5z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.74"/><path d="M188.9 219.5l1.6 2.9h-3.2z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.43"/><path d="M351.7 241.6l2.1 3.7h-4.1z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.62"/><path d="M154.6 223.5l2.2 4.0h-4.4z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.65"/><path d="M294.8 244.4l1.7 3.1h-3.4z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.41"/><path d="M297.8 243.2l2.1 3.7h-4.2z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.74"/><path d="M151.5 225.2l1.8 3.2h-3.5z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.50"/><path d="M354.1 239.9l2.2 4.0h-4.4z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.52"/><path d="M189.0 215.4l3.1 5.6h-6.2z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.73"/><path d="M217.5 229.6l2.4 4.3h-4.8z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.40"/><path d="M342.0 238.0l2.4 4.4h-4.9z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.68"/><path d="M140.1 231.3l2.0 3.6h-4.0z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.60"/><path d="M326.3 237.3l2.2 3.9h-4.3z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.43"/><path d="M265.6 237.8l3.8 6.9h-7.7z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.76"/><path d="M167.7 214.3l3.1 5.6h-6.2z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.44"/><path d="M362.5 236.2l3.0 5.4h-6.0z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.58"/><path d="M160.1 218.3l1.9 3.5h-3.9z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.70"/><path d="M276.0 238.8l3.3 6.0h-6.6z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.38"/><path d="M319.8 235.8l1.9 3.4h-3.8z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.74"/><path d="M138.3 230.9l2.4 4.4h-4.9z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.53"/><path d="M351.4 233.6l4.0 7.2h-7.9z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.48"/><path d="M206.2 217.4l3.1 5.6h-6.2z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.77"/><path d="M195.1 212.1l2.9 5.2h-5.8z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.39"/><path d="M357.6 233.2l3.2 5.8h-6.4z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.65"/><path d="M139.8 228.0l3.6 6.5h-7.2z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.64"/><path d="M311.0 232.7l3.4 6.2h-6.9z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.39"/><path d="M288.2 236.7l2.1 3.7h-4.1z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.78"/><path d="M149.9 223.0l1.6 2.8h-3.2z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.46"/><path d="M365.9 231.1l2.3 4.1h-4.6z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.54"/><path d="M172.9 209.8l2.2 3.9h-4.3z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.74"/><path d="M229.8 228.4l2.0 3.6h-4.1z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.36"/><path d="M339.6 229.6l3.9 6.9h-7.7z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.72"/><path d="M131.6 231.2l3.7 6.6h-7.4z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.57"/><path d="M341.3 230.5l2.3 4.1h-4.6z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.43"/><path d="M227.6 224.5l3.1 5.6h-6.3z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.79"/><path d="M173.7 207.7l2.5 4.5h-5.0z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.40"/><path d="M367.5 225.5l3.8 6.8h-7.6z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.62"/><path d="M146.7 222.6l2.6 4.8h-5.3z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.69"/><path d="M291.0 232.0l2.2 3.9h-4.3z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.36"/><path d="M310.8 229.2l2.1 3.8h-4.2z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.77"/><path d="M136.8 227.8l2.9 5.2h-5.8z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.50"/><path d="M362.5 226.0l2.2 3.9h-4.3z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.49"/><path d="M191.1 203.5l3.0 5.3h-5.9z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.78"/><path d="M206.5 207.9l3.7 6.7h-7.5z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.36"/><path d="M355.7 225.6l2.5 4.5h-5.0z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.69"/><path d="M131.3 230.1l2.0 3.7h-4.1z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.62"/><path d="M325.7 224.1l4.0 7.2h-8.0z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.39"/><path d="M275.0 228.1l2.8 5.0h-5.5z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.81"/><path d="M154.9 216.1l1.7 3.1h-3.5z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.42"/><path d="M371.7 219.6l1.6 2.9h-3.2z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.57"/><path d="M159.3 212.7l1.8 3.2h-3.5z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.74"/><path d="M268.2 225.0l3.1 5.5h-6.1z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.34"/><path d="M331.9 222.7l3.5 6.3h-7.0z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.76"/><path d="M128.6 228.2l2.6 4.6h-5.1z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.54"/><path d="M353.5 222.6l1.7 3.0h-3.3z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.44"/><path d="M212.6 207.8l2.5 4.4h-4.9z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.81"/><path d="M183.7 197.8l4.0 7.2h-8.0z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.36"/><path d="M367.7 216.0l2.8 5.1h-5.6z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.65"/><path d="M136.3 222.7l3.9 7.1h-7.9z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.68"/><path d="M306.1 221.3l3.7 6.6h-7.3z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.35"/><path d="M298.9 223.9l1.5 2.8h-3.1z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.81"/><path d="M139.2 221.1l3.3 5.9h-6.6z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.46"/><path d="M370.9 211.9l3.2 5.8h-6.4z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.51"/><path d="M176.2 198.9l2.8 5.1h-5.7z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.78"/><path d="M220.0 209.1l2.2 3.9h-4.3z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.33"/><path d="M350.7 217.2l3.1 5.6h-6.2z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.73"/><path d="M125.0 225.3l1.8 3.2h-3.6z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.59"/><path d="M339.9 218.2l2.6 4.7h-5.2z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.39"/><path d="M236.3 216.1l2.6 4.7h-5.3z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.83"/><path d="M162.2 203.9l3.9 7.0h-7.8z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.38"/><path d="M375.8 205.4l3.7 6.6h-7.4z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.60"/><path d="M146.0 215.6l2.2 3.9h-4.3z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.73"/><path d="M283.7 219.5l2.8 5.0h-5.5z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.32"/><path d="M322.4 217.2l1.9 3.5h-3.9z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.79"/><path d="M126.8 220.1l3.8 6.8h-7.6z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.50"/><path d="M365.6 208.1l3.7 6.6h-7.4z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.46"/><path d="M196.5 193.5l2.2 4.0h-4.5z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.82"/><path d="M195.1 192.0l3.1 5.6h-6.2z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.33"/><path d="M367.2 206.9l3.0 5.4h-6.0z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.69"/><path d="M125.6 220.3l1.9 3.4h-3.8z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.65"/><path d="M322.5 213.4l3.4 6.1h-6.8z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.35"/><path d="M285.7 216.2l2.8 5.1h-5.7z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.83"/><path d="M142.1 212.4l3.4 6.2h-6.9z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.42"/><path d="M380.1 199.1l2.8 5.1h-5.7z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.54"/><path d="M159.8 202.7l1.5 2.7h-3.0z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.78"/><path d="M234.8 209.2l2.3 4.2h-4.6z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.31"/><path d="M345.5 211.7l1.5 2.8h-3.1z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.77"/><path d="M117.6 215.7l3.8 6.9h-7.6z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.56"/><path d="M356.1 206.6l3.7 6.7h-7.4z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.41"/><path d="M220.0 198.5l3.6 6.4h-7.2z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.84"/><path d="M169.8 193.6l2.3 4.1h-4.5z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.35"/><path d="M381.1 197.2l1.6 3.0h-3.3z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.64"/><path d="M130.4 212.4l3.7 6.7h-7.4z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.71"/><path d="M301.3 210.2l3.9 7.0h-7.7z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.32"/><path d="M312.4 211.1l1.7 3.1h-3.4z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.83"/><path d="M123.8 213.5l2.7 4.9h-5.4z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.47"/><path d="M380.3 196.2l1.7 3.0h-3.3z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.49"/><path d="M177.9 186.4l3.4 6.1h-6.8z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.82"/><path d="M207.6 189.0l3.4 6.1h-6.8z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.31"/><path d="M367.7 200.9l1.8 3.3h-3.6z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.73"/><path d="M112.1 212.0l2.7 4.8h-5.4z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.62"/><path d="M341.9 205.7l2.9 5.2h-5.7z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.36"/><path d="M270.7 207.2l2.2 3.9h-4.3z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.85"/><path d="M144.4 201.3l3.7 6.6h-7.4z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.38"/><path d="M391.9 188.3l2.6 4.6h-5.1z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.58"/><path d="M140.1 204.3l2.0 3.7h-4.1z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.76"/><path d="M276.0 206.1l2.8 5.1h-5.7z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.29"/><path d="M340.2 203.4l3.3 6.0h-6.6z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.80"/><path d="M108.0 209.7l2.0 3.6h-4.0z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.52"/><path d="M375.8 194.4l2.3 4.1h-4.6z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.43"/><path d="M200.7 182.0l4.0 7.2h-8.0z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.85"/><path d="M178.3 181.3l3.1 5.6h-6.2z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.32"/><path d="M388.2 188.1l2.6 4.7h-5.2z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.68"/><path d="M111.3 207.2l2.8 5.0h-5.6z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.68"/><path d="M322.4 204.0l1.8 3.2h-3.6z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.32"/><path d="M300.6 204.8l2.1 3.7h-4.1z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.85"/><path d="M119.8 205.5l2.3 4.2h-4.7z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.43"/><path d="M398.3 182.8l3.0 5.3h-5.9z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.52"/><path d="M155.5 188.9l2.1 3.7h-4.2z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.81"/><path d="M222.7 191.0l2.1 3.7h-4.1z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.29"/><path d="M368.2 195.1l1.7 3.0h-3.4z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.77"/><path d="M96.1 203.5l3.1 5.5h-6.2z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.58"/><path d="M365.1 195.2l2.1 3.7h-4.1z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.37"/><path d="M228.6 190.7l3.8 6.8h-7.5z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.87"/><path d="M147.7 188.4l3.6 6.6h-7.3z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.35"/><path d="M405.4 180.3l1.7 3.0h-3.4z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.62"/><path d="M116.7 201.8l2.1 3.8h-4.2z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.74"/><path d="M297.0 199.7l3.2 5.7h-6.3z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.29"/><path d="M332.8 198.6l2.0 3.7h-4.1z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.83"/><path d="M97.7 202.3l1.8 3.3h-3.7z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.48"/><path d="M398.5 179.4l3.8 6.9h-7.7z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.46"/><path d="M177.5 174.4l2.9 5.3h-5.9z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.85"/><path d="M189.8 174.3l2.7 4.8h-5.4z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.29"/><path d="M394.7 180.7l3.5 6.2h-6.9z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.72"/><path d="M90.0 198.6l3.5 6.3h-7.0z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.65"/><path d="M347.3 195.0l2.0 3.6h-4.0z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.33"/><path d="M285.1 197.2l1.7 3.1h-3.5z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.87"/><path d="M117.6 195.6l2.6 4.6h-5.2z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.39"/><path d="M417.2 173.8l2.6 4.6h-5.1z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.56"/><path d="M129.6 190.0l2.7 4.8h-5.3z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.79"/><path d="M265.8 189.9l3.3 6.0h-6.6z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.27"/><path d="M365.8 188.6l3.2 5.7h-6.4z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.80"/><path d="M80.3 194.9l4.0 7.1h-7.9z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.54"/><path d="M390.9 181.7l1.7 3.1h-3.5z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.40"/><path d="M206.3 175.1l2.5 4.5h-5.0z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.87"/><path d="M154.9 175.7l2.3 4.2h-4.7z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.32"/><path d="M417.2 170.8l3.7 6.6h-7.3z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.66"/><path d="M91.9 195.6l2.1 3.8h-4.2z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.71"/><path d="M321.8 193.2l2.0 3.6h-4.0z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.29"/><path d="M320.9 192.2l2.6 4.7h-5.2z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.86"/><path d="M90.4 194.0l2.6 4.6h-5.1z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.44"/><path d="M421.2 170.3l2.2 4.0h-4.4z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.49"/><path d="M151.1 174.2l2.1 3.8h-4.2z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.84"/><path d="M206.1 170.9l3.8 6.9h-7.6z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.27"/><path d="M396.9 176.3l2.6 4.7h-5.2z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.76"/><path d="M70.4 190.4l3.7 6.6h-7.3z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.61"/><path d="M374.1 182.5l2.9 5.2h-5.8z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.34"/><path d="M264.9 184.7l1.6 2.9h-3.3z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.88"/><path d="M120.7 182.3l4.0 7.2h-8.0z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.35"/><path d="M432.8 165.0l3.6 6.5h-7.2z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.60"/><path d="M103.4 186.7l3.9 7.1h-7.8z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.77"/><path d="M289.2 186.3l3.8 6.9h-7.6z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.27"/><path d="M357.4 183.4l3.6 6.5h-7.2z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.83"/><path d="M69.4 189.7l1.9 3.4h-3.8z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.50"/><path d="M415.4 167.9l2.7 4.9h-5.4z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.43"/><path d="M180.8 163.8l2.0 3.7h-4.1z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.87"/><path d="M168.3 163.6l2.5 4.5h-5.0z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.29"/><path d="M422.8 166.3l1.6 3.0h-3.3z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.70"/><path d="M70.3 187.6l2.4 4.4h-4.9z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.67"/><path d="M348.3 182.2l4.0 7.1h-7.9z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.30"/><path d="M303.1 185.9l2.2 3.9h-4.3z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.88"/><path d="M90.4 184.7l3.5 6.2h-6.9z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.40"/><path d="M438.9 161.5l2.6 4.7h-5.3z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.53"/><path d="M124.8 174.9l2.6 4.6h-5.1z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.82"/><path d="M227.5 171.4l3.9 7.0h-7.8z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.26"/><path d="M391.3 170.7l4.0 7.2h-8.0z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.79"/><path d="M57.4 183.6l2.9 5.2h-5.8z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.57"/><path d="M399.0 168.4l3.3 5.9h-6.6z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.37"/><path d="M216.9 168.1l1.9 3.4h-3.8z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.89"/><path d="M131.6 169.9l2.2 4.0h-4.5z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.32"/><path d="M440.4 157.5l3.9 7.1h-7.8z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.64"/><path d="M81.2 182.3l2.9 5.3h-5.9z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.74"/><path d="M314.6 181.4l2.9 5.1h-5.7z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.27"/><path d="M341.7 179.1l3.4 6.1h-6.7z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.86"/><path d="M67.5 182.9l1.6 3.0h-3.3z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.46"/><path d="M433.9 157.5l3.0 5.3h-5.9z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.46"/><path d="M155.1 158.9l2.8 5.0h-5.5z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.86"/><path d="M188.0 155.7l3.6 6.5h-7.3z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.27"/><path d="M418.9 160.4l1.9 3.4h-3.8z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.74"/><path d="M56.5 178.3l3.9 7.0h-7.8z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.63"/><path d="M372.7 172.8l1.7 3.1h-3.4z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.32"/><path d="M280.4 175.5l2.0 3.5h-3.9z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.89"/><path d="M99.9 174.8l3.0 5.4h-6.0z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.36"/><path d="M447.4 153.8l3.2 5.7h-6.4z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.57"/><path d="M102.8 174.2l2.1 3.8h-4.2z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.79"/><path d="M276.0 173.1l1.8 3.2h-3.6z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.26"/><path d="M376.7 167.5l3.7 6.7h-7.5z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.83"/><path d="M54.7 177.3l2.1 3.8h-4.2z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.52"/><path d="M417.5 156.0l3.0 5.4h-6.0z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.40"/><path d="M191.9 152.8l3.0 5.5h-6.1z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.89"/><path d="M150.4 155.6l2.5 4.6h-5.1z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.29"/><path d="M437.2 151.6l3.0 5.3h-5.9z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.68"/><path d="M67.2 175.5l2.8 5.1h-5.6z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.70"/><path d="M338.6 172.3l3.8 6.9h-7.7z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.28"/><path d="M319.7 175.0l2.0 3.6h-4.0z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.88"/><path d="M76.4 173.7l3.3 5.9h-6.6z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.42"/><path d="M442.6 150.5l2.1 3.8h-4.2z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.50"/><path d="M133.3 158.9l2.5 4.5h-5.0z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.84"/><path d="M212.0 154.2l3.2 5.7h-6.4z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.26"/><path d="M404.9 155.5l2.2 4.0h-4.5z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.78"/><path d="M53.5 172.5l2.3 4.1h-4.6z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.59"/><path d="M391.2 157.5l3.4 6.1h-6.8z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.35"/><path d="M231.7 160.6l1.7 3.0h-3.4z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.90"/><path d="M118.3 162.2l2.6 4.8h-5.3z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.33"/><path d="M444.5 146.1l4.0 7.2h-8.0z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.61"/><path d="M88.6 168.2l4.0 7.2h-8.0z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.76"/><path d="M300.1 170.3l1.7 3.0h-3.4z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.26"/><path d="M354.9 166.3l2.0 3.7h-4.1z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.85"/><path d="M63.3 170.5l2.2 3.9h-4.3z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.48"/><path d="M426.6 145.1l3.8 6.9h-7.7z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.44"/><path d="M169.8 144.5l3.7 6.7h-7.4z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.87"/><path d="M174.4 143.8l3.7 6.7h-7.4z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.27"/><path d="M423.5 145.7l2.4 4.4h-4.8z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.72"/><path d="M63.6 169.0l1.9 3.4h-3.8z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.66"/><path d="M357.8 161.2l3.6 6.5h-7.2z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.30"/><path d="M294.7 164.8l3.3 5.9h-6.5z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.89"/><path d="M94.6 164.6l3.0 5.5h-6.1z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.38"/><path d="M440.4 141.8l4.0 7.1h-7.9z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.54"/><path d="M118.2 157.5l3.1 5.6h-6.3z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.82"/><path d="M236.7 155.9l1.5 2.7h-3.0z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.25"/><path d="M383.1 150.9l3.5 6.4h-7.1z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.81"/><path d="M61.2 165.5l2.2 4.0h-4.5z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.55"/><path d="M401.6 144.8l3.2 5.7h-6.3z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.38"/><path d="M208.5 143.2l3.8 6.9h-7.7z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.89"/><path d="M142.5 148.7l1.8 3.3h-3.7z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.30"/><path d="M431.7 141.1l1.8 3.2h-3.6z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.66"/><path d="M83.4 164.5l1.8 3.2h-3.5z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.73"/><path d="M320.6 163.1l2.9 5.2h-5.8z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.27"/><path d="M329.4 162.8l2.2 3.9h-4.4z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.87"/><path d="M80.6 162.5l3.0 5.4h-6.0z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.44"/><path d="M426.3 137.9l3.3 5.9h-6.6z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.48"/><path d="M152.8 143.5l2.0 3.6h-4.0z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.86"/><path d="M200.0 138.8l3.1 5.6h-6.2z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.26"/><path d="M402.5 140.3l2.2 3.9h-4.3z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.76"/><path d="M69.3 160.8l2.7 4.9h-5.4z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.62"/><path d="M370.4 147.3l3.8 6.8h-7.5z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.33"/><path d="M270.2 150.6l3.6 6.5h-7.2z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.90"/><path d="M118.3 154.0l1.7 3.1h-3.5z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.35"/><path d="M429.8 136.4l2.6 4.6h-5.1z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.59"/><path d="M110.3 155.5l2.2 3.9h-4.4z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.79"/><path d="M283.0 155.4l1.5 2.7h-3.0z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.25"/><path d="M357.8 149.1l3.4 6.2h-6.9z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.84"/><path d="M76.3 157.9l3.1 5.6h-6.2z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.51"/><path d="M404.4 135.5l2.2 3.9h-4.3z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.41"/><path d="M189.2 133.2l3.4 6.0h-6.7z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.89"/><path d="M168.3 135.1l2.9 5.2h-5.8z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.28"/><path d="M412.8 133.2l2.6 4.6h-5.1z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.70"/><path d="M85.6 157.9l1.5 2.7h-3.0z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.69"/><path d="M336.2 154.4l1.7 3.0h-3.4z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.29"/><path d="M304.2 154.7l3.7 6.7h-7.4z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.89"/><path d="M102.3 153.0l3.8 6.8h-7.5z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.40"/><path d="M419.5 131.6l2.9 5.2h-5.7z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.52"/><path d="M141.3 140.4l3.6 6.5h-7.2z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.83"/><path d="M223.7 136.8l3.0 5.3h-5.9z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.25"/><path d="M378.9 136.3l1.9 3.4h-3.7z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.79"/><path d="M80.3 154.6l1.8 3.3h-3.6z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.58"/><path d="M377.6 135.4l2.3 4.1h-4.5z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.36"/><path d="M224.7 134.7l3.7 6.7h-7.5z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.90"/><path d="M142.8 138.4l3.5 6.3h-7.0z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.32"/><path d="M415.1 128.1l3.7 6.6h-7.3z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.63"/><path d="M107.6 149.3l3.7 6.7h-7.5z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.75"/><path d="M301.7 152.2l2.0 3.6h-4.1z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.26"/><path d="M333.2 149.1l2.1 3.8h-4.2z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.86"/><path d="M94.0 152.2l1.8 3.2h-3.5z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.46"/><path d="M403.0 126.2l3.5 6.2h-6.9z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.45"/><path d="M173.8 127.4l3.7 6.7h-7.4z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.87"/><path d="M192.3 126.8l2.5 4.5h-5.0z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.27"/><path d="M393.0 126.1l3.1 5.5h-6.1z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.74"/><path d="M90.9 150.5l1.9 3.4h-3.8z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.65"/><path d="M348.1 138.8l3.8 6.9h-7.6z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.31"/><path d="M281.6 142.4l3.7 6.6h-7.3z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.90"/><path d="M123.6 141.6l3.9 7.1h-7.9z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.37"/><path d="M410.7 124.1l3.5 6.3h-7.1z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.56"/><path d="M133.0 137.8l3.7 6.7h-7.4z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.80"/><path d="M268.5 137.9l1.6 2.8h-3.1z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.25"/><path d="M356.9 132.6l3.3 6.0h-6.7z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.82"/><path d="M92.0 147.3l2.3 4.2h-4.7z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.53"/><path d="M382.3 122.8l3.8 6.9h-7.7z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.39"/><path d="M206.2 122.6l3.5 6.3h-7.0z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.89"/><path d="M165.0 125.2l3.7 6.6h-7.3z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.30"/><path d="M401.0 120.8l3.5 6.3h-7.1z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.67"/><path d="M106.1 145.0l2.2 3.9h-4.3z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.71"/><path d="M317.7 143.9l3.5 6.2h-6.9z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.28"/><path d="M311.3 145.9l1.8 3.2h-3.5z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.88"/><path d="M109.9 141.9l3.7 6.6h-7.4z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.43"/><path d="M401.4 119.1l3.6 6.6h-7.3z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.49"/><path d="M160.4 125.8l2.1 3.7h-4.1z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.85"/><path d="M213.3 120.5l3.5 6.4h-7.1z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.26"/><path d="M375.7 120.8l2.7 4.8h-5.3z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.77"/><path d="M95.2 143.1l2.3 4.1h-4.5z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.60"/><path d="M358.9 124.9l3.5 6.3h-7.0z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.34"/><path d="M237.6 128.1l2.1 3.7h-4.1z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.89"/><path d="M141.8 130.5l1.6 2.8h-3.1z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.34"/><path d="M404.0 118.4l2.0 3.6h-4.0z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.60"/><path d="M124.7 135.5l2.3 4.2h-4.6z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.77"/><path d="M287.1 135.8l3.7 6.6h-7.3z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.26"/><path d="M338.0 132.0l3.9 7.1h-7.8z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.84"/><path d="M100.8 140.3l2.2 4.0h-4.4z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.49"/><path d="M388.2 114.9l3.1 5.6h-6.2z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.43"/><path d="M189.0 116.1l2.5 4.5h-5.0z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.87"/><path d="M184.2 114.7l4.0 7.1h-7.9z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.28"/><path d="M390.3 114.0l2.8 5.1h-5.7z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.71"/><path d="M102.6 136.8l3.8 6.9h-7.7z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.67"/><path d="M333.4 133.8l1.8 3.2h-3.6z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.30"/><path d="M292.1 134.0l3.9 7.1h-7.9z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.88"/><path d="M122.2 132.5l1.9 3.5h-3.9z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.39"/><path d="M402.7 111.9l3.9 7.0h-7.8z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.54"/><path d="M146.3 122.4l2.2 3.9h-4.3z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.82"/><path d="M232.5 119.9l1.8 3.2h-3.5z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.26"/><path d="M361.9 117.6l2.6 4.7h-5.2z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.80"/><path d="M96.0 135.0l3.3 6.0h-6.6z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.56"/><path d="M371.4 113.9l2.3 4.1h-4.6z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.37"/><path d="M218.7 113.1l3.0 5.4h-6.0z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.89"/><path d="M156.9 116.1l2.8 5.0h-5.6z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.32"/><path d="M401.0 110.3l2.5 4.4h-4.9z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.64"/><path d="M114.0 130.0l2.9 5.3h-5.9z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.73"/><path d="M305.8 134.5l2.1 3.8h-4.3z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.28"/><path d="M321.7 132.0l3.3 5.9h-6.5z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.86"/><path d="M106.0 132.4l1.5 2.7h-3.0z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.45"/><path d="M397.1 106.8l3.8 6.9h-7.6z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.47"/><path d="M170.9 110.6l2.8 5.1h-5.7z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.85"/><path d="M201.7 107.8l3.3 5.9h-6.6z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.27"/><path d="M383.0 106.8l3.4 6.0h-6.7z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.74"/><path d="M95.8 130.5l3.2 5.7h-6.4z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.63"/><path d="M350.8 118.7l2.4 4.3h-4.8z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.33"/><path d="M273.6 120.6l1.7 3.0h-3.3z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.88"/><path d="M131.8 117.9l3.2 5.7h-6.3z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.36"/><path d="M407.3 106.2l2.3 4.2h-4.7z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.58"/><path d="M130.0 118.4l2.3 4.1h-4.6z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.78"/><path d="M275.8 118.1l3.6 6.5h-7.2z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.27"/><path d="M350.0 116.8l3.3 5.9h-6.6z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.82"/><path d="M94.0 128.5l2.3 4.1h-4.5z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.52"/><path d="M386.3 104.2l2.3 4.1h-4.5z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.41"/><path d="M198.8 104.5l2.5 4.5h-5.0z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.87"/><path d="M171.1 105.8l2.5 4.5h-5.0z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.30"/><path d="M400.3 102.6l2.2 4.0h-4.5z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.68"/><path d="M100.9 125.3l1.8 3.3h-3.6z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.69"/><path d="M325.8 125.9l2.6 4.6h-5.1z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.30"/><path d="M305.4 125.1l3.9 6.9h-7.7z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.87"/><path d="M109.7 119.4l3.2 5.7h-6.4z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.42"/><path d="M408.0 99.7l3.8 6.8h-7.5z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.51"/><path d="M151.1 105.5l3.0 5.5h-6.1z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.82"/><path d="M219.8 103.4l2.3 4.1h-4.5z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.27"/><path d="M376.1 102.8l2.9 5.2h-5.7z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.77"/><path d="M87.6 124.8l1.5 2.7h-3.0z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.59"/><path d="M369.7 105.3l2.2 4.0h-4.4z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.36"/><path d="M229.9 104.0l2.6 4.6h-5.1z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.88"/><path d="M141.8 104.9l2.9 5.3h-5.9z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.34"/><path d="M412.3 97.6l3.1 5.6h-6.3z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.62"/><path d="M112.4 113.5l2.7 4.8h-5.3z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.75"/><path d="M296.6 119.5l2.6 4.7h-5.2z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.28"/><path d="M337.0 119.4l2.0 3.7h-4.1z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.84"/><path d="M92.4 118.8l2.7 4.8h-5.4z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.48"/><path d="M401.8 94.6l3.8 6.8h-7.5z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.45"/><path d="M177.6 97.3l3.5 6.3h-7.0z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.85"/><path d="M186.9 98.0l1.9 3.5h-3.8z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.29"/><path d="M398.1 95.8l1.7 3.1h-3.4z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.72"/><path d="M88.1 117.4l2.8 5.0h-5.6z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.65"/><path d="M346.8 112.8l3.1 5.5h-6.2z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.33"/><path d="M287.2 112.5l2.3 4.2h-4.7z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.87"/><path d="M115.7 105.4l3.5 6.4h-7.1z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.39"/><path d="M417.4 92.6l3.4 6.1h-6.8z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.55"/><path d="M131.2 100.2l3.2 5.7h-6.4z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.79"/><path d="M263.9 101.3l2.1 3.7h-4.1z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.28"/><path d="M366.3 103.1l2.0 3.6h-4.0z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.79"/><path d="M82.0 116.3l1.6 2.8h-3.1z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.55"/><path d="M387.8 94.2l2.1 3.8h-4.2z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.40"/><path d="M208.7 92.9l2.7 4.8h-5.4z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.86"/><path d="M155.1 93.9l3.6 6.5h-7.2z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.33"/><path d="M413.7 90.9l1.7 3.0h-3.4z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.65"/><path d="M97.1 107.8l2.5 4.6h-5.1z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.71"/><path d="M318.0 115.7l3.1 5.5h-6.1z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.30"/><path d="M320.6 116.5l2.0 3.6h-4.0z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.84"/><path d="M95.4 106.1l3.2 5.8h-6.5z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.45"/><path d="M413.8 88.0l2.7 4.9h-5.5z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.49"/><path d="M156.8 92.8l2.1 3.8h-4.2z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.82"/><path d="M205.8 89.2l3.1 5.7h-6.3z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.29"/><path d="M390.8 90.9l1.5 2.7h-3.0z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.74"/><path d="M80.2 108.7l3.4 6.1h-6.8z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.61"/><path d="M365.9 98.6l3.4 6.2h-6.9z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.36"/><path d="M266.6 96.1l1.8 3.2h-3.5z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.86"/><path d="M127.2 93.3l2.6 4.6h-5.1z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.37"/><path d="M420.8 86.1l1.9 3.5h-3.9z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.59"/><path d="M114.6 94.0l3.9 7.0h-7.8z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.75"/><path d="M285.1 101.3l2.8 5.0h-5.6z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.30"/><path d="M351.2 105.9l1.6 2.9h-3.3z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.81"/><path d="M83.3 105.1l2.1 3.8h-4.2z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.51"/><path d="M400.9 83.4l3.6 6.5h-7.2z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.44"/><path d="M187.9 86.0l2.6 4.8h-5.3z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.84"/><path d="M173.2 85.7l3.5 6.3h-7.0z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.32"/><path d="M407.6 82.0l3.2 5.7h-6.3z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.69"/><path d="M88.2 99.2l4.0 7.1h-7.9z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.67"/><path d="M337.4 107.3l3.0 5.4h-6.0z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.33"/><path d="M300.5 103.1l3.9 7.0h-7.8z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.84"/><path d="M106.1 91.7l3.7 6.7h-7.5z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.42"/><path d="M417.9 80.0l3.0 5.5h-6.1z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.53"/><path d="M139.9 85.1l3.3 5.9h-6.6z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.79"/><path d="M226.9 84.1l2.8 5.0h-5.5z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.30"/><path d="M376.1 88.4l3.6 6.4h-7.2z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.76"/><path d="M81.1 99.3l2.9 5.2h-5.7z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.57"/><path d="M379.3 86.1l3.7 6.7h-7.5z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.40"/><path d="M221.7 81.1l3.4 6.0h-6.7z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.84"/><path d="M145.2 83.3l2.7 4.8h-5.4z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.36"/><path d="M414.9 77.9l2.1 3.9h-4.3z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.63"/><path d="M105.5 89.3l2.1 3.8h-4.2z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.71"/><path d="M304.8 101.1l3.1 5.6h-6.2z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.32"/><path d="M330.9 103.6l3.4 6.1h-6.8z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.81"/><path d="M94.1 91.3l2.8 5.0h-5.6z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.48"/><path d="M405.1 75.9l3.1 5.5h-6.1z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.48"/><path d="M170.6 80.5l2.2 3.9h-4.4z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.81"/><path d="M194.7 79.0l1.7 3.0h-3.4z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.32"/><path d="M392.5 78.5l2.2 4.0h-4.4z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.71"/><path d="M89.1 91.9l2.2 3.9h-4.4z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.63"/><path d="M351.2 96.7l2.3 4.1h-4.6z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.36"/><path d="M278.8 87.0l2.9 5.1h-5.7z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.83"/><path d="M124.7 81.1l1.8 3.3h-3.7z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.40"/><path d="M411.7 73.2l2.1 3.7h-4.2z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.57"/><path d="M130.5 78.3l3.2 5.8h-6.5z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.75"/><path d="M271.4 81.9l3.3 5.9h-6.5z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.32"/><path d="M354.8 93.5l1.7 3.0h-3.3z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.77"/><path d="M92.4 87.5l2.5 4.5h-5.0z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.54"/><path d="M383.8 77.0l2.9 5.1h-5.7z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.43"/><path d="M203.5 73.5l2.5 4.6h-5.1z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.82"/><path d="M167.9 76.3l2.0 3.6h-4.0z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.35"/><path d="M399.0 71.2l2.6 4.6h-5.1z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.66"/><path d="M106.3 79.6l3.8 6.8h-7.5z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.68"/><path d="M319.5 97.6l3.0 5.3h-5.9z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.35"/><path d="M307.9 94.6l3.2 5.8h-6.5z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.81"/><path d="M113.7 76.7l3.6 6.6h-7.3z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.46"/><path d="M398.8 68.2l3.4 6.1h-6.8z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.52"/><path d="M160.2 73.7l2.5 4.4h-4.9z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.78"/><path d="M216.8 71.3l1.5 2.7h-3.0z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.33"/><path d="M370.0 79.2l2.4 4.3h-4.8z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.73"/><path d="M100.6 79.5l3.4 6.1h-6.8z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.59"/><path d="M356.6 84.3l3.6 6.5h-7.3z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.40"/><path d="M235.0 70.4l3.9 7.0h-7.8z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.81"/><path d="M148.9 71.6l2.5 4.6h-5.1z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.40"/><path d="M395.4 65.5l3.4 6.1h-6.7z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.60"/><path d="M130.4 71.2l2.9 5.2h-5.7z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.71"/><path d="M287.9 82.4l3.0 5.4h-6.0z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.34"/><path d="M330.1 93.6l2.1 3.7h-4.1z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.78"/><path d="M112.7 74.5l2.0 3.7h-4.1z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.51"/><path d="M378.3 69.7l2.6 4.7h-5.2z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.47"/><path d="M191.2 68.5l1.6 2.8h-3.1z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.79"/><path d="M191.9 67.3l2.3 4.2h-4.7z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.36"/><path d="M375.6 68.9l3.2 5.8h-6.4z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.68"/><path d="M117.2 71.3l2.5 4.5h-5.0z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.64"/><path d="M326.9 91.7l1.9 3.4h-3.8z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.38"/><path d="M285.9 78.7l2.7 4.8h-5.3z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.80"/><path d="M139.1 67.9l1.8 3.3h-3.6z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.44"/><path d="M383.1 63.1l3.1 5.5h-6.1z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.55"/><path d="M158.1 67.6l1.6 2.8h-3.1z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.74"/><path d="M235.7 65.4l2.5 4.5h-5.0z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.35"/><path d="M343.9 82.8l2.9 5.2h-5.8z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.73"/><path d="M120.6 69.1l1.6 2.8h-3.1z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.56"/><path d="M353.2 76.4l3.1 5.6h-6.2z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.44"/><path d="M220.1 61.8l1.8 3.3h-3.7z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.79"/><path d="M174.7 64.4l2.7 4.8h-5.3z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.40"/><path d="M372.1 65.0l1.6 2.9h-3.3z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.63"/><path d="M139.3 63.7l2.4 4.4h-4.9z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.68"/><path d="M298.2 82.1l2.0 3.7h-4.1z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.38"/><path d="M306.0 84.7l2.3 4.2h-4.6z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.77"/><path d="M138.3 61.8l3.4 6.1h-6.8z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.49"/><path d="M364.5 65.5l2.4 4.4h-4.9z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.51"/><path d="M186.2 60.6l3.4 6.1h-6.8z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.75"/><path d="M213.3 56.8l3.6 6.4h-7.2z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.38"/><path d="M348.9 74.1l2.1 3.8h-4.3z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.69"/><path d="M135.5 62.1l1.7 3.1h-3.4z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.60"/><path d="M326.6 84.4l1.5 2.8h-3.1z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.42"/><path d="M268.2 61.9l2.8 5.1h-5.7z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.77"/><path d="M165.9 58.8l4.0 7.2h-8.0z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.44"/><path d="M361.2 62.8l2.4 4.3h-4.7z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.58"/><path d="M163.9 58.9l3.1 5.6h-6.3z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.70"/><path d="M273.1 62.3l3.5 6.2h-6.9z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.38"/><path d="M318.3 81.9l3.1 5.6h-6.3z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.73"/><path d="M145.2 56.9l3.4 6.1h-6.8z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.54"/><path d="M342.3 71.1l3.9 7.0h-7.7z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.48"/><path d="M211.6 54.3l2.0 3.6h-4.0z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.75"/><path d="M198.1 56.4l1.6 2.8h-3.1z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.41"/><path d="M345.9 69.0l1.9 3.4h-3.8z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.64"/><path d="M154.8 56.8l1.8 3.3h-3.6z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.64"/><path d="M301.4 76.5l3.2 5.7h-6.3z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.41"/><path d="M285.7 67.7l2.9 5.2h-5.8z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.75"/><path d="M165.1 56.1l2.0 3.7h-4.1z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.48"/><path d="M345.0 65.4l3.2 5.8h-6.5z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.54"/><path d="M188.2 53.9l3.4 6.2h-6.8z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.71"/><path d="M229.6 51.3l1.9 3.5h-3.8z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.40"/><path d="M322.6 76.6l3.0 5.4h-6.0z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.69"/><path d="M158.1 52.5l3.4 6.1h-6.7z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.58"/><path d="M319.3 77.9l1.8 3.2h-3.6z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.46"/><path d="M232.3 48.8l3.5 6.4h-7.1z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.74"/><path d="M190.6 51.3l3.9 7.0h-7.8z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.45"/><path d="M336.3 68.7l1.8 3.2h-3.5z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.60"/><path d="M176.0 53.7l1.6 2.8h-3.1z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.66"/><path d="M279.9 60.6l2.3 4.1h-4.6z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.42"/><path d="M296.0 69.9l3.2 5.7h-6.4z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.71"/><path d="M171.3 50.1l3.9 7.0h-7.8z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.53"/><path d="M325.8 71.9l2.5 4.5h-5.0z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.52"/><path d="M210.0 46.0l3.3 5.9h-6.6z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.71"/><path d="M217.0 46.2l1.7 3.0h-3.4z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.44"/><path d="M319.4 72.4l3.2 5.8h-6.5z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.64"/><path d="M175.1 49.5l3.1 5.5h-6.1z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.61"/><path d="M297.7 70.2l1.8 3.2h-3.5z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.46"/><path d="M270.9 50.3l3.4 6.2h-6.9z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.71"/><path d="M190.9 47.4l3.6 6.5h-7.3z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.49"/><path d="M321.5 70.1l3.0 5.4h-6.0z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.57"/><path d="M197.3 47.6l1.8 3.2h-3.6z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.67"/><path d="M263.8 44.4l4.0 7.1h-7.9z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.45"/><path d="M298.2 67.0l3.5 6.2h-6.9z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.67"/><path d="M184.1 47.7l2.4 4.3h-4.7z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.56"/><path d="M305.0 69.8l2.6 4.6h-5.1z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.51"/><path d="M227.4 40.9l2.4 4.4h-4.9z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.69"/><path d="M212.5 41.3l2.8 5.0h-5.5z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.48"/><path d="M308.5 69.8l2.4 4.2h-4.7z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.61"/><path d="M195.6 43.5l3.6 6.5h-7.2z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.62"/><path d="M279.0 51.4l3.6 6.4h-7.1z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.48"/><path d="M277.5 51.7l1.8 3.2h-3.5z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.67"/><path d="M200.3 41.3l3.9 7.0h-7.8z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.53"/><path d="M301.0 65.4l3.1 5.6h-6.2z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.55"/><path d="M217.5 37.1l3.6 6.4h-7.1z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.65"/><path d="M231.2 37.3l3.3 5.9h-6.5z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.49"/><path d="M289.9 58.5l2.6 4.7h-5.2z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.62"/><path d="M205.4 38.9l3.3 6.0h-6.7z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.58"/><path d="M282.4 50.8l3.9 7.0h-7.8z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.52"/><path d="M262.3 39.0l2.2 3.9h-4.4z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.64"/><path d="M220.6 34.6l3.5 6.3h-7.0z" fill="none" stroke="#8052ff" stroke-width=".8" opacity="0.53"/><path d="M284.4 52.3l2.8 5.1h-5.7z" fill="none" stroke="#ffb829" stroke-width=".8" opacity="0.58"/><path d="M223.0 34.5l2.7 4.9h-5.4z" fill="none" stroke="#15846e" stroke-width=".8" opacity="0.60"/><path d="M264.4 38.1l2.6 4.7h-5.2z" fill="none" stroke="#c565dc" stroke-width=".8" opacity="0.54"/><path d="M266.6 38.1l3.3 6.0h-6.7z" fill="none" stroke="#6688ff" stroke-width=".8" opacity="0.59"/></svg><svg class="splice-art" viewBox="0 0 1100 360" preserveAspectRatio="xMidYMid slice" aria-hidden="true"><path d="M0 300 C250 300 250 70 550 70 S850 290 1100 120 M0 320 C250 320 250 90 550 90 S850 310 1100 140 M0 340 C250 340 250 110 550 110 S850 330 1100 160"/><path class="signal" d="M0 300 C250 300 250 70 550 70 S850 290 1100 120"/></svg><div><h2>从剪接事件，走向新的研究线索。</h2><p>上传事件数据，确认字段与分组，再查看统计结果和研究报告。</p><button class="btn btn-primary" onclick="showUploadModal()">新建分析项目</button><button class="btn btn-secondary" onclick="navigateTo('peptide')">已有肽序列？直接预测</button></div><ol><li><b>01</b><span><strong>准备数据</strong>支持事件表与报告目录导入</span></li><li><b>02</b><span><strong>检查与分析</strong>确认数据映射，跟踪每一步进度</span></li><li><b>03</b><span><strong>探索与导出</strong>浏览候选事件，生成图表与报告</span></li></ol></section>
        <div class="grid grid-2">
          <div class="card">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px;">
              <div style="font-size: 14px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; color: var(--text-secondary);">当前运行 Agent</div>
              <div id="current-agent-indicator" style="display: none;"><span class="status status-running"><span class="status-dot"></span>分析中</span></div>
            </div>
            <div id="current-agent">
              <div style="padding: 40px; text-align: center; color: var(--text-muted);">
                <div style="font-size: 36px; margin-bottom: 12px; opacity: 0.3;"></div>
                <div style="font-size: 14px;">暂无运行中的分析</div>
                <button class="btn btn-primary" style="margin-top: 16px;" onclick="showUploadModal()">启动新分析</button>
              </div>
            </div>
          </div>
          <div class="card">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px;">
              <div style="font-size: 14px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; color: var(--text-secondary);">历史项目</div>
              <button class="btn btn-sm btn-secondary" onclick="loadDashboard()">刷新</button>
            </div>
            <input aria-label="搜索历史项目" id="project-search" type="search" placeholder="搜索历史项目" oninput="renderProjectHistory()" style="width:100%;margin-bottom:12px;padding:9px;border:1px solid var(--border);border-radius:var(--radius-sm);">
            <div id="recent-projects" style="max-height:440px;overflow:auto;">
              <div style="padding: 40px; text-align: center; color: var(--text-muted);">
                <div style="font-size: 36px; margin-bottom: 12px; opacity: 0.3;"></div>
                <div style="font-size: 14px;">暂无项目</div>
              </div>
            </div>
            <div id="storage-hint" style="margin-top:12px;padding-top:10px;border-top:1px solid var(--border);font-size:12px;line-height:1.6;color:var(--text-muted);">
              数据目录：读取中…
            </div>
          </div>
        </div>

        <div class="detail-drawer-backdrop" id="detail-backdrop" onclick="closeProjectDetail()" aria-hidden="true"></div>
        <section class="card detail-drawer" id="project-detail" aria-label="历史项目详情">
          <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:16px;margin-bottom:20px;flex-wrap:wrap;">
            <div>
              <div style="font-size:12px;font-weight:600;letter-spacing:1px;text-transform:uppercase;color:var(--text-muted);">历史项目详情</div>
              <div style="font-size:20px;font-weight:600;margin-top:4px;" id="detail-title">-</div>
              <div style="font-size:12px;color:var(--text-secondary);margin-top:6px;" id="detail-meta">-</div>
            </div>
            <div style="display:flex;gap:8px;flex-wrap:wrap;">
              <button class="btn btn-sm btn-secondary" type="button" onclick="closeProjectDetail()">关闭详情</button>
              <button class="btn btn-sm btn-secondary" onclick="openReport('html')"> 打开 HTML 报告</button>
              <button class="btn btn-sm btn-secondary" onclick="openReport('pdf')"> 下载 PDF</button>
              <button class="btn btn-sm btn-secondary" onclick="revealProjectBundle()"> 成果文件夹</button>
              <button class="btn btn-sm btn-secondary" onclick="packageProject()"> 打包 ZIP</button>
              <button class="btn btn-sm btn-secondary" onclick="jumpToExplorer()"> 浏览全部事件</button>
              <button class="btn btn-sm btn-danger" onclick="deleteCurrentProject()" style="color:var(--danger);"> 删除项目</button>
            </div>
          </div>
          <div id="detail-bundle-hint" style="font-size:12px;color:var(--text-muted);margin:-6px 0 10px;"></div>
          <div class="grid grid-2" style="gap:20px;">
            <div>
              <div style="font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:.8px;color:var(--text-muted);margin-bottom:10px;">样本分组</div>
              <div id="detail-groups" style="display:flex;flex-wrap:wrap;gap:8px;"></div>
              <div style="font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:.8px;color:var(--text-muted);margin:20px 0 10px;">事件类型分布</div>
              <div id="detail-types" style="display:flex;flex-wrap:wrap;gap:8px;"></div>
              <div style="font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:.8px;color:var(--text-muted);margin:20px 0 10px;">流程日志（最近 12 条）</div>
              <div id="detail-logs" style="max-height:220px;overflow:auto;font-size:12px;line-height:1.7;"></div>
            </div>
            <div>
              <div style="font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:.8px;color:var(--text-muted);margin-bottom:10px;">图表（点击放大）</div>
              <div id="detail-figures" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:10px;"></div>
              <div style="font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:.8px;color:var(--text-muted);margin:20px 0 10px;">候选事件 Top 10</div>
              <div id="detail-candidates" style="max-height:260px;overflow:auto;font-size:12px;"></div>
            </div>
          </div>
        </section>
      </div>
      <div class="page" id="page-pipeline"><header class="workspace-heading"><div><h1>分析流程</h1><p>查看数据处理、统计分析与解读进度，定位当前执行阶段。</p></div></header>
        <div class="card" style="margin-bottom: 24px;">
          <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px;">
            <div>
              <div style="font-size: 16px; font-weight: 600;">分析进度</div>
              <div style="font-size: 13px; color: var(--text-secondary); margin-top: 4px;" id="pipeline-status-text">等待启动...</div>
            </div>
            <div id="pipeline-progress" style="font-size: 20px; font-weight: 600; color: var(--accent);">0%</div>
          </div>
          <div style="height: 8px; background: var(--gray-100); border-radius: var(--radius-sm); overflow: hidden; box-shadow: inset 0 1px 2px rgba(0,0,0,0.05);">
            <div id="progress-bar" style="height: 100%; width: 0%; background: var(--black); transition: width 0.5s cubic-bezier(0.4, 0, 0.2, 1); box-shadow: 0 2px 4px rgba(8, 145, 178, 0.3);"></div>
          </div>
        </div>
        
        <div class="card" style="margin-bottom: 24px;">
          <div style="font-size: 14px; font-weight: 600; margin-bottom: 16px; color: var(--text);">Agent 工作流</div>
          <div class="pipeline" id="pipeline-steps">
            <div class="pipeline-step waiting">
              <div class="step-number">1</div>
              <div class="step-info">
                <div class="step-name"> 数据 Agent</div>
                <div class="step-desc">加载并验证输入数据，检查文件格式和完整性</div>
              </div>
              <span class="status status-waiting"><span class="status-dot"></span>等待中</span>
            </div>
            <div class="pipeline-step waiting">
              <div class="step-number">2</div>
              <div class="step-info">
                <div class="step-name"> 质控 Agent</div>
                <div class="step-desc">执行质量控制检查，过滤低质量样本</div>
              </div>
              <span class="status status-waiting"><span class="status-dot"></span>等待中</span>
            </div>
            <div class="pipeline-step waiting">
              <div class="step-number">3</div>
              <div class="step-info">
                <div class="step-name"> 剪接检测 Agent</div>
                <div class="step-desc">使用统计模型检测可变剪接事件</div>
              </div>
              <span class="status status-waiting"><span class="status-dot"></span>等待中</span>
            </div>
            <div class="pipeline-step waiting">
              <div class="step-number">4</div>
              <div class="step-info">
                <div class="step-name"> 统计 Agent</div>
                <div class="step-desc">计算显著性（FDR）和效应量（Delta PSI）</div>
              </div>
              <span class="status status-waiting"><span class="status-dot"></span>等待中</span>
            </div>
            <div class="pipeline-step waiting">
              <div class="step-number">5</div>
              <div class="step-info">
                <div class="step-name"> 注释 Agent</div>
                <div class="step-desc">功能注释、通路富集和文献证据收集</div>
              </div>
              <span class="status status-waiting"><span class="status-dot"></span>等待中</span>
            </div>
            <div class="pipeline-step waiting">
              <div class="step-number">6</div>
              <div class="step-info">
                <div class="step-name"> 解读 Agent</div>
                <div class="step-desc">生成生物学解读和专业分析报告</div>
              </div>
              <span class="status status-waiting"><span class="status-dot"></span>等待中</span>
            </div>
          </div>
        </div>
      </div>
      <div class="page" id="page-explorer"><header class="workspace-heading"><div><h1>事件浏览器</h1><p>按基因、事件类型与显著性筛选，追溯候选事件的统计依据。</p></div></header>
        <div class="card" style="margin-bottom: 24px;">
          <div style="font-size: 16px; font-weight: 600; margin-bottom: 20px;">筛选条件</div>
          <div class="search-bar" style="margin-bottom: 20px;">
            <input type="text" class="search-input" placeholder="搜索基因名称、事件ID或染色体位置..." aria-label="搜索事件" id="search-input" onkeypress="if(event.key==='Enter') applyFilters()">
            <button class="btn btn-primary" onclick="applyFilters()"> 应用筛选</button>
          </div>
          <div class="filters" style="margin-bottom: 0;">
            <div class="filter-group">
              <div class="filter-label">事件类型</div>
              <div class="checkbox-group">
                <label class="checkbox-label"><input type="checkbox" value="SE" checked> SE (外显子跳跃)</label>
                <label class="checkbox-label"><input type="checkbox" value="MXE" checked> MXE (互斥外显子)</label>
                <label class="checkbox-label"><input type="checkbox" value="A3SS" checked> A3SS (可变3'剪接)</label>
                <label class="checkbox-label"><input type="checkbox" value="A5SS" checked> A5SS (可变5'剪接)</label>
                <label class="checkbox-label"><input type="checkbox" value="RI" checked> RI (内含子保留)</label>
              </div>
            </div>
            <div class="filter-group">
              <div class="filter-label">统计阈值</div>
              <div style="display: flex; gap: 20px; flex-wrap: wrap; align-items: center;">
                <label class="checkbox-label"><input type="checkbox" id="filter-significant"> 仅显著事件</label>
                <label class="checkbox-label">排序
                  <select id="filter-order" style="margin-left:6px;padding:6px 8px;border:1px solid var(--border);border-radius:var(--radius-sm);background:transparent;color:var(--text);font-family:inherit;font-size:12px;">
                    <option value="fdr">按 FDR</option>
                    <option value="delta_psi">按 |ΔPSI|</option>
                    <option value="gene">按基因名</option>
                  </select>
                </label>
              </div>
            </div>
          </div>
        </div>
        <div class="table-container">
          <table>
            <thead>
              <tr>
                <th>事件 ID</th>
                <th>基因</th>
                <th>类型</th>
                <th class="num">ΔPSI</th>
                <th class="num">FDR</th>
                <th aria-label="查看详情"></th>
              </tr>
            </thead>
            <tbody id="events-table">
              <tr>
                <td colspan="6" style="text-align: center; padding: 60px; color: var(--text-muted);">
                  <div style="font-size: 36px; margin-bottom: 16px; opacity: 0.3;"></div>
                  <div style="font-size: 16px; font-weight: 600;">未加载事件数据</div>
                  <div style="font-size: 14px; margin-top: 8px;">请完成分析后查看结果</div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div id="events-pager" style="display:flex;align-items:center;justify-content:space-between;gap:12px;margin-top:16px;flex-wrap:wrap;font-size:13px;color:var(--text-secondary);">
          <div id="events-pager-info">-</div>
          <div style="display:flex;gap:8px;align-items:center;">
            <button class="btn btn-sm btn-secondary" onclick="gotoEventPage(1)">首页</button>
            <button class="btn btn-sm btn-secondary" onclick="gotoEventPage(state.eventPage - 1)">上一页</button>
            <span id="events-pager-page">1 / 1</span>
            <button class="btn btn-sm btn-secondary" onclick="gotoEventPage(state.eventPage + 1)">下一页</button>
            <button class="btn btn-sm btn-secondary" onclick="gotoEventPage(state.eventPages)">末页</button>
          </div>
        </div>
      </div>
      <div class="page" id="page-visualization"><header class="workspace-heading"><div><h1>可视化工作室</h1><p>选择研究问题对应的图表，查看当前项目的可视化结果。</p></div></header>
        <div class="mobile-chart-select"><label for="chart-select-mobile">图表类型</label><select id="chart-select-mobile" onchange="if(this.value) loadChart(this.value)"><option value="">选择要查看的图表</option><option value="volcano">火山图 Volcano</option><option value="dpsi_waterfall">ΔPSI 瀑布图 Waterfall</option><option value="dpsi_ecdf">ΔPSI 累积分布 ECDF</option><option value="fdr_scree">显著性碎石图 Scree</option><option value="event_type_counts">事件类型分布</option><option value="event_significance">类型×显著性堆叠图</option><option value="event_schematic">剪接机制示意图 Schematic</option><option value="psi_heatmap">PSI 热图 Heatmap</option><option value="psi_distribution">分组 PSI 箱线图</option><option value="sample_composition">队列构成图</option><option value="candidate_ranking">候选基因排名</option><option value="score_components">评分分解堆叠图</option><option value="enrichment">功能富集点图</option></select></div><div class="grid grid-2">
          <div>
            <div class="card" style="margin-bottom: 20px;">
              <div style="font-size: 14px; font-weight: 600; margin-bottom: 6px; color: var(--text);"> 核心统计图</div>
              <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 14px;">差异剪接的显著性与效应量</div>
              <div style="display: flex; flex-direction: column; gap: 10px;">
                <button class="btn btn-secondary" onclick="loadChart('volcano')" style="justify-content: flex-start; padding: 12px 16px; text-align: left;">
                  <div><div style="font-weight: 600; margin-bottom: 2px;"> 火山图 Volcano</div><div style="font-size: 12px; color: var(--text-secondary); font-weight: 400;">ΔPSI vs -log10(FDR)，标注显著性阈值</div></div>
                </button>
                <button class="btn btn-secondary" onclick="loadChart('dpsi_waterfall')" style="justify-content: flex-start; padding: 12px 16px; text-align: left;">
                  <div><div style="font-weight: 600; margin-bottom: 2px;"> ΔPSI 瀑布图 Waterfall</div><div style="font-size: 12px; color: var(--text-secondary); font-weight: 400;">Top 25 效应量排序，区分包含上调/下调</div></div>
                </button>
                <button class="btn btn-secondary" onclick="loadChart('dpsi_ecdf')" style="justify-content: flex-start; padding: 12px 16px; text-align: left;">
                  <div><div style="font-weight: 600; margin-bottom: 2px;"> ΔPSI 累积分布 ECDF</div><div style="font-size: 12px; color: var(--text-secondary); font-weight: 400;">效应量经验累积分布与阈值占比</div></div>
                </button>
                <button class="btn btn-secondary" onclick="loadChart('fdr_scree')" style="justify-content: flex-start; padding: 12px 16px; text-align: left;">
                  <div><div style="font-weight: 600; margin-bottom: 2px;"> 显著性碎石图 Scree</div><div style="font-size: 12px; color: var(--text-secondary); font-weight: 400;">候选排名 vs -log10(FDR)，定位显著性拐点</div></div>
                </button>
              </div>
            </div>
            <div class="card" style="margin-bottom: 20px;">
              <div style="font-size: 14px; font-weight: 600; margin-bottom: 6px; color: var(--text);"> 事件组成与机制</div>
              <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 14px;">剪接事件类型构成与分子机制</div>
              <div style="display: flex; flex-direction: column; gap: 10px;">
                <button class="btn btn-secondary" onclick="loadChart('event_type_counts')" style="justify-content: flex-start; padding: 12px 16px; text-align: left;">
                  <div><div style="font-weight: 600; margin-bottom: 2px;"> 事件类型分布</div><div style="font-size: 12px; color: var(--text-secondary); font-weight: 400;">SE/MXE/A5SS/A3SS/RI 五类事件计数</div></div>
                </button>
                <button class="btn btn-secondary" onclick="loadChart('event_significance')" style="justify-content: flex-start; padding: 12px 16px; text-align: left;">
                  <div><div style="font-weight: 600; margin-bottom: 2px;"> 类型×显著性堆叠图</div><div style="font-size: 12px; color: var(--text-secondary); font-weight: 400;">各类型中显著与非显著事件构成</div></div>
                </button>
                <button class="btn btn-secondary" onclick="loadChart('event_schematic')" style="justify-content: flex-start; padding: 12px 16px; text-align: left;">
                  <div><div style="font-weight: 600; margin-bottom: 2px;"> 剪接机制示意图 Schematic</div><div style="font-size: 12px; color: var(--text-secondary); font-weight: 400;">五类可变剪接的外显子-内含子结构模式图</div></div>
                </button>
              </div>
            </div>
            <div class="card" style="margin-bottom: 20px;">
              <div style="font-size: 14px; font-weight: 600; margin-bottom: 6px; color: var(--text);"> 样本与质控</div>
              <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 14px;">队列构成与样本水平 PSI 模式</div>
              <div style="display: flex; flex-direction: column; gap: 10px;">
                <button class="btn btn-secondary" onclick="loadChart('psi_heatmap')" style="justify-content: flex-start; padding: 12px 16px; text-align: left;">
                  <div><div style="font-weight: 600; margin-bottom: 2px;"> PSI 热图 Heatmap</div><div style="font-size: 12px; color: var(--text-secondary); font-weight: 400;">Top 事件逐样本 PSI 聚类热图</div></div>
                </button>
                <button class="btn btn-secondary" onclick="loadChart('psi_distribution')" style="justify-content: flex-start; padding: 12px 16px; text-align: left;">
                  <div><div style="font-weight: 600; margin-bottom: 2px;"> 分组 PSI 箱线图</div><div style="font-size: 12px; color: var(--text-secondary); font-weight: 400;">各组 PSI 分布与离群样本检测</div></div>
                </button>
                <button class="btn btn-secondary" onclick="loadChart('sample_composition')" style="justify-content: flex-start; padding: 12px 16px; text-align: left;">
                  <div><div style="font-weight: 600; margin-bottom: 2px;"> 队列构成图</div><div style="font-size: 12px; color: var(--text-secondary); font-weight: 400;">分组占比与批次分布（QC 必备）</div></div>
                </button>
              </div>
            </div>
            <div class="card">
              <div style="font-size: 14px; font-weight: 600; margin-bottom: 6px; color: var(--text);"> AI 排序与功能富集</div>
              <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 14px;">智能体候选评分与通路注释</div>
              <div style="display: flex; flex-direction: column; gap: 10px;">
                <button class="btn btn-secondary" onclick="loadChart('candidate_ranking')" style="justify-content: flex-start; padding: 12px 16px; text-align: left;">
                  <div><div style="font-weight: 600; margin-bottom: 2px;"> 候选基因排名</div><div style="font-size: 12px; color: var(--text-secondary); font-weight: 400;">综合评分 Top 15 候选事件条形图</div></div>
                </button>
                <button class="btn btn-secondary" onclick="loadChart('score_components')" style="justify-content: flex-start; padding: 12px 16px; text-align: left;">
                  <div><div style="font-weight: 600; margin-bottom: 2px;"> 评分分解堆叠图</div><div style="font-size: 12px; color: var(--text-secondary); font-weight: 400;">显著性/效应/生物学/文献四维贡献</div></div>
                </button>
                <button class="btn btn-secondary" onclick="loadChart('enrichment')" style="justify-content: flex-start; padding: 12px 16px; text-align: left;">
                  <div><div style="font-weight: 600; margin-bottom: 2px;"> 功能富集点图</div><div style="font-size: 12px; color: var(--text-secondary); font-weight: 400;">GO/KEGG 富集倍数 vs FDR 气泡图</div></div>
                </button>
              </div>
            </div>
          </div>
          <div>
            <div class="chart-container" id="chart-display" style="min-height: 600px; position: sticky; top: 88px;">
              <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; color: var(--text-muted);">
                <div style="font-size: 36px; margin-bottom: 20px; opacity: 0.3;"></div>
                <div style="font-size: 16px; font-weight: 600; margin-bottom: 8px;">选择图表类型</div>
                <div style="font-size: 14px;">选择图表后，预览将在这里显示</div>
              </div>
            </div>
          </div>
        </div>
      </div>
      <div class="page" id="page-gene"><header class="workspace-heading"><div><h1>基因探索</h1><p>以基因为线索，连接剪接事件、统计结果与生物学证据。</p></div></header>
        <div class="search-bar">
          <input type="text" class="search-input" placeholder="输入基因符号（如 TP53、BRCA1、MYC）..." aria-label="基因符号" id="gene-search" onkeypress="if(event.key==='Enter') exploreGene()">
          <button class="btn btn-primary" onclick="exploreGene()"> 探索</button>
        </div>
        <div style="margin-bottom: 24px; padding: 20px; background: var(--gray-100); border-radius: var(--radius); border-left: 1px solid var(--gray-700);">
          <div style="font-size: 13px; font-weight: 600; color: var(--secondary); margin-bottom: 8px;"> 提示</div>
          <div style="font-size: 13px; line-height: 1.8; color: var(--text);">
            输入基因符号查看该基因的所有剪接事件、统计信息和文献证据。支持热门基因如 TP53、BRCA1、MYC、EGFR 等。
          </div>
        </div>
        <div id="gene-details">
          <div class="card">
            <div style="padding: 60px; text-align: center; color: var(--text-muted);">
              <div style="font-size: 36px; margin-bottom: 16px; opacity: 0.3;"></div>
              <div style="font-size: 16px; font-weight: 600; margin-bottom: 8px;">探索基因剪接模式</div>
              <div style="font-size: 14px;">在上方输入基因符号以探索其剪接事件和生物学功能</div>
            </div>
          </div>
        </div>
      </div>
      <div class="page" id="page-report"><header class="workspace-heading"><div><h1>报告与交付</h1><p>将当前项目的统计结果、图表和解读整理为可分享的研究报告。</p></div></header>
        <div class="card">
          <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 24px;">
            <div>
              <div style="font-size: 16px; font-weight: 600; margin-bottom: 4px;">生成分析报告</div>
              <div style="font-size: 13px; color: var(--text-secondary);">基于当前分析结果生成专业报告</div>
            </div>
            <div style="display: flex; gap: 12px;">
              <button class="btn btn-primary" onclick="generateReport('html')">
                <span> HTML 报告</span>
              </button>
              <button class="btn btn-secondary" onclick="generateReport('pdf')">
                <span> PDF 报告</span>
              </button>
            </div>
          </div>
          
          <div id="report-output">
            <div style="padding: 40px; text-align: center; color: var(--text-muted);">
              <div style="font-size: 36px; margin-bottom: 20px; opacity: 0.3;"></div>
              <div style="font-size: 16px; font-weight: 600; margin-bottom: 8px;">准备生成报告</div>
              <div style="font-size: 14px;">完成分析后可生成包含统计结果、可视化和生物学解读的专业报告</div>
            </div>
          </div>
          
          <div style="margin-top: 24px; padding: 20px; background: var(--gray-100); border-radius: var(--radius); border-left: 1px solid var(--black);">
            <div style="font-size: 13px; font-weight: 600; color: var(--accent); margin-bottom: 8px;"> 报告内容</div>
            <div style="font-size: 13px; line-height: 1.8; color: var(--text);">
              <div>• 项目概览与样本统计</div>
              <div>• 显著剪接事件列表（FDR < 0.05）</div>
              <div>• 关键基因的功能注释与通路富集</div>
              <div>• 可视化图表（火山图、热图、分布图）</div>
              <div>• AI 生成的生物学解读与建议</div>
            </div>
          </div>
        </div>
      </div>
      
      
      <div class="page" id="page-trace"><header class="workspace-heading"><div><h1>决策轨迹</h1><p>一次分析里，每一步由谁决定、依据是什么，以及模型与工具各自做了什么。数值计算仍由确定性工具完成。</p></div>
        <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
          <select id="trace-project" class="trace-control" style="min-width:230px" onchange="loadDecisionTrace()"></select>
          <button class="btn btn-sm btn-secondary" onclick="loadDecisionTrace()">刷新轨迹</button>
        </div></header>
        <div id="trace-summary" class="grid grid-4" style="margin-bottom:16px;"></div>
        <div class="card" style="margin-bottom:16px;">
          <div style="font-size:16px;font-weight:600;margin-bottom:6px;">完整性与重放校验</div>
          <div id="trace-integrity" class="trace-meta">选择项目后加载轨迹…</div>
          <div style="display:flex;gap:8px;margin-top:12px;flex-wrap:wrap;">
            <input id="trace-compare-right" class="trace-control" placeholder="另一个 agent_state.json 路径（可选）" style="flex:1;min-width:260px;">
            <button class="btn btn-sm btn-secondary" onclick="compareDecisionTrace()">对比两次运行</button>
          </div>
          <div id="trace-compare-result" class="trace-meta" style="margin-top:10px;"></div>
        </div>
        <div class="grid grid-2">
          <div class="card"><div style="font-size:16px;font-weight:600;margin-bottom:12px;">决策时间线</div><div id="trace-steps"></div></div>
          <div class="card"><div style="font-size:16px;font-weight:600;margin-bottom:12px;">模型与工具调用</div><div id="trace-calls"></div></div>
        </div>
      </div>

      <div class="page" id="page-mission"><header class="workspace-heading"><div><h1>自主任务</h1><p>用一句科研目标生成可审阅的分析计划；确认后自主执行，并给出可离线复现的证明。</p></div></header>
        <div class="card" style="margin-bottom:16px;">
          <div style="font-size:16px;font-weight:600;margin-bottom:10px;">1 · 描述目标</div>
          <textarea id="mission-query" class="trace-control" rows="2" style="width:100%;resize:vertical;" placeholder="例如：为 UPF1 敲低样本找 3 个可验证的 MHC-I 新抗原候选">为 UPF1 敲低样本找 3 个可验证的 MHC-I 新抗原候选</textarea>
          <div style="display:flex;gap:8px;margin-top:10px;flex-wrap:wrap;align-items:center;">
            <input id="mission-input" class="trace-control" style="flex:1;min-width:280px;" placeholder="输入数据目录，例如 E:/rMATS_data/UPF1_KD_vs_scr2">
            <button class="btn btn-sm btn-primary" onclick="missionGenerate()">生成计划</button>
          </div>
          <div id="mission-plan-status" class="trace-meta" style="margin-top:8px;"></div>
          <div class="trace-meta" style="margin-top:4px;color:var(--text-muted);">输入目录请指向含 sample_metadata.tsv 的单个数据集文件夹；不要填多个数据集共用的上级目录，否则样本分组读不到，会筛不出显著事件。</div>
        </div>
        <div class="card" id="mission-plan-card" style="margin-bottom:16px;display:none;">
          <div style="font-size:16px;font-weight:600;margin-bottom:10px;">2 · 审阅并修改计划（这份契约会随运行一起存档）</div>
          <div class="grid grid-2">
            <div><div class="trace-meta">目标</div><input id="mission-goal" class="trace-control" style="width:100%;"></div>
            <div><div class="trace-meta">意图</div><select id="mission-intent" class="trace-control" style="width:100%;"><option value="differential_AS">差异可变剪接</option><option value="neoantigen">新抗原 / 肽预测</option><option value="exploration">数据探索</option></select></div>
          </div>
          <div class="grid grid-4" style="margin-top:10px;">
            <div><div class="trace-meta">FDR 阈值</div><input id="mission-fdr" class="trace-control" style="width:100%;" type="number" step="0.01" min="0.001" max="0.99"></div>
            <div><div class="trace-meta">|dPSI| 阈值</div><input id="mission-dpsi" class="trace-control" style="width:100%;" type="number" step="0.01" min="0.001" max="0.99"></div>
            <div><div class="trace-meta">候选数上限</div><input id="mission-topn" class="trace-control" style="width:100%;" type="number" min="1" max="200"></div>
            <div><div class="trace-meta">最大步数</div><input id="mission-steps" class="trace-control" style="width:100%;" type="number" min="1" max="60"></div>
          </div>
          <div style="margin-top:10px;"><div class="trace-meta">允许调用的工具（每行一个；删掉即不允许该动作）</div>
            <textarea id="mission-tools" class="trace-control" rows="7" style="width:100%;resize:vertical;font-family:var(--font-mono,monospace);font-size:12px;"></textarea></div>
          <div id="mission-plan-meta" class="trace-meta" style="margin-top:8px;"></div>
          <div style="display:flex;gap:8px;margin-top:12px;flex-wrap:wrap;">
            <button class="btn btn-sm btn-primary" onclick="missionRun()">确认并执行</button>
            <span class="trace-meta">阈值与预算来自本机配置，模型不能改写。</span>
          </div>
        </div>
        <div class="card" id="mission-result" style="display:none;">
          <div style="font-size:16px;font-weight:600;margin-bottom:10px;">3 · 执行结果与可复现证明</div>
          <div id="mission-status-banner"></div>
          <div id="mission-artifacts"></div>
          <div id="mission-run-summary" class="trace-meta" style="margin-top:8px;"></div>
          <div id="mission-deviations" style="margin-top:12px;"></div>
          <div id="mission-proof" style="margin-top:12px;"></div>
          <div class="mission-actions">
            <button class="btn btn-sm btn-primary" onclick="missionOpenReport('html')">打开本次报告</button>
            <button class="btn btn-sm btn-secondary" onclick="missionOpenReport('pdf')">打开 PDF</button>
            <button class="btn btn-sm btn-secondary" onclick="missionVerify()">一键离线重放验证</button>
            <button class="btn btn-sm btn-secondary" onclick="missionCopyProof()">复制重放命令</button>
            <button class="btn btn-sm btn-secondary" onclick="missionOpenTrace()">查看决策轨迹</button>
          </div>
          <div id="mission-verify-result" class="trace-meta" style="margin-top:10px;"></div>
        </div>
      </div>
<div class="page" id="page-settings"><header class="workspace-heading"><div><h1>工作区设置</h1><p>配置 AI 解读服务与外部工具，查看连接状态。</p></div></header>
        <div class="grid grid-2">
          <div class="card">
            <div style="font-size: 16px; font-weight: 600; margin-bottom: 6px;"> 模型配置</div>
            <div style="font-size: 13px; color: var(--text-secondary); margin-bottom: 18px;">
              用于报告里的 AI 解读与 MCP 工具的自然语言调用。密钥只保存在本机，不会写入报告或日志。
            </div>
            <div class="model-config-body" style="display: block;">
              <div class="cfg-row"><label for="cfg-base">Base URL</label><input id="cfg-base" type="text" autocomplete="off" placeholder="https://api.deepseek.com"></div>
              <div class="cfg-row"><label for="cfg-model">模型名</label><input id="cfg-model" type="text" autocomplete="off" placeholder="deepseek-flash"></div>
              <div class="cfg-row"><label for="cfg-key">API Key</label><input id="cfg-key" type="password" autocomplete="off" placeholder="留空则保持当前密钥"></div>
              <div class="cfg-row">
                <button class="btn btn-primary btn-sm" id="cfg-save" type="button" onclick="saveModelConfig()">保存并启用</button>
                <span class="cfg-msg" id="cfg-msg"></span>
              </div>
              <div class="cfg-row" style="margin-top: 12px;">
                <span class="status status-waiting" id="cfg-status"><span class="status-dot"></span><span id="cfg-status-text">检查中…</span></span>
              </div>
              <div class="cfg-hint">密钥仅保存在本机 .env / 配置大模型.env，保存后即时生效。</div>
            </div>
          </div>

          <div class="card">
            <div class="mcp-panel" id="mcp-panel">
              <div class="mcp-head">
                <div>
                  <div class="mcp-title"> MCP 工具</div>
                  <div class="mcp-sub">Model Context Protocol · 运行时外部工具调用</div>
                </div>
                <span class="mcp-badge" id="mcp-status">未加载</span>
              </div>

              <div class="mcp-field">
                <label for="mcp-agent-question">自然语言指令</label>
                <div class="mcp-inline">
                  <input id="mcp-agent-question" type="text" placeholder="例如：查一下 CD44 有哪些显著剪接事件" onkeypress="if(event.key==='Enter') runMcpAgent()">
                  <button class="btn btn-primary btn-sm" id="mcp-agent-btn" type="button" onclick="runMcpAgent()">AI 调用</button>
                </div>
                <div class="mcp-hint" id="mcp-agent-status">模型选择 MCP 工具 → 本地校验 → 执行并返回结果</div>
              </div>

              <div class="mcp-field">
                <label for="mcp-server-select">MCP 服务器</label>
                <div class="mcp-inline">
                  <select id="mcp-server-select" onchange="onMcpServerChange()"></select>
                  <button class="btn btn-secondary btn-sm" type="button" onclick="loadMcpServers(true)">刷新</button>
                </div>
                <div class="mcp-hint" id="mcp-server-hint">正在读取服务器配置…</div>
              </div>

              <div class="mcp-field">
                <label for="mcp-ext-url">连接外部 MCP 服务器（访问外网）</label>
                <div class="mcp-inline">
                  <input id="mcp-ext-name" type="text" placeholder="名称，例如 remote-tools" style="width:34%;">
                  <input id="mcp-ext-url" type="text" placeholder="https://host/mcp" style="flex:1;">
                  <button class="btn btn-secondary btn-sm" type="button" onclick="addExternalMcpServer()">连接</button>
                </div>
                <div class="mcp-hint" id="mcp-ext-status">配置保存在 ~/.epitoperank/mcp/servers.json；内置 web_fetch 工具可直接访问白名单域名。</div>
              </div>

              <div class="mcp-field">
                <label for="mcp-tool-select">工具</label>
                <select id="mcp-tool-select" onchange="onMcpToolChange()"></select>
                <div class="mcp-desc" id="mcp-tool-desc">选择服务器与工具后调用</div>
              </div>

              <div class="mcp-field">
                <label for="mcp-args">参数（JSON）</label>
                <textarea id="mcp-args" spellcheck="false" rows="4">{}</textarea>
              </div>

              <div class="mcp-actions">
                <button class="btn btn-primary btn-sm" id="mcp-call-btn" type="button" onclick="callMcpTool()">调用工具</button>
                <span class="mcp-hint" id="mcp-call-status"></span>
              </div>

              <pre class="mcp-result" id="mcp-result">尚未调用</pre>
            </div>
          </div>
        </div>
      </div>
    <div class="page" id="page-neoantigen"><header class="workspace-heading"><div><h1>剪接候选新抗原</h1><p>检查编码序列，生成跨连接点候选肽，再进入结合预测与证据审计。</p></div></header>
      <div class="card" style="max-width: 880px; padding: 24px;">
        <h2>剪接来源候选新抗原</h2>
        <p>使用当前项目查找候选肽。先检查数据，再决定是否进行 HLA 结合预测。</p>
        <div style="padding:16px;border:1px solid var(--border);border-radius:var(--radius);margin:16px 0;">
          <strong>第一步：检查项目数据</strong>
          <p style="margin:6px 0 12px;">系统会检查剪接事件和生成肽所需的编码序列表。</p>
          <button class="btn btn-secondary" type="button" id="neo-check" onclick="checkNeoReadiness()">检查当前项目</button>
          <div id="neo-readiness" style="white-space:pre-wrap;margin-top:12px;" aria-live="polite">请先选择一个项目。</div>
        </div>
        <div style="padding:16px;border:1px solid var(--border);border-radius:var(--radius);margin:16px 0;">
          <strong>可选：从 rMATS 事件自动重建编码序列表（ORF 重建）</strong>
          <p style="margin:6px 0 12px;">不需要外部脚本。平台读取项目里的原始 rMATS 表，参考转录本 CDS 结构重建「参考 / 改变后」CDS 对并写入项目目录；完成后第二步会自动选中它。仅重建 SE 与 RI，其余事件类型会记录跳过原因。</p>
          <div style="display:grid;grid-template-columns:repeat(2,1fr);gap:10px;">
            <label for="orf-source">参考源</label>
            <select id="orf-source" onchange="toggleOrfSource()" style="padding:8px;"><option value="ensembl">Ensembl REST（在线 GRCh38）</option><option value="local">本地 GTF + FASTA（离线可复现）</option></select>
            <label for="orf-max-events">最多处理事件数</label>
            <input id="orf-max-events" type="number" value="12" min="1" max="200" style="padding:8px;">
            <label for="orf-fdr">FDR 上限</label>
            <input id="orf-fdr" type="number" value="0.05" step="0.01" min="0" style="padding:8px;">
            <label for="orf-dpsi">|ΔPSI| 下限</label>
            <input id="orf-dpsi" type="number" value="0.1" step="0.05" min="0" style="padding:8px;">
          </div>
          <div id="orf-local-fields" style="display:none;margin:10px 0;">
            <label for="orf-gtf">GTF 文件路径（项目目录或运行根内）</label>
            <input id="orf-gtf" type="text" placeholder="例如 annotation.gtf" style="display:block;width:100%;padding:8px;margin:4px 0 8px;">
            <label for="orf-fasta">基因组 FASTA 路径（项目目录或运行根内）</label>
            <input id="orf-fasta" type="text" placeholder="例如 genome.fa" style="display:block;width:100%;padding:8px;margin:4px 0 8px;">
          </div>
          <label for="orf-event-ids">指定事件 ID（可选，逗号分隔，留空则取显著事件）</label>
          <input id="orf-event-ids" type="text" placeholder="例如 SE:77508,RI:5737" style="display:block;width:100%;padding:8px;margin:4px 0 12px;">
          <button class="btn btn-secondary" type="button" id="orf-build" onclick="buildOrfTable()">自动重建编码序列表</button>
          <div id="orf-status" style="margin-top:12px;white-space:pre-wrap;" aria-live="polite"></div>
        </div>
        <div style="padding:16px;border:1px solid var(--border);border-radius:var(--radius);margin:16px 0;">
          <strong>第二步：选择编码序列表，生成候选肽</strong>
          <p style="margin:6px 0 10px;">编码序列表就是「每个剪接事件对应的参考 CDS 与改变后 CDS」。系统按表头自动识别，<b>文件名不限</b>；下面若已列出文件，直接选即可。</p>
          <label for="neo-cds-select">编码序列表</label>
          <select id="neo-cds-select" style="display:block;width:100%;padding:10px;margin:8px 0 10px;"></select>
          <div id="neo-mapping-panel" style="display:none;border:1px solid var(--border);border-radius:var(--radius);padding:12px;margin:0 0 12px;background:rgba(255,255,255,.02);">
            <div style="font-weight:600;margin-bottom:4px;">确认列的含义</div>
            <p id="neo-mapping-note" style="margin:0 0 10px;font-size:13px;color:var(--text-muted);">这张表的列名不是标准写法，系统已按内容猜测。请核对下面四项，确认后只需设置一次。</p>
            <div id="neo-mapping-fields" style="display:grid;grid-template-columns:1fr 1fr;gap:10px;"></div>
            <div id="neo-mapping-preview" style="margin-top:10px;overflow-x:auto;"></div>
            <div style="display:flex;gap:10px;align-items:center;margin-top:10px;flex-wrap:wrap;">
              <button class="btn btn-secondary btn-sm" type="button" onclick="saveColumnMapping()">确认这套对应关系</button>
              <span id="neo-mapping-status" style="font-size:12px;color:var(--text-muted);"></span>
            </div>
          </div>
          <div style="display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin:0 0 6px;">
            <button class="btn btn-secondary btn-sm" type="button" onclick="document.getElementById('neo-cds-file').click()">从本机添加编码序列表…</button>
            <input id="neo-cds-file" type="file" accept=".tsv,.csv,.txt" style="display:none;" onchange="uploadCdsTable(this)">
            <span id="neo-cds-hint" style="font-size:12px;color:var(--text-muted);"></span>
          </div>
          <label for="neo-hla">HLA-I 型别（可选，多个用逗号分隔）</label>
          <input id="neo-hla" type="text" placeholder="例如 HLA-A*02:01,HLA-B*07:02" style="display:block;width:100%;padding:10px;margin:8px 0 14px;">
          <p style="margin:6px 0 12px;">填写后，候选肽和 HLA 型别会分批发送至 IEDB 做 NetMHCpan 结合预测（需要联网，几百条肽通常 30–90 秒）。预测不等于免疫原性验证。</p>
          <button class="btn btn-primary" type="button" id="neo-guided-run" onclick="runNeoantigen(true)" disabled style="opacity:.55;">生成候选肽</button>
          <div id="neo-status" style="margin-top:12px;white-space:pre-wrap;" aria-live="polite"></div>
        </div>
        <details style="margin-top:20px;">
        <summary style="cursor:pointer;font-weight:600;">高级选项：其他文件和专业分析工具</summary>
        <h3>moPepGen · Docker 变异肽生成</h3>
        <p>自动识别当前项目中的 rMATS 事件表（JC 或 JCEC，文件名不限）。请提供版本匹配的参考文件并启动 Docker；生成的是蛋白质组学变异肽，不是 HLA 预测或 CDS 对照表。</p>
        <div id="mopep-fields"></div>
        <button class="btn btn-secondary" type="button" id="mopep-run" onclick="runMopepgen()">运行 moPepGen</button>
        <div id="mopep-status" style="white-space:pre-wrap;margin:12px 0;" aria-live="polite"></div>
        <h3>分阶段证据审计</h3>
        <p>使用当前项目逐阶段运行。每次确认只执行下一阶段；输入文件应位于项目数据目录。流程进度会保存。</p>
        <div id="neo-stage-params"></div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;">
          <button class="btn btn-secondary" type="button" onclick="startNeoWorkflow()">开始阶段 0 审计</button>
          <button class="btn btn-primary" type="button" id="neo-stage-next" onclick="advanceNeoWorkflow()" disabled>确认并执行下一阶段</button>
        </div>
        <pre id="neo-stage-result" style="white-space:pre-wrap;overflow-wrap:anywhere;margin:12px 0;" aria-live="polite">请先选择项目并填写已知证据。</pre>
        <h3>探索性候选肽生成</h3>
        <p>默认使用当前项目已上传的数据。编码序列对照表按表头自动识别，文件名不限；也可在下方选择文件进行独立分析。MHC 结合预测不等于免疫原性验证。</p>
        <p>编码序列对照表需包含 <code>event_id, reference_cds, altered_cds, junction_nt</code>，其中 junction_nt 是异常 CDS 内新连接点前的核苷酸数。</p>
        <label for="neo-files">可选：选择其他文件进行独立分析</label>
        <input id="neo-files" type="file" multiple accept=".tsv,.csv,.txt" style="display:block;margin:12px 0;">
        <button class="btn btn-secondary" type="button" onclick="runNeoantigen()">使用所选文件生成候选肽</button>
        </details>
      </div>
      <div class="card" id="neo-result-panel" style="display:none;max-width:1240px;margin-top:18px;padding:22px;">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:16px;flex-wrap:wrap;">
          <div>
            <div class="card-title" style="margin-bottom:4px;">分析结果</div>
            <div id="neo-result-title" style="font-size:16px;font-weight:600;color:var(--white);">—</div>
            <div id="neo-result-meta" style="font-size:12px;color:var(--text-muted);margin-top:4px;"></div>
          </div>
          <div style="display:flex;gap:8px;flex-wrap:wrap;">
            <button class="btn btn-secondary btn-sm" type="button" onclick="copyNeoResult()">复制全部</button>
            <button class="btn btn-secondary btn-sm" type="button" onclick="downloadNeoResult()">下载当前文件</button>
            <button class="btn btn-secondary btn-sm" type="button" onclick="revealNeoResult()">打开结果目录</button>
            <button class="btn btn-secondary btn-sm" type="button" onclick="closeNeoResult()">关闭</button>
          </div>
        </div>
        <div class="neo-tabs" id="neo-result-tabs"></div>
        <div class="neo-result-body" id="neo-result-body"></div>
        <div class="neo-path" id="neo-result-path" style="display:none;"></div>
      </div>
    </div>
    <div class="page" id="page-peptide">
      <div class="pep-workspace">
        <header class="pep-header"><div><h2>肽预测工作台</h2><p>从候选序列出发，比较 HLA 结合能力，找到值得进一步研究的肽段。</p></div><button type="button" class="btn btn-secondary" onclick="pepFillExample()">填入示例</button></header>
        <ol class="pep-steps" aria-label="预测流程"><li><b>1</b> 准备候选肽</li><li><b>2</b> 选择 HLA</li><li><b>3</b> 预测与解读</li></ol>
        <div class="pep-layout"><div class="pep-inputs">
        <section class="pep-section">
          <h3><label for="pep-sequences">候选肽序列</label></h3>
          <p style="margin:6px 0 10px;color:var(--text-secondary);font-size:13px;">
            每行一个肽段；<b>MHC-I 请用 8–11 aa，MHC-II 请用 11–30 aa</b>；可直接粘贴 FASTA 序列，
            <code>&gt;</code> 开头的标题行会被忽略。页面单次最多 200 条肽、8 个 HLA（API 上限 2000 条），
            避免触发 IEDB 频率限制。
          </p>
          <textarea id="pep-sequences" rows="7" spellcheck="false"
            style="display:block;width:100%;padding:10px;margin:8px 0 6px;border:1px solid var(--border);border-radius:var(--radius);background:transparent;color:var(--text);font-family:var(--font-mono,monospace);font-size:13px;line-height:1.6;resize:vertical;"
            placeholder="SLYNTVATL&#10;GILGFVFTL&#10;NLVPMVATV"></textarea>
          <div id="pep-seq-count" role="status" aria-live="polite" style="font-size:12px;color:var(--text-muted);">已识别 0 条肽段</div>
        </section>
        <section class="pep-section">
          <h3><label for="pep-alleles">HLA 型别</label></h3>
          <p style="margin:6px 0 10px;color:var(--text-secondary);font-size:13px;">
            逗号分隔；输入时会在 IEDB 等位基因表中搜索（最多显示 500 条）。class-I 与 class-II 需分别预测，
            选择“both”时平台会按类别拆分。
          </p>
          <div style="display:flex;gap:8px;flex-wrap:wrap;margin:8px 0 10px;">
            <button class="btn btn-secondary btn-sm" type="button" onclick="pepUsePanel('class1_common')">常用 MHC-I 面板</button>
            <button class="btn btn-secondary btn-sm" type="button" onclick="pepUsePanel('class2_common')">常用 MHC-II 面板</button>
            <button class="btn btn-secondary btn-sm" type="button" onclick="pepClearAlleles()">清空型别</button>
          </div>
          <input id="pep-alleles" type="text" list="pep-allele-list" autocomplete="off" spellcheck="false"
            placeholder="例如 HLA-A*02:01, HLA-B*07:02"
            style="display:block;width:100%;padding:10px;border:1px solid var(--border);border-radius:var(--radius);background:transparent;color:var(--text);font-family:inherit;font-size:13px;">
          <datalist id="pep-allele-list"></datalist>
          <div id="pep-allele-hint" style="font-size:12px;color:var(--text-muted);margin-top:6px;">参考表尚未加载。</div>
          <div id="pep-allele-chips" style="display:flex;gap:6px;flex-wrap:wrap;margin-top:8px;"></div>
        </section></div>
        <aside class="pep-options"><section class="pep-section">
          <h3>预测设置</h3><p class="pep-help">先选类别，再选择运行方式。在线预测需要网络连接。</p>
          <div style="display:grid;grid-template-columns:1fr;gap:14px;margin-top:12px;">
            <div>
              <label for="pep-mhc-class" style="display:block;font-size:12px;color:var(--text-secondary);margin-bottom:6px;">MHC 类别</label>
              <select id="pep-mhc-class" style="width:100%;padding:8px;border:1px solid var(--border);border-radius:var(--radius-sm);background:transparent;color:var(--text);font-family:inherit;font-size:13px;">
                <option value="class1">class1（MHC-I，8–11 aa）</option>
                <option value="class2">class2（MHC-II，11–30 aa）</option>
                <option value="both">both（按类别拆分）</option>
              </select>
            </div>
            <div>
              <label for="pep-predictor" style="display:block;font-size:12px;color:var(--text-secondary);margin-bottom:6px;">预测器</label>
              <select id="pep-predictor" style="width:100%;padding:8px;border:1px solid var(--border);border-radius:var(--radius-sm);background:transparent;color:var(--text);font-family:inherit;font-size:13px;">
                <option value="iedb">IEDB（在线）</option>
                <option value="local" id="pep-predictor-local">MHCflurry（本地，需安装）</option>
                <option value="auto">auto（本地优先，失败转 IEDB）</option>
              </select>
            </div>
            <label style="display:flex;align-items:center;gap:8px;font-size:13px;color:var(--text-secondary);margin-top:22px;">
              <input type="checkbox" id="pep-processing" checked> 加工预测（proteasome / TAP）
            </label>
            <label style="display:flex;align-items:center;gap:8px;font-size:13px;color:var(--text-secondary);margin-top:22px;">
              <input type="checkbox" id="pep-lookup"> 查询 IEDB 已知表位
            </label>
          </div>
          <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-top:14px;">
            <button class="btn btn-primary" type="button" id="pep-predict-btn" onclick="pepPredict()">预测并排序</button>
            <span id="pep-capabilities" style="font-size:12px;color:var(--text-muted);"></span>
          </div>
        </section><div class="pep-guide"><h3>如何看结果？</h3><p><b>Percentile rank 越低越好。</b>它代表相对排名，不是亲和力 Kd。</p><p>结合预测不等于抗原呈递，也不等于免疫原性。排序仅用于探索性候选筛选。</p></div></aside></div>
        <section class="pep-output"><h3>预测结果</h3>
          <div id="pep-status" role="status" aria-live="polite" style="white-space:pre-wrap;"></div>
          <div id="pep-errors"></div><div id="pep-results" style="margin-top:14px;"></div>
        </section>
        <details class="pep-project"><summary>从当前项目生成候选肽</summary>
          <p style="margin:6px 0 10px;color:var(--text-secondary);font-size:13px;">
            使用当前项目的剪接事件与已重建的编码序列对照表生成跨连接点候选肽（对照表按表头自动识别，文件名不限），
            再按上面的 HLA 与预测选项排序。读码框与 ORF 必须由上游提供，平台不会从坐标猜测序列。
          </p>
          <div id="pep-project-hint" style="font-size:12px;color:var(--text-muted);margin-bottom:10px;">正在读取当前项目…</div>
          <button class="btn btn-secondary" type="button" id="pep-project-btn" onclick="pepRunProject()" disabled style="opacity:.55;">从当前项目生成并排序</button>
          <div id="pep-project-status" role="status" aria-live="polite" style="margin-top:12px;white-space:pre-wrap;"></div>
          <div id="pep-project-files" style="margin-top:10px;display:flex;gap:14px;flex-wrap:wrap;font-size:13px;"></div>
        </details>
      </div>
    </div>
  </main>
</div>

<dialog id="quick-dialog" class="quick-dialog" aria-labelledby="quick-title">
  <div class="quick-head"><h2 id="quick-title">快速前往工作区</h2><button type="button" class="btn btn-secondary btn-sm" onclick="closeQuickSwitch()" aria-label="关闭快捷跳转">关闭</button></div>
  <div class="quick-search"><input id="quick-search" type="search" placeholder="搜索页面，如 肽预测、报告…" aria-label="搜索工作区" autocomplete="off" oninput="filterQuickSwitch()"></div>
  <div class="quick-results" id="quick-results"></div>
</dialog>
<!-- Upload Modal -->
<div role="dialog" aria-modal="true" aria-label="新建分析项目" id="upload-modal" style="display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: var(--white); z-index: 1000; align-items: center; justify-content: center;">
  <div style="background: var(--white); border: 1px solid var(--gray-300); border-radius: var(--radius); padding: 32px; max-width: 600px; width: 90%; max-height: 80vh; overflow-y: auto;">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px;">
      <h2 style="font-size: 20px; font-weight: 600; color: var(--black);">新建分析项目</h2>
      <button onclick="closeUploadModal()" style="background: none; border: none; font-size: 20px; cursor: pointer; color: var(--gray-700);">×</button>
    </div>
    <div style="margin-bottom: 20px;">
      <label style="display: block; font-size: 13px; font-weight: 600; margin-bottom: 6px; color: var(--gray-700);">项目名称</label>
      <input type="text" id="project-name" placeholder="输入项目名称（如 My_RNA_Study）" style="width: 100%; padding: 10px; border: 1px solid var(--gray-300); border-radius: var(--radius); font-size: 14px; font-family: var(--font-sans); color: var(--gray-900); background: var(--white);">
    </div>
    <div style="margin-bottom: 20px;">
      <label style="display: block; font-size: 13px; font-weight: 600; margin-bottom: 6px; color: var(--gray-700);">分析查询</label>
      <input type="text" id="analysis-query" placeholder="输入分析查询（如 compare treatment vs control）" style="width: 100%; padding: 10px; border: 1px solid var(--gray-300); border-radius: var(--radius); font-size: 14px; font-family: var(--font-sans); color: var(--gray-900); background: var(--white);">
    </div>
    <div style="margin-bottom: 24px;">
      <label style="display: block; font-size: 13px; font-weight: 600; margin-bottom: 8px; color: var(--gray-700);">上传文件</label>
      <div id="drop-zone" role="button" tabindex="0" aria-label="选择数据文件" onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault();document.getElementById('file-input').click();}" style="border: 2px dashed var(--gray-300); border-radius: var(--radius); padding: 40px; text-align: center; cursor: pointer; transition: all 0.2s; background: var(--gray-100);" ondragover="handleDragOver(event)" ondragleave="handleDragLeave(event)" ondrop="handleDrop(event)" onclick="document.getElementById('file-input').click()">
        <div style="font-size: 36px; margin-bottom: 12px;"></div>
        <div style="font-size: 14px; color: var(--gray-700);">拖拽文件到此处，或点击选择文件</div>
        <div style="font-size: 12px; color: var(--gray-500); margin-top: 8px;">支持 CSV、TSV、TXT、文本 .xls、Excel .xls/.xlsx/.xlsm 及压缩文本 .gz；表达量表会被识别并提示所需事件数据</div>
      </div>
      <input type="file" id="file-input" multiple style="display: none;" onchange="handleFileSelect(event)">
      <input type="file" id="report-directory-input" webkitdirectory directory multiple style="display: none;" onchange="handleReportDirectory(event)">
      <button type="button" class="btn btn-secondary" style="margin-top: 10px;" onclick="document.getElementById('report-directory-input').click()">选择华大报告目录</button>
      <div id="file-list" style="margin-top: 12px;"></div>
    </div>
    <div style="display: flex; gap: 12px; justify-content: flex-end;">
      <button class="btn btn-secondary" onclick="closeUploadModal()">取消</button>
      <button class="btn btn-primary" id="start-analysis-btn" onclick="startAnalysis()" disabled>开始分析</button>
    </div>
  </div>
</div>

<!-- Smart Ingestion Review Modal -->
<div id="ingest-modal" role="dialog" aria-modal="true" aria-labelledby="ingest-title">
  <div class="ingest-panel">
    <div class="ingest-head">
      <div>
        <div class="ingest-title" id="ingest-title">智能接入检查</div>
        <div class="ingest-sub" id="ingest-sub">Agent 已读取数据结构，请确认字段映射后开始分析。</div>
      </div>
      <button class="ingest-close" type="button" onclick="closeIngestModal()" aria-label="关闭">×</button>
    </div>
    <div class="ingest-body" id="ingest-body"></div>
    <div class="ingest-footer">
      <div class="ingest-error" id="ingest-error"></div>
      <button class="btn btn-secondary" type="button" id="ingest-cancel" onclick="closeIngestModal()">取消</button>
      <button class="btn btn-primary" type="button" id="ingest-confirm" onclick="confirmIngest()">确认映射并分析</button>
    </div>
  </div>
</div>

<script>
const state = { currentProject: localStorage.getItem('epitoperank.currentProject'), projects: [], analysisStatus: null, detail: null, storage: null, events: [], eventPage: 1, eventPages: 1, eventTotal: 0, currentPage: 'dashboard' };
let neoResultDir = '', neoResultName = '', neoResultText = '';
const NEO_CR = String.fromCharCode(13), NEO_LF = String.fromCharCode(10), NEO_TAB = String.fromCharCode(9);
async function checkNeoReadiness() {
  const resultBox = document.getElementById('neo-readiness');
  const runButton = document.getElementById('neo-guided-run');
  const button = document.getElementById('neo-check');
  runButton.disabled = true; runButton.style.opacity = '.55';
  if (!state.currentProject) { resultBox.textContent = '还没有选择项目。请先创建或选择一个项目，再回来检查。'; return; }
  const projectId = state.currentProject; button.disabled = true; resultBox.textContent = '正在检查项目数据…';
  try {
    const response = await fetch('/api/neoantigen/readiness/' + encodeURIComponent(projectId));
    const data = await response.json(); if (!response.ok) throw new Error(data.detail || '检查失败');
    if (projectId !== state.currentProject) { resultBox.textContent = '当前项目已切换，请重新检查。'; return; }
    const lines = ['项目：' + data.project_name, '剪接事件：' + data.event_count + ' 条'];
    const files = data.cds_files || [];
    if (data.cds_status === 'available' && files.length) {
      lines.push('编码序列表：已自动识别 ' + files.length + ' 份（' + files.join('、') + '）',
                 '可以继续生成候选肽。检查只确认了表头，序列的读码框仍需由专业人员核实。');
    } else {
      lines.push('编码序列表：暂未找到',
                 '需要一份含 event_id、reference_cds、altered_cds、junction_nt 四列的表，文件名随意。',
                 '点下方「从本机添加编码序列表」就能直接补上，不用重新跑整个分析。');
      if ((data.rmats_files || []).length) lines.push('已识别 rMATS 文件：' + data.rmats_files.join('、') + '。');
    }
    if ((data.cds_partial || []).length) {
      lines.push('另有 ' + data.cds_partial.length + ' 个文件看着像编码序列表，但没被采用（不影响下面的生成）：'
        + data.cds_partial.map(item => item.name + '——' + item.reason).join('；'));
    }
    resultBox.textContent = lines.join(NEO_LF);
    renderCdsChoices(data);
    neoReadiness = data;
    renderColumnMapping(data);
  } catch (error) { const message = String(error.message || error); resultBox.textContent = message.includes('input_dir must be inside') ? '无法访问此项目的原始数据目录。请重新选择该项目的数据文件，或联系管理员检查存储位置。' : '检查失败：' + message; }
  finally { button.disabled = false; }
}
function renderCdsChoices(data) {
  const select = document.getElementById('neo-cds-select');
  const hint = document.getElementById('neo-cds-hint');
  const runButton = document.getElementById('neo-guided-run');
  const files = (data && data.cds_files) || [];
  select.replaceChildren();
  if (!files.length) {
    const option = document.createElement('option');
    option.value = ''; option.textContent = '（还没有可用的编码序列表）';
    select.appendChild(option); select.disabled = true;
    hint.textContent = '点左侧按钮从本机添加，或重新上传项目时把它一起放进去。';
    runButton.disabled = true; runButton.style.opacity = '.55';
    document.getElementById('neo-mapping-panel').style.display = 'none';
    return;
  }
  files.forEach(name => {
    const option = document.createElement('option');
    option.value = name; option.textContent = name;
    select.appendChild(option);
  });
  const preferred = (data.cds_selected && files.indexOf(data.cds_selected) >= 0) ? data.cds_selected : files[0];
  select.value = preferred; select.disabled = false;
  select.onchange = () => renderColumnMapping(neoReadiness);
  hint.textContent = files.length > 1 ? '检测到 ' + files.length + ' 份，默认用 ' + preferred + '，可在下拉里切换。' : '文件已自动选中。';
  runButton.disabled = false; runButton.style.opacity = '1';
}
const NEO_FIELD_ORDER = ['event_id', 'reference_cds', 'altered_cds', 'junction_nt'];
const NEO_FIELD_FALLBACK = {event_id:'事件 ID', reference_cds:'参考（正常）编码序列',
  altered_cds:'改变后（变异）编码序列', junction_nt:'新剪接连接点位置（整数）'};
let neoReadiness = null;
function neoClip(value, limit) { const text = String(value == null ? '' : value); return text.length > limit ? text.slice(0, limit) + '…' : text; }
function renderColumnMapping(data) {
  const panel = document.getElementById('neo-mapping-panel');
  const fields = document.getElementById('neo-mapping-fields');
  const preview = document.getElementById('neo-mapping-preview');
  const status = document.getElementById('neo-mapping-status');
  if (!panel || !data) return;
  const name = (document.getElementById('neo-cds-select').value || data.cds_selected || '');
  const detail = (data.cds_details || {})[name];
  if (!detail || !detail.needs_confirmation) { panel.style.display = 'none'; fields.replaceChildren(); preview.innerHTML = ''; return; }
  const labels = data.field_labels || NEO_FIELD_FALLBACK;
  const header = detail.header || [];
  fields.replaceChildren();
  NEO_FIELD_ORDER.forEach(field => {
    const wrap = document.createElement('label');
    wrap.style.cssText = 'display:block;font-size:13px;';
    wrap.appendChild(document.createTextNode(labels[field] || field));
    const select = document.createElement('select');
    select.id = 'neo-map-' + field;
    select.style.cssText = 'display:block;width:100%;padding:8px;margin-top:4px;';
    const blank = document.createElement('option'); blank.value = ''; blank.textContent = '（请选择）';
    select.appendChild(blank);
    header.forEach(column => {
      const option = document.createElement('option');
      option.value = column; option.textContent = column || '（空列名）';
      select.appendChild(option);
    });
    select.value = (detail.map || {})[field] || '';
    wrap.appendChild(select);
    fields.appendChild(wrap);
  });
  const columns = detail.preview || [];
  if (columns.length) {
    const head = columns.map(item => '<th>' + neoEscape(item.column || '（空列名）') + '</th>').join('');
    const body = [0, 1].map(index => '<tr>' + columns.map(item => {
      const value = (item.samples || [])[index] || '';
      return '<td style="max-width:280px;"><span title="' + neoEscape(value) + '">' + neoEscape(neoClip(value, 46)) + '</span></td>';
    }).join('') + '</tr>').join('');
    preview.innerHTML = '<div style="font-size:12px;color:var(--text-muted);margin-bottom:4px;">样本内容（前两行）——用它确认哪列是参考、哪列是改变后</div>'
      + '<table><thead><tr>' + head + '</tr></thead><tbody>' + body + '</tbody></table>';
  } else {
    preview.innerHTML = '';
  }
  status.textContent = detail.source === 'saved' ? '已保存过映射。' : '自动猜测结果，确认后以后不再询问。';
  panel.style.display = 'block';
}
async function saveColumnMapping() {
  const status = document.getElementById('neo-mapping-status');
  const name = document.getElementById('neo-cds-select').value || '';
  if (!state.currentProject || !name) { status.textContent = '请先选择项目和编码序列表。'; return; }
  const map = {};
  NEO_FIELD_ORDER.forEach(field => {
    const select = document.getElementById('neo-map-' + field);
    map[field] = select ? select.value : '';
  });
  const missing = NEO_FIELD_ORDER.filter(field => !map[field]);
  if (missing.length) { status.textContent = '还有 ' + missing.length + ' 项没有选择。'; return; }
  if (new Set(Object.keys(map).map(key => map[key])).size < NEO_FIELD_ORDER.length) {
    status.textContent = '同一列不能承担两个角色，请分别选择。'; return;
  }
  status.textContent = '正在保存…';
  try {
    const response = await fetch('/api/neoantigen/column-map', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({project_id: state.currentProject, file: name, map: map})});
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || '保存失败');
    const message = data.warning || ('已保存，按这套映射可为 ' + data.verified_rows + ' 行样本生成肽。');
    await checkNeoReadiness();
    document.getElementById('neo-mapping-status').textContent = message;
  } catch (error) { status.textContent = String(error.message || error); }
}
async function uploadCdsTable(input) {
  const status = document.getElementById('neo-status');
  const file = input.files && input.files[0];
  if (!file) return;
  if (!state.currentProject) { status.textContent = '请先选择一个项目。'; input.value = ''; return; }
  status.textContent = '正在上传 ' + file.name + '…';
  try {
    const form = new FormData();
    form.append('project_id', state.currentProject);
    form.append('file', file, file.name);
    const response = await fetch('/api/neoantigen/cds-upload', {method:'POST', body:form});
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || '上传失败');
    status.textContent = '已添加 ' + data.saved + '，列：' + (data.columns || []).join('、');
    await checkNeoReadiness();
    document.getElementById('neo-cds-select').value = data.saved;
  } catch (error) { status.textContent = String(error.message || error); }
  finally { input.value = ''; }
}
const mopepFields = {genome:'参考基因组 FASTA 文件',gtf:'转录本注释 GTF 文件',proteome:'参考蛋白组 FASTA 文件',reference_source:'参考来源（GENCODE 或 ENSEMBL）',reference_version:'基因组及注释版本'};
Object.entries(mopepFields).forEach(([key, labelText]) => {
  const label = document.createElement('label'); label.style.display = 'block'; label.style.margin = '8px 0';
  const input = document.createElement('input'); input.id = 'mopep-' + key; input.type = 'text'; input.style.display = 'block'; input.style.width = '100%';
  input.placeholder = key === 'reference_version' ? '例如 GRCh38 / GENCODE vXX（须与上游一致）' : key === 'reference_source' ? 'GENCODE 或 ENSEMBL' : '相对于项目上传目录的文件路径';
  label.appendChild(document.createTextNode(labelText)); label.appendChild(input); document.getElementById('mopep-fields').appendChild(label);
});
async function runMopepgen() {
  const status = document.getElementById('mopep-status'); const button = document.getElementById('mopep-run');
  if (!state.currentProject) { status.textContent = '请先选择项目。'; return; }
  const payload = {project_id:state.currentProject}; Object.keys(mopepFields).forEach(key => { payload[key] = document.getElementById('mopep-' + key).value.trim(); });
  button.disabled = true; status.textContent = '正在运行 Docker，耗时取决于输入大小，请勿关闭程序…';
  try {
    const response = await fetch('/api/neoantigen/mopepgen', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    const result = await response.json(); if (!response.ok) throw new Error(result.detail || '执行失败');
    const manifest = result.manifest;
    status.textContent = (result.exit_code ? '执行失败，请查看日志。' : '执行完成。') + NEO_LF + '结果目录：' + result.output_dir + NEO_LF + (manifest.warnings || []).join(NEO_LF) + NEO_LF;
    ['manifest.json','events.gvf','variant_peptides.fasta','step_1.log','step_2.log'].forEach(name => {
      const link = document.createElement('a'); link.href = '/api/neoantigen/mopepgen/file?output_dir=' + encodeURIComponent(result.output_dir) + '&name=' + encodeURIComponent(name); link.textContent = name; link.style.marginRight = '12px'; status.appendChild(link);
    });
  } catch (error) { status.textContent = '无法运行：' + String(error.message || error); }
  finally { button.disabled = false; }
}
let neoWorkflow = null;
const neoStageExamples = [
  {normal_design:'',input_kind:'',genome_build:'',annotation_version:'',coordinate_system:'',hla_source:'',hla_confidence:'',has_frame_correct_cds:false},
  {input_is_quantified_events:false,event_set:'unknown'},
  {min_support:null,min_samples:null,support_is_junction_reads:false},
  {orf_file:''},
  {protein_fastas:{paired_normal:'',gtex:'',proteome:''},event_junctions:'',gtex_junctions:'',event_build:'',gtex_build:'',normal_expression_file:'',acknowledge_missing_gtex_junction_and_tissue_expression:false},
  {expression_file:''},
  {alleles:[],hla_source:'',hla_confidence:''},
  {}
];
const neoLabels = {normal_design:'正常对照设计',input_kind:'输入数据类型',genome_build:'基因组版本',annotation_version:'注释版本',coordinate_system:'坐标基准',hla_source:'HLA 分型来源',hla_confidence:'HLA 置信度',has_frame_correct_cds:'已有读码框正确的 CDS',input_is_quantified_events:'确认输入为已量化事件',event_set:'事件表完整性：complete / subset / unknown',min_support:'最低 junction 支持读数',min_samples:'最低有效样本数',support_is_junction_reads:'确认支持读数为 junction 读数',orf_file:'上游 ORF 表文件名（留空自动识别）',paired_normal:'配对正常蛋白 FASTA 文件名',gtex:'GTEx 蛋白 FASTA 文件名',proteome:'全蛋白组 FASTA 文件名',event_junctions:'事件连接点表文件名',gtex_junctions:'GTEx 连接点表文件名',event_build:'事件基因组版本',gtex_build:'GTEx 基因组版本',normal_expression_file:'正常组织表达表文件名',acknowledge_missing_gtex_junction_and_tissue_expression:'接受跳过缺失的连接点或组织表达检查',expression_file:'肿瘤表达及复现率表文件名',alleles:'HLA-I 型别，逗号分隔'};
let neoFormStage = 0;
function buildNeoForm(stage) {
  neoFormStage = stage;
  const container = document.getElementById('neo-stage-params'); container.replaceChildren();
  function addFields(obj, prefix) {
    Object.entries(obj).forEach(([key, val]) => {
      const path = prefix ? prefix + '.' + key : key;
      if (val && typeof val === 'object' && !Array.isArray(val)) { addFields(val, path); return; }
      const label = document.createElement('label'); label.style.display = 'block'; label.style.margin = '8px 0';
      const input = document.createElement('input'); input.dataset.path = path;
      input.type = typeof val === 'boolean' ? 'checkbox' : (val === null ? 'number' : 'text');
      if (input.type !== 'checkbox') { input.style.display = 'block'; input.style.width = '100%'; input.value = Array.isArray(val) ? val.join(',') : (val == null ? '' : val); }
      label.appendChild(document.createTextNode(neoLabels[key] || key)); label.appendChild(input); container.appendChild(label);
    });
  }
  addFields(neoStageExamples[stage] || {}, '');
}
function readNeoForm() {
  const result = {};
  document.querySelectorAll('#neo-stage-params input').forEach(input => {
    const path = input.dataset.path.split('.'); let target = result;
    path.slice(0, -1).forEach(key => { target[key] = target[key] || {}; target = target[key]; });
    const key = path[path.length - 1];
    target[key] = input.type === 'checkbox' ? input.checked : input.type === 'number' ? (input.value === '' ? null : Number(input.value)) : key === 'alleles' ? input.value.split(',').map(x => x.trim()).filter(Boolean) : input.value.trim();
  });
  return result;
}
buildNeoForm(0);
function renderNeoWorkflow(data) {
  neoWorkflow = data;
  const last = data.history[data.history.length - 1];
  document.getElementById('neo-stage-result').textContent = '阶段 ' + last.stage + ' 结果：' + NEO_LF + JSON.stringify(last, null, 2) + (data.stopped ? NEO_LF + '已停止：' + data.stopped : '');
  const next = document.getElementById('neo-stage-next');
  next.disabled = !!data.stopped || data.next_stage > 7;
  next.textContent = next.disabled ? '流程已停止或完成' : '确认并执行阶段 ' + data.next_stage;
  buildNeoForm(data.next_stage);
}
async function startNeoWorkflow() {
  const out = document.getElementById('neo-stage-result');
  try {
    if (!state.currentProject) throw new Error('请先选择项目');
    if (neoFormStage !== 0) { buildNeoForm(0); out.textContent = '请填写新审计的证据，再点击开始阶段 0。'; return; }
    const evidence = readNeoForm();
    out.textContent = '正在审计…';
    const response = await fetch('/api/neoantigen/workflow/start', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({project_id:state.currentProject,evidence:evidence})});
    const result = await response.json(); if (!response.ok) throw new Error(result.detail || '审计失败');
    localStorage.setItem('epitoperank.neoWorkflow.' + state.currentProject, result.workflow_id);
    renderNeoWorkflow(result);
  } catch (error) { out.textContent = '无法开始：' + String(error.message || error); }
}
async function advanceNeoWorkflow() {
  const out = document.getElementById('neo-stage-result');
  const button = document.getElementById('neo-stage-next');
  if (!neoWorkflow) return;
  try {
    const params = readNeoForm(); params.confirm = true;
    button.disabled = true; out.textContent = '正在执行阶段 ' + neoWorkflow.next_stage + '…';
    const response = await fetch('/api/neoantigen/workflow/advance', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({workflow_id:neoWorkflow.workflow_id,expected_stage:neoWorkflow.next_stage,parameters:params})});
    const result = await response.json(); if (!response.ok) throw new Error(result.detail || '执行失败');
    renderNeoWorkflow(result);
  } catch (error) { out.textContent = '无法继续：' + String(error.message || error); button.disabled = false; }
}
async function restoreNeoWorkflow() {
  neoWorkflow = null;
  document.getElementById('neo-stage-next').disabled = true;
  const id = state.currentProject && localStorage.getItem('epitoperank.neoWorkflow.' + state.currentProject);
  if (!id) { buildNeoForm(0); document.getElementById('neo-stage-result').textContent = '请填写已知证据并开始审计。'; return; }
  try {
    const response = await fetch('/api/neoantigen/workflow/' + encodeURIComponent(id));
    if (!response.ok) throw new Error('无法恢复流程，请重新开始审计。');
    renderNeoWorkflow(await response.json());
  } catch (error) { buildNeoForm(0); document.getElementById('neo-stage-result').textContent = String(error.message || error); }
}
const NEO_RESULT_FILES = ['splice_peptides.tsv','ranked_candidates.tsv','mhc_i_predictions.tsv','neoantigen_manifest.json'];
function toggleOrfSource() {
  const local = document.getElementById('orf-source').value === 'local';
  document.getElementById('orf-local-fields').style.display = local ? 'block' : 'none';
}
async function buildOrfTable() {
  const status = document.getElementById('orf-status');
  const button = document.getElementById('orf-build');
  if (!state.currentProject) { status.textContent = '请先选择一个项目。'; return; }
  const ids = document.getElementById('orf-event-ids').value.split(',').map(v => v.trim()).filter(Boolean);
  const payload = {
    project_id: state.currentProject,
    source: document.getElementById('orf-source').value,
    max_events: Number(document.getElementById('orf-max-events').value || 25),
    fdr_max: Number(document.getElementById('orf-fdr').value || 0.05),
    min_abs_dpsi: Number(document.getElementById('orf-dpsi').value || 0.1),
    event_ids: ids
  };
  if (payload.source === 'local') {
    payload.gtf = document.getElementById('orf-gtf').value.trim();
    payload.fasta = document.getElementById('orf-fasta').value.trim();
  }
  button.disabled = true;
  status.textContent = '正在重建 ORF（在线参考源需联网，可能耗时几十秒）…';
  try {
    const response = await fetch('/api/orf/build', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)});
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || '重建失败');
    const reasons = (data.skipped || []).reduce((acc, item) => { acc[item.reason] = (acc[item.reason] || 0) + 1; return acc; }, {});
    const reasonText = Object.keys(reasons).map(k => k + ' ' + reasons[k]).join('、');
    status.innerHTML = '已重建 <b>' + Number(data.written) + '</b> 条 CDS（共检查 ' + Number(data.event_count) + ' 个事件）' +
      '<br>参考：' + neoEscape(data.reference) + ' / ' + neoEscape(data.genome_build) +
      '<br>输出：' + neoEscape(data.output_name) + (reasonText ? '<br>跳过原因：' + neoEscape(reasonText) : '');
    await checkNeoReadiness();
    if (data.written) document.getElementById('neo-cds-select').value = data.output_name;
  } catch (error) { status.textContent = String(error.message || error); }
  finally { button.disabled = false; }
}
async function runNeoantigen(useProject = false) {
  const status = document.getElementById('neo-status');
  const files = useProject ? [] : Array.from(document.getElementById('neo-files').files);
  if (!files.length && !state.currentProject) { status.textContent = '请先选择已上传数据的项目，或选择文件进行独立分析。'; return; }
  const cdsChoice = useProject ? (document.getElementById('neo-cds-select').value || '') : '';
  if (useProject && !cdsChoice) {
    status.textContent = '还没有可用的编码序列表。点第一步下方的「从本机添加编码序列表」补上，再回来生成。'; return;
  }
  const alleles = document.getElementById('neo-hla').value.split(',').map(v => v.trim()).filter(Boolean);
  status.textContent = alleles.length
    ? '正在生成候选肽并查询 IEDB（' + alleles.length + ' 个 HLA 型别，通常 30–90 秒，请勿关闭页面）…'
    : (files.length ? '正在上传和分析…' : '正在使用当前项目数据分析…');
  try {
    let payload = {project_id: state.currentProject, alleles: alleles};
    if (useProject) payload.cds_table = cdsChoice;
    if (files.length) {
      const form = new FormData(); files.forEach(file => form.append('files', file, file.name));
      const upload = await fetch('/api/upload', {method:'POST', body:form});
      const staged = await upload.json();
      if (!upload.ok) throw new Error(staged.detail || '上传失败');
      payload = {input_dir: staged.upload_dir, alleles: alleles};
    }
    const response = await fetch('/api/neoantigen/run', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)});
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || '分析失败');
    const resultDir = result.input_dir;
    const base = '/api/neoantigen/file?input_dir=' + encodeURIComponent(resultDir) + '&name=';
    const links = NEO_RESULT_FILES.map(name => '<a href="' + base + encodeURIComponent(name) + '">' + name + '</a>').join(' · ');
    const failures = (result.prediction_errors || []).length;
    const truncated = Number(result.prediction_truncated || 0);
    let summary = '使用编码序列表：' + neoEscape(result.cds_table_name || '自动识别') + '<br>候选肽段 ' + Number(result.candidate_count) + ' 条';
    if (alleles.length) {
      summary += '；HLA 结合预测成功 ' + Number(result.prediction_count) + ' 条';
      if (failures) summary += '，失败 ' + failures + ' 条（详见 manifest 的 prediction_errors）';
      if (truncated) summary += '；超出单次上限的部分（' + truncated + ' 条）未预测，可缩小 CDS 表后重跑';
      summary += '。';
      const tiers = result.binding_tiers;
      if (tiers && tiers.total) {
        summary += '<br><b>自动分级（percentile_rank）：强结合 &lt;0.5% ' + Number(tiers.strong_count) +
                   ' 条 · 弱结合 0.5~2% ' + Number(tiers.weak_count) + ' 条 · 其余 ' +
                   Number(tiers.not_binding_count + tiers.unknown_count) + ' 条</b>' +
                   '<br><span style="color:var(--text-muted);font-size:12px;">已按 rank 升序写入 ranked_candidates.tsv；' +
                   'EL 分数不等于实测亲和力或免疫原性。</span>';
      }
    } else {
      summary += '；未填写 HLA，只生成候选肽，未做任何外部预测。';
    }
    summary += '<br>' + links;
    status.innerHTML = summary;
    neoResultDir = resultDir;
    document.getElementById('neo-result-panel').style.display = 'block';
    const tabs = document.getElementById('neo-result-tabs');
    tabs.replaceChildren();
    NEO_RESULT_FILES.forEach(name => {
      const button = document.createElement('button'); button.type = 'button'; button.className = 'btn btn-secondary btn-sm'; button.textContent = name;
      button.onclick = () => openNeoResult(name); tabs.appendChild(button);
    });
    const tiers = result.binding_tiers;
    await openNeoResult(alleles.length && tiers && tiers.total ? 'ranked_candidates.tsv' : 'splice_peptides.tsv');
  } catch (error) { status.textContent = String(error.message || error); }
}

const NEO_ESCAPES = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
function neoEscape(value) { return String(value == null ? '' : value).replace(/[&<>"']/g, ch => NEO_ESCAPES[ch]); }
function neoShorten(value) { const text = value == null ? '' : String(value); return text.length > 240 ? text.slice(0, 240) + '…' : text; }
function neoParseTsv(text) { const lines = String(text).split(NEO_CR).join('').split(NEO_LF).filter(line => line.trim().length > 0); const header = lines.length ? lines[0].split(NEO_TAB) : []; const rows = lines.slice(1).map(line => line.split(NEO_TAB)); return { header, rows }; }
function neoTableHtml(parsed) { if (!parsed.header.length) return '<pre>结果为空</pre>'; const limit = 300; const shown = parsed.rows.slice(0, limit); const head = parsed.header.map(cell => '<th>' + neoEscape(cell) + '</th>').join(''); const body = shown.map(cells => '<tr>' + parsed.header.map((_, index) => '<td>' + neoEscape(neoShorten(cells[index])) + '</td>').join('') + '</tr>').join(''); return '<table><thead><tr>' + head + '</tr></thead><tbody>' + (body || '<tr><td colspan="' + parsed.header.length + '">无数据行</td></tr>') + '</tbody></table>'; }
function neoResultUrl(name) { return '/api/neoantigen/file?input_dir=' + encodeURIComponent(neoResultDir) + '&name=' + encodeURIComponent(name); }

async function openNeoResult(name) {
  if (!neoResultDir || !name) return;
  neoResultName = name;
  document.getElementById('neo-result-title').textContent = name;
  let meta = document.getElementById('neo-result-meta');
  meta.dataset.base = '';
  meta.textContent = '加载中…';
  document.getElementById('neo-result-body').innerHTML = '<pre>加载中…</pre>';
  try {
    const response = await fetch(neoResultUrl(name));
    if (!response.ok) { let detail = ''; try { const parsed = await response.json(); detail = parsed.detail || ''; } catch(ignore) {} throw new Error(detail || ('HTTP ' + response.status)); }
    const text = await response.text();
    neoResultText = text;
    if (name.toLowerCase().endsWith('.json')) {
      let pretty = text;
      try { pretty = JSON.stringify(JSON.parse(text), null, 2); } catch(ignore) {}
      meta.dataset.base = text.length + ' 字符';
      meta.textContent = text.length + ' 字符';
      document.getElementById('neo-result-body').innerHTML = '<pre>' + neoEscape(pretty) + '</pre>';
      return;
    }
    const parsed = neoParseTsv(text);
    meta.dataset.base = parsed.rows.length + ' 行 · ' + parsed.header.length + ' 列';
    meta.textContent = parsed.rows.length + ' 行 · ' + parsed.header.length + ' 列';
    document.getElementById('neo-result-body').innerHTML = neoTableHtml(parsed);
  } catch (error) {
    meta.dataset.base = '';
    meta.textContent = '';
    document.getElementById('neo-result-body').innerHTML = '<pre style="color:var(--danger);">读取失败：' + neoEscape(String(error.message || error)) + '</pre>';
  }
}

let neoHintTimer = null;
function setNeoHint(message) {
  const meta = document.getElementById('neo-result-meta');
  if (!meta.dataset.base) meta.dataset.base = meta.textContent;
  meta.textContent = meta.dataset.base + ' · ' + message;
  if (neoHintTimer) clearTimeout(neoHintTimer);
  neoHintTimer = setTimeout(() => { meta.textContent = meta.dataset.base; meta.dataset.base = ''; neoHintTimer = null; }, 2500);
}

async function copyNeoResult() {
  if (!neoResultText) return;
  try { await navigator.clipboard.writeText(neoResultText); setNeoHint('已复制到剪贴板'); }
  catch (error) {
    const area = document.createElement('textarea'); area.value = neoResultText; area.style.position = 'fixed'; area.style.opacity = '0'; document.body.appendChild(area); area.select();
    const ok = document.execCommand('copy'); area.remove(); setNeoHint(ok ? '已复制到剪贴板' : '复制失败，请手动选择表格内容');
  }
}

async function downloadNeoResult() {
  if (!neoResultName) return;
  try {
    const response = await fetch(neoResultUrl(neoResultName));
    if (!response.ok) throw new Error('HTTP ' + response.status);
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a'); anchor.href = url; anchor.download = neoResultName; document.body.appendChild(anchor); anchor.click(); anchor.remove();
    setTimeout(() => URL.revokeObjectURL(url), 5000);
    setNeoHint('已触发下载；桌面窗口若未保存文件，请直接查看表格或复制全部');
  } catch (error) { setNeoHint('下载失败：' + String(error.message || error)); }
}

async function revealNeoResult() {
  if (!neoResultDir) return;
  try {
    const response = await fetch('/api/neoantigen/reveal', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({input_dir:neoResultDir})});
    const payload = await response.json().catch(()=> ({}));
    if (!response.ok) throw new Error(payload.detail || ('HTTP ' + response.status));
    setNeoHint('已在文件管理器中打开结果目录');
  } catch (error) { setNeoHint('无法打开目录：' + String(error.message || error)); }
}

function closeNeoResult() { document.getElementById('neo-result-panel').style.display = 'none'; }

/* ------------------------------------------------------------------ */
/* Peptide prediction page (additive; all globals prefixed with pep)   */
/* ------------------------------------------------------------------ */
const PEP_CLASS1_PANEL = [
  'HLA-A*01:01', 'HLA-A*02:01', 'HLA-A*03:01', 'HLA-A*11:01',
  'HLA-A*23:01', 'HLA-A*24:02', 'HLA-A*26:01', 'HLA-A*31:01',
  'HLA-B*07:02', 'HLA-B*08:01', 'HLA-B*15:01', 'HLA-B*27:05',
  'HLA-B*35:01', 'HLA-B*40:01', 'HLA-B*44:02', 'HLA-B*44:03',
  'HLA-B*57:01', 'HLA-B*58:01', 'HLA-C*07:02', 'HLA-C*04:01'
];
const PEP_CLASS2_PANEL = [
  'HLA-DRB1*01:01', 'HLA-DRB1*03:01', 'HLA-DRB1*04:01', 'HLA-DRB1*07:01',
  'HLA-DRB1*09:01', 'HLA-DRB1*11:01', 'HLA-DRB1*13:02', 'HLA-DRB1*15:01',
  'HLA-DPA1*01:03/DPB1*04:01', 'HLA-DQA1*05:01/DQB1*02:01'
];
const pepState = {
  loaded: false,
  loading: false,
  capabilities: null,
  referenceTotal: 0,
  searchTimer: null,
  predictions: [],
  sortKey: 'percentile_rank',
  sortDir: 1,
  bound: false,
  projectOutput: ''
};
const PEP_ESCAPES = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
function pepEscape(value) {
  return String(value == null ? '' : value).replace(/[&<>"']/g, ch => PEP_ESCAPES[ch]);
}
function pepSetStatus(id, text, tone) {
  const box = document.getElementById(id);
  if (!box) return;
  box.textContent = text || '';
  box.style.color = tone === 'error' ? 'var(--danger)' : (tone === 'muted' ? 'var(--text-muted)' : 'var(--text-secondary)');
}
function pepErrorDetail(response, payload, fallback) {
  if (payload && payload.detail) {
    return typeof payload.detail === 'string' ? payload.detail : JSON.stringify(payload.detail);
  }
  return fallback + '（HTTP ' + response.status + '）';
}
function pepTokens() {
  const input = document.getElementById('pep-alleles');
  if (!input) return [];
  return input.value.split(/[,;\\s]+/).map(v => v.trim()).filter(Boolean);
}
function pepRenderChips() {
  const wrap = document.getElementById('pep-allele-chips');
  if (!wrap) return;
  wrap.replaceChildren();
  const tokens = pepTokens();
  tokens.forEach(token => {
    const chip = document.createElement('span');
    chip.textContent = token + '  ×';
    chip.title = '点击移除 ' + token;
    chip.style.cssText = 'padding:4px 9px;border:1px solid var(--border);border-radius:999px;font-size:12px;color:var(--text-secondary);cursor:pointer;';
    chip.onclick = () => {
      const remaining = pepTokens().filter(value => value !== token);
      document.getElementById('pep-alleles').value = remaining.join(', ');
      pepRenderChips();
    };
    wrap.appendChild(chip);
  });
}
async function pepFillExample() {
  const field = document.getElementById('pep-sequences');
  if (field.value.trim()) {
    const confirmed = await AppNotify.confirm(
      '填入示例会覆盖当前填写好的肽序列和 HLA 型别。',
      { kind: 'warning', title: '替换当前输入？', confirmLabel: '填入示例', cancelLabel: '保留输入' }
    );
    if (!confirmed) return;
  }
  field.value = ['SLYNTVATL', 'GILGFVFTL', 'NLVPMVATV'].join(String.fromCharCode(10));
  document.getElementById('pep-alleles').value = 'HLA-A*02:01';
  document.getElementById('pep-mhc-class').value = 'class1';
  pepCountSequences(); pepRenderChips(); pepRefreshReference();
  field.focus();
}
function pepCountSequences() {
  const label = document.getElementById('pep-seq-count');
  if (!label) return { peptides: [], invalid: 0 };
  const raw = document.getElementById('pep-sequences').value.split(/\\r?\\n/);
  const peptides = [];
  let invalid = 0;
  raw.forEach(line => {
    let value = line.trim();
    if (!value || value.startsWith('>') || value.startsWith(';')) return;
    value = value.replace(/\\s+/g, '').toUpperCase();
    if (!/^[ACDEFGHIKLMNPQRSTVWY]+$/.test(value) || value.length < 8 || value.length > 30) {
      invalid += 1;
      return;
    }
    peptides.push(value);
  });
  const unique = Array.from(new Set(peptides));
  label.textContent = '已识别 ' + unique.length + ' 条肽段（8–30 aa）' + (invalid ? '，忽略 ' + invalid + ' 行无效输入' : '');
  label.style.color = invalid ? 'var(--danger)' : 'var(--text-muted)';
  return { peptides: unique, invalid: invalid };
}
function pepUsePanel(name) {
  const panel = name === 'class2_common' ? PEP_CLASS2_PANEL : PEP_CLASS1_PANEL;
  document.getElementById('pep-alleles').value = panel.join(', ');
  document.getElementById('pep-mhc-class').value = name === 'class2_common' ? 'class2' : 'class1';
  pepRenderChips();
  pepRefreshReference();
}
function pepClearAlleles() {
  document.getElementById('pep-alleles').value = '';
  pepRenderChips();
  pepRefreshReference();
}
async function pepRefreshReference() {
  const hint = document.getElementById('pep-allele-hint');
  if (!hint) return;
  const mhcClass = document.getElementById('pep-mhc-class').value === 'class2' ? 2 : 1;
  const search = document.getElementById('pep-alleles').value.trim();
  hint.textContent = '正在加载等位基因参考表…';
  hint.style.color = 'var(--text-muted)';
  try {
    const url = '/api/peptide/reference?mhc_class=' + mhcClass
      + '&search=' + encodeURIComponent(search) + '&limit=500';
    const response = await fetch(url);
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(pepErrorDetail(response, payload, '参考表加载失败'));
    const items = payload.items || [];
    const list = document.getElementById('pep-allele-list');
    list.replaceChildren();
    items.forEach(item => {
      const option = document.createElement('option');
      option.value = item.allele;
      option.label = [item.locus, item.supertype].filter(Boolean).join(' · ');
      list.appendChild(option);
    });
    pepState.referenceTotal = Number(payload.total || items.length);
    hint.textContent = 'MHC-' + (mhcClass === 1 ? 'I' : 'II') + ' 参考表：共 '
      + pepState.referenceTotal + ' 个等位基因' + (search ? '（当前匹配 ' + items.length + '）' : '（显示前 ' + items.length + '）');
    hint.style.color = 'var(--text-muted)';
  } catch (error) {
    hint.textContent = '参考表加载失败：' + String(error.message || error);
    hint.style.color = 'var(--danger)';
  }
}
function pepDebounceReference() {
  if (pepState.searchTimer) clearTimeout(pepState.searchTimer);
  pepState.searchTimer = setTimeout(() => { pepRefreshReference(); }, 300);
}
function pepUpdateProjectState() {
  const hint = document.getElementById('pep-project-hint');
  const button = document.getElementById('pep-project-btn');
  if (!hint || !button) return;
  if (state.currentProject) {
    hint.textContent = '当前项目：' + state.currentProject + '。将读取项目目录中的事件表和编码序列对照表。';
    hint.style.color = 'var(--text-muted)';
    button.disabled = false;
    button.style.opacity = '1';
  } else {
    hint.textContent = '尚未选择项目。请先在“仪表盘”新建或选择一个项目，再回来生成候选肽。';
    hint.style.color = 'var(--text-muted)';
    button.disabled = true;
    button.style.opacity = '.55';
  }
}
async function pepLoadMeta() {
  if (pepState.loading) return;
  pepState.loading = true;
  try {
    const response = await fetch('/api/peptide/capabilities');
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(pepErrorDetail(response, payload, '能力信息加载失败'));
    pepState.capabilities = payload;
    const local = (payload.predictors || {}).mhcflurry || {};
    const reference = payload.reference || {};
    const localOption = document.getElementById('pep-predictor-local');
    const predictorSelect = document.getElementById('pep-predictor');
    if (localOption && predictorSelect) {
      const ready = !!local.available;
      localOption.disabled = !ready;
      localOption.textContent = 'MHCflurry（本地，' + (ready ? '可用' : '未安装') + '）';
      if (!ready && predictorSelect.value === 'local') predictorSelect.value = 'iedb';
    }
    const label = document.getElementById('pep-capabilities');
    if (label) {
      label.textContent = 'IEDB 在线 · MHCflurry ' + (local.available ? '可用 ' + (local.version || '') : '未安装')
        + ' · 参考表 class1 ' + (reference.alleles_class1 || 0) + ' / class2 ' + (reference.alleles_class2 || 0)
        + ' · 已知表位 ' + (reference.known_epitopes || 0);
    }
  } catch (error) {
    const label = document.getElementById('pep-capabilities');
    if (label) label.textContent = '能力信息加载失败：' + String(error.message || error);
  } finally {
    pepState.loading = false;
    pepState.loaded = true;
  }
}
function pepBindOnce() {
  if (pepState.bound) return;
  pepState.bound = true;
  const textarea = document.getElementById('pep-sequences');
  if (textarea) textarea.addEventListener('input', pepCountSequences);
  const alleles = document.getElementById('pep-alleles');
  if (alleles) {
    alleles.addEventListener('input', () => { pepRenderChips(); pepDebounceReference(); });
    alleles.addEventListener('change', () => { pepRenderChips(); pepRefreshReference(); });
  }
  const mhcSelect = document.getElementById('pep-mhc-class');
  if (mhcSelect) mhcSelect.addEventListener('change', () => { pepRefreshReference(); });
}
function pepInitPage() {
  pepBindOnce();
  pepUpdateProjectState();
  pepRenderChips();
  const textarea = document.getElementById('pep-sequences');
  if (textarea) textarea.focus();
  if (!pepState.loaded) {
    pepLoadMeta();
    pepRefreshReference();
  } else {
    pepUpdateProjectState();
  }
}
function pepScoreValue(row) {
  const candidates = [row.score, row.total_score, row.mhcnp_probability];
  for (let index = 0; index < candidates.length; index += 1) {
    const value = Number(candidates[index]);
    if (candidates[index] !== null && candidates[index] !== undefined && Number.isFinite(value)) {
      return value;
    }
  }
  return Number.POSITIVE_INFINITY;
}
function pepSortValue(row, key) {
  if (key === 'percentile_rank') {
    const value = Number(row[key]);
    return Number.isFinite(value) ? value : Number.POSITIVE_INFINITY;
  }
  if (key === 'score') return pepScoreValue(row);
  return String(row[key] == null ? '' : row[key]).toLowerCase();
}
function pepSortBy(key) {
  if (pepState.sortKey === key) {
    pepState.sortDir = -pepState.sortDir;
  } else {
    pepState.sortKey = key;
    pepState.sortDir = key === 'percentile_rank' ? 1 : -1;
  }
  pepRenderPredictionTable();
}
function pepRenderPredictionTable() {
  const box = document.getElementById('pep-results');
  if (!box) return;
  const rows = pepState.predictions.slice();
  if (!rows.length) {
    box.innerHTML = '<p style="color:var(--text-muted);font-size:13px;">暂无预测结果。</p>';
    return;
  }
  const key = pepState.sortKey;
  const dir = pepState.sortDir;
  rows.sort((a, b) => {
    const left = pepSortValue(a, key);
    const right = pepSortValue(b, key);
    if (left < right) return -1 * dir;
    if (left > right) return 1 * dir;
    return String(a.peptide || '').localeCompare(String(b.peptide || ''));
  });
  const header = '<th style="white-space:nowrap;">#</th>' + [
    ['peptide', '肽段'], ['allele', 'HLA'],
    ['method', '方法'], ['percentile_rank', 'percentile rank（<0.5 强 / <2 弱）'], ['score', '分数（EL / 加工总分，不可比）']
  ].map(([column, text]) => {
    const marker = pepState.sortKey === column ? (pepState.sortDir === 1 ? ' ▲' : ' ▼') : '';
    return '<th data-sort="' + column + '" style="cursor:pointer;white-space:nowrap;">'
      + pepEscape(text) + marker + '</th>';
  }).join('');
  const body = rows.map((row, index) => {
    const method = row.method_label || row.method || '';
    const rankValue = Number(row.percentile_rank);
    const hasRank = row.percentile_rank !== null && row.percentile_rank !== undefined
      && Number.isFinite(rankValue);
    let tierClass = 'pep-tier-unknown';
    let tierText = '无 rank';
    if (hasRank && rankValue < 0.5) { tierClass = 'pep-tier-strong'; tierText = '强结合'; }
    else if (hasRank && rankValue < 2) { tierClass = 'pep-tier-weak'; tierText = '弱结合'; }
    else if (hasRank) { tierClass = 'pep-tier-none'; tierText = '非结合'; }
    const percentile = (hasRank ? pepEscape(row.percentile_rank) : '—')
      + '<span class="pep-tier ' + tierClass + '">' + tierText + '</span>';
    const scoreValue = pepScoreValue(row);
    const score = scoreValue === Number.POSITIVE_INFINITY ? '—' : pepEscape(scoreValue);
    return '<tr>'
      + '<td>' + (index + 1) + '</td>'
      + '<td style="font-family:var(--font-mono,monospace);">' + pepEscape(row.peptide) + '</td>'
      + '<td>' + pepEscape(row.allele) + '</td>'
      + '<td>' + pepEscape(method) + '</td>'
      + '<td>' + percentile + '</td>'
      + '<td>' + score + '</td>'
      + '</tr>';
  }).join('');
  box.innerHTML = '<div class="table-container" style="max-height:460px;overflow:auto;">'
    + '<table><thead><tr>' + header + '</tr></thead><tbody>' + body + '</tbody></table></div>'
    + '<div style="font-size:12px;color:var(--text-muted);margin-top:6px;">共 '
    + rows.length + ' 行（肽段 × HLA × 方法）。点击表头可排序。'
    + '强结合 &lt;0.5、弱结合 0.5~2、其余不列为候选；EL 分数与加工总分量纲不同，不可横向比较。</div>'
    + '<div id="pep-tier-summary" class="trace-meta" style="margin-top:6px;"></div>';
  const tierCounts = { strong: 0, weak: 0, none: 0, unknown: 0 };
  rows.forEach(function (row) {
    const value = Number(row.percentile_rank);
    if (row.percentile_rank === null || row.percentile_rank === undefined || !Number.isFinite(value)) {
      tierCounts.unknown += 1;
    } else if (value < 0.5) { tierCounts.strong += 1; }
    else if (value < 2) { tierCounts.weak += 1; }
    else { tierCounts.none += 1; }
  });
  const tierSummary = document.getElementById('pep-tier-summary');
  if (tierSummary) {
    const usable = tierCounts.strong + tierCounts.weak;
    tierSummary.textContent = '自动分级：强结合 ' + tierCounts.strong + ' 条 · 弱结合 '
      + tierCounts.weak + ' 条 · 非结合 ' + tierCounts.none + ' 条 · 无 rank '
      + tierCounts.unknown + ' 条。'
      + (usable ? '' : '本批未发现可用结合候选，不能据此宣称找到新抗原。');
    tierSummary.style.color = usable ? 'var(--text-secondary)' : 'var(--danger)';
  }
  box.querySelectorAll('th[data-sort]').forEach(th => {
    th.addEventListener('click', () => pepSortBy(th.getAttribute('data-sort')));
  });
}
function pepRenderErrors(errors) {
  const box = document.getElementById('pep-errors');
  if (!box) return;
  if (!errors || !errors.length) { box.replaceChildren(); return; }
  const items = errors.map(error => {
    const stage = error && error.stage ? String(error.stage) : '未知阶段';
    const message = error && error.error ? String(error.error) : JSON.stringify(error);
    return '<li><strong>' + pepEscape(stage) + '</strong>：' + pepEscape(message) + '</li>';
  }).join('');
  box.innerHTML = '<div style="font-size:12px;color:var(--danger);">预测服务返回 ' + errors.length
    + ' 条错误：</div><ul style="margin:6px 0 0 18px;font-size:12px;color:var(--text-secondary);">'
    + items + '</ul>';
}
function pepRenderEpitopes(matches) {
  const box = document.getElementById('pep-results');
  if (!box || !matches || !matches.length) return;
  const rows = matches.slice(0, 50).map(row => '<tr>'
    + '<td style="font-family:var(--font-mono,monospace);">' + pepEscape(row.candidate_peptide || row.peptide) + '</td>'
    + '<td>' + pepEscape(row.mhc_restriction || '') + '</td>'
    + '<td>' + pepEscape(row.qualitative_measure || '') + '</td>'
    + '<td>' + pepEscape(row.source_organism || '') + '</td>'
    + '<td>' + pepEscape(row.pubmed_id || '') + '</td>'
    + '</tr>').join('');
  const section = document.createElement('div');
  section.style.marginTop = '12px';
  section.innerHTML = '<div style="font-size:12px;color:var(--text-secondary);margin-bottom:6px;">IEDB 已知表位匹配（'
    + matches.length + ' 条；命中只说明该序列曾被检测过，不代表本次候选已验证）</div>'
    + '<div class="table-container" style="max-height:220px;overflow:auto;"><table><thead><tr>'
    + '<th>肽段</th><th>HLA</th><th>结局</th><th>来源</th><th>PMID</th></tr></thead><tbody>'
    + rows + '</tbody></table></div>';
  box.appendChild(section);
}
async function pepPredict() {
  const button = document.getElementById('pep-predict-btn');
  const status = 'pep-status';
  const parsed = pepCountSequences();
  const peptides = parsed.peptides;
  if (!peptides.length) {
    pepSetStatus(status, '请先输入至少一条 8–30 aa 的候选肽序列。', 'error');
    return;
  }
  const alleles = pepTokens();
  if (!alleles.length) {
    pepSetStatus(status, '请至少填写一个 HLA 型别，或点击常用面板快速填充。', 'error');
    return;
  }
  if (peptides.length > 200) {
    pepSetStatus(status, '单次最多 200 条肽，当前输入 ' + peptides.length + ' 条；请分批预测。', 'error');
    return;
  }
  if (alleles.length > 8) {
    pepSetStatus(status, '单次最多 8 个 HLA 型别，当前输入 ' + alleles.length + ' 个；请分批预测。', 'error');
    return;
  }
  const payload = {
    peptides: peptides,
    alleles: alleles,
    mhc_class: document.getElementById('pep-mhc-class').value,
    predictor: document.getElementById('pep-predictor').value,
    processing: document.getElementById('pep-processing').checked,
    lookup_epitopes: document.getElementById('pep-lookup').checked
  };
  button.disabled = true;
  button.style.opacity = '.55';
  pepSetStatus(status, '正在调用预测服务（' + peptides.length + ' 条肽 × ' + alleles.length + ' 个 HLA）…', 'muted');
  try {
    const response = await fetch('/api/peptide/predict', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(pepErrorDetail(response, data, '预测失败'));
    pepState.predictions = data.predictions || [];
    pepRenderErrors(data.errors || []);
    pepRenderPredictionTable();
    pepRenderEpitopes(data.epitope_matches || []);
    const errorCount = (data.errors || []).length;
    const count = Number(data.prediction_count || pepState.predictions.length);
    const zeroHint = (!count && !errorCount && payload.predictor !== 'none')
      ? ' 未产生预测记录：请核对肽长度与 MHC 类别、HLA 型别是否匹配（MHC-I 8–11 aa / MHC-II 11–30 aa）。'
      : '';
    const suffix = errorCount ? '；有 ' + errorCount + ' 条服务错误，见下方说明' : '；无服务错误';
    pepSetStatus(status, '预测完成：候选 ' + Number(data.candidate_count || 0) + ' 条，预测记录 '
      + count + ' 条' + suffix + '。' + zeroHint
      + ' percentile rank 越低越好（<0.5 强 / <2 弱）；预测不等于呈递或免疫原性。', errorCount ? 'error' : 'muted');
  } catch (error) {
    pepState.predictions = [];
    pepRenderPredictionTable();
    pepSetStatus(status, String(error.message || error), 'error');
  } finally {
    button.disabled = false;
    button.style.opacity = '1';
  }
}
async function pepRunProject() {
  const button = document.getElementById('pep-project-btn');
  const statusId = 'pep-project-status';
  const filesBox = document.getElementById('pep-project-files');
  if (filesBox) filesBox.replaceChildren();
  if (!state.currentProject) {
    pepSetStatus(statusId, '尚未选择项目，请先在仪表盘选择或新建项目。', 'error');
    return;
  }
  const alleles = pepTokens();
  if (!alleles.length) {
    pepSetStatus(statusId, '请先在上方填写 HLA 型别。', 'error');
    return;
  }
  const payload = {
    project_id: state.currentProject,
    alleles: alleles,
    mhc_class: document.getElementById('pep-mhc-class').value,
    predictor: document.getElementById('pep-predictor').value,
    processing: document.getElementById('pep-processing').checked,
    lookup_epitopes: document.getElementById('pep-lookup').checked
  };
  button.disabled = true;
  button.style.opacity = '.55';
  pepSetStatus(statusId, '正在读取项目数据并生成候选肽，预测可能需要数十秒…', 'muted');
  try {
    const response = await fetch('/api/peptide/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(pepErrorDetail(response, data, '生成候选肽失败'));
    pepState.projectOutput = data.output_dir || '';
    const tiers = data.tiers || {};
    const tierText = Object.keys(tiers).length
      ? Object.keys(tiers).sort().map(key => key + ':' + tiers[key]).join(' · ')
      : '无';
    const errorCount = (data.errors || []).length;
    pepSetStatus(statusId, '完成：候选 ' + Number(data.candidate_count || 0) + ' 条，预测 '
      + Number(data.prediction_count || 0) + ' 条，排序 ' + Number(data.ranked_count || 0)
      + ' 条；证据分层 ' + tierText + (errorCount ? '；服务错误 ' + errorCount + ' 条' : '') + '。', 'muted');
    pepRenderErrors(data.errors || []);
    if (filesBox && data.output_dir) {
      const names = ['ranked_candidates.tsv', 'splice_peptides.tsv', 'mhc_predictions.tsv', 'manifest.json', 'summary.md'];
      // /api/peptide/file expects the project data directory and appends
      // "peptide_results" itself, so strip the trailing output folder here.
      const normalized = String(data.output_dir).replace(new RegExp(String.fromCharCode(92), 'g'), '/');
      const marker = normalized.lastIndexOf('/peptide_results');
      const inputDir = marker >= 0 ? normalized.slice(0, marker) : normalized;
      const base = '/api/peptide/file?input_dir=' + encodeURIComponent(inputDir) + '&name=';
      names.forEach(name => {
        if ((data.files || []).length && (data.files || []).indexOf(name) < 0) return;
        const link = document.createElement('a');
        link.href = base + encodeURIComponent(name);
        link.textContent = name;
        link.style.color = 'var(--accent)';
        filesBox.appendChild(link);
      });
      const path = document.createElement('div');
      path.textContent = '输出目录：' + data.output_dir;
      path.style.cssText = 'width:100%;font-size:12px;color:var(--text-muted);';
      filesBox.appendChild(path);
    }
  } catch (error) {
    pepSetStatus(statusId, String(error.message || error), 'error');
  } finally {
    button.disabled = false;
    button.style.opacity = '1';
  }
}

document.querySelectorAll('.nav-item').forEach(item => { item.addEventListener('click', () => { navigateTo(item.dataset.page); }); });
function toggleNavigation(force) {
  const open = typeof force === 'boolean' ? force : !document.body.classList.contains('navigation-open');
  const mobile = window.matchMedia('(max-width:768px)').matches;
  const closingFocusedDrawer = !open && document.getElementById('app-navigation').contains(document.activeElement);
  document.querySelector('main').inert = open && mobile;
  document.body.classList.toggle('navigation-open', open);
  if (closingFocusedDrawer) document.querySelector('.mobile-menu').focus();
  document.querySelector('.mobile-menu').setAttribute('aria-expanded', String(open));
  const navigation = document.getElementById('app-navigation');
  navigation.inert = !open && window.matchMedia('(max-width:768px)').matches;
  if (open) { syncFluidMarker(); navigation.querySelector('.nav-item.active').focus(); }

}

const traceState = { projectsLoaded: false, data: null };
function traceEsc(value) {
  return String(value === undefined || value === null ? '' : value)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
function traceShort(value, limit) {
  let text;
  try { text = typeof value === 'string' ? value : JSON.stringify(value); }
  catch (error) { text = String(value); }
  text = String(text || '');
  return text.length > limit ? text.slice(0, limit) + '…' : text;
}
function traceBadge(source) {
  const key = String(source || 'rule');
  const labels = { llm: '模型决策', rule: '规则链', reflection: '反思纠错', episodic: '经验记忆', replay: '重放' };
  const cls = ['llm', 'reflection', 'episodic', 'replay'].includes(key) ? key : 'rule';
  return '<span class="trace-badge trace-' + cls + '">' + traceEsc(labels[key] || key) + '</span>';
}
function traceMetric(label, value, detail, bar) {
  let barHtml = '';
  if (typeof bar === 'number') {
    const pct = Math.max(0, Math.min(100, Math.round(bar * 100)));
    barHtml = '<div class="trace-bar"><span style="width:' + pct + '%"></span></div>';
  }
  return '<div class="card"><div class="trace-meta">' + traceEsc(label) + '</div>'
    + '<div class="trace-metric">' + traceEsc(value) + '</div>'
    + '<div class="trace-meta">' + traceEsc(detail) + '</div>' + barHtml + '</div>';
}
async function loadDecisionTrace() {
  const select = document.getElementById('trace-project');
  if (!select) return;
  const summary = document.getElementById('trace-summary');
  const stepsBox = document.getElementById('trace-steps');
  const callsBox = document.getElementById('trace-calls');
  const integrity = document.getElementById('trace-integrity');
  if (!traceState.projectsLoaded) {
    const projects = await apiCall('/projects');
    const list = (projects && projects.projects) || [];
    select.innerHTML = list.map(function (p) {
      const id = p.project_id || p.id || '';
      return '<option value="' + traceEsc(id) + '">' + traceEsc(p.name || id) + '</option>';
    }).join('');
    if (state.currentProject) select.value = state.currentProject;
    traceState.projectsLoaded = true;
  }
  const id = select.value;
  if (!id) {
    summary.innerHTML = '';
    integrity.textContent = '还没有已分析的项目。请先运行一次分析。';
    stepsBox.innerHTML = '<div class="trace-meta">暂无轨迹。</div>';
    callsBox.innerHTML = '<div class="trace-meta">暂无调用。</div>';
    return;
  }
  stepsBox.innerHTML = '<div class="trace-meta">正在读取轨迹…</div>';
  const data = await apiCall('/projects/' + encodeURIComponent(id) + '/trace');
  if (!data || !data.available) {
    summary.innerHTML = '';
    integrity.textContent = '该项目没有决策轨迹：' + traceEsc((data && data.detail) || '接口不可用')
      + '。只有 agentic 模式运行会写入 agent_state.json。';
    stepsBox.innerHTML = '<div class="trace-meta">暂无轨迹。</div>';
    callsBox.innerHTML = '<div class="trace-meta">暂无调用。</div>';
    return;
  }
  traceState.data = data;
  const pct = Math.round((data.llm_ratio || 0) * 100);
  summary.innerHTML = traceMetric('总决策步数', data.total_steps, '含规则链与模型选步')
    + traceMetric('模型参与决策', data.llm_steps, '占比 ' + pct + '%', data.llm_ratio)
    + traceMetric('自我纠错 / 经验', (data.reflection_steps || 0) + ' / ' + (data.episodic_steps || 0), 'reflection / episodic')
    + traceMetric('模型 / 工具调用', data.model_call_count + ' / ' + data.tool_call_count, '全部写入轨迹文件');
  const fingerprints = Object.keys(data.input_fingerprints || {}).length;
  const reports = Object.keys(data.reports || {}).length;
  let integrityText = '轨迹完整性：' + (data.integrity_ok ? '校验通过' : '未通过或无签名')
    + '；输入指纹 ' + fingerprints + ' 个文件；报告哈希 ' + reports + ' 份；模型 '
    + traceEsc(data.model_name || '未配置') + '；llm_enabled=' + traceEsc(String(data.llm_enabled));
  if (data.errors && data.errors.length) {
    integrityText += '；错误 ' + data.errors.length + ' 条：' + traceShort(data.errors[0], 140);
  }
  integrity.textContent = integrityText;
  stepsBox.innerHTML = (data.steps || []).map(function (s) {
    const args = s.args && Object.keys(s.args).length ? traceShort(s.args, 180) : '';
    const issues = (s.issues || []).length ? '问题：' + traceEsc(traceShort(s.issues.join('、'), 160)) : '';
    return '<div class="trace-step"><div class="trace-step-title">'
      + '<span>' + traceEsc(s.index) + '.</span><span>' + traceEsc(s.action) + '</span>'
      + traceBadge(s.source) + '<span class="trace-meta">' + traceEsc(s.status) + '</span></div>'
      + '<div class="trace-meta">' + traceEsc(s.rationale || '') + '</div>'
      + (args ? '<div class="trace-meta">参数 ' + traceEsc(args) + '</div>' : '')
      + (issues ? '<div class="trace-meta">' + issues + '</div>' : '')
      + '<div class="trace-meta">耗时 ' + traceEsc(s.seconds) + ' s</div></div>';
  }).join('') || '<div class="trace-meta">没有步骤记录。</div>';
  const modelCards = (data.model_calls || []).map(function (c) {
    return '<div class="trace-call"><div style="font-weight:500">#' + traceEsc(c.seq) + ' '
      + traceEsc(c.stage) + ' · ' + traceEsc(c.model || '') + '</div>'
      + '<div class="trace-meta">prompt ' + traceEsc(c.prompt_hash) + ' · temp '
      + traceEsc(c.temperature) + ' · ' + traceEsc(c.elapsed_ms) + ' ms</div>'
      + '<div class="trace-meta">解析结果 ' + traceEsc(traceShort(c.parsed, 220)) + '</div>'
      + '<details><summary class="trace-meta">查看原始响应</summary><div class="trace-meta">'
      + traceEsc(traceShort(c.raw_response, 1200)) + '</div></details></div>';
  }).join('');
  const toolCards = (data.tool_calls || []).map(function (c) {
    return '<div class="trace-call"><div style="font-weight:500">#' + traceEsc(c.seq) + ' MCP '
      + traceEsc(c.tool) + ' · ' + traceEsc(c.server) + '</div>'
      + '<div class="trace-meta">参数 ' + traceEsc(traceShort(c.args, 200)) + '</div>'
      + '<div class="trace-meta">结果 ' + traceEsc(traceShort(c.result, 260)) + '</div></div>';
  }).join('');
  callsBox.innerHTML = modelCards + toolCards || '<div class="trace-meta">这次运行没有模型或工具调用（纯确定性运行）。</div>';
}
async function compareDecisionTrace() {
  const out = document.getElementById('trace-compare-result');
  const left = document.getElementById('trace-project').value;
  const right = document.getElementById('trace-compare-right').value.trim();
  if (!left) { out.textContent = '请先选择项目。'; return; }
  const payload = { left: left, right: right || left };
  out.textContent = '正在对比…';
  const result = await apiCall('/trace/compare', { method: 'POST', body: JSON.stringify(payload) });
  if (!result) { out.textContent = '对比请求失败。'; return; }
  if (result.detail) { out.textContent = '对比失败：' + traceEsc(result.detail); return; }
  out.textContent = result.identical
    ? '两次运行的步骤、参数、排序结果与报告哈希完全一致。'
    : '存在差异：' + traceEsc((result.differences || []).join('；'));
}


const missionState = { plan: null, projectId: '', proof: null, job: '' };
function missionEsc(value) { return traceEsc(value === undefined || value === null ? '' : String(value)); }
function missionRenderStatus(job, proof) {
  const box = document.getElementById('mission-status-banner');
  if (!box) return;
  const info = job || {};
  let status = (proof && proof.run_status) || info.outcome_status
    || (info.status === 'failed' ? 'failed' : (info.status === 'done' ? 'succeeded' : 'running'));
  let cls = 'mission-banner mission-banner-running';
  let title = '正在执行分析';
  let body = '任务已提交；完成后这里会直接给出结论、失败原因和产物位置。';
  if (status === 'failed') {
    cls = 'mission-banner mission-banner-failed';
    title = '本次分析未产出数据';
    body = (proof && proof.run_summary) || ('执行失败：' + (info.error || info.stopped_reason || '未知原因'));
  } else if (status === 'partial') {
    cls = 'mission-banner mission-banner-partial';
    title = '结果不完整';
    body = (proof && proof.run_summary) || ('分析提前结束：' + (info.stopped_reason || '预算耗尽'));
  } else if (status === 'succeeded') {
    cls = 'mission-banner mission-banner-succeeded';
    title = '分析完成';
    body = (proof && proof.run_summary) || '报告、图表与决策轨迹已写入下方目录。';
  }
  let html = '<div class="' + cls + '"><div style="font-size:14px;font-weight:600;margin-bottom:4px;">'
    + missionEsc(title) + '</div><div>' + missionEsc(body) + '</div>';
  const failure = proof && proof.failure;
  if (failure) {
    html += '<div class="mission-hint">终止原因：' + missionEsc(failure.reason) + '</div>';
    html += '<div class="mission-hint">排查建议：' + missionEsc(failure.hint) + '</div>';
  }
  (info.diagnostics || []).forEach(function (item) {
    html += '<div class="mission-hint">数据加载提示：' + missionEsc(item) + '</div>';
  });
  box.innerHTML = html + '</div>';
}
function missionRenderArtifacts(proof) {
  const box = document.getElementById('mission-artifacts');
  if (!box) return;
  const artifacts = (proof && proof.artifacts) || [];
  const dir = (proof && proof.output_dir) || '';
  let html = '<div class="trace-meta" style="font-weight:500;margin-bottom:6px;">本次产物在哪</div>';
  html += '<div class="mission-path">' + missionEsc(dir) + '</div>';
  if (!artifacts.length) {
    html += '<div class="mission-hint">本次没有生成结果文件；失败时通常只有一份占位报告。</div>';
  } else {
    html += '<div class="mission-hint">已生成 ' + artifacts.length + ' 个文件：'
      + artifacts.slice(0, 8).map(function (item) { return missionEsc(item.name); }).join('、') + '</div>';
    const figures = artifacts.filter(function (item) { return item.kind === 'figure'; }).length;
    html += figures
      ? '<div class="mission-hint">图表 ' + figures + ' 张；报告、轨迹都在上面的目录里。</div>'
      : '<div class="mission-hint">没有图表：本次没有进入出图与候选排序环节。</div>';
  }
  html += '<div class="mission-hint">这一区只放可复现凭证；候选表、剪接事件与图表请到左侧「报告」「事件浏览器」「候选新抗原」「可视化」页查看。</div>';
  box.innerHTML = html;
}
function missionOpenReport(format) {
  const id = missionState.projectId;
  if (!id) { document.getElementById('mission-verify-result').textContent = '请先执行一次分析。'; return; }
  const urls = (missionState.proof && missionState.proof.report_urls) || {};
  const url = urls[format] || ('/api/report/' + encodeURIComponent(id) + '?format=' + format);
  window.open(url, '_blank', 'noopener');
}
function missionSetStatus(text) {
  document.getElementById('mission-plan-status').textContent = text;
}
function missionPoll(jobId, onDone, onTick) {
  let attempts = 0;
  const tick = async function () {
    attempts += 1;
    const job = await apiCall('/jobs/' + encodeURIComponent(jobId));
    if (!job) { onDone({ status: 'failed', error: '无法查询任务状态' }); return; }
    if (onTick) onTick(job, attempts);
    if (job.status === 'running' && attempts < 160) {
      setTimeout(tick, 1500);
      return;
    }
    onDone(job);
  };
  tick();
}
async function missionGenerate() {
  missionSetStatus('正在生成计划…');
  const payload = { query: document.getElementById('mission-query').value.trim() };
  const result = await apiCall('/plan/preview', { method: 'POST', body: JSON.stringify(payload) });
  if (!result || !result.plan) { missionSetStatus('计划生成失败：' + traceEsc((result && result.detail) || '接口不可用')); return; }
  missionState.plan = result.plan;
  const plan = result.plan;
  document.getElementById('mission-goal').value = plan.goal || '';
  document.getElementById('mission-intent').value = plan.intent || 'differential_AS';
  document.getElementById('mission-fdr').value = (plan.thresholds || {}).fdr || 0.05;
  document.getElementById('mission-dpsi').value = (plan.thresholds || {}).delta_psi || 0.1;
  document.getElementById('mission-topn').value = (plan.thresholds || {}).top_candidates || 20;
  document.getElementById('mission-steps').value = (plan.budgets || {}).max_steps || 20;
  document.getElementById('mission-tools').value = (plan.expected_tools || []).join(String.fromCharCode(10));
  document.getElementById('mission-plan-meta').textContent = '计划来源 ' + traceEsc(plan.source)
    + '；可用动作注册表 ' + traceEsc(result.registry_size) + ' 个；预期输出：'
    + traceEsc((plan.expected_outputs || []).join('、'));
  document.getElementById('mission-plan-card').style.display = 'block';
  missionSetStatus('计划已生成，请审阅或修改后执行。');
}
function missionCollectPlan() {
  const base = missionState.plan || {};
  const thresholds = Object.assign({}, base.thresholds || {}, {
    fdr: parseFloat(document.getElementById('mission-fdr').value),
    delta_psi: parseFloat(document.getElementById('mission-dpsi').value),
    top_candidates: parseInt(document.getElementById('mission-topn').value, 10)
  });
  const budgets = Object.assign({}, base.budgets || {}, {
    max_steps: parseInt(document.getElementById('mission-steps').value, 10)
  });
  return {
    goal: document.getElementById('mission-goal').value.trim() || base.goal,
    intent: document.getElementById('mission-intent').value,
    thresholds: thresholds, budgets: budgets,
    expected_tools: document.getElementById('mission-tools').value.split(String.fromCharCode(10))
      .map(function (s) { return s.trim(); }).filter(Boolean),
    expected_outputs: base.expected_outputs || [],
    source: 'user', created_at: base.created_at || '', notes: base.notes || []
  };
}
async function missionRun() {
  const inputDir = document.getElementById('mission-input').value.trim();
  if (!inputDir) { missionSetStatus('请先填写输入数据目录。'); return; }
  const resultBox = document.getElementById('mission-result');
  resultBox.style.display = 'block';
  missionRenderStatus({ status: 'running' }, null);
  missionSetStatus('正在执行分析，可能需要几十秒…');
  const payload = {
    query: document.getElementById('mission-query').value.trim(),
    input_dir: inputDir, plan: missionCollectPlan()
  };
  const started = await apiCall('/plan/run', { method: 'POST', body: JSON.stringify(payload) });
  if (!started || !started.job_id) {
    missionRenderStatus({ status: 'failed', error: (started && started.detail) || '接口不可用' }, null);
    missionSetStatus('启动失败：' + traceEsc((started && started.detail) || '接口不可用')); return;
  }
  missionState.job = started.job_id;
  missionPoll(started.job_id, function (job) {
    resultBox.style.display = 'block';
    if (job.status === 'done') {
      missionState.projectId = job.project_id || '';
      missionRenderStatus(job, null);
      document.getElementById('mission-run-summary').textContent = '项目 '
        + missionEsc(job.project_id) + '；模式 ' + missionEsc(job.mode) + '；执行 '
        + missionEsc(job.steps) + ' 步；终止状态 ' + missionEsc(job.stopped_reason || '正常结束')
        + '；输入事件 ' + missionEsc(job.event_count || 0) + ' 条；图表 ' + missionEsc(job.figures || 0) + ' 张。';
      missionSetStatus('正在生成可复现证明…');
      missionLoadProof(job.project_id, job);
    } else {
      missionRenderStatus(job, null);
      missionSetStatus('执行失败：' + missionEsc(job.error || '未知错误'));
    }
  }, function (job, n) {
    if (n % 4 === 0) missionSetStatus('正在执行分析…（已等待 ' + Math.round(n * 1.5) + ' 秒）');
  });
}
async function missionLoadProof(projectId, job) {
  const proof = await apiCall('/projects/' + encodeURIComponent(projectId) + '/proof');
  if (!proof || proof.detail) {
    missionRenderStatus(job || {}, null);
    missionSetStatus('证明生成失败：' + missionEsc((proof && proof.detail) || '接口不可用')); return;
  }
  missionState.proof = proof;
  missionRenderStatus(job || {}, proof);
  missionRenderArtifacts(proof);
  const dev = proof.deviations || {};
  let devHtml = '<div class="trace-meta" style="font-weight:500;margin-bottom:6px;">计划与实际</div>';
  devHtml += '<div class="trace-meta">计划工具 ' + missionEsc(dev.planned_count)
    + ' 个，实际执行 ' + missionEsc(dev.executed_count) + ' 步，计划命中率 '
    + missionEsc(dev.adherence_ratio === null ? '无计划' : Math.round((dev.adherence_ratio || 0) * 100) + '%') + '</div>';
  devHtml += '<div class="mission-hint">' + missionEsc(dev.note || '') + '</div>';
  if ((dev.planned_not_run || []).length) {
    devHtml += '<div class="trace-call"><div style="font-weight:500">未执行的计划动作（'
      + dev.planned_not_run.length + ' 个）</div><div class="trace-meta">'
      + missionEsc(dev.planned_not_run.join('、')) + '</div><div class="mission-hint">'
      + missionEsc(dev.planned_not_run_reason || '') + '</div></div>';
  }
  (dev.autonomous_additions || []).slice(0, 6).forEach(function (item) {
    devHtml += '<div class="trace-call"><div style="font-weight:500">自主补充 ' + missionEsc(item.action)
      + ' · ' + traceBadge(item.source) + '</div><div class="trace-meta">'
      + missionEsc(item.reason_zh || item.reason) + '</div>'
      + '<details style="margin-top:4px;"><summary class="trace-meta" style="cursor:pointer;">查看模型原始依据</summary>'
      + '<div class="trace-meta">' + missionEsc(item.reason) + '</div></details></div>';
  });
  document.getElementById('mission-deviations').innerHTML = devHtml;
  const traj = proof.trajectory || {};
  const reports = Object.keys(proof.reports || {}).length;
  document.getElementById('mission-proof').innerHTML =
    '<div class="trace-meta" style="font-weight:500;margin-bottom:6px;">可复现证明</div>'
    + '<div class="trace-meta">完整性 ' + (proof.integrity_ok ? '校验通过' : '未通过')
    + '；输入指纹 ' + missionEsc(Object.keys(proof.input_fingerprints || {}).length)
    + ' 个文件；报告哈希 ' + missionEsc(reports) + ' 份；模型调用 '
    + missionEsc(traj.model_calls) + ' 次；工具调用 ' + missionEsc(traj.tool_calls) + ' 次</div>'
    + '<div class="trace-call mission-code" style="margin-top:8px;">'
    + missionEsc(proof.replay_command) + '</div>'
    + '<div class="mission-hint">' + missionEsc((proof.limitations || []).join(' ')) + '</div>';
  missionSetStatus(proof.run_status === 'failed'
    ? '分析未产出数据；失败原因与产物位置已显示在上方。'
    : '分析完成，证明已生成。可点「一键离线重放验证」。');
}
async function missionVerify() {
  const id = missionState.projectId;
  if (!id) return;
  document.getElementById('mission-verify-result').textContent = '正在离线重放并逐项比对…';
  const started = await apiCall('/projects/' + encodeURIComponent(id) + '/verify',
    { method: 'POST', body: JSON.stringify({}) });
  if (!started || !started.job_id) {
    document.getElementById('mission-verify-result').textContent =
      '验证启动失败：' + traceEsc((started && started.detail) || '接口不可用');
    return;
  }
  missionPoll(started.job_id, function (job) {
    const box = document.getElementById('mission-verify-result');
    if (job.status === 'done') {
      box.textContent = job.identical
        ? '重放通过：步骤、参数、排序结果与报告哈希逐项一致，且全程未调用模型或外部工具。'
        : '重放存在差异：' + traceEsc((job.differences || []).join('；'));
    } else {
      box.textContent = '验证失败：' + traceEsc(job.error || '未知错误');
    }
  }, function (job, n) {
    if (n % 4 === 0) document.getElementById('mission-verify-result').textContent =
      '正在离线重放…（已等待 ' + Math.round(n * 1.5) + ' 秒）';
  });
}
function missionCopyProof() {
  const command = missionState.proof && missionState.proof.replay_command;
  const box = document.getElementById('mission-verify-result');
  if (!command) { box.textContent = '暂无可复制的重放命令。'; return; }
  if (navigator.clipboard) navigator.clipboard.writeText(command);
  box.textContent = '重放命令已复制到剪贴板（单行，可直接粘贴到终端）。';
}
function missionOpenTrace() {
  const id = missionState.projectId;
  if (!id) return;
  const select = document.getElementById('trace-project');
  if (select) {
    const option = Array.from(select.options).find(function (o) { return o.value === id; });
    if (!option) { const opt = document.createElement('option'); opt.value = id; opt.textContent = id; select.appendChild(opt); }
    select.value = id;
  }
  navigateTo('trace');
}

function navigateTo(page) {
  if (!document.getElementById('page-' + page)) return;
  closeProjectDetail();
  const previousPage = state.currentPage;
  toggleNavigation(false);
  document.querySelectorAll('.nav-item').forEach(item => {
    if (item.dataset.page === page) item.setAttribute('aria-current', 'page');
    else item.removeAttribute('aria-current');
  });

  document.querySelectorAll('.nav-item').forEach(item => { item.classList.toggle('active', item.dataset.page === page); });
  document.querySelectorAll('.page').forEach(p => { p.classList.toggle('active', p.id === `page-${page}`); });
  state.currentPage = page;
  syncFluidMarker();
  animateWorkspace(previousPage, page);
  document.getElementById('workspace-content').focus({preventScroll:true});
  window.scrollTo({top:0, behavior:'instant'});
  if (page === 'dashboard') loadDashboard();
  if (page === 'pipeline') loadPipeline();
  if (page === 'neoantigen') { restoreNeoWorkflow(); checkNeoReadiness(); }
  if (page === 'peptide') { pepInitPage(); }
  if (page === 'explorer') loadExplorer();
  if (page === 'settings') { loadModelConfig(); loadMcpServers(); }
  if (page === 'trace') loadDecisionTrace();
  if (page === 'mission') missionGenerate();
}
async function apiCall(endpoint, options = {}) {
  try { const response = await fetch(`/api${endpoint}`, { headers: { 'Content-Type': 'application/json' }, ...options }); return await response.json(); }
  catch (error) { console.error('API Error:', error); return null; }
}
async function loadDashboard() {
  const response = await apiCall('/projects');
  if (!response) {
    document.getElementById('recent-projects').innerHTML = '<div role="alert" style="padding:24px;color:var(--danger)">暂时无法连接项目服务。请检查服务是否启动，然后点击上方刷新。</div>';
    return;
  }
  const projectsData = (response && response.projects) || response || [];
  state.projects = Array.isArray(projectsData) ? projectsData : [];

  // Keep the selected historical project across refreshes.
  if (state.projects.length > 0) {
    const selectedProject = state.projects.find(p => p.project_id === state.currentProject) || state.projects[0];
    state.currentProject = selectedProject.project_id;
    localStorage.setItem('epitoperank.currentProject', state.currentProject);
    document.getElementById('current-project').textContent = selectedProject.name || selectedProject.project_id;

    // Counters come from the list endpoint (SQL counts), so the dashboard stays
    // fast even for projects with a million events.
    document.getElementById('stat-samples').textContent = selectedProject.sample_count ?? '-';
    document.getElementById('stat-events').textContent = fmtCount(selectedProject.event_count);
    document.getElementById('stat-significant').textContent = fmtCount(selectedProject.significant_count);
    document.getElementById('stat-status').innerHTML = '<span class="status status-waiting"><span class="status-dot"></span>已归档</span>';

    await loadProjectDetail(state.currentProject);
  } else {
    document.getElementById('stat-samples').textContent = '-';
    document.getElementById('stat-events').textContent = '-';
    document.getElementById('stat-significant').textContent = '-';
    closeProjectDetail();
  }

  renderProjectHistory();
  loadStorageHint();
}
function fmtCount(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return '-';
  return n.toLocaleString('en-US');
}
function fmtDate(value) {
  if (!value) return '-';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return String(value);
  const pad = n => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}
async function loadStorageHint() {
  if (state.storage) { renderStorageHint(); return; }
  const info = await apiCall('/storage');
  if (info) { state.storage = info; renderStorageHint(); }
}
function renderStorageHint() {
  const box = document.getElementById('storage-hint');
  if (!box || !state.storage) return;
  const root = state.storage.runtime_root || '-';
  const db = (state.storage.databases || {})['epitoperank.sqlite3'] || {};
  box.innerHTML = `数据目录：<span style="font-family:var(--font-mono);word-break:break-all;color:var(--text-secondary);">${ingestEsc(root)}</span>`
    + `　·　数据库 ${db.size_mb || 0} MB`;
}
function openProjectDetail() {
  if (!state.currentProject) {
    AppNotify.toast('请先在仪表盘选择一个项目，再打开项目详情。', 'warning');
    return;
  }
  toggleNavigation(false);
  document.body.classList.add('detail-open');
  if (!state.detail) loadProjectDetail(state.currentProject);
}
function closeProjectDetail() { document.body.classList.remove('detail-open'); }
async function loadProjectDetail(projectId) {
  const status = await apiCall(`/status/${projectId}`);
  state.detail = status || null;
  if (!status) { closeProjectDetail(); return; }

  const project = status.project || {};
  document.getElementById('detail-title').textContent = project.name || project.project_id || projectId;
  document.getElementById('detail-meta').textContent =
    `${project.project_id || projectId} · ${fmtDate(project.created_at)} · 输入格式 ${project.source_format || '-'} · ${fmtCount(status.events)} 个事件 / ${fmtCount(status.significant)} 个显著`;

  const groups = {};
  (status.samples || []).forEach(s => { const g = s.group_name || '未分组'; (groups[g] = groups[g] || []).push(s.sample_id); });
  const groupChips = Object.entries(groups).map(([g, ids]) =>
    `<span class="hero-chip" title="${ingestEsc(ids.join(', '))}">${ingestEsc(g)} · ${ids.length}</span>`).join('');
  document.getElementById('detail-groups').innerHTML = groupChips || '<span style="font-size:12px;color:var(--text-muted);">未记录样本分组</span>';

  const types = status.event_types || {};
  document.getElementById('detail-types').innerHTML = Object.entries(types).map(([k, v]) =>
    `<span class="hero-chip">${ingestEsc(k)} · ${fmtCount(v)}</span>`).join('') || '<span style="font-size:12px;color:var(--text-muted);">-</span>';

  const logs = (status.logs || []).slice(-12).reverse();
  document.getElementById('detail-logs').innerHTML = logs.length ? logs.map(l =>
    `<div style="display:flex;gap:8px;border-bottom:1px dashed var(--border);padding:4px 0;">
       <span style="color:var(--text-muted);white-space:nowrap;">${ingestEsc((l.created_at || '').replace('T', ' ').slice(5, 16))}</span>
       <span style="color:var(--text-secondary);">[${ingestEsc(l.agent || '')}] ${ingestEsc(l.action || '')}</span>
       <span style="margin-left:auto;color:${l.status === 'ok' ? 'var(--secondary)' : 'var(--danger)'};">${ingestEsc(l.status || '')}</span>
     </div>`).join('') : '<span style="font-size:12px;color:var(--text-muted);">无日志</span>';

  const figures = (status.artifacts || []).filter(a => (a.kind || '').startsWith('figure:'));
  document.getElementById('detail-figures').innerHTML = figures.length ? figures.map(a => {
    const name = a.kind.split(':')[1];
    const url = `/api/figure/${encodeURIComponent(projectId)}/${encodeURIComponent(name)}`;
    return `<a href="${url}" target="_blank" rel="noopener" style="display:block;border:1px solid var(--border);border-radius:var(--radius);overflow:hidden;background:rgba(3,12,17,.5);">
      <img src="${url}" alt="${ingestEsc(name)}" loading="lazy" style="width:100%;height:96px;object-fit:cover;display:block;">
      <div style="font-size:12px;padding:4px 6px;color:var(--text-secondary);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${ingestEsc(name)}</div>
    </a>`;
  }).join('') : '<span style="font-size:12px;color:var(--text-muted);">该项目没有保存图表</span>';

  const candidates = status.candidates || [];
  document.getElementById('detail-candidates').innerHTML = candidates.length ? `<table style="width:100%;border-collapse:collapse;">
      <thead><tr style="text-align:left;color:var(--text-muted);font-size:12px;">
        <th style="padding:4px 6px;">#</th><th style="padding:4px 6px;">基因</th><th style="padding:4px 6px;">类型</th>
        <th style="padding:4px 6px;">ΔPSI</th><th style="padding:4px 6px;">FDR</th></tr></thead>
      <tbody>${candidates.map(c => `<tr style="border-top:1px solid var(--border);">
        <td style="padding:4px 6px;">${ingestEsc(c.rank)}</td>
        <td style="padding:4px 6px;font-weight:600;">${ingestEsc(c.gene_symbol || c.gene_id || '-')}</td>
        <td style="padding:4px 6px;">${ingestEsc(c.event_type || '-')}</td>
        <td style="padding:4px 6px;color:${(c.delta_psi || 0) > 0 ? 'var(--danger)' : 'var(--secondary)'};">${c.delta_psi === null || c.delta_psi === undefined ? '-' : Number(c.delta_psi).toFixed(3)}</td>
        <td style="padding:4px 6px;">${c.fdr === null || c.fdr === undefined ? '-' : fmtFdr(c.fdr)}</td>
      </tr>`).join('')}</tbody></table>`
    : '<span style="font-size:12px;color:var(--text-muted);">该项目没有候选事件记录</span>';
}
function openReport(format) {
  if (!state.currentProject) return;
  window.open(`/api/report/${encodeURIComponent(state.currentProject)}?format=${format}`, '_blank');
}
async function revealProjectBundle() {
  if (!state.currentProject) return;
  const hint = document.getElementById('detail-bundle-hint');
  const say = (text, ok) => {
    if (!hint) return;
    hint.textContent = text;
    hint.style.color = ok ? 'var(--secondary)' : 'var(--danger)';
  };
  if (hint) say('正在整理成果文件夹…', true);
  try {
    const response = await fetch(`/api/projects/${encodeURIComponent(state.currentProject)}/reveal-bundle`, { method: 'POST' });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) { say(data.detail || '打开成果文件夹失败', false); return; }
    say('已打开：' + (data.path || ''), true);
  } catch (error) {
    say('打开成果文件夹失败：' + error.message, false);
  }
}
async function packageProject() {
  if (!state.currentProject) return;
  const hint = document.getElementById('detail-bundle-hint');
  const say = (text, ok) => {
    if (!hint) return;
    hint.textContent = text;
    hint.style.color = ok ? 'var(--secondary)' : 'var(--danger)';
  };
  if (hint) say('正在打包…', true);
  try {
    const response = await fetch(`/api/projects/${encodeURIComponent(state.currentProject)}/package`, { method: 'POST' });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) { say(data.detail || '打包失败', false); return; }
    say(`已打包（${data.size_mb} MB）：${data.path}`, true);
  } catch (error) {
    say('打包失败：' + error.message, false);
  }
}
function jumpToExplorer() {
  if (!state.currentProject) return;
  navigateTo('explorer');
  loadExplorer();
}
async function deleteCurrentProject() {
  if (!state.currentProject) return;
  const project = (state.projects || []).find(p => p.project_id === state.currentProject) || {};
  const label = project.name || state.currentProject;
  const confirmed = await AppNotify.confirm(
    `项目「${label}」的数据库记录、图表与报告目录都会被移除，且无法撤销。原始输入数据不会被删除。`,
    { kind: 'warning', title: '删除这个项目？', confirmLabel: '删除项目', cancelLabel: '保留项目', danger: true }
  );
  if (!confirmed) return;
  const response = await fetch(`/api/projects/${encodeURIComponent(state.currentProject)}`, { method: 'DELETE' });
  if (!response.ok) { AppNotify.toast('删除失败：HTTP ' + response.status, 'error'); return; }
  localStorage.removeItem('epitoperank.currentProject');
  state.currentProject = null;
  state.detail = null;
  closeProjectDetail();
  await loadDashboard();
}
function renderProjectHistory() {
  const projectsList = document.getElementById('recent-projects');
  const term = (document.getElementById('project-search')?.value || '').toLowerCase();
  const projects = state.projects.filter(p => ((p.name || '') + ' ' + (p.project_id || '') + ' ' + (p.query || '')).toLowerCase().includes(term));
  if (state.projects.length === 0) {
    projectsList.innerHTML = '<div style="padding: 40px; text-align: center; color: var(--text-muted);">暂无项目</div>';
  } else {
    projectsList.innerHTML = projects.map(p => {
      const active = p.project_id === state.currentProject;
      return `<div style="padding: 11px 12px; border-bottom: 1px solid var(--border); cursor: pointer; ${active ? 'background:var(--gray-100);border-left:1px solid var(--black);' : 'border-left:3px solid transparent;'}" onclick="selectProject('${ingestEsc(p.project_id)}')">
        <div style="display:flex;justify-content:space-between;gap:8px;align-items:baseline;">
          <div style="font-weight:600;font-size:13px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${ingestEsc(p.name || p.project_id)}</div>
          <div style="font-size:12px;color:var(--text-muted);white-space:nowrap;">${ingestEsc(fmtDate(p.created_at).slice(0, 10))}</div>
        </div>
        <div style="font-size:12px;color:var(--text-secondary);margin-top:5px;display:flex;gap:10px;flex-wrap:wrap;">
          <span>${ingestEsc(p.source_format || '-')}</span>
          <span>事件 ${fmtCount(p.event_count)}</span>
          <span style="color:var(--danger);">显著 ${fmtCount(p.significant_count)}</span>
        </div>
        <div style="font-size:12px;color:var(--text-muted);margin-top:3px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${ingestEsc(p.query || '分析查询')}</div>
      </div>`;
    }).join('') || '<div style="padding:20px;text-align:center;color:var(--text-muted);">没有匹配的项目</div>';
  }
}
async function loadPipeline() {
  if (!state.currentProject) return;
  const status = await apiCall(`/status/${state.currentProject}`);
  state.analysisStatus = status;
  if (status) updatePipelineUI(status);
}
function updatePipelineUI(status) {
  const steps = document.querySelectorAll('.pipeline-step');
  
  // Try to get current_step from status, or infer from logs
  let currentStep = status.current_step;
  let statusText = '等待启动...';
  
  if (currentStep === undefined || currentStep === null) {
    // Infer step from logs
    const logs = status.logs || [];
    const actions = logs.map(l => l.action);
    
    if (actions.includes('run_finished')) {
      currentStep = steps.length; // All steps completed
      statusText = '分析已完成';
    } else if (actions.includes('interpret_candidates') || actions.includes('generate_report')) {
      currentStep = 5; // Interpretation done
      statusText = '解读 Agent 正在生成生物学解读...';
    } else if (actions.includes('collect_literature_evidence')) {
      currentStep = 4;
      statusText = '注释 Agent 正在收集文献证据...';
    } else if (actions.includes('run_enrichment')) {
      currentStep = 4;
      statusText = '注释 Agent 正在进行通路富集分析...';
    } else if (actions.includes('rank_candidates')) {
      currentStep = 3;
      statusText = '统计 Agent 正在排序候选事件...';
    } else if (actions.includes('filter_significant_events')) {
      currentStep = 3;
      statusText = '剪接检测 Agent 正在筛选显著事件...';
    } else if (actions.includes('summarize_dataset')) {
      currentStep = 2;
      statusText = '质控 Agent 正在进行质量检查...';
    } else if (actions.includes('understand_query')) {
      currentStep = 1;
      statusText = '数据 Agent 正在理解查询...';
    } else if (actions.includes('run_started')) {
      currentStep = 0;
      statusText = '分析已启动，准备中...';
    } else {
      currentStep = 0;
      statusText = '等待启动...';
    }
  } else {
    const stepNames = ['数据加载', '质量控制', '剪接检测', '统计分析', '功能注释', '生物学解读'];
    statusText = currentStep < stepNames.length ? `正在执行: ${stepNames[currentStep]}` : '处理中...';
  }
  
  document.getElementById('pipeline-status-text').textContent = statusText;
  
  const totalSteps = steps.length;
  const progress = Math.round((currentStep / totalSteps) * 100);
  document.getElementById('pipeline-progress').textContent = `${progress}%`;
  document.getElementById('progress-bar').style.width = `${progress}%`;
  
  steps.forEach((step, index) => {
    step.classList.remove('waiting', 'active', 'completed');
    if (index < currentStep) { 
      step.classList.add('completed'); 
      step.querySelector('.status').className = 'status status-completed'; 
      step.querySelector('.status').innerHTML = '<span class="status-dot"></span>已完成'; 
    } else if (index === currentStep && currentStep < totalSteps) { 
      step.classList.add('active'); 
      step.querySelector('.status').className = 'status status-running'; 
      step.querySelector('.status').innerHTML = '<span class="status-dot"></span>运行中'; 
    } else { 
      step.classList.add('waiting'); 
      step.querySelector('.status').className = 'status status-waiting'; 
      step.querySelector('.status').innerHTML = '<span class="status-dot"></span>等待中'; 
    }
  });
}
async function loadExplorer() {
  if (!state.currentProject) return;
  // Real rMATS projects hold 10^5-10^6 events: filtering and paging happen in
  // SQLite, the browser only ever receives one page.
  await loadEventPage(1);
}
function explorerFilters() {
  const term = (document.getElementById('search-input')?.value || '').trim();
  const types = Array.from(document.querySelectorAll('.checkbox-group input[type="checkbox"]'))
    .filter(cb => cb.checked).map(cb => cb.value);
  return {
    q: term,
    // The backend accepts a single event type; when several are ticked we omit
    // the filter and let the user narrow further, rather than silently
    // showing only the first one.
    event_type: types.length === 1 ? types[0] : '',
    significant_only: !!document.getElementById('filter-significant')?.checked,
    order_by: document.getElementById('filter-order')?.value || 'fdr',
  };
}
async function loadEventPage(page) {
  if (!state.currentProject) return;
  const filters = explorerFilters();
  const params = new URLSearchParams({
    page: String(page),
    size: '50',
    q: filters.q,
    event_type: filters.event_type,
    significant_only: filters.significant_only ? 'true' : 'false',
    order_by: filters.order_by,
  });
  const skeletonTimer = setTimeout(eventsSkeleton, 120);
  let data;
  try { data = await apiCall(`/projects/${encodeURIComponent(state.currentProject)}/events?${params.toString()}`); }
  finally { clearTimeout(skeletonTimer); }
  if (!data || data.events === undefined) {
    document.getElementById('events-table').innerHTML =
      '<tr><td colspan="6" style="text-align:center;padding:40px;color:var(--danger);">读取事件失败（项目可能已被删除）</td></tr>';
    return;
  }
  state.events = data.events;
  state.eventPage = data.page;
  state.eventPages = data.pages;
  state.eventTotal = data.total;
  renderEventsTable(data.events);
  const info = document.getElementById('events-pager-info');
  if (info) info.textContent = `共 ${fmtCount(data.total)} 个事件 · 每页 ${data.size} 条 · 已按${({fdr: 'FDR', delta_psi: '|ΔPSI|', gene: '基因名'})[filters.order_by] || 'FDR'}排序`;
  const pager = document.getElementById('events-pager-page');
  if (pager) pager.textContent = `${data.page} / ${data.pages}`;
}
function gotoEventPage(page) {
  const target = Math.min(Math.max(1, Number(page) || 1), state.eventPages || 1);
  loadEventPage(target);
}
function fmtSci(value, digits) {
  if (value === null || value === undefined || value === '') return '-';
  const n = Number(value);
  if (!isFinite(n)) return '-';
  if (n === 0) return '0';
  if (Math.abs(n) < 1e-300) return n > 0 ? '<1e-300' : '>-1e-300';
  const parts = n.toExponential(digits === undefined ? 2 : digits).split('e');
  let mantissa = parts[0];
  if (mantissa.indexOf('.') >= 0) mantissa = mantissa.replace(/0+$/, '').replace(/[.]$/, '');
  return mantissa + 'e' + String(Number(parts[1]));
}
function fmtFdr(value) {
  if (value === null || value === undefined || value === '') return '-';
  const n = Number(value);
  if (!isFinite(n)) return '-';
  if (n === 0) return '0';
  return n >= 0.001 ? n.toFixed(3) : fmtSci(n, 2);
}
function dpsiCell(value) {
  if (value === null || value === undefined || value === '' || !isFinite(Number(value))) return '<td class="num">-</td>';
  const n = Number(value), direction = n > 0 ? 'up' : n < 0 ? 'down' : 'neutral';
  return `<td class="num"><span class="dpsi-cell"><span class="dpsi-value ${direction}">${n > 0 ? '+' : ''}${n.toFixed(3)}</span><span class="dpsi-bar" aria-hidden="true"><span class="${direction}" style="width:${(Math.min(Math.abs(n),1)*50).toFixed(1)}%"></span></span></span></td>`;
}
function eventsSkeleton() {
  const tbody = document.getElementById('events-table');
  if (!tbody) return;
  tbody.innerHTML = Array.from({length:9}, () => '<tr class="skeleton-row">' + [70,52,38,34,44].map((width,i) => `<td><span class="sk" style="width:${width}%;${i > 2 ? 'margin-left:auto;' : ''}"></span></td>`).join('') + '<td></td></tr>').join('');
}
const eventTable = document.getElementById('events-table');
function openEventRow(event) {
  const row = event.target.closest('tr[data-event]');
  if (!row || !eventTable.contains(row)) return;
  if (event.type === 'keydown' && event.key !== 'Enter' && event.key !== ' ') return;
  if (event.type === 'keydown') event.preventDefault();
  viewEventDetails(row.dataset.event);
}
eventTable.addEventListener('click', openEventRow);
eventTable.addEventListener('keydown', openEventRow);
function renderEventsTable(events) {
  const tbody = document.getElementById('events-table');
  if (!events || events.length === 0) {
    tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; padding: 40px; color: var(--text-muted);">未找到匹配的事件</td></tr>';
    return;
  }
  tbody.innerHTML = events.map(event => {
    const eventId = event.event_id || event.id || '-';
    const gene = event.gene_symbol || event.gene || event.gene_id || '-';
    const eventType = event.event_type || event.type || '-';
    const dpsi = (event.delta_psi !== null && event.delta_psi !== undefined) ? Number(event.delta_psi).toFixed(3) : '-';
    const fdr = (event.fdr !== null && event.fdr !== undefined) ? fmtFdr(event.fdr) : '-';
    const color = (Number(event.delta_psi) || 0) > 0 ? 'var(--danger)' : 'var(--secondary)';
    const flag = event.significant ? '' : ' <span style="font-size:12px;color:var(--text-muted);">(不显著)</span>';
    return `<tr class="event-row" tabindex="0" data-event="${ingestEsc(eventId)}">
      <td class="mono">${ingestEsc(eventId)}</td>
      <td><strong>${ingestEsc(gene)}</strong>${flag}</td>
      <td>${ingestEsc(eventType)}</td>
      ${dpsiCell(event.delta_psi)}
      <td class="num">${ingestEsc(fdr)}</td>
      <td><span class="row-go" aria-hidden="true">›</span></td>
    </tr>`;
  }).join('');
}
function applyFilters() {
  loadEventPage(1);
}
function loadChart(chartType) {
  document.querySelectorAll('#page-visualization button[onclick^="loadChart"]').forEach(button => {
    button.setAttribute('aria-pressed', String(button.getAttribute('onclick').includes("'" + chartType + "'")));
  });
  document.getElementById('chart-select-mobile').value = chartType;

  const container = document.getElementById('chart-display');
  if (!state.currentProject) { 
    container.innerHTML = `
      <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 600px; color: var(--text-muted);">
        <div style="font-size: 36px; margin-bottom: 16px; opacity: 0.3;"></div>
        <div style="font-size: 16px; font-weight: 600;">未选择项目</div>
        <div style="font-size: 14px; margin-top: 8px;">请先在仪表盘选择一个分析项目</div>
      </div>`; 
    return; 
  }
  
  const meta = {
    volcano: ['火山图 Volcano Plot', '以 ΔPSI 为横轴、-log10(FDR) 为纵轴展示全部剪接事件；虚线为 FDR=0.05 与 |ΔPSI|=0.1 阈值，橙色点为显著事件。'],
    dpsi_waterfall: ['ΔPSI 瀑布图 Waterfall', '按 |ΔPSI| 排序的 Top 25 候选事件；橙色为包含水平上调，蓝色为下调，直观展示效应量谱。'],
    dpsi_ecdf: ['ΔPSI 累积分布 ECDF', 'ΔPSI 的经验累积分布曲线，并标注 |ΔPSI|>0.1 的事件占比，用于评估整体效应量分布。'],
    fdr_scree: ['显著性碎石图 Scree Plot', '候选排名对 -log10(FDR) 曲线，配合 FDR=0.05 参考线定位显著性拐点（elbow）。'],
    event_type_counts: ['事件类型分布 Composition', 'SE / MXE / A5SS / A3SS / RI 五类可变剪接事件的检出计数。'],
    event_significance: ['类型 × 显著性堆叠图', '各事件类型中通过阈值（FDR<0.05 且 |ΔPSI|>0.1）的显著事件与非显著事件构成。'],
    event_schematic: ['剪接机制示意图 Schematic', '五类可变剪接事件的外显子-内含子结构模式图（methods 级示意图）。'],
    psi_heatmap: ['PSI 热图 Heatmap', 'Top |ΔPSI| 事件的逐样本 PSI 热图，列上方标注样本分组，用于观察聚类模式。'],
    psi_distribution: ['分组 PSI 箱线图 Box Plot', '按实验组拆分的 Top 事件 PSI 分布（箱线 + 散点），用于识别离群样本。'],
    sample_composition: ['队列构成图 Cohort QC', '样本分组占比（环图）与批次分布（条形），为质控必备图表。'],
    candidate_ranking: ['候选基因排名 Ranking', 'AI 智能体综合评分（显著性+效应+生物学+文献）Top 15 候选事件。'],
    score_components: ['评分分解堆叠图 Decomposition', 'Top 候选的四维评分贡献分解：显著性 / 效应量 / 生物学 / 文献证据。'],
    enrichment: ['功能富集点图 Dot Plot', 'GO/KEGG 富集结果：横轴为富集倍数，颜色为 -log10(FDR)，点大小为重叠基因数。']
  };
  const info = meta[chartType] || ['图表', ''];
  
  container.innerHTML = `
    <div style="padding: 24px;">
      <div style="font-size: 16px; font-weight: 600; margin-bottom: 8px; color: var(--text);">${info[0]}</div>
      <div style="font-size: 13px; color: var(--text-secondary); margin-bottom: 24px; line-height: 1.6;">${info[1]}</div>
      <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 500px; background: var(--gray-100); border-radius: var(--radius);">
        <div style="width: 48px; height: 48px; border: 4px solid var(--border); border-top-color: var(--accent); border-radius: 50%; animation: spin 1s linear infinite;"></div>
        <div style="margin-top: 20px; font-size: 14px; color: var(--text-secondary);">正在渲染图表（首次生成约需数秒）...</div>
      </div>
    </div>
  `;
  
  const img = document.createElement('img');
  img.src = '/api/figure/' + state.currentProject + '/' + chartType;
  img.style.width = '100%';
  img.style.borderRadius = 'var(--radius)';
  img.style.marginTop = '20px';
  img.style.boxShadow = 'var(--shadow)';
  
  img.onload = function() {
    container.innerHTML = `
      <div style="padding: 24px;">
        <div style="font-size: 16px; font-weight: 600; margin-bottom: 8px; color: var(--text);">${info[0]}</div>
        <div style="font-size: 13px; color: var(--text-secondary); margin-bottom: 24px; line-height: 1.6;">${info[1]}</div>
      </div>
    `;
    container.appendChild(img);
  };
  
  img.onerror = function() { 
    container.innerHTML = `
      <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 600px; color: var(--text-muted);">
        <div style="font-size: 36px; margin-bottom: 16px; opacity: 0.3;"></div>
        <div style="font-size: 16px; font-weight: 600; margin-bottom: 8px;">图表不可用</div>
        <div style="font-size: 14px;">该项目可能尚未生成此图表，请完成分析后重试</div>
      </div>
    `; 
  };
}
async function exploreGene() {
  const geneSymbol = document.getElementById('gene-search').value.trim();
  if (!geneSymbol) {
    AppNotify.toast('请输入基因符号', 'warning');
    return;
  }
  
  const container = document.getElementById('gene-details');
  if (!state.currentProject) {
    container.innerHTML = `
      <div class="card">
        <div style="padding: 40px; text-align: center; color: var(--text-muted);">
          <div style="font-size: 36px; margin-bottom: 12px; opacity: 0.3;"></div>
          <div style="font-size: 16px; font-weight: 600; margin-bottom: 8px;">请先选择项目</div>
          <div style="font-size: 14px;">在仪表盘选择一个分析项目后再探索基因</div>
        </div>
      </div>`;
    return;
  }
  
  // Show loading state
  container.innerHTML = `
    <div class="card">
      <div style="padding: 60px; text-align: center;">
        <div style="width: 48px; height: 48px; border: 4px solid var(--border); border-top-color: var(--accent); border-radius: 50%; animation: spin 1s linear infinite; margin: 0 auto 20px;"></div>
        <div style="font-size: 16px; font-weight: 600;">正在加载 ${geneSymbol} 的信息...</div>
      </div>
    </div>`;
  
  const status = await apiCall(`/status/${state.currentProject}`);
  const candidates = (status && status.candidates) || [];
  const geneEvents = candidates.filter(e => (e.gene_symbol || '').toLowerCase() === geneSymbol.toLowerCase());
  
  if (geneEvents.length === 0) {
    container.innerHTML = `
      <div class="card">
        <div style="padding: 60px; text-align: center; color: var(--text-muted);">
          <div style="font-size: 36px; margin-bottom: 16px; opacity: 0.3;"></div>
          <div style="font-size: 16px; font-weight: 600; margin-bottom: 8px;">未找到 ${geneSymbol} 的剪接事件</div>
          <div style="font-size: 14px;">该基因可能不在当前分析的候选列表中，或未达到显著性阈值</div>
          <button class="btn btn-secondary" style="margin-top: 20px;" onclick="navigateTo('explorer')">浏览所有事件</button>
        </div>
      </div>`;
    return;
  }
  
  // Sort events by significance
  geneEvents.sort((a, b) => (a.fdr || 1) - (b.fdr || 1));
  
  // Calculate summary statistics
  const significantEvents = geneEvents.filter(e => e.fdr < 0.05);
  const avgDeltaPSI = geneEvents.reduce((sum, e) => sum + Math.abs(parseFloat(e.delta_psi || 0)), 0) / geneEvents.length;
  const eventTypeCounts = {};
  geneEvents.forEach(e => {
    const type = e.event_type || 'Unknown';
    eventTypeCounts[type] = (eventTypeCounts[type] || 0) + 1;
  });
  
  // Build event types summary
  const eventTypeSummary = Object.entries(eventTypeCounts).map(([type, count]) => `${type}: ${count}`).join(', ');
  
  let eventsHtml = `
    <table style="width: 100%; font-size: 13px; border-collapse: collapse;">
      <thead>
        <tr style="border-bottom: 2px solid var(--border);">
          <th style="text-align: left; padding: 12px 16px; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.8px; color: var(--text-secondary);">事件 ID</th>
          <th style="text-align: left; padding: 12px 16px; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.8px; color: var(--text-secondary);">类型</th>
          <th style="text-align: left; padding: 12px 16px; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.8px; color: var(--text-secondary);">Delta PSI</th>
          <th style="text-align: left; padding: 12px 16px; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.8px; color: var(--text-secondary);">FDR</th>
          <th style="text-align: left; padding: 12px 16px; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.8px; color: var(--text-secondary);">评分</th>
          <th style="text-align: left; padding: 12px 16px; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.8px; color: var(--text-secondary);">操作</th>
        </tr>
      </thead>
      <tbody>
        ${geneEvents.map(e => {
          const dpsi = Number(e.delta_psi).toFixed(3);
          const fdr = fmtFdr(e.fdr);
          const score = e.score !== undefined ? Number(e.score).toFixed(3) : '-';
          const sigLevel = e.fdr < 0.001 ? '***' : e.fdr < 0.01 ? '**' : e.fdr < 0.05 ? '*' : '';
          const sigColor = e.fdr < 0.001 ? '#dc2626' : e.fdr < 0.01 ? '#f59e0b' : e.fdr < 0.05 ? '#059669' : '#94a3b8';
          
          return `<tr style="border-bottom: 1px solid var(--border);">
            <td style="padding: 12px 16px; font-family: monospace;">${e.event_id || '-'}</td>
            <td style="padding: 12px 16px;"><span style="background: var(--bg); padding: 4px 10px; border-radius: var(--radius); font-size: 12px; font-weight: 600;">${e.event_type || '-'}</span></td>
            <td style="padding: 12px 16px; font-family: monospace; font-weight: 600;">${dpsi}</td>
            <td style="padding: 12px 16px; font-family: monospace; font-weight: 600; color: ${sigColor};">${ingestEsc(fdr)} ${sigLevel}</td>
            <td style="padding: 12px 16px; font-family: monospace;">${score}</td>
            <td style="padding: 12px 16px;"><button class="btn btn-sm btn-secondary" onclick="viewEventDetails('${e.event_id || e.id}')">详情</button></td>
          </tr>`;
        }).join('')}
      </tbody>
    </table>
  `;
  
  // Process evidence
  let evidence = geneEvents.length > 0 ? (geneEvents[0].evidence_json || '') : '';
  if (evidence) {
    try {
      const parsed = typeof evidence === 'string' ? JSON.parse(evidence) : evidence;
      if (Array.isArray(parsed)) { 
        evidence = parsed.map(item => `<div style="margin-bottom: 10px; padding-left: 16px; border-left: 1px solid var(--accent);">• ${typeof item === 'string' ? item : JSON.stringify(item)}</div>`).join(''); 
      } else if (typeof parsed === 'object') { 
        evidence = Object.entries(parsed).map(([k, v]) => `<div style="margin-bottom: 10px;"><strong>${k}:</strong> ${v}</div>`).join(''); 
      }
    } catch (e) { 
      evidence = `<div>${evidence}</div>`; 
    }
  }
  
  container.innerHTML = `
    <div class="card" style="margin-bottom: 24px;">
      <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 24px;">
        <div>
          <div style="font-size: 28px; font-weight: 600; background: var(--black); ">${geneSymbol}</div>
          <div style="font-size: 13px; color: var(--text-secondary); margin-top: 4px;">基因剪接分析报告</div>
        </div>
        <button class="btn btn-secondary" onclick="navigateTo('explorer')">返回事件列表</button>
      </div>
      
      <div class="grid grid-3" style="margin-bottom: 28px;">
        <div style="background: var(--gray-100); padding: 20px; border-radius: var(--radius); text-align: center;">
          <div style="font-size: 12px; text-transform: uppercase; letter-spacing: 1px; color: #0e7490; font-weight: 600; margin-bottom: 8px;">总事件数</div>
          <div style="font-size: 28px; font-weight: 600; color: #0e7490;">${geneEvents.length}</div>
        </div>
        <div style="background: var(--gray-100); padding: 20px; border-radius: var(--radius); text-align: center;">
          <div style="font-size: 12px; text-transform: uppercase; letter-spacing: 1px; color: #065f46; font-weight: 600; margin-bottom: 8px;">显著事件</div>
          <div style="font-size: 28px; font-weight: 600; color: #065f46;">${significantEvents.length}</div>
        </div>
        <div style="background: var(--gray-100); padding: 20px; border-radius: var(--radius); text-align: center;">
          <div style="font-size: 12px; text-transform: uppercase; letter-spacing: 1px; color: #7c3aed; font-weight: 600; margin-bottom: 8px;">平均 |ΔPSI|</div>
          <div style="font-size: 28px; font-weight: 600; color: #7c3aed;">${avgDeltaPSI.toFixed(3)}</div>
        </div>
      </div>
      
      <div style="margin-bottom: 24px; padding: 16px; background: var(--bg); border-radius: var(--radius);">
        <div style="font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 8px;">事件类型分布</div>
        <div style="font-size: 14px; line-height: 1.6;">${eventTypeSummary}</div>
      </div>
      
      <div style="margin-bottom: 24px;">
        <div style="font-size: 14px; font-weight: 600; margin-bottom: 16px; color: var(--text);">剪接事件详情</div>
        ${eventsHtml}
      </div>
      
      ${evidence ? `
      <div>
        <div style="font-size: 14px; font-weight: 600; margin-bottom: 16px; color: var(--text);">文献证据</div>
        <div style="padding: 20px; background: var(--bg); border-radius: var(--radius); font-size: 14px; line-height: 1.8;">
          ${evidence}
        </div>
      </div>
      ` : ''}
    </div>
  `;
}
async function generateReport(format) {
  if (!state.currentProject) { 
    AppNotify.toast('请先选择一个项目', 'warning'); 
    return; 
  }
  
  const output = document.getElementById('report-output');
  output.innerHTML = `
    <div style="padding: 40px; text-align: center;">
      <div style="width: 48px; height: 48px; border: 4px solid var(--border); border-top-color: var(--accent); border-radius: 50%; animation: spin 1s linear infinite; margin: 0 auto 20px;"></div>
      <div style="font-size: 16px; font-weight: 600; margin-bottom: 8px;">正在生成报告...</div>
      <div style="font-size: 13px; color: var(--text-secondary);">这可能需要几分钟时间，请耐心等待</div>
    </div>
  `;
  
  try {
    const reportUrl = `/api/report/${state.currentProject}?format=${format}`;
    const response = await fetch(reportUrl, { method: 'GET' });
    
    if (!response.ok) {
      throw new Error(`报告生成失败 (${response.status})`);
    }
    
    // Get blob and create download link
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${state.currentProject}_report.${format === 'html' ? 'html' : 'pdf'}`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
    
    output.innerHTML = `
      <div style="padding: 24px; background: var(--gray-100); border-radius: var(--radius); border-left: 1px solid var(--gray-900);">
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
          <div style="font-size: 20px;"></div>
          <div>
            <div style="font-size: 16px; font-weight: 600; color: var(--secondary);">报告生成成功！</div>
            <div style="font-size: 13px; color: var(--text-secondary);">文件已自动下载</div>
          </div>
        </div>
        <div style="margin-top: 16px; padding-top: 16px; border-top: 1px solid rgba(5, 150, 105, 0.2);">
          <button class="btn btn-sm btn-primary" onclick="window.open('${reportUrl}', '_blank')">在新窗口中查看</button>
        </div>
      </div>
    `;
  } catch (error) { 
    console.error('Report generation error:', error);
    output.innerHTML = `
      <div style="padding: 24px; background: var(--gray-100); border-radius: var(--radius); border-left: 1px solid var(--gray-900);">
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
          <div style="font-size: 20px;"></div>
          <div>
            <div style="font-size: 16px; font-weight: 600; color: var(--error);">报告生成失败</div>
            <div style="font-size: 13px; color: var(--text-secondary);">${error.message}</div>
          </div>
        </div>
        <div style="margin-top: 16px; padding-top: 16px; border-top: 1px solid rgba(220, 38, 38, 0.2);">
          <button class="btn btn-sm btn-secondary" onclick="generateReport('${format}')">重试</button>
        </div>
      </div>
    `; 
  }
}
function selectProject(projectId) { state.currentProject = projectId; localStorage.setItem('epitoperank.currentProject', projectId); loadDashboard(); if (state.currentPage === 'neoantigen') { restoreNeoWorkflow(); checkNeoReadiness(); } }
function refreshData() { if (state.currentPage === 'dashboard') loadDashboard(); if (state.currentPage === 'pipeline') loadPipeline(); if (state.currentPage === 'explorer') loadExplorer(); }

document.addEventListener('keydown', event => {
  const modal = document.getElementById('upload-modal');
  if (event.key === 'Escape') { toggleNavigation(false); if (modal.style.display === 'flex') closeUploadModal(); }
  if (event.key !== 'Tab' || modal.style.display !== 'flex') return;
  const controls = Array.from(modal.querySelectorAll('button,input,select,textarea,[tabindex="0"]')).filter(el => !el.disabled && el.getClientRects().length);
  const first = controls[0], last = controls[controls.length - 1];
  if (event.shiftKey && document.activeElement === first) { last.focus(); event.preventDefault(); }
  if (!event.shiftKey && document.activeElement === last) { first.focus(); event.preventDefault(); }
});
// Upload Modal Functions
let selectedFiles = [];
let uploadReturnFocus = null;

function showUploadModal() {
  uploadReturnFocus = document.activeElement;
  document.body.style.overflow = 'hidden';
  document.getElementById('upload-modal').style.display = 'flex';
  selectedFiles = [];
  updateFileList();
  document.getElementById('project-name').focus();
}

function closeUploadModal() {
  document.body.style.overflow = '';
  if (uploadReturnFocus) uploadReturnFocus.focus();
  document.getElementById('upload-modal').style.display = 'none';
  document.getElementById('project-name').value = '';
  document.getElementById('analysis-query').value = '';
  selectedFiles = [];
  updateFileList();
}

function handleDragOver(event) {
  event.preventDefault();
  event.stopPropagation();
  const dropZone = document.getElementById('drop-zone');
  dropZone.style.borderColor = 'var(--accent)';
  dropZone.style.background = '#eff6ff';
}

function handleDragLeave(event) {
  event.preventDefault();
  event.stopPropagation();
  const dropZone = document.getElementById('drop-zone');
  dropZone.style.borderColor = 'var(--border)';
  dropZone.style.background = '';
}

function handleDrop(event) {
  event.preventDefault();
  event.stopPropagation();
  const dropZone = document.getElementById('drop-zone');
  dropZone.style.borderColor = 'var(--border)';
  dropZone.style.background = '';
  
  const files = Array.from(event.dataTransfer.files);
  handleFiles(files);
}

function handleFileSelect(event) {
  console.log('handleFileSelect called');
  console.log('event.target:', event.target);
  console.log('event.target.files:', event.target.files);
  
  const files = Array.from(event.target.files);
  console.log('Converted files array:', files.length, files);
  
  handleFiles(files);
}

function handleReportDirectory(event) {
  const files = Array.from(event.target.files).filter(file => /.+[.](SE|MXE|A3SS|A5SS|RI)[.]xls$/i.test(file.name));
  if (!files.length) {
    AppNotify.toast('目录中没有找到华大逐样本剪接表（如 OC_001.SE.xls）', 'error');
    return;
  }
  handleFiles(files);
}

function handleFiles(files) {
  console.log('handleFiles called with', files.length, 'files');
  selectedFiles = [...selectedFiles, ...files];
  console.log('selectedFiles now:', selectedFiles.length, selectedFiles.map(f => f.name));
  updateFileList();
}

function updateFileList() {
  const fileListDiv = document.getElementById('file-list');
  const startBtn = document.getElementById('start-analysis-btn');
  
  if (selectedFiles.length === 0) {
    fileListDiv.innerHTML = '';
    startBtn.disabled = true;
  } else {
    fileListDiv.innerHTML = (selectedFiles.length > 30 ? '<div style="margin-bottom:8px">已选择 ' + selectedFiles.length + ' 个文件（仅显示前 30 个）</div>' : '') + selectedFiles.slice(0, 30).map((file, index) => 
      `<div style="padding: 8px; background: var(--bg); border-radius: var(--radius); margin-bottom: 4px; display: flex; justify-content: space-between; align-items: center;">
        <span style="font-size: 13px;">${file.name}</span>
        <button onclick="removeFile(${index})" style="background: none; border: none; cursor: pointer; color: var(--error); font-size: 16px;">×</button>
      </div>`
    ).join('');
    startBtn.disabled = false;
  }
}

function removeFile(index) {
  selectedFiles.splice(index, 1);
  updateFileList();
}

async function startAnalysis() {
  const projectName = document.getElementById('project-name').value.trim();
  const analysisQuery = document.getElementById('analysis-query').value.trim() ||
    (selectedFiles.some(file => /.+[.](SE|MXE|A3SS|A5SS|RI)[.]xls$/i.test(file.name)) ? 'Explore per-sample PSI' : '');
  
  if (!projectName) {
    AppNotify.toast('请输入项目名称', 'warning');
    return;
  }
  
  if (!analysisQuery) {
    AppNotify.toast('请输入分析查询', 'warning');
    return;
  }
  
  if (selectedFiles.length === 0) {
    AppNotify.toast('请至少选择一个文件', 'warning');
    return;
  }
  
  // Save files reference BEFORE closing modal (closeUploadModal clears selectedFiles)
  const filesToUpload = [...selectedFiles];
  
  // Close modal and show loading
  closeUploadModal();
  const statusDiv = document.getElementById('stat-status');
  statusDiv.innerHTML = '<span class="status status-running"><span class="status-dot"></span>上传中...</span>';
  
  try {
    // Step 1: Upload files
    const formData = new FormData();
    
    console.log('Uploading files count:', filesToUpload.length);
    console.log('Files to upload:', filesToUpload.map(f => f.name));
    
    filesToUpload.forEach((file, index) => {
      console.log(`Adding file ${index}:`, file.name, file.type, file.size);
      formData.append('files', file, file.name);
    });
    
    // Verify FormData contents
    for (let [key, value] of formData.entries()) {
      console.log('FormData entry:', key, value.name, value.size);
    }
    
    const uploadResponse = await fetch('/api/upload', {
      method: 'POST',
      body: formData
      // Don't set Content-Type header - browser will set it with boundary
    });
    
    console.log('Upload response status:', uploadResponse.status);
    
    if (!uploadResponse.ok) {
      const errorText = await uploadResponse.text();
      console.error('Upload error response:', errorText);
      throw new Error(`上传失败 (${uploadResponse.status}): ${errorText}`);
    }
    
    const uploadResult = await uploadResponse.json();
    const uploadDir = uploadResult.upload_dir;
    
    console.log('Files uploaded to:', uploadDir);
    
    // Step 2: let the ingestion agent read the table structure before analysis.
    statusDiv.innerHTML = '<span class="status status-running"><span class="status-dot"></span>智能体正在理解数据结构...</span>';
    let preview = null;
    try {
      const previewResponse = await fetch('/api/ingest/preview', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ input_dir: uploadDir, use_llm: true })
      });
      if (previewResponse.ok) {
        preview = await previewResponse.json();
      } else {
        console.warn('ingest preview rejected:', previewResponse.status, await previewResponse.text());
      }
    } catch (previewError) {
      console.warn('ingest preview unavailable:', previewError);
    }

    if (preview && preview.native && (!preview.validation || preview.validation.ok) && !(preview.sample_ids || []).length) {
      statusDiv.innerHTML = '<span class="status status-running"><span class="status-dot"></span>已识别标准格式，开始分析...</span>';
      runAnalysisOnDir(analysisQuery, uploadDir, projectName, statusDiv);
      return;
    }
    if (preview) {
      statusDiv.dataset.ingestPending = '1';
      statusDiv.innerHTML = '<span class="status status-waiting"><span class="status-dot"></span>等待确认数据映射...</span>';
      showIngestModal(preview, { uploadDir: uploadDir, projectName: projectName, analysisQuery: analysisQuery, statusDiv: statusDiv });
      return;
    }
    runAnalysisOnDir(analysisQuery, uploadDir, projectName, statusDiv);

  } catch (error) {
    console.error('Analysis error:', error);
    statusDiv.innerHTML = '<span class="status status-waiting"><span class="status-dot"></span>空闲</span>';
    AppNotify.dialog({
      kind: 'error',
      title: '上传没有完成',
      message: '文件或数据目录在上传阶段中断，分析尚未启动。',
      detail: String(error && error.message ? error.message : error),
      bullets: ['确认文件格式为 CSV、TSV、TXT 或表格型 XLS', '单个文件不要过大，必要时先拆分', '检查网络与本地服务是否可用']
    });
  }
}

function runAnalysisOnDir(analysisQuery, inputDir, projectName, statusDiv) {
  const prevLatest = (state.projects && state.projects[0] && state.projects[0].project_id) || null;
  statusDiv.innerHTML = '<span class="status status-running"><span class="status-dot"></span>分析中（预计 3-6 分钟）...</span>';
  navigateTo('pipeline');

  const pollTimer = setInterval(async () => {
    try {
      const resp = await apiCall('/projects');
      const list = (resp && resp.projects) || [];
      if (list.length > 0 && list[0].project_id !== prevLatest && state.currentProject !== list[0].project_id) {
        state.currentProject = list[0].project_id;
        localStorage.setItem('epitoperank.currentProject', state.currentProject);
        document.getElementById('current-project').textContent = state.currentProject;
      }
      if (state.currentProject) loadPipeline();
    } catch (pollError) { console.warn('poll error:', pollError); }
  }, 4000);

  fetch('/api/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query: analysisQuery, input_dir: inputDir, project_name: projectName })
  }).then(async analyzeResponse => {
    clearInterval(pollTimer);
    if (!analyzeResponse.ok) {
      const errorText = await analyzeResponse.text();
      statusDiv.innerHTML = '<span class="status status-waiting"><span class="status-dot"></span>空闲</span>';
      AppNotify.dialog({
        kind: 'error',
        title: '分析未能完成',
        message: '服务返回了错误，本次分析已中止。修正输入后可以重新发起。',
        detail: 'HTTP ' + analyzeResponse.status + '\\n' + String(errorText || '').slice(0, 800)
      });
      return;
    }
    const analyzeResult = await analyzeResponse.json();
    if (analyzeResult && analyzeResult.project_id) {
      state.currentProject = analyzeResult.project_id;
      localStorage.setItem('epitoperank.currentProject', state.currentProject);
      document.getElementById('current-project').textContent = state.currentProject;
    }
    statusDiv.innerHTML = '<span class="status status-completed"><span class="status-dot"></span>已完成</span>';
    loadPipeline();
    loadDashboard();
    AppNotify.dialog({
      kind: 'success',
      title: '分析完成',
      subtitle: '结果已写入当前项目',
      message: '事件表已解析，显著性筛选与候选排序都已完成。接下来可以逐条查看事件，或直接生成研究报告。',
      actions: [
        { label: '生成研究报告', value: 'report', onClick: function () { navigateTo('report'); } },
        { label: '查看可视化', value: 'visualization', onClick: function () { navigateTo('visualization'); } },
        { label: '浏览事件', variant: 'primary', value: 'explorer', onClick: function () { navigateTo('explorer'); } }
      ]
    });
  }).catch(fetchError => {
    clearInterval(pollTimer);
    console.error('Analysis request error:', fetchError);
    statusDiv.innerHTML = '<span class="status status-waiting"><span class="status-dot"></span>空闲</span>';
    AppNotify.dialog({
      kind: 'warning',
      title: '连接已中断',
      message: '前端没能拿到分析响应，但后台任务可能仍在运行。稍后点击右上角「刷新」即可看到最新进度。',
      detail: String(fetchError && fetchError.message ? fetchError.message : fetchError)
    });
  });
}

// ---------------------------------------------------------------------------
// Smart ingestion review
// ---------------------------------------------------------------------------
let ingestState = null;

const INGEST_STEP_LABELS = {
  profile: ['文件画像', 'Profiling'],
  heuristic: ['规则映射', 'Rule mapping'],
  llm: ['模型映射', 'LLM mapping'],
  validate: ['标准化', 'Standardization'],
  preview: ['置信度', 'Confidence']
};

function ingestT(zh, en) { return cfgText(zh, en); }

function ingestEsc(value) {
  return String(value === null || value === undefined ? '' : value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function ingestLevel(level) {
  if (level === 'high') return ingestT('高', 'high');
  if (level === 'medium') return ingestT('中', 'medium');
  return ingestT('低', 'low');
}

function ingestDelimiter(value) {
  if (value === String.fromCharCode(9)) return 'TAB';
  if (value === ',') return 'CSV';
  return value || '—';
}

function ingestFixed(value, digits) {
  const num = Number(value);
  if (value === null || value === undefined || value === '' || !isFinite(num)) return '—';
  return num.toFixed(digits);
}

function ingestSci(value) {
  const num = Number(value);
  if (value === null || value === undefined || value === '' || !isFinite(num)) return '—';
  if (num === 0) return '0';
  return fmtSci(num, 2);
}

function ingestTraceSteps(trace) {
  const order = [];
  const byName = {};
  (trace || []).forEach(function (step) {
    if (!step || !step.step) return;
    if (!byName[step.step]) order.push(step.step);
    byName[step.step] = step;
  });
  return order.map(function (name) { return byName[name]; });
}

function showIngestModal(data, context) {
  ingestState = {
    data: data,
    context: context,
    mapping: JSON.parse(JSON.stringify(data.mapping || {})),
    applying: false,
    groupLabels: []
  };
  if (!ingestState.mapping.columns) ingestState.mapping.columns = {};
  if (!ingestState.mapping.sample_groups) ingestState.mapping.sample_groups = {};
  const suggested = [...new Set(Object.values(ingestState.mapping.sample_groups).filter(Boolean))];
  ingestState.groupLabels = [suggested[0] || 'Control', suggested[1] || 'Treatment'];
  const modal = document.getElementById('ingest-modal');
  if (modal) modal.classList.add('open');
  document.body.style.overflow = 'hidden';
  renderIngestModal();
  const confirmBtn = document.getElementById('ingest-confirm');
  if (confirmBtn && !confirmBtn.disabled) confirmBtn.focus();
}

function closeIngestModal() {
  if (ingestState && ingestState.applying) return;
  const statusDiv = ingestState && ingestState.context ? ingestState.context.statusDiv : null;
  const modal = document.getElementById('ingest-modal');
  if (modal) modal.classList.remove('open');
  document.body.style.overflow = '';
  if (statusDiv && statusDiv.dataset.ingestPending === '1') {
    delete statusDiv.dataset.ingestPending;
    statusDiv.innerHTML = '<span class="status status-waiting"><span class="status-dot"></span>空闲</span>';
  }
  ingestState = null;
}

function renderIngestModal() {
  if (!ingestState) return;
  const data = ingestState.data || {};
  const preview = data.preview || {};
  const issues = data.issues || [];
  const native = !!data.native;
  const bgi = data.status === 'bgi_single_sample';
  const unmappable = data.status === 'unmappable';
  const expressionOnly = data.detected_format === 'expression_quantification' || data.detected_format === 'transcript_quantification';

  const title = document.getElementById('ingest-title');
  const sub = document.getElementById('ingest-sub');
  const body = document.getElementById('ingest-body');
  const confirmBtn = document.getElementById('ingest-confirm');
  const cancelBtn = document.getElementById('ingest-cancel');
  const errorDiv = document.getElementById('ingest-error');
  if (!body || !confirmBtn) return;

  let subText = ingestT('Agent 已读取数据结构。确认字段映射后，将标准化并进入原有分析流程。', 'The agent has read the data structure. Confirm the field mapping to standardize and continue to analysis.');
  if (native) subText = ingestT('请核对每个样本的分组，确认后开始分析。', 'Review each sample group before analysis.');
  if (bgi) subText = ingestT('已识别华大逐样本剪接表。确认真实分组后可生成探索性 PSI 表；原报告没有组间显著性检验。', 'BGI per-sample PSI tables found. Confirm biological groups to create an exploratory table; the report has no differential significance test.');
  if (unmappable) subText = ingestT('未能从这些文件中识别出可分析的剪接事件表。', 'No analyzable splicing event table could be recognized in these files.');
  if (expressionOnly) subText = ingestT('文件已读取并识别为表达量矩阵。请另选剪接事件结果表进行剪接分析。', 'File read as an expression matrix. Select splicing event results for splicing analysis.');
  if (title) title.textContent = ingestT('智能接入检查', 'Smart ingestion review');
  if (sub) sub.textContent = subText;
  if (errorDiv) errorDiv.textContent = '';

  const html = [];
  const steps = ingestTraceSteps(data.agent_trace);
  if (steps.length) {
    html.push('<div class="ingest-trace">' + steps.map(function (step) {
      const labels = INGEST_STEP_LABELS[step.step] || [step.step, step.step];
      const detail = ingestT(step.detail || '', step.detail_en || step.detail || '');
      return '<span class="ingest-step ' + ingestEsc(step.status || 'ok') + '" title="' + ingestEsc(detail) + '"><span class="dot"></span>' + ingestEsc(ingestT(labels[0], labels[1])) + '</span>';
    }).join('') + '</div>');
  }

  const sourceBits = [];
  if (native) {
    sourceBits.push(ingestT('原生格式：', 'Native format: ') + ingestEsc(data.native_format || 'standard'));
  } else {
    sourceBits.push(ingestT('映射来源：', 'Mapping source: ') + (data.mapping_source === 'llm+heuristic' ? ingestT('大模型 + 规则', 'LLM + rules') : ingestT('确定性规则', 'Deterministic rules')));
    const confidence = data.confidence || {};
    sourceBits.push(ingestT('置信度：', 'Confidence: ') + ingestLevel(confidence.level) + ' · ' + Math.round(Number(confidence.score || 0) * 100) + '%');
  }
  if (data.elapsed_ms !== undefined && data.elapsed_ms !== null) sourceBits.push(ingestT('用时 ', 'took ') + Number(data.elapsed_ms) + ' ms');
  html.push('<div class="ingest-source">' + sourceBits.join(' · ') + '</div>');

  const validEvents = preview.valid_events !== undefined ? preview.valid_events : ((data.summary && data.summary.event_count) || 0);
  const sampleCount = preview.sample_count !== undefined ? preview.sample_count : ((data.summary && data.summary.sample_count) || 0);
  const fdrCoverage = preview.fdr_coverage !== undefined ? preview.fdr_coverage : 0;
  const deltaCoverage = preview.delta_coverage !== undefined ? preview.delta_coverage : 0;
  html.push('<div class="ingest-stats">' +
    '<div class="ingest-stat"><div class="v">' + ingestEsc(validEvents) + '</div><div class="k">' + ingestEsc(ingestT('有效事件', 'Valid events')) + '</div></div>' +
    '<div class="ingest-stat"><div class="v">' + ingestEsc(sampleCount) + '</div><div class="k">' + ingestEsc(ingestT('样本', 'Samples')) + '</div></div>' +
    '<div class="ingest-stat"><div class="v">' + Math.round(Number(fdrCoverage) * 100) + '%</div><div class="k">' + ingestEsc(ingestT('FDR 覆盖', 'FDR coverage')) + '</div></div>' +
    '<div class="ingest-stat"><div class="v">' + Math.round(Number(deltaCoverage) * 100) + '%</div><div class="k">' + ingestEsc(ingestT('ΔPSI 覆盖', 'ΔPSI coverage')) + '</div></div>' +
    '</div>');

  if (!native && data.event_file) {
    const eventFile = data.event_file;
    const metaFile = data.metadata_file;
    const rows = Number(eventFile.row_count || 0);
    const line = ingestT('事件表', 'Event table') + ' <code>' + ingestEsc(eventFile.name) + '</code> · ' + ingestDelimiter(eventFile.delimiter) + ' · ' + ingestT('表头第 ', 'header row ') + (Number(eventFile.header_row || 0) + 1) + ' · ' + rows + ingestT(' 行', ' rows');
    const metaLine = ingestT('样本表', 'Sample table') + ' <code>' + ingestEsc(metaFile ? metaFile.name : '—') + '</code>' + (metaFile ? '' : ' ' + ingestT('（未提供，已根据样本名推断分组）', '(not provided; groups inferred from sample names)'));
    const typeCounts = preview.event_types || {};
    const typeText = Object.keys(typeCounts).map(function (key) { return key + ' ' + typeCounts[key]; }).join(' · ');
    html.push('<div class="ingest-files"><div>' + line + '</div><div>' + metaLine + '</div>' + (typeText ? '<div>' + ingestEsc(ingestT('事件类型：', 'Event types: ') + typeText) + '</div>' : '') + '</div>');
  }

  if (unmappable && Array.isArray(data.files) && data.files.length) {
    const fileLines = data.files.map(function (file) {
      const suffix = file.supported ? ingestT('可解析', 'parseable') : ingestT('不可解析', 'not parseable');
      return '<div><code>' + ingestEsc(file.name) + '</code> · ' + suffix + (file.error ? ' · ' + ingestEsc(file.error) : '') + '</div>';
    });
    html.push('<div class="ingest-files">' + fileLines.join('') + '</div>');
  }

  if (!native && Array.isArray(data.mapping_fields) && data.mapping_fields.length && data.event_file) {
    const headers = data.event_file.headers || [];
    const columns = (data.mapping && data.mapping.columns) || {};
    const rows = data.mapping_fields.map(function (field) {
      const current = columns[field.field] || '';
      const label = ingestT(field.label_zh || field.field, field.label_en || field.field) + (field.required ? ' *' : '');
      let options = '<option value="">' + ingestEsc(ingestT('— 未映射 —', '— unmapped —')) + '</option>';
      let found = false;
      headers.forEach(function (header) {
        if (header === current) found = true;
        options += '<option value="' + ingestEsc(header) + '"' + (header === current ? ' selected' : '') + '>' + ingestEsc(header) + '</option>';
      });
      if (current && !found) options += '<option value="' + ingestEsc(current) + '" selected>' + ingestEsc(current) + '</option>';
      const missing = field.required && !current ? ' missing' : '';
      return '<div class="ingest-map-row"><label>' + ingestEsc(label) + '</label><select data-field="' + ingestEsc(field.field) + '"' + (field.required ? ' data-required="1"' : '') + ' onchange="ingestSelectChanged(this)"' + (missing ? ' class="missing"' : '') + '>' + options + '</select></div>';
    });
    html.push('<div><div class="ingest-section-title">' + ingestEsc(ingestT('字段映射', 'Field mapping')) + '</div><div class="ingest-map-grid">' + rows.join('') + '</div></div>');
  }

  const sampleIds = data.sample_ids || [];
  if (sampleIds.length) {
    const labels = ingestState.groupLabels;
    const assignments = ingestState.mapping.sample_groups;
    const assignedCount = sampleIds.filter(id => !!assignments[id]).length;
    const source = data.group_suggestion_source;
    const sourceText = source === 'previous_metadata'
      ? ingestT('已从相同事件文件的历史样本表恢复分组建议。', 'Group suggestions were restored from a previous sample sheet for the identical event file.')
      : source === 'metadata'
        ? ingestT('已读取上传的样本表。', 'Groups were read from the uploaded sample sheet.')
        : source === 'llm' || data.mapping_source === 'llm+heuristic'
          ? ingestT('大模型已提出分组建议，请核对。', 'The model suggested sample groups; please review them.')
          : ingestT('尚无可靠的完整分组建议，可修改分组名称并批量分配。', 'No complete reliable grouping was found; you can edit group names and assign samples in batches.');
    html.push('<div><div class="ingest-section-title">' + ingestEsc(ingestT('样本分组确认', 'Confirm sample groups')) + '</div>' +
      '<div style="margin:8px 0;color:var(--text-secondary)">' + ingestEsc(sourceText) + ' ' + assignedCount + '/' + sampleIds.length + '</div>' +
      '<div style="display:flex;gap:8px;margin:8px 0"><input data-group-label="0" value="' + ingestEsc(labels[0]) + '" oninput="ingestGroupLabelChanged(this)" aria-label="Group 1" placeholder="Group 1" style="width:48%;padding:8px"><input data-group-label="1" value="' + ingestEsc(labels[1]) + '" oninput="ingestGroupLabelChanged(this)" aria-label="Group 2" placeholder="Group 2" style="width:48%;padding:8px"></div>' +
      '<div style="display:flex;gap:8px;margin:8px 0"><button type="button" class="btn btn-sm btn-secondary" onclick="ingestAssignUnassigned(0)">' + ingestEsc(ingestT('未分配项 → 第一组', 'Unassigned → group 1')) + '</button><button type="button" class="btn btn-sm btn-secondary" onclick="ingestAssignUnassigned(1)">' + ingestEsc(ingestT('未分配项 → 第二组', 'Unassigned → group 2')) + '</button></div>' +
      '<details' + (assignedCount < sampleIds.length ? ' open' : '') + '><summary style="cursor:pointer;margin:8px 0">' + ingestEsc(ingestT('查看或调整逐样本分组', 'Review or edit individual samples')) + '</summary><div class="ingest-map-grid">' + sampleIds.map(function (sampleId) {
        const current = assignments[sampleId] || '';
        return '<div class="ingest-map-row"><label>' + ingestEsc(sampleId) + '</label><select data-sample-id="' + ingestEsc(sampleId) + '" onchange="ingestGroupChanged(this)"><option value="">' + ingestEsc(ingestT('— 请选择 —', '— Select —')) + '</option><option value="0"' + (current === labels[0] ? ' selected' : '') + '>' + ingestEsc(labels[0]) + '</option><option value="1"' + (current === labels[1] ? ' selected' : '') + '>' + ingestEsc(labels[1]) + '</option></select></div>';
      }).join('') + '</div></details></div>');
  } else {
    html.push('<div class="ingest-issue warning">' + ingestEsc(expressionOnly
      ? ingestT('FPKM、TPM 和 read_count 是表达量，不是剪接事件 PSI；请上传 SE/MXE/A3SS/A5SS/RI 事件表。', 'FPKM, TPM and read counts are expression values, not event PSI. Upload SE/MXE/A3SS/A5SS/RI event tables.')
      : ingestT('没有每样本 PSI 数据，无法生成真实的样本箱线图或热图。', 'No per-sample PSI data: sample box plots and heatmaps cannot be generated.')) + '</div>');
  }

  if (issues.length) {
    const items = issues.map(function (issue) {
      const severity = issue.severity === 'error' ? 'error' : (issue.severity === 'warning' ? 'warning' : 'info');
      const tag = severity === 'error' ? ingestT('错误', 'ERROR') : (severity === 'warning' ? ingestT('提示', 'WARN') : ingestT('信息', 'INFO'));
      const message = ingestT(issue.message || '', issue.message_en || issue.message || '');
      return '<div class="ingest-issue ' + severity + '"><span class="tag">' + ingestEsc(tag) + '</span><span>' + ingestEsc(message) + '</span></div>';
    });
    html.push('<div><div class="ingest-section-title">' + ingestEsc(ingestT('检查结果', 'Checks')) + '</div><div class="ingest-issues">' + items.join('') + '</div></div>');
  }

  const sampleEvents = preview.events || [];
  if (sampleEvents.length) {
    const head = ingestT('事件 ID', 'Event ID') + '</th><th>' + ingestT('基因', 'Gene') + '</th><th>' + ingestT('类型', 'Type') + '</th><th>ΔPSI</th><th class="num">FDR</th><th>' + ingestT('坐标', 'Coordinates');
    const rows = sampleEvents.map(function (event) {
      return '<tr><td>' + ingestEsc(event.event_id) + '</td><td>' + ingestEsc(event.gene) + '</td><td>' + ingestEsc(event.event_type) + '</td><td>' + ingestFixed(event.delta_psi, 3) + '</td><td>' + ingestSci(event.fdr) + '</td><td>' + ingestEsc(event.coordinates) + '</td></tr>';
    }).join('');
    html.push('<div><div class="ingest-section-title">' + ingestEsc(ingestT('标准化预览（前 5 行）', 'Standardized preview (first 5 rows)')) + '</div><div class="ingest-preview-table"><table><thead><tr><th>' + head + '</th></tr></thead><tbody>' + rows + '</tbody></table></div></div>');
  }

  const privacy = ingestT(data.privacy || '', data.privacy_en || data.privacy || '');
  if (privacy && !native) html.push('<div class="ingest-privacy">' + ingestEsc(privacy) + '</div>');

  body.innerHTML = html.join('');

  if (cancelBtn) cancelBtn.textContent = ingestT('取消', 'Cancel');
  if (!ingestState.applying) {
    if (unmappable || (native && data.validation && !data.validation.ok)) {
      confirmBtn.disabled = true;
      confirmBtn.textContent = unmappable
        ? ingestT('无法自动标准化', 'Cannot standardize')
        : ingestT('数据校验未通过', 'Validation failed');
    } else {
      updateIngestConfirmState();
    }
  }
}

function ingestSelectChanged(select) {
  if (!ingestState) return;
  if (!ingestState.mapping.columns) ingestState.mapping.columns = {};
  const field = select.getAttribute('data-field');
  if (!field) return;
  if (select.value) ingestState.mapping.columns[field] = select.value;
  else delete ingestState.mapping.columns[field];
  if (select.getAttribute('data-required') === '1') select.classList.toggle('missing', !select.value);
  updateIngestConfirmState();
}

function ingestGroupChanged(select) {
  if (!ingestState) return;
  const sampleId = select.getAttribute('data-sample-id');
  ingestState.mapping.sample_groups[sampleId] = select.value === '' ? '' : ingestState.groupLabels[Number(select.value)];
  updateIngestConfirmState();
}

function ingestAssignUnassigned(index) {
  if (!ingestState) return;
  const label = ingestState.groupLabels[index];
  (ingestState.data.sample_ids || []).forEach(function (id) {
    if (!ingestState.mapping.sample_groups[id]) ingestState.mapping.sample_groups[id] = label;
  });
  renderIngestModal();
}

function ingestGroupLabelChanged(input) {
  if (!ingestState) return;
  const index = Number(input.getAttribute('data-group-label'));
  const oldLabel = ingestState.groupLabels[index];
  const newLabel = input.value.trim();
  ingestState.groupLabels[index] = newLabel;
  Object.keys(ingestState.mapping.sample_groups).forEach(function (id) {
    if (ingestState.mapping.sample_groups[id] === oldLabel) ingestState.mapping.sample_groups[id] = newLabel;
  });
  document.querySelectorAll('#ingest-body select[data-sample-id]').forEach(function (select) {
    select.options[index + 1].textContent = newLabel;
  });
  updateIngestConfirmState();
}

function updateIngestConfirmState() {
  if (!ingestState) return;
  const data = ingestState.data || {};
  if (data.status === 'unmappable') return;
  const confirmBtn = document.getElementById('ingest-confirm');
  if (!confirmBtn || ingestState.applying) return;
  const columns = {};
  document.querySelectorAll('#ingest-body select[data-field]').forEach(function (select) {
    if (select.value) columns[select.getAttribute('data-field')] = select.value;
  });
  const preview = data.preview || {};
  const validation = preview.validation || data.validation || {};
  const sampleIds = data.sample_ids || [];
  const groupLabels = ingestState.groupLabels || [];
  const groupsReady = !sampleIds.length || (groupLabels[0] && groupLabels[1] && groupLabels[0] !== groupLabels[1] && sampleIds.every(id => groupLabels.includes(ingestState.mapping.sample_groups[id])) && new Set(sampleIds.map(id => ingestState.mapping.sample_groups[id])).size === 2);
  const missingGene = !columns.gene_symbol && !columns.gene_id;
  const hasDelta = !!columns.delta_PSI || (!!columns.mean_PSI_group1 && !!columns.mean_PSI_group2) || Number(preview.sample_psi_columns || 0) > 0;
  const hasSignificance = !!columns.FDR || !!columns.p_value;
  const ready = groupsReady && (data.native ? Number(validation.error_count || 0) === 0 : (data.status === 'bgi_single_sample' ? true : (!missingGene && hasDelta && hasSignificance)));
  confirmBtn.disabled = !ready;
  confirmBtn.textContent = ready ? (data.status === 'bgi_single_sample' ? ingestT('确认分组并生成探索性表', 'Create exploratory table') : ingestT('确认映射并分析', 'Confirm & analyze')) : ingestT('请先补全映射', 'Complete the mapping');
}

async function confirmIngest() {
  if (!ingestState || ingestState.applying) return;
  const data = ingestState.data || {};
  const ctx = ingestState.context || {};
  const errorDiv = document.getElementById('ingest-error');
  const confirmBtn = document.getElementById('ingest-confirm');
  if (errorDiv) errorDiv.textContent = '';

  if (data.status === 'bgi_single_sample') {
    ingestState.applying = true;
    if (confirmBtn) confirmBtn.disabled = true;
    try {
      const response = await fetch('/api/ingest/apply', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({input_dir:ctx.uploadDir, mapping:{adapter:'bgi_single_sample',sample_groups:ingestState.mapping.sample_groups}})});
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || 'HTTP ' + response.status);
      closeIngestModal();
      const statusDiv = ctx.statusDiv || document.getElementById('stat-status');
      if (statusDiv) statusDiv.textContent = ingestT('探索性事件表已生成：', 'Exploratory event table created: ') + result.path + ingestT('。原报告没有组间 p 值或 FDR，不会报告显著差异。', '. No differential p-values or FDR were available.');
    } catch (error) {
      if (errorDiv) errorDiv.textContent = error.message;
    } finally {
      ingestState.applying = false;
      updateIngestConfirmState();
    }
    return;
  }

  if (data.native) {
    const sampleIds = data.sample_ids || [];
    const groups = ingestState.mapping.sample_groups || {};
    if (sampleIds.length && (sampleIds.some(id => !groups[id]) || new Set(sampleIds.map(id => groups[id])).size !== 2)) {
      if (errorDiv) errorDiv.textContent = ingestT('请为每个样本选择分组，并确保两组都有样本。', 'Assign every sample and include both groups.');
      return;
    }
    if (!sampleIds.length) { closeIngestModal(); runAnalysisOnDir(ctx.analysisQuery, ctx.uploadDir, ctx.projectName, ctx.statusDiv); return; }
    ingestState.applying = true;
    if (confirmBtn) confirmBtn.disabled = true;
    try {
      const response = await fetch('/api/ingest/groups', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({input_dir:ctx.uploadDir,sample_groups:groups})});
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || 'HTTP ' + response.status);
      ingestState.applying = false;
      closeIngestModal();
      runAnalysisOnDir(ctx.analysisQuery, result.path, ctx.projectName, ctx.statusDiv);
    } catch (error) {
      ingestState.applying = false;
      if (errorDiv) errorDiv.textContent = error.message;
      updateIngestConfirmState();
    }
    return;
  }

  const columns = {};
  const selects = document.querySelectorAll('#ingest-body select[data-field]');
  for (let i = 0; i < selects.length; i++) {
    const field = selects[i].getAttribute('data-field');
    if (field && selects[i].value) columns[field] = selects[i].value;
  }
  const mappedFields = {};
  (data.mapping_fields || []).forEach(function (field) { mappedFields[field.field] = true; });
  const originalColumns = (data.mapping && data.mapping.columns) || {};
  Object.keys(originalColumns).forEach(function (key) {
    if (!mappedFields[key]) columns[key] = originalColumns[key];
  });

  if (!columns.gene_symbol && !columns.gene_id) {
    if (errorDiv) errorDiv.textContent = ingestT('请至少映射基因符号或基因 ID。', 'Map at least a gene symbol or gene ID column.');
    return;
  }
  const preview = data.preview || {};
  const hasDelta = !!columns.delta_PSI || (!!columns.mean_PSI_group1 && !!columns.mean_PSI_group2) || Number(preview.sample_psi_columns || 0) > 0;
  if (!hasDelta) {
    if (errorDiv) errorDiv.textContent = ingestT('请映射 ΔPSI，或同时映射两组平均 PSI。', 'Map delta PSI, or both group mean PSI columns.');
    return;
  }
  if (!columns.FDR && !columns.p_value) {
    if (errorDiv) errorDiv.textContent = ingestT('请映射 FDR 或 p 值，否则无法筛选显著事件。', 'Map an FDR or p-value column so significant events can be selected.');
    return;
  }

  const mapping = JSON.parse(JSON.stringify(data.mapping || {}));
  mapping.columns = columns;
  mapping.sample_groups = ingestState.mapping.sample_groups;
  mapping.sample_groups_confirmed = (data.sample_ids || []).length > 0;
  if (data.event_file && data.event_file.name) mapping.event_file = data.event_file.name;

  ingestState.applying = true;
  if (confirmBtn) { confirmBtn.disabled = true; confirmBtn.textContent = ingestT('标准化中…', 'Standardizing…'); }
  try {
    const response = await fetch('/api/ingest/apply', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ input_dir: ctx.uploadDir, mapping: mapping })
    });
    let result = {};
    try { result = await response.json(); } catch (parseError) { result = {}; }
    if (!response.ok) {
      const detail = result && result.detail;
      const message = typeof detail === 'string' ? detail : (detail ? JSON.stringify(detail) : 'HTTP ' + response.status);
      throw new Error(message);
    }
    const statusDiv = ctx.statusDiv || document.getElementById('stat-status');
    ingestState.applying = false;
    closeIngestModal();
    statusDiv.innerHTML = '<span class="status status-running"><span class="status-dot"></span>标准化完成，开始分析...</span>';
    runAnalysisOnDir(ctx.analysisQuery, result.path, ctx.projectName, statusDiv);
  } catch (error) {
    ingestState.applying = false;
    if (errorDiv) errorDiv.textContent = ingestT('标准化失败：', 'Standardization failed: ') + error.message;
    if (confirmBtn) { confirmBtn.disabled = false; confirmBtn.textContent = ingestT('确认映射并分析', 'Confirm & analyze'); }
  }
}

document.addEventListener('keydown', function (event) {
  if (event.key === 'Escape' && ingestState) closeIngestModal();
});

document.addEventListener('epitoperank:language', function () {
  if (ingestState) renderIngestModal();
});

function viewEventDetails(eventId) { 
  const event = state.events.find(e => (e.event_id || e.id) === eventId);
  if (!event) { AppNotify.toast('事件未找到', 'warning'); return; }
  
  const gene = event.gene_symbol || event.gene || 'Unknown';
  const eventType = event.event_type || event.type || 'Unknown';
  const dpsi = event.delta_psi !== null && event.delta_psi !== undefined ? Number(event.delta_psi).toFixed(4) : 'N/A';
  const fdr = event.fdr !== null && event.fdr !== undefined ? fmtFdr(event.fdr) : 'N/A';
  const pValue = event.p_value !== null && event.p_value !== undefined ? fmtSci(event.p_value, 3) : 'N/A';
  const score = event.score !== null && event.score !== undefined ? Number(event.score).toFixed(3) : 'N/A';
  
  // Determine significance level
  let sigLevel = 'ns';
  let sigColor = '#94a3b8';
  if (fdr !== 'N/A') {
    const fdrNum = parseFloat(String(fdr).replace('<', ''));
    if (fdrNum < 0.001) { sigLevel = '***'; sigColor = '#dc2626'; }
    else if (fdrNum < 0.01) { sigLevel = '**'; sigColor = '#f59e0b'; }
    else if (fdrNum < 0.05) { sigLevel = '*'; sigColor = '#059669'; }
  }
  
  // Biological interpretation based on delta PSI
  let biologicalImpact = '';
  let impactColor = '';
  const dpsiAbs = Math.abs(parseFloat(dpsi));
  if (dpsi !== 'N/A') {
    if (dpsiAbs > 0.3) { biologicalImpact = '强效应 - 可能导致蛋白质功能重大改变'; impactColor = '#dc2626'; }
    else if (dpsiAbs > 0.15) { biologicalImpact = '中等效应 - 可能影响蛋白质结构域'; impactColor = '#f59e0b'; }
    else if (dpsiAbs > 0.05) { biologicalImpact = '弱效应 - 可能对功能有轻微影响'; impactColor = '#059669'; }
    else { biologicalImpact = '微小效应 - 可能无显著生物学影响'; impactColor = '#94a3b8'; }
  }
  
  // Event type descriptions
  const eventDescriptions = {
    'SE': '外显子跳跃 (Skipped Exon): 最常见的外显子类型，可能导致蛋白质结构域缺失',
    'MXE': '互斥外显子 (Mutually Exclusive Exons): 两个相邻外显子中只保留一个',
    'A3SS': "可变3'剪接位点 (Alternative 3' Splice Site): 影响外显子3'端边界",
    'A5SS': "可变5'剪接位点 (Alternative 5' Splice Site): 影响外显子5'端边界",
    'RI': '内含子保留 (Retained Intron): 内含子未被正确移除'
  };
  
  const eventDesc = eventDescriptions[eventType] || '未知剪接事件类型';
  
  // Create modal HTML
  const modalHTML = `
    <div id="event-detail-modal" style="position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: var(--white); z-index: 2000; display: flex; align-items: center; justify-content: center;">
      <div style="background: var(--white); border: 1px solid var(--gray-300); border-radius: var(--radius); padding: 0; max-width: 900px; width: 95%; max-height: 90vh; overflow-y: auto;">
        <!-- Header -->
        <div style="background: var(--black); padding: 32px; color: white; position: relative;">
          <button onclick="closeEventModal()" style="position: absolute; top: 20px; right: 20px; background: rgba(255,255,255,0.2); border: none; width: 36px; height: 36px; border-radius: 50%; color: white; font-size: 20px; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: all 0.2s;" onmouseover="this.style.background='rgba(255,255,255,0.3)'" onmouseout="this.style.background='rgba(255,255,255,0.2)'">×</button>
          <div style="font-size: 28px; font-weight: 600; margin-bottom: 8px;">${gene}</div>
          <div style="display: flex; gap: 12px; align-items: center; flex-wrap: wrap;">
            <span style="background: rgba(255,255,255,0.15); padding: 6px 14px; border-radius: var(--radius); font-size: 13px; font-weight: 400;">${eventType}</span>
            <span style="background: rgba(255,255,255,0.15); padding: 6px 14px; border-radius: var(--radius); font-size: 13px; font-weight: 400;">FDR ${ingestEsc(fdr)} ${sigLevel}</span>
          </div>
        </div>
        
        <!-- Content -->
        <div style="padding: 32px;">
          <!-- Key Metrics -->
          <div class="grid grid-3" style="margin-bottom: 28px;">
            <div style="background: var(--gray-100); border: 1px solid var(--gray-300); padding: 20px; border-radius: var(--radius); text-align: center;">
              <div style="font-size: 12px; text-transform: uppercase; letter-spacing: 0.8px; color: var(--gray-700); font-weight: 600; margin-bottom: 8px;">Delta PSI</div>
              <div style="font-size: 28px; font-weight: 600; color: var(--black);">${dpsi}</div>
            </div>
            <div style="background: var(--gray-100); border: 1px solid var(--gray-300); padding: 20px; border-radius: var(--radius); text-align: center;">
              <div style="font-size: 12px; text-transform: uppercase; letter-spacing: 0.8px; color: var(--gray-700); font-weight: 600; margin-bottom: 8px;">FDR</div>
              <div style="font-size: 28px; font-weight: 600; color: var(--black);">${ingestEsc(fdr)}</div>
            </div>
            <div style="background: var(--gray-100); border: 1px solid var(--gray-300); padding: 20px; border-radius: var(--radius); text-align: center;">
              <div style="font-size: 12px; text-transform: uppercase; letter-spacing: 0.8px; color: var(--gray-700); font-weight: 600; margin-bottom: 8px;">评分</div>
              <div style="font-size: 28px; font-weight: 600; color: var(--black);">${score}</div>
            </div>
          </div>
          
          <!-- Biological Impact -->
          <div style="background: var(--gray-100); border-left: 1px solid var(--gray-700); padding: 20px; border-radius: var(--radius); margin-bottom: 24px;">
            <div style="font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.8px; color: var(--gray-900); margin-bottom: 8px;">生物学影响评估</div>
            <div style="font-size: 14px; line-height: 1.7; color: var(--gray-900);">${biologicalImpact}</div>
          </div>
          
          <!-- Event Description -->
          <div style="margin-bottom: 24px;">
            <div style="font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.8px; color: var(--gray-700); margin-bottom: 12px;">事件类型说明</div>
            <div style="font-size: 14px; line-height: 1.7; color: var(--gray-900); padding: 16px; background: var(--gray-100); border: 1px solid var(--gray-300); border-radius: var(--radius);">${eventDesc}</div>
          </div>
          
          <!-- Statistical Details -->
          <div style="margin-bottom: 24px;">
            <div style="font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.8px; color: var(--gray-700); margin-bottom: 12px;">统计详情</div>
            <table style="width: 100%; font-size: 14px; border-collapse: collapse;">
              <tr style="border-bottom: 1px solid var(--gray-300);">
                <td style="padding: 12px 16px; font-weight: 600; color: var(--gray-700); width: 40%;">P值</td>
                <td style="padding: 12px 16px; font-family: var(--font-mono); font-size: 14px; color: var(--gray-900);">${ingestEsc(pValue)}</td>
              </tr>
              <tr style="border-bottom: 1px solid var(--gray-300);">
                <td style="padding: 12px 16px; font-weight: 600; color: var(--gray-700);">Delta PSI</td>
                <td style="padding: 12px 16px; font-family: var(--font-mono); font-size: 14px; color: var(--gray-900);">${dpsi}</td>
              </tr>
              <tr style="border-bottom: 1px solid var(--gray-300);">
                <td style="padding: 12px 16px; font-weight: 600; color: var(--gray-700);">FDR校正值</td>
                <td style="padding: 12px 16px; font-family: var(--font-mono); font-size: 14px; color: var(--gray-900);">${ingestEsc(fdr)}</td>
              </tr>
              <tr>
                <td style="padding: 12px 16px; font-weight: 600; color: var(--gray-700);">综合评分</td>
                <td style="padding: 12px 16px; font-family: var(--font-mono); font-size: 14px; color: var(--gray-900);">${score}</td>
              </tr>
            </table>
          </div>
          
          <!-- Literature Evidence -->
          ${event.evidence_json ? `
          <div style="margin-bottom: 24px;">
            <div style="font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.8px; color: var(--gray-700); margin-bottom: 12px;">文献证据</div>
            <div style="padding: 20px; background: var(--gray-100); border: 1px solid var(--gray-300); border-radius: var(--radius); font-size: 14px; line-height: 1.7; color: var(--gray-900);" id="evidence-content">加载中...</div>
          </div>
          ` : '<div style="padding: 20px; background: var(--gray-100); border: 1px solid var(--gray-300); border-radius: var(--radius); font-size: 14px; color: var(--gray-500); text-align: center; margin-bottom: 24px;">暂无文献证据</div>'}
          
          <!-- Action Buttons -->
          <div style="display: flex; gap: 12px; justify-content: flex-end; margin-top: 28px; padding-top: 24px; border-top: 1px solid var(--border);">
            <button class="btn btn-secondary" onclick="closeEventModal()">关闭</button>
            <button class="btn btn-primary" onclick="viewGeneInBrowser('${gene}')">查看基因详情</button>
          </div>
        </div>
      </div>
    </div>
  `;
  
  document.body.insertAdjacentHTML('beforeend', modalHTML);
  
  // Load evidence if available
  if (event.evidence_json) {
    setTimeout(() => {
      try {
        const evidence = typeof event.evidence_json === 'string' ? JSON.parse(event.evidence_json) : event.evidence_json;
        const evidenceDiv = document.getElementById('evidence-content');
        if (Array.isArray(evidence)) {
          evidenceDiv.innerHTML = evidence.map(item => `<div style="margin-bottom: 8px;">• ${item}</div>`).join('');
        } else if (typeof evidence === 'object') {
          evidenceDiv.innerHTML = Object.entries(evidence).map(([k, v]) => `<div style="margin-bottom: 8px;"><strong>${k}:</strong> ${v}</div>`).join('');
        } else {
          evidenceDiv.textContent = evidence;
        }
      } catch (e) {
        document.getElementById('evidence-content').textContent = event.evidence_json;
      }
    }, 100);
  }
}

function closeEventModal() {
  const modal = document.getElementById('event-detail-modal');
  if (modal) {
    modal.style.animation = 'fadeOut 0.3s';
    setTimeout(() => modal.remove(), 300);
  }
}

function viewGeneInBrowser(geneSymbol) {
  closeEventModal();
  navigateTo('gene');
  document.getElementById('gene-search').value = geneSymbol;
  exploreGene();
}

// ==================== MCP Tool Console ====================
const mcpState = { servers: {}, configPath: '', selectedServer: '', tools: [], loading: false };

function mcpStatusBadge(text, kind) {
  const badge = document.getElementById('mcp-status');
  if (!badge) return;
  badge.textContent = text;
  badge.className = 'mcp-badge' + (kind ? ' ' + kind : '');
}

async function loadMcpServers(force) {
  if (mcpState.loading) return;
  mcpState.loading = true;
  mcpStatusBadge('连接中…', '');
  document.getElementById('mcp-server-hint').textContent = '正在连接 MCP 服务器…';
  try {
    const response = await fetch('/api/mcp/servers' + (force ? '?refresh=1' : ''));
    if (!response.ok) throw new Error('HTTP ' + response.status);
    const data = await response.json();
    mcpState.servers = data.servers || {};
    mcpState.configPath = data.config_path || '';
    renderMcpServers();
  } catch (error) {
    mcpStatusBadge('连接失败', 'err');
    document.getElementById('mcp-server-hint').textContent = String(error);
    document.getElementById('mcp-server-select').innerHTML = '<option value="">无法读取 MCP 配置</option>';
    document.getElementById('mcp-tool-select').innerHTML = '<option value="">—</option>';
  } finally {
    mcpState.loading = false;
  }
}

function renderMcpServers() {
  const select = document.getElementById('mcp-server-select');
  const names = Object.keys(mcpState.servers);
  const connected = names.filter(function (name) { return mcpState.servers[name].status === 'connected'; });
  if (!names.length) {
    mcpStatusBadge('未配置', 'err');
    select.innerHTML = '<option value="">未配置 MCP 服务器</option>';
    document.getElementById('mcp-server-hint').textContent = '在 ' + (mcpState.configPath || '~/.epitoperank/mcp/servers.json') + ' 中添加服务器';
    return;
  }
  const previous = mcpState.selectedServer;
  select.innerHTML = '';
  names.forEach(function (name) {
    const server = mcpState.servers[name];
    const option = document.createElement('option');
    const toolCount = (server.tools || []).length;
    const tag = server.builtin ? '内置' : (server.via || server.transport || 'MCP');
    option.value = name;
    option.textContent = name + ' · ' + tag + ' · ' + toolCount + ' 工具' + (server.status === 'connected' ? '' : '（未连接）');
    option.disabled = server.status !== 'connected';
    select.appendChild(option);
  });
  const preferred = (connected.indexOf(previous) >= 0 ? previous : connected[0]) || '';
  select.value = preferred;
  mcpState.selectedServer = preferred;
  if (connected.length) {
    mcpStatusBadge(connected.length + ' / ' + names.length + ' 已连接', 'ok');
  } else {
    mcpStatusBadge('未连接', 'err');
  }
  onMcpServerChange();
}

function onMcpServerChange() {
  const name = document.getElementById('mcp-server-select').value;
  mcpState.selectedServer = name;
  const server = mcpState.servers[name];
  const toolSelect = document.getElementById('mcp-tool-select');
  const hint = document.getElementById('mcp-server-hint');
  if (!server || server.status !== 'connected') {
    toolSelect.innerHTML = '<option value="">无可用工具</option>';
    hint.textContent = server ? ('状态：' + server.status + (server.error ? ' · ' + server.error : '')) : '';
    onMcpToolChange();
    return;
  }
  mcpState.tools = server.tools || [];
  toolSelect.innerHTML = '';
  mcpState.tools.forEach(function (tool) {
    const option = document.createElement('option');
    option.value = tool.name;
    option.textContent = tool.name;
    toolSelect.appendChild(option);
  });
  const parts = ['连接方式：' + (server.via || server.transport || 'MCP')];
  if (server.url) parts.push(server.url);
  hint.textContent = parts.join(' · ');
  onMcpToolChange();
}

function onMcpToolChange() {
  const toolName = document.getElementById('mcp-tool-select').value;
  const tool = mcpState.tools.find(function (item) { return item.name === toolName; });
  const desc = document.getElementById('mcp-tool-desc');
  const args = document.getElementById('mcp-args');
  if (!tool) {
    desc.textContent = '选择服务器与工具后调用';
    args.value = '{}';
    return;
  }
  desc.textContent = tool.description || '（无描述）';
  args.value = JSON.stringify(buildMcpExample(tool), null, 2);
}

function buildMcpExample(tool) {
  const schema = tool.input_schema || {};
  const properties = schema.properties || {};
  const example = {};
  Object.keys(properties).forEach(function (key) {
    const spec = properties[key] || {};
    if (spec.default !== undefined) {
      example[key] = spec.default;
    } else if (key === 'project_id' && state.currentProject) {
      example[key] = state.currentProject;
    } else if (spec.type === 'integer' || spec.type === 'number') {
      example[key] = spec.minimum !== undefined ? spec.minimum : 0;
    } else if (spec.type === 'boolean') {
      example[key] = false;
    } else if (spec.enum && spec.enum.length) {
      example[key] = spec.enum[0];
    } else {
      example[key] = '';
    }
  });
  return example;
}

function extractMcpPayload(result) {
  if (result === null || result === undefined) return result;
  if (typeof result !== 'object') return result;
  const structured = result.structuredContent !== undefined ? result.structuredContent : result.structured_content;
  if (structured !== undefined) {
    if (structured && typeof structured === 'object' && !Array.isArray(structured) && Object.keys(structured).length === 1 && typeof structured.result === 'string') {
      try { return JSON.parse(structured.result); } catch (error) { return structured.result; }
    }
    return structured;
  }
  if (Array.isArray(result.content)) {
    const texts = result.content.filter(function (item) {
      return item && item.type === 'text';
    }).map(function (item) { return item.text; });
    const text = texts.join(String.fromCharCode(10));
    if (text) {
      try { return JSON.parse(text); } catch (error) { return text; }
    }
  }
  return result;
}

async function callMcpTool() {
  const serverName = document.getElementById('mcp-server-select').value;
  const toolName = document.getElementById('mcp-tool-select').value;
  const resultEl = document.getElementById('mcp-result');
  const statusEl = document.getElementById('mcp-call-status');
  const button = document.getElementById('mcp-call-btn');
  if (!serverName || !toolName) {
    statusEl.textContent = '请选择可用的服务器与工具';
    return;
  }
  let args = {};
  const raw = document.getElementById('mcp-args').value.trim();
  if (raw) {
    try {
      args = JSON.parse(raw);
    } catch (error) {
      resultEl.className = 'mcp-result err';
      resultEl.textContent = '参数不是合法 JSON：' + error.message;
      return;
    }
  }
  if (!args || typeof args !== 'object' || Array.isArray(args)) {
    resultEl.className = 'mcp-result err';
    resultEl.textContent = '参数必须是 JSON 对象，例如 {"project_id": "SPN-XXXX"}';
    return;
  }
  button.disabled = true;
  statusEl.textContent = '调用中…';
  resultEl.className = 'mcp-result';
  resultEl.textContent = '正在通过 MCP 调用 ' + serverName + ' / ' + toolName + ' …';
  const started = performance.now();
  try {
    const response = await fetch('/api/mcp/call', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ server_name: serverName, tool_name: toolName, arguments: args })
    });
    const data = await response.json();
    const elapsed = Math.round(performance.now() - started);
    if (!response.ok || !data.success) {
      const message = data.error || (data.detail ? JSON.stringify(data.detail) : ('HTTP ' + response.status));
      resultEl.className = 'mcp-result err';
      resultEl.textContent = '调用失败：' + message;
      statusEl.textContent = elapsed + ' ms · 失败';
      return;
    }
    const payload = extractMcpPayload(data.result);
    resultEl.className = 'mcp-result';
    resultEl.textContent = typeof payload === 'string' ? payload : JSON.stringify(payload, null, 2);
    statusEl.textContent = elapsed + ' ms · ' + serverName + ' / ' + toolName;
  } catch (error) {
    resultEl.className = 'mcp-result err';
    resultEl.textContent = '调用异常：' + error.message;
    statusEl.textContent = '失败';
  } finally {
    button.disabled = false;
  }
}

async function addExternalMcpServer() {
  const status = document.getElementById('mcp-ext-status');
  const name = document.getElementById('mcp-ext-name').value.trim();
  const url = document.getElementById('mcp-ext-url').value.trim();
  if (!name || !url) { status.textContent = '请填写服务器名称与 URL。'; return; }
  status.textContent = '正在注册并连接…';
  try {
    const response = await fetch('/api/mcp/servers', {method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({name: name, url: url, transport: 'http', protocol: 'auto'})});
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || '连接失败');
    status.textContent = '状态：' + data.status + ' · 可用工具 ' + (data.tools || []).length + ' 个 · 配置：' + data.config_path;
    await loadMcpServers(true);
    document.getElementById('mcp-server-select').value = data.name;
    onMcpServerChange();
  } catch (error) { status.textContent = String(error.message || error); }
}
async function runMcpAgent() {
  const question = document.getElementById('mcp-agent-question').value.trim();
  const statusEl = document.getElementById('mcp-agent-status');
  const resultEl = document.getElementById('mcp-result');
  const button = document.getElementById('mcp-agent-btn');
  if (!question) {
    statusEl.textContent = '请输入自然语言指令';
    return;
  }
  button.disabled = true;
  statusEl.textContent = '模型正在选择工具…';
  resultEl.className = 'mcp-result';
  resultEl.textContent = 'Agent 正在规划 MCP 工具调用…';
  const started = performance.now();
  try {
    const response = await fetch('/api/mcp/agent', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: question, project_id: state.currentProject || '' })
    });
    const data = await response.json();
    const elapsed = Math.round(performance.now() - started);
    if (!response.ok) {
      resultEl.className = 'mcp-result err';
      resultEl.textContent = 'Agent 调用失败：' + (data.detail || ('HTTP ' + response.status));
      statusEl.textContent = elapsed + ' ms · 失败';
      return;
    }
    const plan = data.plan || {};
    const axis = data.source === 'llm' ? 'LLM 规划' : '规则回退';
    const header = [
      'Agent 规划（' + axis + '）：' + (plan.server || '?') + ' / ' + (plan.tool || '?'),
      plan.reason ? '理由：' + plan.reason : '',
      '─'.repeat(34)
    ].filter(Boolean).join(String.fromCharCode(10));
    const payload = extractMcpPayload(data.result);
    const body = typeof payload === 'string' ? payload : JSON.stringify(payload, null, 2);
    resultEl.className = data.success ? 'mcp-result' : 'mcp-result err';
    resultEl.textContent = header + String.fromCharCode(10) + (data.success ? body : ('调用失败：' + (data.error || body)));
    statusEl.textContent = elapsed + ' ms · ' + axis + ' · ' + (data.success ? '成功' : '失败');
    if (plan.server && mcpState.servers[plan.server]) {
      document.getElementById('mcp-server-select').value = plan.server;
      onMcpServerChange();
      if (plan.tool) {
        document.getElementById('mcp-tool-select').value = plan.tool;
        onMcpToolChange();
        document.getElementById('mcp-args').value = JSON.stringify(plan.arguments || {}, null, 2);
      }
    }
    if (data.llm_errors && data.llm_errors.length) {
      statusEl.textContent += ' · 模型回退';
    }
  } catch (error) {
    resultEl.className = 'mcp-result err';
    resultEl.textContent = 'Agent 调用异常：' + error.message;
    statusEl.textContent = '失败';
  } finally {
    button.disabled = false;
  }
}

function cfgText(zh, en) {
  var i18n = window.__epitoperankI18n;
  return i18n && i18n.getLang && i18n.getLang() === 'en' ? en : zh;
}

async function loadModelConfig(force) {
  const base = document.getElementById('cfg-base');
  if (!base) return;
  try {
    const response = await fetch('/api/llm/status');
    if (!response.ok) throw new Error('HTTP ' + response.status);
    const data = await response.json();
    const values = (data.config && data.config.values) || {};
    if (force || !base.dataset.loaded) {
      base.value = values.MODEL_API_BASE_URL || '';
      document.getElementById('cfg-model').value = values.MODEL_NAME || '';
      const key = document.getElementById('cfg-key');
      key.value = '';
      key.placeholder = values.MODEL_API_KEY
        ? cfgText('当前密钥 ' + values.MODEL_API_KEY + '，留空保持不变', 'Current key ' + values.MODEL_API_KEY + ' — leave blank to keep it')
        : cfgText('粘贴你的 API Key', 'Paste your API key');
      base.dataset.loaded = '1';
    }
    const badge = document.getElementById('cfg-status');
    const statusText = document.getElementById('cfg-status-text');
    if (data.configured && data.enabled) {
      badge.className = 'status status-completed';
      statusText.textContent = cfgText('已配置 · ' + (data.model || 'LLM'), 'Configured · ' + (data.model || 'LLM'));
    } else {
      badge.className = 'status status-waiting';
      statusText.textContent = data.enabled ? cfgText('未配置 Key', 'No API key') : cfgText('模型已关闭', 'Model disabled');
    }
    const button = document.getElementById('cfg-save');
    if (button && !button.disabled) button.textContent = cfgText('保存并启用', 'Save & enable');
  } catch (error) {
    const badge = document.getElementById('cfg-status');
    if (badge) {
      badge.className = 'status status-waiting';
      document.getElementById('cfg-status-text').textContent = cfgText('状态不可用', 'Status unavailable');
    }
    console.error('loadModelConfig', error);
  }
}

async function saveModelConfig() {
  const button = document.getElementById('cfg-save');
  const message = document.getElementById('cfg-msg');
  if (!button || button.disabled) return;
  const base = document.getElementById('cfg-base').value.trim();
  const model = document.getElementById('cfg-model').value.trim();
  const key = document.getElementById('cfg-key').value.trim();
  if (!base || !model) {
    message.className = 'cfg-msg err';
    message.textContent = cfgText('请填写 Base URL 和模型名', 'Base URL and model name are required');
    return;
  }
  const values = { MODEL_API_BASE_URL: base, MODEL_NAME: model };
  if (key) values.MODEL_API_KEY = key;
  button.disabled = true;
  button.textContent = cfgText('保存中…', 'Saving…');
  message.className = 'cfg-msg';
  message.textContent = '';
  try {
    const response = await fetch('/api/llm/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ values }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || ('HTTP ' + response.status));
    message.className = 'cfg-msg ok';
    message.textContent = key
      ? cfgText('配置已保存并即时生效', 'Saved — active immediately')
      : cfgText('配置已保存（保留原 Key）', 'Saved (existing key kept)');
    document.getElementById('cfg-key').value = '';
    document.getElementById('cfg-base').dataset.loaded = '';
    await loadModelConfig(true);
  } catch (error) {
    message.className = 'cfg-msg err';
    message.textContent = cfgText('保存失败: ', 'Save failed: ') + error.message;
  } finally {
    button.disabled = false;
    button.textContent = cfgText('保存并启用', 'Save & enable');
  }
}

document.addEventListener('epitoperank:language', function () {
  if (!document.getElementById('cfg-status-text')) return;
  const message = document.getElementById('cfg-msg');
  if (message) {
    message.className = 'cfg-msg';
    message.textContent = '';
  }
  loadModelConfig(true);
});

document.addEventListener('DOMContentLoaded', () => { loadDashboard(); loadModelConfig(); setInterval(() => { if (state.currentPage === 'pipeline' && state.currentProject) { loadPipeline(); } }, 5000); });
</script>
<script>
// 统一的应用内提示层：toast（轻量、自动消失）与 dialog（需要用户确认）。
// 不再使用浏览器原生 alert/confirm —— 原生弹窗在 Chrome / WebView2 / Electron
// 里样式各不相同，无法跟随本应用的主题、语言与圆角体系。
(function () {
  "use strict";

  var ICONS = {
    success: '<path d="M4.5 12.4l4.8 4.8L19.6 6.9"/>',
    error: '<path d="M6.6 6.6l10.8 10.8M17.4 6.6L6.6 17.4"/>',
    warning: '<path d="M12 4.8v9.4"/><circle cx="12" cy="18.9" r="1.45" fill="currentColor" stroke="none"/>',
    info: '<path d="M12 10.6v8.6"/><circle cx="12" cy="6.1" r="1.45" fill="currentColor" stroke="none"/>'
  };
  var TITLES = {
    success: ["完成", "Done"],
    error: ["未完成", "Not completed"],
    warning: ["请注意", "Please check"],
    info: ["提示", "Notice"]
  };
  var CLOSE_LABEL = ["关闭", "Close"];
  var DISMISS_LABEL = ["知道了", "Got it"];
  var TOAST_LIMIT = 4;

  function currentLang() {
    var i18n = window.__epitoperankI18n;
    var value = i18n && i18n.getLang ? i18n.getLang() : "zh";
    return value === "en" || value === "zh-Hant" ? value : "zh";
  }
  function pair(item) { return currentLang() === "en" ? item[1] : item[0]; }
  function translate(text) {
    var i18n = window.__epitoperankI18n;
    var raw = String(text === null || text === undefined ? "" : text);
    if (currentLang() === "zh") return raw;
    if (!i18n || !i18n.translate) return raw;
    // translateOne 按整串匹配字典，多段文案需要逐段翻译。
    var parts = raw.split("\\n\\n");
    for (var i = 0; i < parts.length; i++) parts[i] = i18n.translate(parts[i]);
    return parts.join("\\n\\n");
  }
  function iconSvg(kind) {
    return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.3" ' +
      'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
      (ICONS[kind] || ICONS.info) + "</svg>";
  }
  function resolveStack() {
    var node = document.getElementById("toast-stack");
    if (!node) {
      node = document.createElement("div");
      node.id = "toast-stack";
      node.setAttribute("role", "region");
      node.setAttribute("aria-live", "polite");
      document.body.appendChild(node);
    }
    return node;
  }

  function dismissToast(node, immediate) {
    if (!node || node.getAttribute("data-leaving") === "1") return;
    node.setAttribute("data-leaving", "1");
    if (immediate) { node.remove(); return; }
    node.classList.add("leaving");
    setTimeout(function () { node.remove(); }, 220);
  }

  function toast(message, kind, options) {
    options = options || {};
    kind = ICONS[kind] ? kind : "info";
    var stack = resolveStack();
    while (stack.children.length >= TOAST_LIMIT) dismissToast(stack.firstElementChild, true);

    var life = typeof options.duration === "number" ? options.duration : 5200;
    var node = document.createElement("div");
    node.className = "app-toast " + kind;
    node.setAttribute("role", kind === "error" ? "alert" : "status");
    node.style.setProperty("--toast-life", life + "ms");

    var head = options.title ? translate(options.title) : pair(TITLES[kind]);
    var body = translate(message);
    node.innerHTML =
      '<span class="app-toast-icon">' + iconSvg(kind) + "</span>" +
      '<div class="app-toast-body"><div class="app-toast-title"></div>' +
      (body ? '<div class="app-toast-msg"></div>' : "") + "</div>" +
      '<button type="button" class="app-toast-close" aria-label="' + pair(CLOSE_LABEL) + '">&#10005;</button>';
    node.querySelector(".app-toast-title").textContent = head;
    if (body) node.querySelector(".app-toast-msg").textContent = body;

    var timer = null;
    function arm(ms) {
      clearTimeout(timer);
      timer = setTimeout(function () { dismissToast(node); }, ms);
    }
    node.addEventListener("mouseenter", function () {
      clearTimeout(timer);
      node.classList.add("paused");
      node.style.removeProperty("--toast-life");
    });
    node.addEventListener("mouseleave", function () {
      node.classList.remove("paused");
      arm(1600);
    });
    node.addEventListener("click", function (event) {
      if (event.target.closest(".app-toast-close")) dismissToast(node);
    });
    stack.appendChild(node);
    if (life > 0) arm(life);
    return node;
  }

  var activeActions = [];
  var activeResolve = null;
  var dismissValue = null;

  function dialogNode() {
    var node = document.getElementById("app-dialog");
    if (!node) {
      node = document.createElement("dialog");
      node.id = "app-dialog";
      node.className = "app-dialog";
      document.body.appendChild(node);
    }
    return node;
  }

  function settle(value) {
    var node = dialogNode();
    if (node.open) {
      try { node.close(); } catch (e) {}
    }
    var resolve = activeResolve;
    activeResolve = null;
    activeActions = [];
    if (resolve) resolve(value);
  }

  function dialog(options) {
    options = options || {};
    var kind = ICONS[options.kind] ? options.kind : "info";
    var node = dialogNode();
    if (node.open) settle(null);

    activeActions = options.actions && options.actions.length ? options.actions.slice() : [{
      label: pair(DISMISS_LABEL), variant: "primary", value: true
    }];
    dismissValue = "dismissValue" in options ? options.dismissValue : (activeActions.length === 1 ? activeActions[0].value : null);

    node.className = "app-dialog " + kind;
    var html =
      '<div class="app-dialog-head">' +
        '<div class="app-dialog-mark">' + iconSvg(kind) + "</div>" +
        '<div class="app-dialog-titles">' +
          '<div class="app-dialog-title" id="app-dialog-title"></div>' +
          (options.subtitle ? '<div class="app-dialog-sub"></div>' : "") +
        "</div>" +
        '<button type="button" class="app-dialog-close" aria-label="' + pair(CLOSE_LABEL) + '">&#10005;</button>' +
      "</div>" +
      '<div class="app-dialog-body"></div>' +
      '<div class="app-dialog-foot"></div>';
    node.innerHTML = html;
    node.querySelector(".app-dialog-title").textContent = translate(options.title || pair(TITLES[kind]));
    if (options.subtitle) node.querySelector(".app-dialog-sub").textContent = translate(options.subtitle);

    var body = node.querySelector(".app-dialog-body");
    body.textContent = translate(options.message || "");
    if (options.detail) {
      var detail = document.createElement("div");
      detail.className = "app-dialog-detail";
      detail.textContent = translate(options.detail);
      body.appendChild(detail);
    }
    if (options.bullets && options.bullets.length) {
      var list = document.createElement("ul");
      list.className = "app-dialog-list";
      options.bullets.forEach(function (item) {
        var li = document.createElement("li");
        li.textContent = translate(item);
        list.appendChild(li);
      });
      body.appendChild(list);
    }

    var foot = node.querySelector(".app-dialog-foot");
    activeActions.forEach(function (action, index) {
      var button = document.createElement("button");
      button.type = "button";
      button.className = "btn " + (action.variant === "primary" ? "btn-primary"
        : action.variant === "danger" ? "btn-danger" : "btn-secondary");
      button.setAttribute("data-app-action", String(index));
      button.textContent = translate(action.label || "");
      foot.appendChild(button);
    });
    foot.lastElementChild && foot.lastElementChild.focus({ preventScroll: true });

    node.onclick = function (event) {
      var button = event.target.closest("[data-app-action]");
      if (button) {
        var action = activeActions[Number(button.getAttribute("data-app-action"))];
        var value = action && "value" in action ? action.value : true;
        settle(value);
        if (action && typeof action.onClick === "function") setTimeout(action.onClick, 0);
        return;
      }
      if (event.target.closest(".app-dialog-close")) settle(dismissValue);
    };
    node.oncancel = function (event) {
      event.preventDefault();
      settle(dismissValue);
    };

    return new Promise(function (resolve) {
      var opener = document.activeElement;
      activeResolve = function (value) {
        // 关闭后把焦点还给触发元素，避免键盘用户丢失位置。
        if (opener && opener.isConnected && typeof opener.focus === "function") {
          try { opener.focus({ preventScroll: true }); } catch (e) {}
        }
        resolve(value);
      };
      node.showModal();
    });
  }

  function confirmAsync(message, options) {
    options = options || {};
    return dialog({
      kind: options.kind || "warning",
      title: options.title,
      message: message,
      actions: [
        { label: options.cancelLabel || pair(["取消", "Cancel"]), value: false },
        { label: options.confirmLabel || pair(["继续", "Continue"]),
          variant: options.danger ? "danger" : "primary", value: true }
      ],
      dismissValue: false
    }).then(function (value) { return value === true; });
  }

  window.AppNotify = {
    toast: toast,
    dialog: dialog,
    confirm: confirmAsync,
    translate: translate,
    clear: function () {
      var stack = document.getElementById("toast-stack");
      if (stack) Array.prototype.slice.call(stack.children).forEach(function (node) { dismissToast(node, true); });
    }
  };
})();
</script>

<script>
(function () {
  "use strict";
  // 繁简转换依赖 opencc-cn2t.js（约 1.1MB，占整个前端静态资源的大头）。
  // 绝大多数用户从不切到繁體，所以这里不再在首屏同步加载，而是等真正需要
  // 转换时才注入 <script>；加载完成后若当前语言仍是 zh-Hant，会自动重放一次
  // applyLanguage，把已经渲染出来的文字补上转换结果。
  var traditionalConverter = null;
  var converterLoad = null;
  var converterFailed = false;

  function ensureTraditionalConverter() {
    if (converterLoad || converterFailed) return converterLoad;
    // 资源拿不到时不能静默：用户点了繁體却看到简体，必须说明原因。
    function reportFailure() {
      if (lang === "zh-Hant") {
        AppNotify.toast("繁體中文轉換資源載入失敗，已保持簡體顯示。請檢查網路後重新整理。", "error");
      }
    }
    converterLoad = new Promise(function (resolve) {
      var script = document.createElement("script");
      script.src = "/assets/opencc-cn2t.js";
      script.async = true;
      script.onload = function () {
        try {
          traditionalConverter = window.OpenCC.Converter({ from: "cn", to: "t" });
        } catch (e) {
          converterFailed = true;
          reportFailure();
        }
        resolve(traditionalConverter);
        // 加载期间页面可能已经切成繁體：重新套用一次即可补齐。
        if (traditionalConverter && lang === "zh-Hant") applyLanguage("zh-Hant");
      };
      script.onerror = function () {
        converterFailed = true;
        reportFailure();
        resolve(null);
      };
      document.head.appendChild(script);
    });
    return converterLoad;
  }

  // 转换器未就绪时原样返回，避免为了一个未完成的下载阻塞整页渲染。
  function toTraditional(text) {
    if (traditionalConverter) return traditionalConverter(text);
    ensureTraditionalConverter();
    return text;
  }
  var DICT = {
    "仪表盘": "Dashboard",
    "AI 流水线": "AI Pipeline",
    "事件浏览器": "Event Explorer",
    "可视化": "Visualization",
    "基因浏览器": "Gene Browser",
    "报告": "Report",
    "设置": "Settings",
    "主菜单": "Main Menu",
    "分析工具": "Analysis Tools",
    "智能助手": "Assistant",
    "刷新": "Refresh",
    "+ 新建分析": "+ New Analysis",
    "未加载项目": "No project loaded",
    "AI 智能分析平台": "AI Analysis Platform",
    "EpitopeRank - AI 智能分析平台": "EpitopeRank - AI Analysis Platform",
    "从剪接事件，到可复现的生物学证据。": "From splicing events to reproducible biological evidence.",
    "让 Agent 整理数据、追踪分析状态，并把每一个结论连接到可验证的结果。": "Let agents organize data, track analysis status, and connect every conclusion to verifiable results.",
    "总样本数": "Total Samples",
    "RNA-seq 样本": "RNA-seq samples",
    "剪接事件": "Splicing Events",
    "检测到的事件总数": "Total detected events",
    "显著事件": "Significant Events",
    "系统状态": "System Status",
    "空闲": "Idle",
    "分析中": "Running",
    "当前运行 Agent": "Current Running Agent",
    "暂无运行中的分析": "No analysis running",
    "启动新分析": "Start New Analysis",
    "最近项目": "Recent Projects",
    "暂无项目": "No projects",
    "分析进度": "Analysis Progress",
    "等待启动...": "Waiting to start...",
    "Agent 工作流": "Agent Workflow",
    "加载并验证输入数据，检查文件格式和完整性": "Load and validate input data, checking file format and integrity",
    "执行质量控制检查，过滤低质量样本": "Run quality-control checks and filter low-quality samples",
    "使用统计模型检测可变剪接事件": "Detect alternative splicing events with statistical models",
    "计算显著性（FDR）和效应量（Delta PSI）": "Compute significance (FDR) and effect size (Delta PSI)",
    "功能注释、通路富集和文献证据收集": "Functional annotation, pathway enrichment, and literature evidence collection",
    "生成生物学解读和专业分析报告": "Generate biological interpretation and a professional analysis report",
    "等待中": "Waiting",
    "运行中": "Running",
    "已完成": "Completed",
    "数据加载": "Data Loading",
    "质量控制": "Quality Control",
    "剪接检测": "Splicing Detection",
    "统计分析": "Statistical Analysis",
    "功能注释": "Functional Annotation",
    "生物学解读": "Biological Interpretation",
    "未加载事件数据": "No event data loaded",
    "等待分析结果": "Waiting for analysis results",
    "请完成分析后查看结果": "Complete an analysis to view results",
    "准备生成报告": "Ready to generate report",
    "事件 ID": "Event ID",
    "类型": "Type",
    "基因": "Gene",
    "评分": "Score",
    "操作": "Actions",
    "详情": "Details",
    "事件类型": "Event Type",
    "查看": "View",
    "筛选条件": "Filters",
    "统计阈值": "Statistical Thresholds",
    "搜索基因名称、事件ID或染色体位置...": "Search gene name, event ID, or chromosome position...",
    "选择图表类型": "Select chart type",
    "左侧共 13 张专业科研图，点击即可渲染": "13 publication-ready figures on the left; click to render",
    "差异剪接的显著性与效应量": "Significance and effect size of differential splicing",
    "ΔPSI vs -log10(FDR)，标注显著性阈值": "ΔPSI vs -log10(FDR) with significance thresholds",
    "Top 25 效应量排序，区分包含上调/下调": "Top 25 by effect size, separating inclusion up/down",
    "SE/MXE/A5SS/A3SS/RI 五类事件计数": "Counts of the five event classes: SE/MXE/A5SS/A3SS/RI",
    "五类可变剪接的外显子-内含子结构模式图": "Exon-intron schematic of the five alternative splicing classes",
    "分组占比与批次分布（QC 必备）": "Group proportions and batch distribution (essential for QC)",
    "效应量经验累积分布与阈值占比": "Empirical effect-size CDF and threshold proportions",
    "候选排名 vs -log10(FDR)，定位显著性拐点": "Candidate rank vs -log10(FDR) to locate the significance elbow",
    "各类型中显著与非显著事件构成": "Significant vs non-significant events within each class",
    "剪接事件类型构成与分子机制": "Splicing event composition and molecular mechanisms",
    "Top 事件逐样本 PSI 聚类热图": "Per-sample PSI clustering heatmap for top events",
    "各组 PSI 分布与离群样本检测": "PSI distribution by group and outlier detection",
    "队列构成与样本水平 PSI 模式": "Cohort composition and sample-level PSI patterns",
    "综合评分 Top 15 候选事件条形图": "Bar chart of the top 15 candidates by composite score",
    "显著性/效应/生物学/文献四维贡献": "Four-dimensional contribution: significance / effect / biology / literature",
    "GO/KEGG 富集倍数 vs FDR 气泡图": "GO/KEGG enrichment fold vs FDR bubble plot",
    "智能体候选评分与通路注释": "Agent-based candidate scoring and pathway annotation",
    "SE (外显子跳跃)": "SE (skipped exon)",
    "MXE (互斥外显子)": "MXE (mutually exclusive exons)",
    "A5SS (可变5'剪接)": "A5SS (alternative 5' splice site)",
    "A3SS (可变3'剪接)": "A3SS (alternative 3' splice site)",
    "RI (内含子保留)": "RI (intron retention)",
    "基因注释": "Gene Annotation",
    "文献搜索": "Literature Search",
    "通路富集": "Pathway Enrichment",
    "剪接解读": "Splice Interpretation",
    "支持基因注释、文献搜索、通路富集和剪接事件解读等专业技能": "Professional skills including gene annotation, literature search, pathway enrichment, and splice event interpretation",
    "模型配置": "Model configuration",
    "检查中…": "Checking…",
    "模型名": "Model",
    "留空则保持当前密钥": "Leave blank to keep the current key",
    "保存并启用": "Save & enable",
    "保存中…": "Saving…",
    "密钥仅保存在本机 .env / 配置大模型.env，不会写入报告或日志；保存后即时生效。": "The key is stored only in the local .env / 配置大模型.env file; it is never written to reports or logs and applies immediately.",
    "未配置 Key": "No API key",
    "模型已关闭": "Model disabled",
    "状态不可用": "Status unavailable",
    "请填写 Base URL 和模型名": "Base URL and model name are required",
    "配置已保存并即时生效": "Saved — active immediately",
    "配置已保存（保留原 Key）": "Saved (existing key kept)",
    "选择左侧的技能按钮执行专业分析": "Choose a skill on the left to run a professional analysis",
    "请选择上方的技能按钮开始，或直接输入你的问题。": "Choose a skill above to start, or type your question.",
    "• 项目概览与样本统计": "• Project overview and sample statistics",
    "• 显著剪接事件列表（FDR": "• Significant splicing event list (FDR",
    "• 显著剪接事件列表（FDR < 0.05）": "• Significant splicing event list (FDR < 0.05)",
    "• 关键基因的功能注释与通路富集": "• Functional annotation and pathway enrichment for key genes",
    "• 可视化图表（火山图、热图、分布图）": "• Visualizations (volcano, heatmap, distribution)",
    "• AI 生成的生物学解读与建议": "• AI-generated biological interpretation and recommendations",
    "• 搜索相关科学文献": "• Search relevant scientific literature",
    "• 执行通路富集分析": "• Run pathway enrichment analysis",
    "• 解读剪接事件的临床意义": "• Interpret the clinical significance of splicing events",
    "• 查询基因注释和剪接位点信息": "• Query gene annotation and splice-site information",
    "Model Context Protocol · 运行时外部工具调用": "Model Context Protocol · runtime external tool calls",
    "未加载": "Not loaded",
    "自然语言指令": "Natural-language instruction",
    "AI 调用": "AI Call",
    "模型选择 MCP 工具 → 本地校验 → 执行并返回结果": "Model selects an MCP tool → local validation → execute and return results",
    "例如：查一下 CD44 有哪些显著剪接事件": "e.g. Show significant splicing events for CD44",
    "MCP 服务器": "MCP Server",
    "正在读取服务器配置…": "Reading server configuration…",
    "工具": "Tool",
    "选择服务器与工具后调用": "Select a server and tool to call",
    "参数（JSON）": "Arguments (JSON)",
    "调用工具": "Call Tool",
    "尚未调用": "Not called yet",
    "请输入自然语言指令": "Enter a natural-language instruction",
    "请选择可用的服务器与工具": "Select an available server and tool",
    "请输入问题或选择上方技能...": "Type a question or choose a skill above...",
    "输入问题或选择上方技能...": "Type a question or choose a skill above...",
    "发送": "Send",
    "我理解你的问题。请选择上方的技能按钮开始专业分析，或者告诉我你想分析哪个基因/事件。": "I understand your question. Choose a skill above to start a professional analysis, or tell me which gene or event you want to analyze.",
    "查询基因的详细信息，包括外显子结构、剪接位点、保守性评分和临床变异。": "Detailed gene information including exon structure, splice sites, conservation scores, and clinical variants.",
    "搜索 PubMed、Europe PMC 等数据库中的科学文献，查找与基因或疾病相关的剪接研究。": "Search PubMed, Europe PMC, and other databases for splicing studies related to a gene or disease.",
    "对候选基因列表进行 GO、KEGG、Reactome 通路富集分析，识别显著的功能类别。": "Run GO, KEGG, and Reactome pathway enrichment on candidate genes to identify significant functional categories.",
    "解读特定剪接事件的生物学和临床意义，包括致病性预测和治疗靶点分析。": "Interpret the biological and clinical significance of a specific splicing event, including pathogenicity prediction and therapeutic targets.",
    "请提供必要的参数（如基因名称、事件类型等），我将为你执行分析。": "Please provide the required parameters (e.g., gene name, event type) and I will run the analysis.",
    "探索基因剪接模式": "Explore Gene Splicing Patterns",
    "输入基因符号（如 TP53、BRCA1、MYC）...": "Enter a gene symbol (e.g., TP53, BRCA1, MYC)...",
    "输入基因符号查看该基因的所有剪接事件、统计信息和文献证据。支持热门基因如 TP53、BRCA1、MYC、EGFR 等。": "Enter a gene symbol to view all splicing events, statistics, and literature evidence. Popular genes: TP53, BRCA1, MYC, EGFR.",
    "在上方输入基因符号以探索其剪接事件和生物学功能": "Enter a gene symbol above to explore its splicing events and biological function",
    "基因剪接分析报告": "Gene Splicing Analysis Report",
    "返回事件列表": "Back to Event List",
    "总事件数": "Total Events",
    "平均 |ΔPSI|": "Mean |ΔPSI|",
    "事件类型分布": "Event Type Distribution",
    "剪接事件详情": "Splicing Event Details",
    "该基因可能不在当前分析的候选列表中，或未达到显著性阈值": "This gene may not be in the current candidate list or did not pass the significance threshold",
    "浏览所有事件": "Browse All Events",
    "未选择项目": "No project selected",
    "请先在仪表盘选择一个分析项目": "Select an analysis project on the dashboard first",
    "请先选择项目": "Select a project first",
    "在仪表盘选择一个分析项目后再探索基因": "Select an analysis project on the dashboard before exploring genes",
    "图表不可用": "Figure unavailable",
    "该项目可能尚未生成此图表，请完成分析后重试": "This figure may not exist yet. Complete the analysis and try again.",
    "正在渲染图表（首次生成约需数秒）...": "Rendering figure (the first render may take a few seconds)...",
    "报告生成成功！": "Report generated successfully!",
    "文件已自动下载": "The file has been downloaded automatically",
    "在新窗口中查看": "Open in New Window",
    "报告生成失败": "Report generation failed",
    "重试": "Retry",
    "正在生成报告...": "Generating report...",
    "这可能需要几分钟时间，请耐心等待": "This may take a few minutes. Please wait.",
    "未知错误": "Unknown error",
    "无标题": "Untitled",
    "查看原文 →": "View source →",
    "被引次数:": "Citations:",
    "机制:": "Mechanism:",
    "示例:": "Example:",
    "相关临床试验:": "Related clinical trials:",
    "进行中": "Ongoing",
    "位置:": "Location:",
    "染色体:": "Chromosome:",
    "链方向:": "Strand:",
    "生物类型:": "Biotype:",
    "基因符号:": "Gene symbol:",
    "基因名称:": "Gene name:",
    "基因类型:": "Gene type:",
    "未找到匹配的事件": "No matching events found",
    "暂无文献证据": "No literature evidence",
    "关闭": "Close",
    "查看基因详情": "View Gene Details",
    "生物学影响评估": "Biological Impact Assessment",
    "强效应 - 可能导致蛋白质功能重大改变": "Strong effect - may substantially alter protein function",
    "中等效应 - 可能影响蛋白质结构域": "Moderate effect - may affect a protein domain",
    "弱效应 - 可能对功能有轻微影响": "Weak effect - may have a minor functional impact",
    "微小效应 - 可能无显著生物学影响": "Minimal effect - likely no significant biological impact",
    "事件未找到": "Event not found",
    "事件类型说明": "Event Type Description",
    "统计详情": "Statistical Details",
    "P值": "P-value",
    "FDR校正值": "FDR-adjusted",
    "综合评分": "Composite Score",
    "文献证据": "Literature Evidence",
    "加载中...": "Loading...",
    "外显子跳跃 (Skipped Exon): 最常见的外显子类型，可能导致蛋白质结构域缺失": "Skipped exon (SE): the most common event type; may cause loss of a protein domain",
    "互斥外显子 (Mutually Exclusive Exons): 两个相邻外显子中只保留一个": "Mutually exclusive exons (MXE): only one of two adjacent exons is retained",
    "可变3'剪接位点 (Alternative 3' Splice Site): 影响外显子3'端边界": "Alternative 3' splice site (A3SS): affects the exon 3' boundary",
    "可变5'剪接位点 (Alternative 5' Splice Site): 影响外显子5'端边界": "Alternative 5' splice site (A5SS): affects the exon 5' boundary",
    "内含子保留 (Retained Intron): 内含子未被正确移除": "Retained intron (RI): the intron is not removed correctly",
    "未知剪接事件类型": "Unknown splicing event type",
    "以 ΔPSI 为横轴、-log10(FDR) 为纵轴展示全部剪接事件；虚线为 FDR=0.05 与 |ΔPSI|=0.1 阈值，橙色点为显著事件。": "ΔPSI on the x-axis and -log10(FDR) on the y-axis for all splicing events; dashed lines mark FDR=0.05 and |ΔPSI|=0.1; orange points are significant events.",
    "按 |ΔPSI| 排序的 Top 25 候选事件；橙色为包含水平上调，蓝色为下调，直观展示效应量谱。": "Top 25 candidates ranked by |ΔPSI|; orange indicates inclusion up, blue indicates inclusion down.",
    "ΔPSI 的经验累积分布曲线，并标注 |ΔPSI|>0.1 的事件占比，用于评估整体效应量分布。": "Empirical CDF of ΔPSI with the proportion of events above |ΔPSI|>0.1.",
    "候选排名对 -log10(FDR) 曲线，配合 FDR=0.05 参考线定位显著性拐点（elbow）。": "Candidate rank vs -log10(FDR) with an FDR=0.05 reference line to locate the significance elbow.",
    "SE / MXE / A5SS / A3SS / RI 五类可变剪接事件的检出计数。": "Detected counts for the five alternative splicing classes: SE / MXE / A5SS / A3SS / RI.",
    "各事件类型中通过阈值（FDR<0.05 且 |ΔPSI|>0.1）的显著事件与非显著事件构成。": "Significant vs non-significant events within each class using FDR<0.05 and |ΔPSI|>0.1.",
    "五类可变剪接事件的外显子-内含子结构模式图（methods 级示意图）。": "Exon-intron schematic of the five alternative splicing classes (methods-level figure).",
    "Top |ΔPSI| 事件的逐样本 PSI 热图，列上方标注样本分组，用于观察聚类模式。": "Per-sample PSI heatmap for top |ΔPSI| events with sample groups annotated above the columns.",
    "按实验组拆分的 Top 事件 PSI 分布（箱线 + 散点），用于识别离群样本。": "PSI distribution of top events by experimental group (box + scatter) to identify outliers.",
    "样本分组占比（环图）与批次分布（条形），为质控必备图表。": "Sample group proportions (donut) and batch distribution (bars) for QC.",
    "AI 智能体综合评分（显著性+效应+生物学+文献）Top 15 候选事件。": "Top 15 candidates by the agent composite score (significance + effect + biology + literature).",
    "Top 候选的四维评分贡献分解：显著性 / 效应量 / 生物学 / 文献证据。": "Four-dimensional score decomposition for top candidates: significance / effect size / biology / literature evidence.",
    "GO/KEGG 富集结果：横轴为富集倍数，颜色为 -log10(FDR)，点大小为重叠基因数。": "GO/KEGG enrichment: fold enrichment on the x-axis, color is -log10(FDR), dot size is overlapping gene count.",
    "新建分析项目": "New Analysis Project",
    "项目名称": "Project Name",
    "分析查询": "Analysis Query",
    "输入项目名称（如 My_RNA_Study）": "Enter a project name (e.g., My_RNA_Study)",
    "输入分析查询（如 compare treatment vs control）": "Enter an analysis query (e.g., compare treatment vs control)",
    "上传文件": "Upload Files",
    "拖拽文件到此处，或点击选择文件": "Drag files here, or click to choose files",
    "支持 CSV、TSV、TXT 表格（Excel 请另存为 CSV），可同时上传样本分组表": "CSV, TSV or TXT tables (save Excel as CSV); a sample-group table can be uploaded too",
    "取消": "Cancel",
    "开始分析": "Start Analysis",
    "请至少选择一个文件": "Please select at least one file",
    "请先选择一个项目": "Please select a project first",
    "请输入基因符号": "Please enter a gene symbol",
    "请输入分析查询": "Please enter an analysis query",
    "请输入项目名称": "Please enter a project name",
    "处理中...": "Processing...",
    "分析已完成": "Analysis complete",
    "分析已启动，准备中...": "Analysis started, preparing...",
    "上传中...": "Uploading...",
    "分析中（预计 3-6 分钟）...": "Running (estimated 3-6 minutes)...",
    "数据 Agent 正在理解查询...": "Data Agent is interpreting the query...",
    "质控 Agent 正在进行质量检查...": "QC Agent is running quality checks...",
    "剪接检测 Agent 正在筛选显著事件...": "Splicing Detection Agent is filtering significant events...",
    "统计 Agent 正在排序候选事件...": "Statistics Agent is ranking candidate events...",
    "注释 Agent 正在收集文献证据...": "Annotation Agent is collecting literature evidence...",
    "注释 Agent 正在进行通路富集分析...": "Annotation Agent is running pathway enrichment...",
    "解读 Agent 正在生成生物学解读...": "Interpretation Agent is generating biological interpretation...",
    "生成分析报告": "Generate Analysis Report",
    "基于当前分析结果生成专业报告": "Generate a professional report from the current analysis",
    "完成分析后可生成包含统计结果、可视化和生物学解读的专业报告": "Generate a professional report with statistics, visualizations, and biological interpretation after analysis",
    "你": "You",
    "数据 Agent": "Data Agent",
    "质控 Agent": "QC Agent",
    "剪接检测 Agent": "Splicing Detection Agent",
    "统计 Agent": "Statistics Agent",
    "注释 Agent": "Annotation Agent",
    "解读 Agent": "Interpretation Agent",
    "应用筛选": "Apply filters",
    "探索": "Explore",
    "核心统计图": "Core statistics",
    "样本与质控": "Samples and QC",
    "事件组成与机制": "Event composition and mechanisms",
    "AI 排序与功能富集": "AI ranking and enrichment",
    "火山图 Volcano": "Volcano plot",
    "ΔPSI 累积分布 ECDF": "ΔPSI ECDF",
    "显著性碎石图 Scree": "Significance scree plot",
    "类型×显著性堆叠图": "Type × significance stacked plot",
    "剪接机制示意图 Schematic": "Splicing mechanism schematic",
    "PSI 热图 Heatmap": "PSI heatmap",
    "分组 PSI 箱线图": "Grouped PSI box plot",
    "队列构成图": "Cohort composition",
    "候选基因排名": "Candidate gene ranking",
    "评分分解堆叠图": "Score decomposition stacked plot",
    "功能富集点图": "Functional enrichment dot plot",
    "ΔPSI 瀑布图 Waterfall": "ΔPSI waterfall",
    "分析结果": "Analysis results",
    "EpitopeRank 智能助手": "EpitopeRank Assistant",
    "MCP 工具": "MCP tools",
    "分析完成": "Analysis complete",
    "分析失败": "Analysis failed",
    "通路富集分析结果": "Pathway Enrichment Results",
    "文献搜索结果": "Literature Search Results",
    "剪接事件解读": "Splice Event Interpretation",
    "总结": "Summary",
    "报告内容": "Report contents",
    "HTML 报告": "HTML report",
    "PDF 报告": "PDF report",
    "提示": "Tip",
    "Agent 已读取数据结构，请确认字段映射后开始分析。": "The agent has read the data structure. Confirm the field mapping to start.",
    "HLA 型别": "HLA type",
    "HLA-I 型别（可选，多个用逗号分隔）": "HLA-I alleles (optional, comma-separated)",
    "IEDB（在线）": "IEDB (online)",
    "MHC 类别": "MHC class",
    "MHCflurry（本地，需安装）": "MHCflurry (local, requires install)",
    "Percentile rank 越低越好。": "Lower percentile rank is better.",
    "auto（本地优先，失败转 IEDB）": "auto (local first, fall back to IEDB)",
    "both（按类别拆分）": "both (split by class)",
    "moPepGen · Docker 变异肽生成": "moPepGen · Docker variant peptide generation",
    "上一页": "Previous",
    "上传事件数据，确认字段与分组，再查看统计结果和研究报告。": "Upload event data, confirm fields and groups, then review statistics and the research report.",
    "下一页": "Next",
    "下载 PDF": "Download PDF",
    "下载当前文件": "Download this file",
    "主导航": "Primary navigation",
    "仅显著事件": "Significant only",
    "从候选序列出发，比较 HLA 结合能力，找到值得进一步研究的肽段。": "Start from candidate sequences, compare HLA binding, and find peptides worth following up.",
    "从当前项目生成候选肽": "Generate candidate peptides from the current project",
    "从当前项目生成并排序": "Generate and rank from the current project",
    "从本机添加编码序列表…": "Add a coding-sequence table from this computer…",
    "以基因为线索，连接剪接事件、统计结果与生物学证据。": "Follow a gene to connect splicing events, statistics, and biological evidence.",
    "使用当前项目查找候选肽。先检查数据，再决定是否进行 HLA 结合预测。": "Find candidate peptides from the current project. Check the data first, then decide whether to run HLA binding prediction.",
    "使用当前项目的剪接事件与已重建的编码序列对照表生成跨连接点候选肽（对照表按表头自动识别，文件名不限）， 再按上面的 HLA 与预测选项排序。读码框与 ORF 必须由上游提供，平台不会从坐标猜测序列。": "Build junction-spanning candidate peptides from the current project's splicing events and reconstructed coding-sequence table (the table is detected by its header, file name unrestricted), then rank them with the HLA and prediction options above. The reading frame and ORF must come from upstream; the platform never guesses sequences from coordinates.",
    "使用当前项目逐阶段运行。每次确认只执行下一阶段；输入文件应位于项目数据目录。流程进度会保存。": "Run the current project stage by stage. Each confirmation executes only the next stage; input files should live in the project data directory. Progress is saved.",
    "使用所选文件生成候选肽": "Generate candidate peptides from the selected files",
    "例如 HLA-A*02:01, HLA-B*07:02": "e.g. HLA-A*02:01, HLA-B*07:02",
    "例如 HLA-A*02:01,HLA-B*07:02": "e.g. HLA-A*02:01,HLA-B*07:02",
    "候选事件 Top 10": "Top 10 candidate events",
    "候选肽序列": "Candidate peptide sequences",
    "先选类别，再选择运行方式。在线预测需要网络连接。": "Choose the class first, then the run mode. Online prediction requires a network connection.",
    "关闭导航": "Close navigation",
    "关闭快捷跳转": "Close quick switch",
    "关闭菜单": "Close menu",
    "准备候选肽": "Prepare candidate peptides",
    "准备数据": "Prepare data",
    "分析流程": "Analysis pipeline",
    "分阶段证据审计": "Staged evidence audit",
    "删除项目": "Delete project",
    "剪接事件与候选肽分析": "Splicing events and candidate peptide analysis",
    "剪接候选新抗原": "Splice-derived neoantigens",
    "剪接来源候选新抗原": "Splice-derived candidate neoantigens",
    "加工预测（proteasome / TAP）": "Processing prediction (proteasome / TAP)",
    "动态：开": "Motion: on",
    "历史项目": "Project history",
    "历史项目详情": "Project details",
    "项目详情": "Project details",
    "关闭详情": "Close details",
    "参考表尚未加载。": "The reference table is not loaded yet.",
    "可视化工作室": "Visualization studio",
    "可选：选择其他文件进行独立分析": "Optional: choose other files for a standalone analysis",
    "图表类型": "Chart type",
    "图表（点击放大）": "Figures (click to enlarge)",
    "基因探索": "Gene explorer",
    "基因符号": "Gene symbol",
    "填入示例": "Fill example",
    "填写后，候选肽和 HLA 型别会分批发送至 IEDB 做 NetMHCpan 结合预测（需要联网，几百条肽通常 30–90 秒）。预测不等于免疫原性验证。": "After you fill them in, candidate peptides and HLA alleles are sent in batches to IEDB for NetMHCpan binding prediction (network required; a few hundred peptides usually take 30–90 s). Prediction is not proof of immunogenicity.",
    "复制全部": "Copy all",
    "如何看结果？": "How to read the results",
    "它代表相对排名，不是亲和力 Kd。": "It is a relative ranking, not an affinity Kd.",
    "密钥仅保存在本机 .env / 配置大模型.env，保存后即时生效。": "The key is stored only in a local .env file and applies immediately after saving.",
    "将当前项目的统计结果、图表和解读整理为可分享的研究报告。": "Assemble the current project's statistics, figures, and interpretation into a shareable research report.",
    "工作区": "Workspace",
    "工作区设置": "Workspace settings",
    "已有肽序列？直接预测": "Already have peptides? Predict directly",
    "已识别 0 条肽段": "0 peptides recognized",
    "常用 MHC-I 面板": "Common MHC-I panels",
    "常用 MHC-II 面板": "Common MHC-II panels",
    "开头的标题行会被忽略。 单次最多 200 条肽、8 个 HLA（接口限制），避免触发 IEDB 频率限制。": "Leading header lines are ignored. Up to 200 peptides and 8 HLA alleles per run (API limits) to stay under IEDB rate limits.",
    "开始一次新的分析": "Start a new analysis",
    "开始使用": "Getting started",
    "开始阶段 0 审计": "Start stage 0 audit",
    "快捷跳转": "Quick switch",
    "快速前往工作区": "Jump to a workspace",
    "成果文件夹": "Results folder",
    "打包 ZIP": "Package ZIP",
    "打开 HTML 报告": "Open HTML report",
    "打开结果目录": "Open results directory",
    "报告与交付": "Reports and delivery",
    "按 FDR": "By FDR",
    "按 |ΔPSI|": "By |ΔPSI|",
    "按基因、事件类型与显著性筛选，追溯候选事件的统计依据。": "Filter by gene, event type, and significance to trace the statistical basis of each candidate.",
    "按基因名": "By gene name",
    "排序": "Sort",
    "探索与导出": "Explore and export",
    "探索性候选肽生成": "Exploratory candidate peptide generation",
    "搜索事件": "Search events",
    "搜索历史项目": "Search project history",
    "搜索工作区": "Search workspace",
    "搜索页面，如 肽预测、报告…": "Search pages, e.g. peptide, report…",
    "支持 CSV、TSV、TXT、文本 .xls、Excel .xls/.xlsx/.xlsm 及压缩文本 .gz；表达量表会被识别并提示所需事件数据": "Supports CSV, TSV, TXT, text .xls, Excel .xls/.xlsx/.xlsm, and gzipped text .gz; expression matrices are detected and the required event data is reported",
    "支持事件表与报告目录导入": "Import event tables and report directories",
    "数据目录：读取中…": "Data directory: reading…",
    "文件名不限": "Any file name",
    "智能接入检查": "Smart ingestion check",
    "末页": "Last",
    "查看数据处理、统计分析与解读进度，定位当前执行阶段。": "Track data processing, statistical analysis, and interpretation, and see which stage is running.",
    "查询 IEDB 已知表位": "Query known IEDB epitopes",
    "样本分组": "Sample groups",
    "检查与分析": "Check and analyze",
    "检查当前项目": "Check the current project",
    "检查编码序列，生成跨连接点候选肽，再进入结合预测与证据审计。": "Validate coding sequences, build junction-spanning candidate peptides, then move on to binding prediction and evidence audit.",
    "正在读取当前项目…": "Reading the current project…",
    "每行一个肽段（8–30 aa）；可直接粘贴 FASTA 序列，": "One peptide per line (8–30 aa); FASTA can be pasted directly,",
    "流程日志（最近 12 条）": "Pipeline log (last 12 entries)",
    "浏览候选事件，生成图表与报告": "Browse candidate events, generate figures and reports",
    "浏览全部事件": "Browse all events",
    "清空型别": "Clear alleles",
    "生成候选肽": "Generate candidate peptides",
    "用于报告里的 AI 解读与 MCP 工具的自然语言调用。密钥只保存在本机，不会写入报告或日志。": "Used for AI interpretation in reports and natural-language MCP tool calls. The key stays on this machine and is never written to reports or logs.",
    "研究工作区": "Research workspace",
    "确认列的含义": "Confirm what each column means",
    "确认并执行下一阶段": "Confirm and run the next stage",
    "确认数据映射，跟踪每一步进度": "Confirm the data mapping and follow every step",
    "确认映射并分析": "Confirm mapping and analyze",
    "确认这套对应关系": "Confirm this mapping",
    "第一步：检查项目数据": "Step 1: check project data",
    "第二步：选择编码序列表，生成候选肽": "Step 2: choose a coding-sequence table and generate candidate peptides",
    "管理剪接分析项目，追踪进度，回到每一次研究的结果。": "Manage splicing projects, track progress, and return to each study's results.",
    "系统会检查剪接事件和生成肽所需的编码序列表。": "The system checks the splicing events and the coding-sequence table needed to build peptides.",
    "结合预测不等于抗原呈递，也不等于免疫原性。排序仅用于探索性候选筛选。": "Binding prediction is not antigen presentation and not immunogenicity. Ranking is for exploratory candidate triage only.",
    "编码序列对照表需包含": "The coding-sequence table must contain",
    "编码序列表": "Coding-sequence table",
    "编码序列表就是「每个剪接事件对应的参考 CDS 与改变后 CDS」。系统按表头自动识别，": "A coding-sequence table maps each splicing event to its reference CDS and altered CDS. It is detected by header,",
    "肽预测": "Peptide prediction",
    "肽预测工作台": "Peptide prediction workbench",
    "自动识别当前项目中的 rMATS 事件表（JC 或 JCEC，文件名不限）。请提供版本匹配的参考文件并启动 Docker；生成的是蛋白质组学变异肽，不是 HLA 预测或 CDS 对照表。": "Auto-detect rMATS event tables in the current project (JC or JCEC, any file name). Provide a version-matched reference and start Docker; the output is proteomic variant peptides, not HLA predictions or a CDS table.",
    "菜单": "Menu",
    "请先选择一个项目。": "Select a project first.",
    "请先选择项目并填写已知证据。": "Select a project and fill in the known evidence first.",
    "跳到工作区": "Skip to workspace",
    "运行 moPepGen": "Run moPepGen",
    "这张表的列名不是标准写法，系统已按内容猜测。请核对下面四项，确认后只需设置一次。": "This table does not use standard column names, so the system guessed from the content. Check the four fields below; you only need to confirm once.",
    "选择 HLA": "Select HLA",
    "选择华大报告目录": "Choose a BGI report directory",
    "选择图表后，预览将在这里显示": "Pick a chart and the preview appears here",
    "选择数据文件": "Choose data files",
    "选择研究问题对应的图表，查看当前项目的可视化结果。": "Choose the chart that matches your research question to view this project's visualizations.",
    "选择要查看的图表": "Choose a chart",
    "逗号分隔；输入时会在 IEDB 等位基因表中搜索（最多显示 500 条）。class-I 与 class-II 需分别预测， 选择“both”时平台会按类别拆分。": "Comma-separated; typing searches the IEDB allele table (up to 500 matches). class-I and class-II are predicted separately; choosing \\"both\\" splits by class.",
    "配置 AI 解读服务与外部工具，查看连接状态。": "Configure the AI interpretation service and external tools, and check their connection status.",
    "项目工作台": "Project workspace",
    "预测与解读": "Prediction and interpretation",
    "预测器": "Predictor",
    "预测并排序": "Predict and rank",
    "预测流程": "Prediction pipeline",
    "预测结果": "Prediction results",
    "预测设置": "Prediction settings",
    "首页": "First",
    "高级选项：其他文件和专业分析工具": "Advanced: other files and specialist tools",
    "默认使用当前项目已上传的数据。编码序列对照表按表头自动识别，文件名不限；也可在下方选择文件进行独立分析。MHC 结合预测不等于免疫原性验证。": "Uses the data already uploaded to the current project by default. The coding-sequence table is detected by header with no file-name restriction; you can also pick files below for a standalone analysis. MHC binding prediction is not immunogenicity validation.",
    "，其中 junction_nt 是异常 CDS 内新连接点前的核苷酸数。": ", where junction_nt is the number of nucleotides before the novel junction in the altered CDS.",
    "；下面若已列出文件，直接选即可。": "; if files are already listed below, just pick one.",
    "完成": "Done",
    "未完成": "Not completed",
    "请注意": "Please check",
    "通知": "Notice",
    "上传没有完成": "Upload did not finish",
    "文件或数据目录在上传阶段中断，分析尚未启动。": "The upload was interrupted before analysis started.",
    "确认文件格式为 CSV、TSV、TXT 或表格型 XLS": "Check the file is CSV, TSV, TXT, or a table-style XLS",
    "单个文件不要过大，必要时先拆分": "Keep individual files small; split them if needed",
    "检查网络与本地服务是否可用": "Check that the network and the local service are up",
    "分析未能完成": "Analysis did not finish",
    "服务返回了错误，本次分析已中止。修正输入后可以重新发起。": "The service returned an error and this run was stopped. Fix the input and start again.",
    "结果已写入当前项目": "Results written to the current project",
    "事件表已解析，显著性筛选与候选排序都已完成。接下来可以逐条查看事件，或直接生成研究报告。": "The event table is parsed; significance filtering and candidate ranking are done. You can now review events one by one, or generate the research report.",
    "生成研究报告": "Generate report",
    "查看可视化": "View figures",
    "浏览事件": "Browse events",
    "连接已中断": "Connection lost",
    "前端没能拿到分析响应，但后台任务可能仍在运行。稍后点击右上角「刷新」即可看到最新进度。": "The UI did not receive the response, but the job may still be running. Use Refresh at the top right shortly to see the latest progress.",
    "删除这个项目？": "Delete this project?",
    "保留项目": "Keep project",
    "替换当前输入？": "Replace the current input?",
    "填入示例会覆盖当前填写好的肽序列和 HLA 型别。": "Filling in the example will overwrite the peptide sequences and HLA alleles you already entered.",
    "保留输入": "Keep input",
    "删除失败：": "Delete failed:",
    "删除失败：HTTP": "Delete failed: HTTP",
    "Agent 已读取数据结构。确认字段映射后，将标准化并进入原有分析流程。": "The agent has read the data structure. After you confirm the field mapping it will normalize the data and enter the standard analysis pipeline.",
    "Agent 正在规划 MCP 工具调用…": "The agent is planning an MCP tool call…",
    "Agent 规划（": "Agent plan (",
    "Agent 调用失败：": "Agent call failed:",
    "Agent 调用异常：": "Agent call error:",
    "FDR 覆盖": "FDR coverage",
    "FPKM、TPM 和 read_count 是表达量，不是剪接事件 PSI；请上传 SE/MXE/A3SS/A5SS/RI 事件表。": "FPKM, TPM, and read_count are expression levels, not splicing PSI; please upload SE/MXE/A3SS/A5SS/RI event tables.",
    "GENCODE 或 ENSEMBL": "GENCODE or ENSEMBL",
    "GTEx 基因组版本": "GTEx genome build",
    "GTEx 蛋白 FASTA 文件名": "GTEx protein FASTA file name",
    "GTEx 连接点表文件名": "GTEx junction table file name",
    "HLA 分型来源": "HLA typing source",
    "HLA 置信度": "HLA confidence",
    "HLA-I 型别，逗号分隔": "HLA-I alleles, comma-separated",
    "IEDB 在线 · MHCflurry": "IEDB online · MHCflurry",
    "LLM 规划": "LLM plan",
    "percentile rank 越低越好；预测不等于呈递或免疫原性。": "Lower percentile rank is better; prediction is not presentation or immunogenicity.",
    "— 未映射 —": "— not mapped —",
    "— 请选择 —": "— select —",
    "。原报告没有组间 p 值或 FDR，不会报告显著差异。": ". The original report has no between-group p-values or FDR, so no significant differences are reported.",
    "。将读取项目目录中的事件表和编码序列对照表。": ". Event tables and the coding-sequence table will be read from the project directory.",
    "上传失败": "Upload failed",
    "上游 ORF 表文件名（留空自动识别）": "Upstream ORF table file name (leave blank to auto-detect)",
    "不可解析": "Unparseable",
    "个等位基因": "alleles",
    "事件基因组版本": "Event genome build",
    "事件表": "Event table",
    "事件表完整性：complete / subset / unknown": "Event table completeness: complete / subset / unknown",
    "事件连接点表文件名": "Event junction table file name",
    "事件类型分布 Composition": "Event type composition",
    "事件类型：": "Event types:",
    "例如 GRCh38 / GENCODE vXX（须与上游一致）": "e.g. GRCh38 / GENCODE vXX (must match upstream)",
    "保存失败": "Save failed",
    "保存失败:": "Save failed:",
    "信息": "Info",
    "候选基因排名 Ranking": "Candidate gene ranking",
    "全蛋白组 FASTA 文件名": "Whole-proteome FASTA file name",
    "内置": "Built-in",
    "分组 PSI 箱线图 Box Plot": "Grouped PSI box plot",
    "剪接事件：": "Splicing events:",
    "功能富集点图 Dot Plot": "Functional enrichment dot plot",
    "加载中…": "Loading…",
    "动态：关": "Motion: off",
    "动态：系统关闭": "Motion: off by system",
    "单次最多 200 条肽，当前输入": "At most 200 peptides per run; currently",
    "单次最多 8 个 HLA 型别，当前输入": "At most 8 HLA alleles per run; currently",
    "原生格式：": "Native format:",
    "参数不是合法 JSON：": "Arguments are not valid JSON:",
    "参数必须是 JSON 对象，例如 {\\"project_id\\": \\"SPN-XXXX\\"}": "Arguments must be a JSON object, e.g. {\\"project_id\\": \\"SPN-XXXX\\"}",
    "参考基因组 FASTA 文件": "Reference genome FASTA file",
    "参考来源（GENCODE 或 ENSEMBL）": "Reference source (GENCODE or ENSEMBL)",
    "参考蛋白组 FASTA 文件": "Reference proteome FASTA file",
    "参考表加载失败": "Failed to load the reference table",
    "参考表加载失败：": "Failed to load the reference table:",
    "参考表：共": "Reference table:",
    "参考（正常）编码序列": "Reference (normal) coding sequence",
    "另有": "Additionally",
    "可以继续生成候选肽。检查只确认了表头，序列的读码框仍需由专业人员核实。": "You can continue generating candidate peptides. The check only confirmed headers; a specialist must still verify the reading frames.",
    "可用": "Available",
    "可解析": "Parseable",
    "同一列不能承担两个角色，请分别选择。": "One column cannot serve two roles; choose them separately.",
    "图表": "Chart",
    "在": "in",
    "坐标": "Coordinates",
    "坐标基准": "Coordinate basis",
    "基因组及注释版本": "Genome and annotation build",
    "基因组版本": "Genome build",
    "复制失败，请手动选择表格内容": "Copy failed; select the table content manually",
    "大模型 + 规则": "LLM + rules",
    "大模型已提出分组建议，请核对。": "The LLM suggested groups; please verify.",
    "失败": "Failed",
    "字段映射": "Field mapping",
    "字符": "characters",
    "完成：候选": "Done: candidates",
    "审计失败": "Audit failed",
    "尚无可靠的完整分组建议，可修改分组名称并批量分配。": "No reliable complete grouping yet; rename groups and assign samples in bulk.",
    "尚未选择项目。请先在“仪表盘”新建或选择一个项目，再回来生成候选肽。": "No project selected. Create or select one on the Dashboard, then come back to generate candidate peptides.",
    "尚未选择项目，请先在仪表盘选择或新建项目。": "No project selected. Select or create one on the Dashboard first.",
    "已从相同事件文件的历史样本表恢复分组建议。": "Group suggestions restored from a previous sample table for the same event file.",
    "已保存过映射。": "A mapping has already been saved.",
    "已保存，按这套映射可为": "Saved; this mapping can be used for",
    "已停止：": "Stopped:",
    "已在文件管理器中打开结果目录": "Opened the results directory in the file manager",
    "已复制到剪贴板": "Copied to clipboard",
    "已打开：": "Opened:",
    "已有读码框正确的 CDS": "CDS with a verified reading frame already available",
    "已添加": "Added",
    "已触发下载；桌面窗口若未保存文件，请直接查看表格或复制全部": "Download triggered; if the desktop window did not save the file, view the table or copy everything",
    "已识别": "Recognized",
    "已识别 rMATS 文件：": "rMATS files recognized:",
    "已识别华大逐样本剪接表。确认真实分组后可生成探索性 PSI 表；原报告没有组间显著性检验。": "Per-sample BGI splicing tables recognized. After you confirm the real groups an exploratory PSI table can be generated; the original report has no between-group significance test.",
    "已读取上传的样本表。": "The uploaded sample table has been read.",
    "已连接": "Connected",
    "已配置 ·": "Configured ·",
    "当前密钥": "Current key",
    "当前项目已切换，请重新检查。": "The current project changed; please check again.",
    "当前项目：": "Current project:",
    "成功": "OK",
    "打包失败": "Packaging failed",
    "打包失败：": "Packaging failed:",
    "打开成果文件夹失败": "Failed to open the results folder",
    "打开成果文件夹失败：": "Failed to open the results folder:",
    "执行失败": "Run failed",
    "执行失败，请查看日志。": "Run failed; check the log.",
    "执行完成。": "Run finished.",
    "探索性事件表已生成：": "Exploratory event table generated:",
    "接受跳过缺失的连接点或组织表达检查": "Allow skipping missing junction or tissue-expression checks",
    "改变后（变异）编码序列": "Altered (variant) coding sequence",
    "数据校验未通过": "Data validation failed",
    "文件已自动选中。": "The file has been selected automatically.",
    "文件已读取并识别为表达量矩阵。请另选剪接事件结果表进行剪接分析。": "The file was read and identified as an expression matrix. Choose a splicing event result table for splicing analysis.",
    "文件画像": "File profile",
    "新剪接连接点位置（整数）": "Novel junction position (integer)",
    "方法": "Method",
    "无": "None",
    "无法开始：": "Cannot start:",
    "无法恢复流程，请重新开始审计。": "The pipeline cannot be resumed; restart the audit.",
    "无法打开目录：": "Cannot open the directory:",
    "无法继续：": "Cannot continue:",
    "无法自动标准化": "Cannot normalize automatically",
    "无法访问此项目的原始数据目录。请重新选择该项目的数据文件，或联系管理员检查存储位置。": "The project's raw data directory is not accessible. Re-select the project's data files, or ask an administrator to check the storage location.",
    "无法运行：": "Cannot run:",
    "映射来源：": "Mapping source:",
    "显著性碎石图 Scree Plot": "Significance scree plot",
    "最低 junction 支持读数": "Minimum junction-support reads",
    "最低有效样本数": "Minimum informative samples",
    "有效事件": "Valid events",
    "未分配项 → 第一组": "Unassigned → group 1",
    "未分配项 → 第二组": "Unassigned → group 2",
    "未分组": "Ungrouped",
    "未安装": "Not installed",
    "未知阶段": "Unknown stage",
    "未能从这些文件中识别出可分析的剪接事件表。": "No analyzable splicing event table could be identified in these files.",
    "未连接": "Not connected",
    "未配置": "Not configured",
    "条服务错误，见下方说明": "service errors, see below",
    "条肽段（8–30 aa）": "peptides (8–30 aa)",
    "查看或调整逐样本分组": "Review or adjust per-sample groups",
    "标准化": "Standardization",
    "标准化中…": "Standardizing…",
    "标准化失败：": "Standardization failed:",
    "标准化预览（前 5 行）": "Normalized preview (first 5 rows)",
    "样本": "Samples",
    "样本分组确认": "Confirm sample groups",
    "样本表": "Sample table",
    "检查失败": "Check failed",
    "检查失败：": "Check failed:",
    "检查结果": "Check results",
    "检测到": "Detected",
    "模型映射": "LLM mapping",
    "模型正在选择工具…": "The model is choosing a tool…",
    "正在上传": "Uploading",
    "正在上传和分析…": "Uploading and analyzing…",
    "正在使用当前项目数据分析…": "Analyzing with the current project's data…",
    "正在保存…": "Saving…",
    "正在加载等位基因参考表…": "Loading the allele reference table…",
    "正在审计…": "Auditing…",
    "正在打包…": "Packaging…",
    "正在执行阶段": "Running stage",
    "正在整理成果文件夹…": "Assembling the results folder…",
    "正在检查项目数据…": "Checking project data…",
    "正在生成候选肽并查询 IEDB（": "Generating candidate peptides and querying IEDB (",
    "正在读取项目数据并生成候选肽，预测可能需要数十秒…": "Reading project data and generating candidate peptides; prediction may take tens of seconds…",
    "正在调用预测服务（": "Calling the prediction service (",
    "正在运行 Docker，耗时取决于输入大小，请勿关闭程序…": "Docker is running; duration depends on input size, please keep the app open…",
    "正在连接 MCP 服务器…": "Connecting to MCP servers…",
    "正在通过 MCP 调用": "Calling via MCP",
    "正常对照设计": "Normal control design",
    "正常组织表达表文件名": "Normal tissue expression table file name",
    "没有匹配的页面，试试「报告」或「设置」。": "No matching page. Try \\"Report\\" or \\"Settings\\".",
    "没有每样本 PSI 数据，无法生成真实的样本箱线图或热图。": "No per-sample PSI data, so a real sample box plot or heatmap cannot be produced.",
    "注释版本": "Annotation release",
    "流程已停止或完成": "The pipeline has stopped or finished",
    "火山图 Volcano Plot": "Volcano plot",
    "点下方「从本机添加编码序列表」就能直接补上，不用重新跑整个分析。": "Use \\"Add a coding-sequence table from this computer\\" below to fill the gap without re-running the whole analysis.",
    "点击移除": "Click to remove",
    "点左侧按钮从本机添加，或重新上传项目时把它一起放进去。": "Use the button on the left to add it from this computer, or include it the next time you upload the project.",
    "状态：": "Status:",
    "理由：": "Reason:",
    "生成候选肽失败": "Failed to generate candidate peptides",
    "用时": "Elapsed",
    "目录中没有找到华大逐样本剪接表（如 OC_001.SE.xls）": "No per-sample BGI splicing table (e.g. OC_001.SE.xls) found in this directory",
    "相对于项目上传目录的文件路径": "Path relative to the project upload directory",
    "确定性规则": "Deterministic rules",
    "确认分组并生成探索性表": "Confirm groups and generate the exploratory table",
    "确认并执行阶段": "Confirm and run stage",
    "确认支持读数为 junction 读数": "Confirm support reads are junction reads",
    "确认输入为已量化事件": "Confirm the input is quantified events",
    "类型 × 显著性堆叠图": "Type × significance stacked plot",
    "粘贴你的 API Key": "Paste your API key",
    "结果目录：": "Results directory:",
    "结果：": "Result:",
    "编码序列表：已自动识别": "Coding-sequence table: detected",
    "编码序列表：暂未找到": "Coding-sequence table: not found yet",
    "置信度": "Confidence",
    "肽段": "Peptide",
    "肿瘤表达及复现率表文件名": "Tumor expression and recurrence table file name",
    "能力信息加载失败": "Failed to load capability information",
    "能力信息加载失败：": "Failed to load capability information:",
    "自动猜测结果，确认后以后不再询问。": "Automatically guessed; confirm once and it will not ask again.",
    "自动识别": "Auto-detect",
    "行": "rows",
    "行 ·": "rows ·",
    "行无效输入": "invalid input lines",
    "规则回退": "Rule fallback",
    "规则映射": "Rule mapping",
    "评分分解堆叠图 Decomposition": "Score decomposition stacked plot",
    "请为每个样本选择分组，并确保两组都有样本。": "Assign a group to every sample and make sure both groups are non-empty.",
    "请先在上方填写 HLA 型别。": "Enter the HLA alleles above first.",
    "请先补全映射": "Complete the mapping first",
    "请先输入至少一条 8–30 aa 的候选肽序列。": "Enter at least one candidate peptide of 8–30 aa.",
    "请先选择已上传数据的项目，或选择文件进行独立分析。": "Select a project with uploaded data, or choose files for a standalone analysis.",
    "请先选择项目。": "Select a project first.",
    "请先选择项目和编码序列表。": "Select a project and a coding-sequence table first.",
    "请填写已知证据并开始审计。": "Fill in the known evidence and start the audit.",
    "请填写新审计的证据，再点击开始阶段 0。": "Fill in the new audit evidence, then start stage 0.",
    "请映射 FDR 或 p 值，否则无法筛选显著事件。": "Map FDR or a p-value, otherwise significant events cannot be filtered.",
    "请映射 ΔPSI，或同时映射两组平均 PSI。": "Map ΔPSI, or map both group mean PSI values.",
    "请核对每个样本的分组，确认后开始分析。": "Verify each sample's group, then start the analysis.",
    "请至少填写一个 HLA 型别，或点击常用面板快速填充。": "Enter at least one HLA allele, or use a common panel.",
    "请至少映射基因符号或基因 ID。": "Map at least the gene symbol or gene ID.",
    "调用中…": "Calling…",
    "调用失败：": "Call failed:",
    "调用异常：": "Call error:",
    "转录本注释 GTF 文件": "Transcript annotation GTF file",
    "输入数据类型": "Input data type",
    "输出目录：": "Output directory:",
    "还没有可用的编码序列表。点第一步下方的「从本机添加编码序列表」补上，再回来生成。": "No coding-sequence table available yet. Add one with \\"Add a coding-sequence table from this computer\\" under step 1, then come back to generate.",
    "还没有选择项目。请先创建或选择一个项目，再回来检查。": "No project selected. Create or select one, then come back to check.",
    "连接中…": "Connecting…",
    "连接失败": "Connection failed",
    "连接方式：": "Connection:",
    "配对正常蛋白 FASTA 文件名": "Matched normal protein FASTA file name",
    "错误": "Error",
    "队列构成图 Cohort QC": "Cohort composition",
    "阶段": "Stage",
    "需要一份含 event_id、reference_cds、altered_cds、junction_nt 四列的表，文件名随意。": "Needs a table with event_id, reference_cds, altered_cds, and junction_nt columns; the file name does not matter.",
    "项目：": "Project:",
    "预测失败": "Prediction failed",
    "预测完成：候选": "Prediction complete: candidates",
    "高": "high",
    "中": "medium",
    "低": "low",
    "（无描述）": "(no description)",
    "（当前匹配": "(currently matching",
    "（显示前": "(showing first",
    "（未提供，已根据样本名推断分组）": "(not provided; groups inferred from sample names)",
    "（未连接）": "(not connected)",
    "（空列名）": "(empty column name)",
    "（请选择）": "(select)",
    "（还没有可用的编码序列表）": "(no coding-sequence table available yet)",
    "，列：": ", columns:",
    "，可在下拉里切换。": "; switch in the dropdown.",
    "，失败": ", failed",
    "，忽略": ", ignored",
    "，留空保持不变": ", leave blank to keep",
    "；HLA 结合预测成功": "; HLA binding prediction succeeded",
    "；无服务错误": "; no service errors",
    "；有": "; there are",
    "；服务错误": "; service errors",
    "；未填写 HLA，只生成候选肽，未做任何外部预测。": "; no HLA alleles given, so only candidate peptides were generated and no external prediction was run.",
    "；超出单次上限的部分（": "; the part beyond the per-run limit (",
    "项没有选择。": "options not selected.",
    "个 HLA 型别，通常 30–90 秒，请勿关闭页面）…": "HLA alleles, usually 30–90 s, please keep the page open)…",
    "个 HLA）…": "HLA)…",
    "个文件看着像编码序列表，但没被采用（不影响下面的生成）：": "files look like coding-sequence tables but were not used (this does not affect generation):",
    "个；请分批预测。": "; please predict in batches.",
    "份（": "files (",
    "份，默认用": "files, defaulting to",
    "条": "items",
    "条，排序": "items, ranked",
    "条，预测": "peptides, predicted",
    "条，预测记录": "entries, prediction records",
    "条；证据分层": "entries; evidence tiers",
    "条；请分批预测。": "; please predict in batches.",
    "条）未预测，可缩小 CDS 表后重跑": ") were not predicted; shrink the CDS table and rerun",
    "条（详见 manifest 的 prediction_errors）": "(see prediction_errors in the manifest)",
    "条肽 ×": "peptides ×",
    "列": "column",
    "分数": "Score",
    "· 参考表 class1": "· reference table class1",
    "· 已知表位": "· known epitopes",
    "· 模型回退": "· model fallback",
    "ms · 失败": "ms · failed",
    "ΔPSI 覆盖": "ΔPSI coverage",
    "系统通知": "System notifications",
    "已归档": "Archived",
    "数据目录：": "Data directory: ",
    "列出本机已分析的 EpitopeRank 项目及 project_id。": "Lists analyzed EpitopeRank projects on this machine with their project_id.",
    "MHC-I 参考表：共 0 个等位基因": "MHC-I reference: 0 alleles",
  };

  var RULES = [
    function (s) {
      var p = "执行中: ";
      if (s.indexOf(p) === 0) return "Running: " + translateOne(s.slice(p.length));
      return null;
    },
    function (s) {
      var p = "请输入 ", q = " 的参数...";
      if (s.indexOf(p) === 0 && s.slice(-q.length) === q) {
        return "Enter parameters for " + translateOne(s.slice(p.length, s.length - q.length)) + "...";
      }
      return null;
    },
    function (s) {
      var p = "我想使用 ", q = " 技能";
      if (s.indexOf(p) === 0 && s.slice(-q.length) === q) {
        return "I want to use the " + translateOne(s.slice(p.length, s.length - q.length)) + " skill";
      }
      return null;
    },
    function (s) {
      var p = "共找到 ", q = " 篇相关文献";
      if (s.indexOf(p) === 0 && s.slice(-q.length) === q) {
        return s.slice(p.length, s.length - q.length) + " papers found";
      }
      return null;
    },
    function (s) {
      var p = "输入基因数: ", q = " | 显著条目数: ";
      var i = s.indexOf(p), j = s.indexOf(q);
      if (i === 0 && j > 0) {
        return "Input genes: " + s.slice(p.length, j) + " | Significant terms: " + s.slice(j + q.length);
      }
      return null;
    },
    function (s) {
      var p = "正在加载 ", q = " 的信息...";
      if (s.indexOf(p) === 0 && s.slice(-q.length) === q) {
        return "Loading information for " + s.slice(p.length, s.length - q.length) + "...";
      }
      return null;
    },
    function (s) {
      var p = "未找到 ", q = " 的剪接事件";
      if (s.indexOf(p) === 0 && s.slice(-q.length) === q) {
        return "No splicing events found for " + s.slice(p.length, s.length - q.length);
      }
      return null;
    },
    function (s) {
      var p = "报告生成失败 (", q = ")";
      if (s.indexOf(p) === 0 && s.slice(-q.length) === q) {
        return "Report generation failed (" + s.slice(p.length, s.length - q.length) + ")";
      }
      return null;
    },
    function (s) {
      var p = "API 错误: ";
      if (s.indexOf(p) === 0) return "API error: " + s.slice(p.length);
      return null;
    },
    function (s) {
      var p = "上传失败 (";
      if (s.indexOf(p) === 0) return "Upload failed (" + s.slice(p.length);
      return null;
    },
    function (s) {
      var p = "分析失败 (";
      if (s.indexOf(p) === 0) return "Analysis failed (" + s.slice(p.length);
      return null;
    },
    function (s) {
      var p = " 分析失败: ";
      if (s.indexOf(p) === 0) return " Analysis failed: " + s.slice(p.length);
      return null;
    },
    function (s) {
      var p = " 执行出错: ";
      if (s.indexOf(p) === 0) return " Execution error: " + s.slice(p.length);
      return null;
    },
    function (s) {
      var p = "操作失败：";
      if (s.indexOf(p) !== 0) return null;
      var out = "Operation failed: " + s.slice(p.length);
      return out
        .split("请检查：").join("Please check: ")
        .split("文件格式是否正确").join("whether the file format is correct")
        .split("文件大小是否过大").join("whether the file is too large")
        .split("网络连接是否正常").join("whether the network connection is working");
    },
    function (s) {
      var p = "分析请求失败：";
      if (s.indexOf(p) !== 0) return null;
      var out = "Analysis request failed: " + s.slice(p.length);
      var q = "（分析可能仍在后台运行，请稍后刷新查看）";
      if (out.slice(-q.length) === q) {
        out = out.slice(0, out.length - q.length) + " (the analysis may still be running in the background; refresh later)";
      }
      return out;
    }
  ];

  // 动态拼接文案（含数字/用户名等），用正则匹配后套模板。
  var PATTERN_RULES = [
    [/^共 ([\\d,]+) 个事件 · 每页 ([\\d,]+) 条 · 已按(.+?)排序$/, "About $1 events · $2 per page · sorted by $3"],
    [/^事件 ([\\d,]+)$/, "Events $1"],
    [/^显著 ([\\d,]+)$/, "Significant $1"],
    [/^·\\s*数据库 ([\\d.,]+ MB)$/, "· Database $1"],
    [/^(\\S+) · (.+?) · 输入格式 (\\S+) · ([\\d,]+) 个事件 \\/ ([\\d,]+) 个显著$/, "$1 · $2 · input $3 · $4 events / $5 significant"],
    [/^MHC-I 参考表：共 ([\\d,]+) 个等位基因（显示前 ([\\d,]+)）$/, "MHC-I reference table: $1 alleles (showing first $2)"],
    [/^IEDB 在线 · MHCflurry 未安装 · 参考表 class1 ([\\d,]+) \\/ class2 ([\\d,]+) · 已知表位 ([\\d,]+)$/, "IEDB online · MHCflurry not installed · reference class1 $1 / class2 $2 · known epitopes $3"],
    [/^IEDB 在线 · MHCflurry 已安装 · 参考表 class1 ([\\d,]+) \\/ class2 ([\\d,]+) · 已知表位 ([\\d,]+)$/, "IEDB online · MHCflurry installed · reference class1 $1 / class2 $2 · known epitopes $3"],
    [/^当前项目：(.+?)。将读取项目目录中的事件表和编码序列对照表。$/, "Current project: $1. Event tables and the coding-sequence table will be read from the project directory."],
    [/^(\\d+) \\/ (\\d+) 已连接$/, "$1 / $2 connected"],
    [/^连接方式：(.+)$/, "Connection: $1"],
    [/^数据目录：(.+)$/, "Data directory: $1"],
    [/^已打包（(.+?) MB）：(.+)$/, "Packaged ($1 MB): $2"],
    [/^正在执行阶段 (.+)$/, "Running stage $1"],
    [/^项目「(.+?)」的数据库记录、图表与报告目录都会被移除，且无法撤销。原始输入数据不会被删除。$/, "The database record, figures, and report folder for “$1” will be removed. This cannot be undone. Raw input data is not deleted."],
    [/^删除失败：HTTP (\\d+)$/, "Delete failed: HTTP $1"],
    [/^([\\d,]+) 行无效输入$/, "$1 invalid input lines"],
    [/^已保存，按这套映射可为 ([\\d,]+) 行样本生成肽。$/, "Saved; this mapping can be used for $1 sample rows."],
    [/^(.+?) · (.+?) · ([\\d,]+) 工具(（未连接）)?$/, "$1 · $2 · $3 tools$4"],
  ];

  function applyPatternRules(value) {
    for (var i = 0; i < PATTERN_RULES.length; i++) {
      var pattern = PATTERN_RULES[i][0];
      if (!pattern.test(value)) continue;
      return value.replace(pattern, PATTERN_RULES[i][1])
        .replace(/基因名/g, "gene name")
        .replace(/内置/g, "built-in")
        .replace(/（未连接）/g, " (not connected)");
    }
    return null;
  }

  var ATTRS = ["placeholder", "title", "aria-label"];
  var NL2 = String.fromCharCode(10, 10);
  var originalText = new WeakMap();
  var originalAttrs = new WeakMap();
  var lang = "zh";
  try {
    var saved = localStorage.getItem("epitoperank_lang");
    if (saved === "en" || saved === "zh" || saved === "zh-Hant") lang = saved;
  } catch (e) {}

  function replaceTrimmed(text, out) {
    var trimmed = text.trim();
    var i = text.indexOf(trimmed);
    if (i < 0) return text;
    return text.slice(0, i) + out + text.slice(i + trimmed.length);
  }

  function translateOne(text) {
    if (lang === "zh-Hant") return toTraditional(text);
    var trimmed = text.trim();
    if (!trimmed) return text;
    // 字典键统一按「空白归一化后的单行文本」查：HTML 里跨行书写的长句、
    // 以及带缩进/换行的模板文本都能命中同一个键。
    var key = trimmed.replace(/\\s+/g, " ");
    if (Object.prototype.hasOwnProperty.call(DICT, key)) {
      return replaceTrimmed(text, DICT[key]);
    }
    if (key !== trimmed && Object.prototype.hasOwnProperty.call(DICT, trimmed)) {
      return replaceTrimmed(text, DICT[trimmed]);
    }
    for (var i = 0; i < RULES.length; i++) {
      var out = RULES[i](key);
      if (!out && key !== trimmed) out = RULES[i](trimmed);
      if (out) return replaceTrimmed(text, out);
    }
    var patterned = applyPatternRules(key);
    if (!patterned && key !== trimmed) patterned = applyPatternRules(trimmed);
    if (patterned) return replaceTrimmed(text, patterned);
    return text;
  }

  function translateText(text) {
    if (lang === "zh-Hant") return toTraditional(text);
    if (text.indexOf(NL2) === -1) return translateOne(text);
    return text.split(NL2).map(translateOne).join(NL2);
  }

  function translateTextNode(node) {
    var parent = node.parentElement;
    if (!parent || parent.closest("script,style,[data-no-i18n]")) return;
    var original = originalText.get(node);
    if (original === undefined) {
      original = node.nodeValue;
      originalText.set(node, original);
    }
    var target = lang === "zh" ? original : translateText(original);
    if (node.nodeValue !== target) node.nodeValue = target;
  }

  function translateAttrs(el) {
    if (el.closest("script,style,[data-no-i18n]")) return;
    var store = originalAttrs.get(el);
    if (!store) {
      store = {};
      originalAttrs.set(el, store);
    }
    for (var i = 0; i < ATTRS.length; i++) {
      var name = ATTRS[i];
      if (!el.hasAttribute(name)) continue;
      if (!Object.prototype.hasOwnProperty.call(store, name)) {
        store[name] = el.getAttribute(name);
      }
      el.setAttribute(name, lang === "zh" ? store[name] : translateOne(store[name]));
    }
  }

  function walk(root) {
    if (!root) return;
    if (root.nodeType === 3) {
      translateTextNode(root);
      return;
    }
    if (root.nodeType !== 1 && root.nodeType !== 9 && root.nodeType !== 11) return;
    if (root.nodeType === 1) translateAttrs(root);
    var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT, null);
    var node = walker.nextNode();
    while (node) {
      if (node.nodeType === 3) translateTextNode(node);
      else translateAttrs(node);
      node = walker.nextNode();
    }
  }

  var observer = new MutationObserver(function (mutations) {
    for (var i = 0; i < mutations.length; i++) {
      var m = mutations[i];
      if (m.type === "characterData") {
        var node = m.target;
        var stored = originalText.get(node);
        var expected = stored === undefined ? undefined : (lang === "zh" ? stored : translateText(stored));
        if (node.nodeValue === expected) continue;
        originalText.set(node, node.nodeValue);
        translateTextNode(node);
      } else if (m.type === "attributes") {
        var el = m.target;
        if (!el || el.nodeType !== 1) continue;
        var store = originalAttrs.get(el);
        if (!store) {
          store = {};
          originalAttrs.set(el, store);
        }
        var name = m.attributeName;
        var current = el.getAttribute(name);
        var wanted = store[name] === undefined ? undefined : (lang === "zh" ? store[name] : translateOne(store[name]));
        if (current === wanted) continue;
        store[name] = current;
        translateAttrs(el);
      } else {
        for (var j = 0; j < m.addedNodes.length; j++) walk(m.addedNodes[j]);
      }
    }
  });

  function translateTitle() {
    var el = document.querySelector("title");
    if (!el) return;
    if (!el.dataset.zh) el.dataset.zh = el.textContent;
    el.textContent = lang === "zh" ? el.dataset.zh : translateOne(el.dataset.zh);
  }

  function applyLanguage(next) {
    lang = next === "en" || next === "zh-Hant" ? next : "zh";
    document.documentElement.lang = lang === "en" ? "en" : (lang === "zh-Hant" ? "zh-Hant" : "zh-CN");
    try {
      localStorage.setItem("epitoperank_lang", lang);
      document.cookie = "epitoperank_lang=" + lang + "; path=/; max-age=31536000; SameSite=Lax";
    } catch (e) {}
    var buttons = document.querySelectorAll(".lang-toggle button");
    for (var i = 0; i < buttons.length; i++) {
      var active = buttons[i].getAttribute("data-lang") === lang;
      buttons[i].classList.toggle("active", active);
      buttons[i].setAttribute("aria-pressed", active ? "true" : "false");
    }
    walk(document.body);
    translateTitle();
    try {
      document.dispatchEvent(new CustomEvent("epitoperank:language", { detail: { lang: lang } }));
    } catch (e) {}
  }

  window.__epitoperankI18n = {
    apply: applyLanguage,
    translate: translateOne,
    translateText: translateText,
    getLang: function () { return lang; }
  };

  // 兜底：任何遗漏的 alert() 都转成应用内 toast，不再弹原生对话框。
  // 业务代码已显式调用 AppNotify；这里只覆盖第三方库或历史遗留调用。
  window.alert = function (message) {
    if (window.AppNotify) {
      window.AppNotify.toast(String(message), "info");
      return;
    }
    var notice = document.createElement("div");
    notice.setAttribute("role", "status");
    notice.textContent = lang === "zh" ? String(message) : translateText(String(message));
    notice.style.cssText = "position:fixed;right:24px;bottom:24px;z-index:99999;max-width:520px;padding:16px 20px;border-radius:var(--radius);background:#12313b;color:#fff;box-shadow:0 12px 36px #0008;white-space:pre-line;font-size:14px;cursor:pointer";
    notice.onclick = function () { notice.remove(); };
    document.body.appendChild(notice);
    setTimeout(function () { notice.remove(); }, 8000);
  };
  var nativeConfirm = window.confirm.bind(window);
  window.confirm = function (message) {
    return nativeConfirm(lang === "zh" ? String(message) : translateText(String(message)));
  };

  function init() {
    var buttons = document.querySelectorAll(".lang-toggle button");
    for (var i = 0; i < buttons.length; i++) {
      buttons[i].addEventListener("click", function () {
        applyLanguage(this.getAttribute("data-lang"));
      });
      // 悬停/聚焦到「繁體中文」就先偷偷下载，点击时基本已经就绪。
      if (buttons[i].getAttribute("data-lang") === "zh-Hant") {
        buttons[i].addEventListener("pointerenter", ensureTraditionalConverter, { once: true });
        buttons[i].addEventListener("focus", ensureTraditionalConverter, { once: true });
      }
    }
    observer.observe(document.body, {
      childList: true,
      subtree: true,
      characterData: true,
      attributes: true,
      attributeFilter: ATTRS
    });
    applyLanguage(lang);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
</script>

<script>
const reducedMotionQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
let workspaceAnimation = null;
function motionIsEnabled() { return !reducedMotionQuery.matches && localStorage.getItem('epitoperank.motion') !== 'off'; }
function syncMotionPreference() {
  const enabled = motionIsEnabled();
  document.body.classList.toggle('motion-paused', !enabled);
  const button = document.getElementById('motion-toggle');
  button.textContent = reducedMotionQuery.matches ? '动态：系统关闭' : enabled ? '动态：开' : '动态：关';
  button.setAttribute('aria-pressed', String(enabled));
  button.disabled = reducedMotionQuery.matches;
  if (!enabled) {
    document.getAnimations().forEach(animation => animation.cancel());
    document.querySelectorAll('.press-wave').forEach(wave => wave.remove());
  }
}
function toggleMotion() { localStorage.setItem('epitoperank.motion', motionIsEnabled() ? 'off' : 'on'); syncMotionPreference(); }
function syncFluidMarker() {
  const sidebar = document.getElementById('app-navigation');
  const active = sidebar.querySelector('.nav-item.active');
  const marker = sidebar.querySelector('.nav-fluid-marker');
  if (!active || !marker) return;
  marker.style.transform = 'translateY(' + (active.getBoundingClientRect().top - sidebar.getBoundingClientRect().top + sidebar.scrollTop) + 'px)';
  marker.style.height = active.offsetHeight + 'px';
}
function animateWorkspace(previous, current) {
  if (workspaceAnimation) workspaceAnimation.cancel();
  if (!motionIsEnabled() || previous === current) return;
  const order = Array.from(document.querySelectorAll('.nav-item')).map(item => item.dataset.page);
  const direction = order.indexOf(current) >= order.indexOf(previous) ? 1 : -1;
  workspaceAnimation = document.getElementById('page-' + current).animate([
    {opacity:.55, transform:'translateY(' + direction * 9 + 'px)'},
    {opacity:1, transform:'translateY(0)'}
  ], {duration:230, easing:'cubic-bezier(.16,1,.3,1)'});
}
let quickReturnFocus = null;
function openQuickSwitch() {
  const dialog = document.getElementById('quick-dialog');
  if (dialog.open) return;
  quickReturnFocus = document.activeElement;
  const results = document.getElementById('quick-results');
  results.replaceChildren();
  document.querySelectorAll('.nav-item').forEach(item => {
    const button = document.createElement('button');
    button.type = 'button'; button.className = 'quick-result'; button.textContent = item.textContent.trim();
    if (item.dataset.page === state.currentPage) button.setAttribute('aria-current','page');
    button.onclick = () => { dialog.close(); if (item.dataset.detail) openProjectDetail(); else navigateTo(item.dataset.page); };
    results.appendChild(button);
  });
  const empty = document.createElement('p'); empty.className = 'quick-empty'; empty.id = 'quick-empty'; empty.textContent = '没有匹配的页面，试试「报告」或「设置」。'; empty.hidden = true; results.appendChild(empty);
  document.getElementById('quick-search').value = '';
  dialog.showModal(); document.getElementById('quick-search').focus();
}
function closeQuickSwitch() { document.getElementById('quick-dialog').close(); if (quickReturnFocus) quickReturnFocus.focus(); }
function filterQuickSwitch() {
  const query = document.getElementById('quick-search').value.trim().toLocaleLowerCase();
  let matches = 0;
  document.querySelectorAll('.quick-result').forEach(button => { button.hidden = !button.textContent.toLocaleLowerCase().includes(query); if (!button.hidden) matches++; });
  document.getElementById('quick-empty').hidden = matches > 0;
}
document.addEventListener('keydown', event => {
  if (event.key === 'Escape' && document.body.classList.contains('detail-open')) closeProjectDetail();
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k' && document.getElementById('upload-modal').style.display !== 'flex' && !document.getElementById('ingest-modal').classList.contains('open')) { event.preventDefault(); openQuickSwitch(); }
  if (event.key === 'ArrowDown' && document.getElementById('quick-dialog').open && event.target.id === 'quick-search') { const first = document.querySelector('.quick-result:not([hidden])'); if (first) { event.preventDefault(); first.focus(); } }
});
document.addEventListener('pointerdown', event => {
  const button = event.target.closest('.btn');
  if (!button || button.disabled || !motionIsEnabled()) return;
  const box = button.getBoundingClientRect(), wave = document.createElement('span');
  wave.className = 'press-wave'; wave.setAttribute('aria-hidden','true');
  wave.style.left = (event.clientX - box.left) + 'px'; wave.style.top = (event.clientY - box.top) + 'px';
  button.appendChild(wave); wave.addEventListener('animationend', () => wave.remove(), {once:true});
});
let lightFrame = 0;
const liquidHero = document.querySelector('.start-guide');
liquidHero.addEventListener('pointermove', event => {
  if (!motionIsEnabled() || event.pointerType !== 'mouse' || lightFrame) return;
  const x = event.clientX, y = event.clientY;
  lightFrame = requestAnimationFrame(() => {
    const box = liquidHero.getBoundingClientRect();
    liquidHero.style.setProperty('--light-x', (x - box.left) + 'px'); liquidHero.style.setProperty('--light-y', (y - box.top) + 'px'); lightFrame = 0;
  });
});
liquidHero.addEventListener('pointerleave', () => { if (lightFrame) cancelAnimationFrame(lightFrame); lightFrame = 0; liquidHero.style.removeProperty('--light-x'); liquidHero.style.removeProperty('--light-y'); });
reducedMotionQuery.addEventListener('change', syncMotionPreference);
window.addEventListener('resize', () => { document.querySelector('main').inert = window.innerWidth <= 768 && document.body.classList.contains('navigation-open'); syncFluidMarker(); document.getElementById('app-navigation').inert = window.innerWidth <= 768 && !document.body.classList.contains('navigation-open'); });
new ResizeObserver(syncFluidMarker).observe(document.getElementById('app-navigation'));
syncMotionPreference(); syncFluidMarker();
document.getElementById('app-navigation').inert = window.innerWidth <= 768;
</script>

<div id="toast-stack" role="region" aria-label="系统通知" aria-live="polite" aria-relevant="additions"></div>
<dialog id="app-dialog" class="app-dialog" aria-labelledby="app-dialog-title"></dialog>
<script>
// Track actual requests initiated by a click without changing request outcomes.
(() => {
  const indicator = document.createElement('div');
  indicator.id = 'request-indicator'; indicator.hidden = true;
  indicator.setAttribute('role', 'status'); indicator.setAttribute('aria-label', '正在加载');
  document.body.append(indicator);
  let activeButton = null, pending = 0;
  const counts = new WeakMap();
  document.addEventListener('click', event => {
    activeButton = event.target.closest('button');
    queueMicrotask(() => { activeButton = null; });
  }, true);
  const originalFetch = window.fetch;
  window.fetch = async function(...args) {
    const button = activeButton;
    if (button) { counts.set(button, (counts.get(button) || 0) + 1); button.setAttribute('aria-busy','true'); }
    pending++; indicator.hidden = false;
    try { return await originalFetch.apply(this,args); }
    finally {
      if (--pending === 0) indicator.hidden = true;
      if (button) { const remaining = counts.get(button) - 1; counts.set(button,remaining); if (!remaining) button.removeAttribute('aria-busy'); }
    }
  };
})();
</script>
</body>
</html>"""


# 中文备注：渲染单页 Web 界面 HTML（参数：title）
def render(title: str = "EpitopeRank") -> HTMLResponse:
    """Render the modern EpitopeRank web UI."""
    return HTMLResponse(content=_HTML.replace("__TITLE__", title))
