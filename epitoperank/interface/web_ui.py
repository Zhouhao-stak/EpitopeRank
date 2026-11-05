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
  --font-sans: ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", Roboto, "Helvetica Neue", Arial, sans-serif;
  --font-mono: ui-monospace, "SF Mono", Monaco, "Cascadia Code", "Roboto Mono", Consolas, monospace;
  --space-1: 4px; --space-2: 8px; --space-3: 12px; --space-4: 16px;
  --space-5: 24px; --space-6: 32px; --space-7: 48px; --space-8: 64px;
  --shadow-sm: 0 4px 16px rgba(0, 0, 0, .18);
  --shadow: 0 12px 30px rgba(0, 0, 0, .24);
  --shadow-lg: 0 22px 70px rgba(0, 0, 0, .32);
  --radius: 12px;
}

* { box-sizing: border-box; margin: 0; padding: 0; }
html { background: var(--bg); }
body { font-family: var(--font-sans); background: var(--bg); color: var(--text); line-height: 1.6; font-size: 15px; -webkit-font-smoothing: antialiased; }
body::before { content: ""; position: fixed; inset: 0; pointer-events: none; z-index: -1; background: radial-gradient(circle at 82% -8%, rgba(94,234,212,.14), transparent 32%), radial-gradient(circle at 5% 100%, rgba(183,227,106,.08), transparent 28%), linear-gradient(120deg, rgba(255,255,255,.015) 1px, transparent 1px); background-size: auto, auto, 34px 34px; }
.app { display: flex; min-height: 100vh; }
.sidebar { width: 264px; background: rgba(7, 21, 30, .88); border-right: 1px solid var(--border); position: fixed; top: 0; left: 0; bottom: 0; overflow-y: auto; z-index: 100; backdrop-filter: blur(18px); }
.main { margin-left: 264px; flex: 1; min-height: 100vh; background: transparent; }
.topbar { height: 72px; background: rgba(7, 21, 30, .72); border-bottom: 1px solid rgba(36,73,87,.8); display: flex; align-items: center; justify-content: space-between; padding: 0 var(--space-6); position: sticky; top: 0; z-index: 50; backdrop-filter: blur(18px); }
.content { padding: 30px 34px 60px; max-width: 1600px; margin: 0 auto; }

.brand { padding: 28px 22px 24px; border-bottom: 1px solid var(--border); position: relative; }
.brand::before { content: ""; display: block; width: 34px; height: 34px; margin-bottom: 16px; border-radius: 11px; background: radial-gradient(circle at 30% 25%, #e7fff8 0 8%, var(--accent) 9% 35%, #157f83 36% 70%, #0b303a 71%); box-shadow: 0 0 0 5px rgba(94,234,212,.08), 0 0 32px rgba(94,234,212,.23); }
.brand-name { font-size: 21px; font-weight: 750; color: var(--white); letter-spacing: -.4px; }
.brand-tagline { font-size: 10px; color: var(--accent); margin-top: 4px; text-transform: uppercase; letter-spacing: 1.7px; font-weight: 700; }
.nav-section { padding: 22px 0 0; }
.nav-label { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 1.7px; color: var(--text-muted); padding: 0 22px; margin-bottom: 9px; }
.nav-item { display: flex; align-items: center; gap: 11px; padding: 11px 20px; margin: 3px 12px 3px 0; color: var(--text-secondary); cursor: pointer; transition: all .2s ease; font-size: 14px; font-weight: 600; border-left: 2px solid transparent; border-radius: 0 9px 9px 0; }
.nav-item:hover { background: rgba(94,234,212,.07); color: var(--white); }
.nav-item.active { background: linear-gradient(90deg, rgba(94,234,212,.16), rgba(94,234,212,.04)); color: var(--white); border-left-color: var(--accent); box-shadow: inset 0 0 24px rgba(94,234,212,.04); }

.card, .chart-container, .filters { background: linear-gradient(145deg, rgba(17,43,54,.92), rgba(10,29,39,.92)); border: 1px solid var(--border); border-radius: var(--radius); padding: var(--space-5); box-shadow: var(--shadow-sm); }
.card { transition: border-color .2s ease, transform .2s ease, box-shadow .2s ease; }
.card:hover { border-color: rgba(94,234,212,.48); transform: translateY(-1px); box-shadow: var(--shadow); }
.card-title { font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: .9px; color: var(--text-secondary); }
.grid { display: grid; gap: 18px; }
.grid-2 { grid-template-columns: repeat(2, 1fr); }
.grid-3 { grid-template-columns: repeat(3, 1fr); }
.grid-4 { grid-template-columns: repeat(4, 1fr); }

.status { display: inline-flex; align-items: center; gap: 8px; font-size: 12px; font-weight: 700; padding: 5px 10px; border-radius: 999px; border: 1px solid transparent; }
.status-running { background: rgba(94,234,212,.12); color: var(--accent); border-color: rgba(94,234,212,.22); }
.status-completed { background: rgba(183,227,106,.12); color: var(--secondary); border-color: rgba(183,227,106,.22); }
.status-waiting { background: rgba(118,146,157,.12); color: var(--text-secondary); border-color: rgba(118,146,157,.2); }
.status-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--text-muted); box-shadow: 0 0 0 3px rgba(118,146,157,.12); }
.status-running .status-dot { background: var(--accent); box-shadow: 0 0 0 3px rgba(94,234,212,.12), 0 0 12px var(--accent); }
.status-completed .status-dot { background: var(--secondary); box-shadow: 0 0 0 3px rgba(183,227,106,.12); }

.btn { display: inline-flex; align-items: center; justify-content: center; gap: var(--space-2); padding: 10px 18px; font-size: 13px; font-weight: 700; border-radius: 9px; border: 1px solid transparent; cursor: pointer; transition: all .2s ease; font-family: var(--font-sans); }
.btn:focus-visible, input:focus-visible, select:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.btn-primary { background: linear-gradient(135deg, #6af3d9, #34bdb2); color: #062027; border-color: #6af3d9; box-shadow: 0 6px 20px rgba(94,234,212,.18); }
.btn-primary:hover { filter: brightness(1.08); transform: translateY(-1px); box-shadow: 0 9px 25px rgba(94,234,212,.28); }
.btn-secondary { background: rgba(17,43,54,.55); color: var(--text-secondary); border-color: var(--border); }
.btn-secondary:hover { color: var(--white); border-color: var(--accent); background: rgba(94,234,212,.08); }
.btn-sm { padding: 7px 13px; font-size: 12px; }

.neo-tabs { display: flex; gap: 8px; flex-wrap: wrap; margin: 16px 0 12px; }
.neo-tab.active { background: rgba(94,234,212,.14); border-color: var(--accent); color: var(--accent); }
.neo-result-body { max-height: 58vh; overflow: auto; border: 1px solid var(--border); border-radius: var(--radius); background: rgba(8,25,34,.6); }
.neo-result-body table { font-size: 12px; }
.neo-result-body th { position: sticky; top: 0; z-index: 1; background: #0d2430; white-space: nowrap; }
.neo-result-body td { white-space: nowrap; font-family: var(--font-mono); font-size: 12px; padding: 8px 12px; }
.neo-result-body pre { margin: 0; padding: 16px; font-size: 12px; line-height: 1.6; white-space: pre; color: var(--text-secondary); font-family: var(--font-mono); }
.neo-path { font-family: var(--font-mono); font-size: 11px; color: var(--text-muted); word-break: break-all; margin-top: 10px; }

.table-container { overflow-x: auto; border: 1px solid var(--border); border-radius: var(--radius); }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
thead { background: rgba(94,234,212,.06); }
th { text-align: left; padding: 11px 14px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .7px; color: var(--text-secondary); border-bottom: 1px solid var(--border); }
td { padding: 11px 14px; border-bottom: 1px solid rgba(36,73,87,.65); color: var(--text-secondary); }
tr:last-child td { border-bottom: none; }
tr:hover { background: rgba(94,234,212,.045); }

.pipeline { display: flex; flex-direction: column; gap: 12px; }
.pipeline-step { display: flex; align-items: center; gap: var(--space-4); padding: var(--space-4); background: rgba(12,32,43,.78); border: 1px solid var(--border); border-radius: 10px; cursor: pointer; transition: all .2s ease; }
.pipeline-step:hover { border-color: var(--accent); transform: translateX(2px); }
.pipeline-step.active { border-color: var(--accent); background: linear-gradient(90deg, rgba(94,234,212,.13), rgba(94,234,212,.03)); }
.pipeline-step.completed { border-color: rgba(183,227,106,.46); }
.step-number { width: 36px; height: 36px; border-radius: 11px; background: var(--surface-3); display: flex; align-items: center; justify-content: center; font-size: 14px; font-weight: 750; color: var(--text-secondary); flex-shrink: 0; }
.pipeline-step.active .step-number { background: var(--accent); color: #062027; }
.pipeline-step.completed .step-number { background: rgba(183,227,106,.18); color: var(--secondary); }
.step-info { flex: 1; }
.step-name { font-weight: 700; font-size: 14px; margin-bottom: var(--space-1); }
.step-desc { font-size: 13px; color: var(--text-muted); line-height: 1.5; }

.filters { display: flex; gap: var(--space-4); flex-wrap: wrap; margin-bottom: var(--space-5); }
.filter-group { display: flex; align-items: center; gap: var(--space-2); }
.filter-label { font-size: 11px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: .5px; }
.checkbox-group { display: flex; gap: var(--space-3); flex-wrap: wrap; }
.checkbox-label { display: flex; align-items: center; gap: var(--space-2); font-size: 13px; cursor: pointer; padding: 4px 8px; border-radius: 7px; color: var(--text-secondary); }
.checkbox-label:hover { background: rgba(94,234,212,.08); color: var(--white); }
input[type="checkbox"] { width: 16px; height: 16px; accent-color: var(--accent); cursor: pointer; }
.search-bar { display: flex; gap: var(--space-3); margin-bottom: var(--space-5); }
.search-input, input, select, textarea { flex: 1; padding: 10px 13px; border: 1px solid var(--border); border-radius: 9px; font-size: 14px; font-family: var(--font-sans); color: var(--text); background: rgba(8,25,34,.78); }
.search-input::placeholder, input::placeholder, textarea::placeholder { color: var(--text-muted); }
.search-input:focus, input:focus, select:focus, textarea:focus { outline: none; border-color: var(--accent); box-shadow: 0 0 0 3px rgba(94,234,212,.1); }
#upload-modal input, #project-name, #analysis-query { color: var(--text) !important; background: rgba(8,25,34,.9) !important; border-color: var(--border) !important; }
#upload-modal input::placeholder, #project-name::placeholder, #analysis-query::placeholder { color: var(--text-muted) !important; opacity: 1; }
select option { color: var(--text); background: var(--surface); }
input:-webkit-autofill, input:-webkit-autofill:hover, input:-webkit-autofill:focus { -webkit-text-fill-color: var(--text); -webkit-box-shadow: 0 0 0 1000px rgba(8,25,34,.9) inset; transition: background-color 9999s ease-out; }
.chart-container { margin-bottom: var(--space-5); }

.page { display: none; }
.page.active { display: block; animation: pageIn .24s ease-out; }
.hero-chip { padding: 7px 10px; border: 1px solid rgba(94,234,212,.26); border-radius: 999px; color: var(--text-secondary); background: rgba(94,234,212,.07); font-size: 11px; font-weight: 700; white-space: nowrap; }
.model-config-body { display: flex; flex-direction: column; gap: 10px; padding: 0 14px 14px; }
.model-config-body .cfg-row { display: flex; align-items: center; gap: 10px; }
.model-config-body .cfg-row label { flex: none; width: 88px; font-size: 12px; font-weight: 700; color: var(--text-secondary); }
.model-config-body .cfg-row input { flex: 1; padding: 8px 10px; font-size: 13px; }
.model-config-body .cfg-hint, .model-config-body .cfg-msg { font-size: 12px; line-height: 1.6; color: var(--text-muted); }
.model-config-body .cfg-msg.ok { color: var(--secondary); }
.model-config-body .cfg-msg.err { color: var(--danger); }

/* Smart-ingestion review dialog */
#ingest-modal { display: none; position: fixed; inset: 0; z-index: 1200; padding: 24px; background: rgba(3,12,17,.84); backdrop-filter: blur(10px); align-items: center; justify-content: center; }
#ingest-modal.open { display: flex; }
.ingest-panel { width: min(980px, 96vw); max-height: 90vh; display: flex; flex-direction: column; background: linear-gradient(160deg, var(--surface), #091b25); border: 1px solid var(--border); border-radius: 18px; box-shadow: var(--shadow-lg); overflow: hidden; }
.ingest-head { display: flex; align-items: flex-start; gap: 12px; padding: 20px 24px 16px; border-bottom: 1px solid var(--border); background: rgba(7,21,30,.72); }
.ingest-head .ingest-title { font-size: 20px; font-weight: 750; color: var(--white); letter-spacing: -.3px; }
.ingest-head .ingest-sub { margin-top: 4px; font-size: 12px; color: var(--text-muted); }
.ingest-close { margin-left: auto; flex: none; width: 32px; height: 32px; border-radius: 9px; border: 1px solid var(--border); background: rgba(8,25,34,.7); color: var(--text-secondary); font-size: 18px; line-height: 1; cursor: pointer; }
.ingest-close:hover { color: var(--white); border-color: var(--accent); }
.ingest-body { padding: 18px 24px 22px; overflow-y: auto; display: flex; flex-direction: column; gap: 16px; }
.ingest-trace { display: flex; gap: 8px; flex-wrap: wrap; }
.ingest-step { display: inline-flex; align-items: center; gap: 7px; padding: 6px 10px; border: 1px solid var(--border); border-radius: 999px; background: rgba(8,25,34,.55); font-size: 11px; font-weight: 650; color: var(--text-secondary); }
.ingest-step .dot { width: 7px; height: 7px; border-radius: 50%; background: var(--text-muted); }
.ingest-step.ok .dot { background: var(--secondary); box-shadow: 0 0 8px rgba(183,227,106,.5); }
.ingest-step.warn .dot { background: var(--warning); }
.ingest-step.error .dot { background: var(--danger); }
.ingest-step.running .dot { background: var(--accent); box-shadow: 0 0 8px rgba(94,234,212,.6); }
.ingest-step.skip { opacity: .62; }
.ingest-source { font-size: 12px; color: var(--text-muted); }
.ingest-stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
.ingest-stat { padding: 12px 14px; border: 1px solid var(--border); border-radius: 11px; background: rgba(8,25,34,.52); }
.ingest-stat .v { font-size: 22px; font-weight: 750; color: var(--white); line-height: 1.2; }
.ingest-stat .k { font-size: 10px; letter-spacing: .8px; text-transform: uppercase; color: var(--text-muted); margin-top: 3px; }
.ingest-files { font-size: 12px; color: var(--text-muted); line-height: 1.85; }
.ingest-files code { font-family: var(--font-mono); color: var(--text-secondary); background: rgba(94,234,212,.06); padding: 1px 5px; border-radius: 5px; }
.ingest-section-title { font-size: 11px; font-weight: 800; letter-spacing: 1.3px; text-transform: uppercase; color: var(--text-muted); margin-bottom: 8px; }
.ingest-map-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 9px 16px; }
.ingest-map-row { display: flex; align-items: center; gap: 9px; }
.ingest-map-row label { flex: none; width: 132px; font-size: 12px; font-weight: 650; color: var(--text-secondary); }
.ingest-map-row select { flex: 1; min-width: 0; padding: 7px 9px; font-size: 12px; border-radius: 8px; }
.ingest-map-row select.missing { border-color: rgba(243,189,114,.55); }
.ingest-issues { display: flex; flex-direction: column; gap: 6px; }
.ingest-issue { display: flex; gap: 8px; padding: 8px 10px; border-radius: 9px; font-size: 12px; line-height: 1.55; border: 1px solid var(--border); background: rgba(8,25,34,.45); color: var(--text-secondary); }
.ingest-issue .tag { flex: none; font-weight: 800; font-size: 10px; letter-spacing: .6px; padding: 2px 6px; border-radius: 5px; height: fit-content; }
.ingest-issue.error { border-color: rgba(251,113,133,.3); }
.ingest-issue.error .tag { background: rgba(251,113,133,.14); color: var(--danger); }
.ingest-issue.warning .tag { background: rgba(243,189,114,.14); color: var(--warning); }
.ingest-issue.info .tag { background: rgba(94,234,212,.12); color: var(--accent); }
.ingest-preview-table { max-height: 260px; overflow: auto; border: 1px solid var(--border); border-radius: 10px; }
.ingest-preview-table table { min-width: 620px; }
.ingest-privacy { font-size: 11px; color: var(--text-muted); line-height: 1.6; }
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
#event-detail-modal [style*="font-size: 32px"] { color: var(--accent) !important; }

/* MCP tool console */
.mcp-panel { margin-top: 22px; padding-top: 18px; border-top: 1px solid var(--border); display: flex; flex-direction: column; gap: 12px; }
.mcp-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
.mcp-title { font-size: 16px; font-weight: 750; color: var(--white); letter-spacing: -.2px; }
.mcp-sub { font-size: 11px; color: var(--text-muted); margin-top: 3px; letter-spacing: .4px; }
.mcp-badge { padding: 4px 9px; border-radius: 999px; font-size: 11px; font-weight: 750; border: 1px solid var(--border); color: var(--text-secondary); background: rgba(8,25,34,.6); white-space: nowrap; }
.mcp-badge.ok { color: var(--secondary); border-color: rgba(183,227,106,.35); background: rgba(183,227,106,.08); }
.mcp-badge.err { color: var(--danger); border-color: rgba(251,113,133,.35); background: rgba(251,113,133,.08); }
.mcp-field { display: flex; flex-direction: column; gap: 6px; }
.mcp-field > label { font-size: 11px; font-weight: 800; letter-spacing: .8px; text-transform: uppercase; color: var(--text-muted); }
.mcp-inline { display: flex; gap: 8px; align-items: center; }
.mcp-inline select { flex: 1; min-width: 0; }
.mcp-panel select, .mcp-panel textarea, .mcp-panel input[type="text"] { width: 100%; padding: 9px 11px; border: 1px solid var(--border); border-radius: 9px; background: rgba(8,25,34,.9); color: var(--text); font-family: inherit; font-size: 13px; }
.mcp-panel input[type="text"]::placeholder { color: var(--text-muted); }
.mcp-panel textarea { font-family: var(--font-mono); font-size: 12px; line-height: 1.55; resize: vertical; min-height: 86px; }
.mcp-desc { font-size: 12px; line-height: 1.6; color: var(--text-secondary); min-height: 18px; }
.mcp-hint { font-size: 11px; line-height: 1.5; color: var(--text-muted); word-break: break-all; }
.mcp-actions { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.mcp-result { margin: 0; padding: 12px; max-height: 300px; overflow: auto; border: 1px solid var(--border); border-radius: 10px; background: rgba(3,12,17,.75); color: var(--text-secondary); font-family: var(--font-mono); font-size: 11.5px; line-height: 1.55; white-space: pre-wrap; word-break: break-word; }
.mcp-result.err { color: var(--danger); }

@keyframes pageIn { from { opacity: .25; transform: translateY(4px); } to { opacity: 1; transform: translateY(0); } }
@keyframes fadeIn { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: translateY(0); } }
@media (max-width: 1100px) { .sidebar { width: 236px; } .main { margin-left: 236px; } .grid-4 { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 768px) { .sidebar { display: none; } .main { margin-left: 0; } .grid-2, .grid-3, .grid-4 { grid-template-columns: 1fr; } .content { padding: 20px 16px 40px; } .topbar { padding: 0 16px; } }
.lang-toggle { display: inline-flex; align-items: center; gap: 2px; padding: 3px; background: rgba(8, 25, 34, .06); border: 1px solid var(--border); border-radius: 999px; }
.lang-toggle button { border: 0; background: transparent; color: var(--text-secondary); font-family: inherit; font-size: 12px; font-weight: 700; line-height: 1; padding: 6px 10px; border-radius: 999px; cursor: pointer; transition: background .18s ease, color .18s ease; }
.lang-toggle button:hover { color: var(--text); }
.lang-toggle button.active { background: var(--black); color: var(--white); box-shadow: 0 1px 3px rgba(0,0,0,.18); }
@media (max-width: 520px) { .lang-toggle button { padding: 5px 7px; font-size: 11px; } }

/* Task-oriented peptide workspace. Shared application colors remain authoritative. */
.pep-workspace { max-width:1280px; margin:auto; }
.pep-header { display:flex; align-items:center; justify-content:space-between; gap:24px; margin-bottom:28px; }
.pep-header h2 { font-size:30px; letter-spacing:-.025em; margin-bottom:8px; }
.pep-header p,.pep-help { color:var(--text-secondary); font-size:14px; }
.pep-steps { list-style:none; display:flex; gap:32px; padding:18px 0; margin-bottom:28px; border-block:1px solid var(--border); }
.pep-steps li { display:flex; align-items:center; gap:10px; color:var(--text-secondary); font-size:14px; }
.pep-steps b { color:var(--accent); font-variant-numeric:tabular-nums; }
.pep-layout { display:grid; grid-template-columns:minmax(0,1fr) 330px; gap:32px; align-items:start; }
.pep-inputs { background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:0 28px; }
.pep-section { padding:24px 0; }
.pep-inputs .pep-section + .pep-section { border-top:1px solid var(--border); }
.pep-workspace h3 { font-size:17px; font-weight:650; margin-bottom:10px; }
.pep-options { padding:0 24px; background:var(--surface-2); border-radius:12px; }
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
.pep-project { margin-top:24px; padding:20px 24px; background:var(--surface); border-radius:12px; border:1px solid var(--border); }
.pep-project summary { cursor:pointer; font-weight:650; }
.pep-project[open] summary { margin-bottom:16px; }
:focus-visible { outline:2px solid var(--accent); outline-offset:4px; }
.btn:disabled { cursor:not-allowed; opacity:.55; }
@media(max-width:1100px) { .pep-layout { grid-template-columns:1fr; } .pep-header { align-items:flex-start; } }
@media(max-width:600px) { .pep-header { flex-direction:column; } .pep-header h2 { font-size:25px; } .pep-steps { gap:12px; flex-wrap:wrap; } .pep-steps li { font-size:12px; } .pep-inputs { padding:0 16px; } }
@media(prefers-reduced-motion:reduce) { *,*::before,*::after { scroll-behavior:auto !important; transition:none !important; animation:none !important; } }

/* EpitopeRank research workspace: daylight surfaces, restrained teal, readable evidence. */
:root { --black:#172f39; --gray-900:#172f39; --gray-700:#445b65; --gray-500:#60737c; --gray-300:#d6e0e3; --gray-100:#f0f4f5; --white:#fff; --bg:#f5f7f8; --surface:#fff; --surface-2:#edf4f3; --surface-3:#e3efec; --text:#172f39; --text-secondary:#455f69; --text-muted:#60737c; --accent:#087e72; --secondary:#367344; --warning:#986015; --danger:#b33449; --border:#d9e3e6; --shadow-sm:none; --shadow:none; --shadow-lg:0 20px 60px #162f3920; --radius:12px; --font-sans:'Segoe UI','Microsoft YaHei',system-ui,sans-serif; }
body { font-size:14px; } body::before { display:none; }
::selection { background:#c4e9e1; color:#173c36; }
* { scrollbar-width:thin; scrollbar-color:#b7c8cd transparent; }
.sidebar { width:232px; background:#142e38; backdrop-filter:none; border:0; padding-bottom:24px; }
.brand { padding:30px 24px; border-color:#ffffff16; }
.brand::before { display:none; }.brand-name { color:#f6fbfa; font-size:24px; letter-spacing:-.7px; }.brand-tagline { color:#a8c4ca; font-size:11px; letter-spacing:1px; margin-top:8px; }
.nav-section { padding-top:24px; }.nav-label { color:#90aeb7; font-size:11px; letter-spacing:.6px; padding-inline:24px; }
.nav-item { width:calc(100% - 24px); margin:4px 12px; padding:12px; color:#c4d5db; border:0; border-radius:7px; background:transparent; text-align:left; font:500 14px var(--font-sans); }
.nav-item::before { display:none !important; }.nav-item svg { width:19px; height:19px; fill:none; stroke:currentColor; stroke-width:1.6; stroke-linecap:round; stroke-linejoin:round; flex-shrink:0; }
.nav-item:hover { background:#ffffff0c; color:#fff; }.nav-item.active { background:#284b53; box-shadow:none; color:#a5f0dc; }
.main { margin-left:232px; min-width:0; }.topbar { height:74px; background:#ffffffed; border-bottom:1px solid var(--border); padding:0 36px; backdrop-filter:none; gap:16px; }
#current-project { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.content { padding:32px 36px 64px; max-width:1560px; }.content:focus { outline:none; }
.workspace-heading { display:flex; justify-content:space-between; align-items:center; gap:20px; margin-bottom:28px; }.workspace-heading h1,.pep-header h2 { font-size:28px; letter-spacing:-.7px; font-weight:650; line-height:1.3; }.workspace-heading p { margin-top:9px; color:var(--text-secondary); max-width:74ch; font-size:14px; }
.workspace-tag { border:1px solid var(--border); border-radius:6px; padding:6px 11px; color:var(--text-secondary); white-space:nowrap; font-size:12px; background:#fff; }
.start-guide { display:grid; grid-template-columns:1.3fr 1fr; gap:40px; background:#eaf3f0; padding:30px; border-radius:12px; margin-bottom:28px; }.start-guide h2 { font-size:21px; font-weight:650; }.start-guide p { margin:10px 0 22px; color:var(--text-secondary); max-width:52ch; }.start-guide .btn { margin:0 8px 8px 0; }.start-guide ol { list-style:none; display:grid; gap:16px; }.start-guide li { display:flex; gap:16px; font-size:12px; color:var(--text-secondary); }.start-guide li b { font-size:13px; color:var(--accent); padding-top:2px; font-variant-numeric:tabular-nums; }.start-guide strong { display:block; font-size:14px; color:var(--text); margin-bottom:3px; }
.card,.chart-container,.filters { background:var(--surface); box-shadow:none; border:1px solid var(--border); padding:24px; }.card:hover { transform:none; box-shadow:none; border-color:var(--border); }
.card-title { text-transform:none; letter-spacing:0; font-size:14px; }.grid { gap:24px; }.grid > * { min-width:0; }
#page-dashboard > .grid-4 { gap:0; background:#fff; border:1px solid var(--border); border-radius:12px; overflow:hidden; }#page-dashboard > .grid-4 > .card { border:0; border-right:1px solid var(--border); border-radius:0; }#page-dashboard > .grid-4 > .card:last-child { border-right:0; }
.btn { border-radius:7px; font-weight:600; min-height:40px; transition:background .15s,border-color .15s; }.btn-sm { min-height:34px; }.btn-primary { background:var(--accent); color:#fff; border-color:var(--accent); box-shadow:none; }.btn-primary:hover { background:#09685f; color:#fff; box-shadow:none; transform:none; filter:none; }.btn-secondary { background:#fff; color:var(--text); border-color:#cbd8dc; }.btn-secondary:hover { background:#edf5f2; color:#12675c; border-color:#8bb9ae; }.btn-danger { background:#fff3f4; border-color:#e8b5be; }.btn:disabled { opacity:.5; cursor:not-allowed; transform:none; }
input,select,textarea,.search-input { background:#fff; color:var(--text); min-width:0; border-color:#c6d5da; border-radius:7px; caret-color:var(--accent); }
input[type=checkbox] { flex:0 0 16px; }.checkbox-label:hover { color:var(--text); background:#eef5f3; }input::placeholder,textarea::placeholder { color:#677b84; }
#upload-modal input,#project-name,#analysis-query { background:#fff !important; }.search-input:focus,input:focus,select:focus,textarea:focus { box-shadow:0 0 0 3px #087e7214; }
:focus-visible { outline:2px solid var(--accent); outline-offset:3px; }.sidebar :focus-visible { outline-color:#a5f0dc; }
.lang-toggle { background:#f5f7f8; border-color:var(--border); border-radius:7px; }.lang-toggle button { color:var(--text-secondary); white-space:nowrap; }.lang-toggle button.active { color:var(--accent); background:#dfeee9; border-radius:5px; }
.status { font-weight:600; }.status-dot { box-shadow:none !important; }.status-running { background:#e5f4ef; border-color:#bddfd4; }.status-completed { background:#eef5e9; border-color:#ccdfbf; }
.pipeline-step { background:#fff; border-color:var(--border); padding:20px; cursor:default; }.pipeline-step:hover { transform:none; border-color:var(--border); }.pipeline-step.active { background:#eff8f5; border-color:#80bbaa; }.pipeline-step.active .step-number { color:#fff; }.step-number { border-radius:50%; font-variant-numeric:tabular-nums; }#progress-bar { background:var(--accent) !important; box-shadow:none !important; }
#page-pipeline > .card:last-child { padding:28px; }.pipeline { gap:0; }.pipeline-step { border:0; border-radius:0; border-bottom:1px solid var(--border); }.pipeline-step:last-child { border-bottom:0; }
#page-explorer .filters { border:0; border-radius:0; padding:0; box-shadow:none; gap:22px; }.filter-group { align-items:flex-start; flex-direction:column; }.filter-label { font-size:12px; }.table-container { background:white; }table { font-variant-numeric:tabular-nums; }th { background:#eff4f5; letter-spacing:0; font-size:12px; padding:13px 16px; }td { border-bottom:1px solid #e8eef0; padding:14px 16px; }tr:hover { background:#f5faf8; }
#page-visualization > .grid { grid-template-columns:320px minmax(0,1fr); }#page-visualization .card { padding:20px; }#page-visualization .card .btn { border-color:transparent; border-radius:5px; background:#f5f8f8; }#page-visualization .card .btn:hover { background:#e5f1ec; }#chart-display { min-height:560px !important; display:flex; flex-direction:column; justify-content:center; }#chart-display img { max-width:100%; height:auto; }
#page-gene .search-bar { max-width:800px; }#page-gene > div:nth-of-type(2) { border-left:0 !important; }#page-gene #gene-details .card { min-height:300px; display:grid; align-content:center; }
#page-report > .card { padding:32px; }#report-output { background:#f7f9fa; border-radius:8px; border:1px dashed #c6d5da; min-height:240px; display:grid; align-content:center; }#page-report .card > div:last-child { border-left:0 !important; }
#page-settings > .grid { grid-template-columns:minmax(300px,.8fr) minmax(0,1.2fr); align-items:start; }.cfg-row { flex-wrap:wrap; gap:10px; margin-bottom:16px; }.cfg-row label { color:var(--text-secondary); }.mcp-panel { background:transparent; border:0; padding:0; }.mcp-result { background:#f3f6f7; color:var(--text); border-color:var(--border); }.mcp-badge { color:var(--text-secondary); background:#edf3f3; }
#page-neoantigen > .card:first-of-type { max-width:none !important; padding:28px !important; }#page-neoantigen > .card:first-of-type > h2 { display:none; }#page-neoantigen > .card:first-of-type > div[style*='padding:16px'] { border:0 !important; border-top:1px solid var(--border) !important; border-radius:0 !important; padding:24px 0 !important; }#page-neoantigen p { color:var(--text-secondary); max-width:85ch; }#page-neoantigen details { padding:22px; background:#f2f6f7; border-radius:8px; }#page-neoantigen details h3 { margin:24px 0 8px; font-size:16px; }.neo-result-body,.neo-result-body th { background:#f6f9fa; }#neo-result-title { color:var(--text) !important; }
.pep-options { background:#eaf3f0; }.pep-header { margin-bottom:28px; }.pep-section { padding:26px 0; }.pep-steps { margin-bottom:24px; }.pep-output { background:#fff; padding:24px; border:1px solid var(--border); border-radius:12px; }#pep-results:empty::before { color:var(--text-secondary); }#pep-sequences { background:#f8fafb !important; }
#upload-modal { background:#112b3866 !important; backdrop-filter:blur(3px); }#upload-modal > div { box-shadow:var(--shadow-lg); border:0 !important; }#drop-zone { background:#f3f8f6 !important; }#ingest-modal { background:#112b3866; }.ingest-panel { background:#fff; }.ingest-head,.ingest-footer { background:#f7f9fa; }
.mobile-menu { display:none; }.skip-link { position:fixed; left:250px; top:-70px; z-index:2000; padding:12px; background:white; color:var(--accent); }.skip-link:focus { top:12px; }
@media(min-width:1600px) { .content { padding-top:40px; } }
@media(max-width:1100px) { .sidebar { width:216px; }.main { margin-left:216px; }.content { padding:26px 24px 48px; }.topbar { padding:0 24px; }.start-guide { grid-template-columns:1fr; gap:24px; }.start-guide ol { grid-template-columns:repeat(3,1fr); }.start-guide li { gap:10px; }#page-visualization > .grid { grid-template-columns:260px minmax(0,1fr); }#page-settings > .grid { grid-template-columns:1fr; } }
@media(max-width:768px) { .mobile-menu { display:inline-flex; }.sidebar { display:none; width:232px; top:74px; box-shadow:12px 0 35px #142e3833; }.navigation-open .sidebar { display:block; }.main { margin-left:0; }.topbar { gap:10px; padding:12px 16px; height:auto; min-height:74px; flex-wrap:wrap; }.topbar > div:last-child { gap:8px !important; flex-wrap:wrap; }.topbar #current-project { flex:1; }.content { padding:24px 16px 48px; }.workspace-heading { align-items:flex-start; }.workspace-heading h1,.pep-header h2 { font-size:25px; }.workspace-tag { display:none; }.start-guide { padding:24px; }.start-guide ol { grid-template-columns:1fr; }.grid-2,.grid-3,.grid-4,#page-visualization > .grid { grid-template-columns:1fr; }#page-dashboard > .grid-4 { grid-template-columns:repeat(2,1fr); }#page-dashboard > .grid-4 > .card { padding:18px; border-bottom:1px solid var(--border); }#chart-display { position:static !important; min-height:320px !important; }.search-bar { flex-wrap:wrap; }.search-bar input { flex-basis:100%; }.pipeline-step { padding:18px 0; flex-wrap:wrap; }.step-info { min-width:150px; }.card { padding:20px; }#page-report > .card { padding:20px; }#page-report .card > div:first-child { flex-wrap:wrap; gap:20px; }#page-report .card > div:first-child > div:last-child { flex-wrap:wrap; }.mcp-inline { flex-wrap:wrap; }.cfg-row { display:flex; flex-direction:column; align-items:stretch; }.cfg-row label { width:auto; }#neo-mapping-fields { grid-template-columns:1fr !important; }.skip-link { left:16px; }.pep-header { gap:18px; } }
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
.start-guide::before { content:''; position:absolute; z-index:-1; width:460px; height:460px; left:var(--light-x,65%); top:var(--light-y,30%); transform:translate(-50%,-50%); border-radius:44% 56% 62% 38% / 52% 42% 58% 48%; background:radial-gradient(ellipse at 40% 35%,#ffffffcf, #b9e7d788 44%, #a3d6e222 67%,transparent 72%); pointer-events:none; transition:border-radius .6s var(--motion-ease); }
.start-guide:hover::before { border-radius:62% 38% 44% 56% / 38% 60% 40% 62%; }
.start-guide::after { content:''; position:absolute; z-index:-1; right:-60px; bottom:-120px; width:360px; height:300px; border:1px solid #9bcab766; border-radius:50%; transform:rotate(-28deg); pointer-events:none; }
.start-guide ol { background:#ffffff70; border:1px solid #ffffffa8; border-radius:14px; padding:20px 24px; backdrop-filter:blur(8px); }
.sidebar { isolation:isolate; }
.nav-item { position:relative; z-index:1; transition:color .18s,background .18s; }
.nav-item.active { background:transparent; }
.nav-fluid-marker { position:absolute; left:12px; top:0; width:calc(100% - 24px); height:46px; border-radius:10px; background:linear-gradient(115deg,#365e66,#244a53); border:1px solid #7ea7ab45; box-shadow:0 5px 14px #071d2426; pointer-events:none; z-index:0; transition:transform .42s var(--motion-ease),height .25s var(--motion-ease),border-radius .3s; }
.nav-fluid-marker::after { content:''; position:absolute; inset:0; border-radius:inherit; background:linear-gradient(110deg,#a8eee512,transparent 65%); }
.nav-item:hover svg { transform:translateX(2px); }.nav-item svg { transition:transform .2s var(--motion-ease); }
.btn { position:relative; isolation:isolate; overflow:hidden; transition:background .18s,border-color .18s,box-shadow .18s,transform .18s var(--motion-ease); }
.btn:active:not(:disabled) { transform:scale(.975); }
.btn-primary:hover { box-shadow:0 5px 14px #087e7226; }
.press-wave { position:absolute; pointer-events:none; width:160px; height:160px; border-radius:50%; background:currentColor; opacity:.12; transform:translate(-50%,-50%) scale(0); animation:pressWave .48s var(--motion-ease) forwards; z-index:-1; }
@keyframes pressWave { to { transform:translate(-50%,-50%) scale(2); opacity:0; } }
#page-visualization .card .btn[aria-pressed=true] { background:#dceee6; border-color:#8bb9ae; color:#125e50; }
#chart-display { transition:border-color .2s; }
details[open] > :not(summary) { animation:detailReveal .22s var(--motion-ease); }
@keyframes detailReveal { from { opacity:.4; transform:translateY(-3px); } to { opacity:1; transform:translateY(0); } }
.quick-switch { padding-inline:12px; gap:10px; }.quick-switch kbd { border:1px solid var(--border); border-radius:4px; padding:1px 4px; font:10px var(--font-sans); color:var(--text-secondary); }
.quick-dialog { border:1px solid #dce8e5; border-radius:18px; padding:0; width:min(540px,calc(100vw - 32px)); max-height:80vh; margin:12vh auto auto; color:var(--text); background:#ffffffed; box-shadow:0 24px 80px #142e3838; backdrop-filter:blur(18px); }
.quick-dialog::backdrop { background:#102e3d66; backdrop-filter:blur(5px); }
.quick-dialog[open] { animation:quickOpen .24s var(--motion-ease); }
@keyframes quickOpen { from { opacity:0; transform:translateY(-10px) scale(.98); } to { opacity:1; transform:none; } }
.quick-head { display:flex; gap:16px; align-items:center; justify-content:space-between; padding:20px 22px 8px; }.quick-head h2 { font-size:18px; }.quick-search { padding:12px 22px; }.quick-search input { width:100%; background:#f1f6f5; }.quick-results { display:grid; gap:4px; padding:0 12px 16px; overflow:auto; max-height:48vh; }.quick-result { text-align:left; padding:12px 14px; border:0; border-radius:8px; background:transparent; font:14px var(--font-sans); color:var(--text); cursor:pointer; }.quick-result:hover,.quick-result:focus-visible { background:#e5f2ec; }.quick-result[aria-current=page] { color:var(--accent); background:#f0f7f4; }.quick-result[hidden] { display:none; }.quick-empty { padding:20px 14px; color:var(--text-secondary); font-size:13px; }
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
        <section class="start-guide" aria-label="开始使用"><div><h2>开始一次新的分析</h2><p>上传事件数据，确认字段与分组，再查看统计结果和研究报告。</p><button class="btn btn-primary" onclick="showUploadModal()">新建分析项目</button><button class="btn btn-secondary" onclick="navigateTo('peptide')">已有肽序列？直接预测</button></div><ol><li><b>01</b><span><strong>准备数据</strong>支持事件表与报告目录导入</span></li><li><b>02</b><span><strong>检查与分析</strong>确认数据映射，跟踪每一步进度</span></li><li><b>03</b><span><strong>探索与导出</strong>浏览候选事件，生成图表与报告</span></li></ol></section>
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
        <div class="grid grid-2">
          <div class="card">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px;">
              <div style="font-size: 14px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; color: var(--text-secondary);">当前运行 Agent</div>
              <div id="current-agent-indicator" style="display: none;"><span class="status status-running"><span class="status-dot"></span>分析中</span></div>
            </div>
            <div id="current-agent">
              <div style="padding: 40px; text-align: center; color: var(--text-muted);">
                <div style="font-size: 48px; margin-bottom: 12px; opacity: 0.3;"></div>
                <div style="font-size: 14px;">暂无运行中的分析</div>
                <button class="btn btn-primary" style="margin-top: 16px;" onclick="showUploadModal()">启动新分析</button>
              </div>
            </div>
          </div>
          <div class="card">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px;">
              <div style="font-size: 14px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; color: var(--text-secondary);">历史项目</div>
              <button class="btn btn-sm btn-secondary" onclick="loadDashboard()">刷新</button>
            </div>
            <input aria-label="搜索历史项目" id="project-search" type="search" placeholder="搜索历史项目" oninput="renderProjectHistory()" style="width:100%;margin-bottom:12px;padding:9px;border:1px solid var(--border);border-radius:6px;">
            <div id="recent-projects" style="max-height:440px;overflow:auto;">
              <div style="padding: 40px; text-align: center; color: var(--text-muted);">
                <div style="font-size: 48px; margin-bottom: 12px; opacity: 0.3;"></div>
                <div style="font-size: 14px;">暂无项目</div>
              </div>
            </div>
            <div id="storage-hint" style="margin-top:12px;padding-top:10px;border-top:1px solid var(--border);font-size:11px;line-height:1.6;color:var(--text-muted);">
              数据目录：读取中…
            </div>
          </div>
        </div>

        <section class="card" id="project-detail" style="margin-top: 24px; display: none;">
          <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:16px;margin-bottom:20px;flex-wrap:wrap;">
            <div>
              <div style="font-size:11px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:var(--text-muted);">历史项目详情</div>
              <div style="font-size:20px;font-weight:700;margin-top:4px;" id="detail-title">-</div>
              <div style="font-size:12px;color:var(--text-secondary);margin-top:6px;" id="detail-meta">-</div>
            </div>
            <div style="display:flex;gap:8px;flex-wrap:wrap;">
              <button class="btn btn-sm btn-secondary" onclick="openReport('html')"> 打开 HTML 报告</button>
              <button class="btn btn-sm btn-secondary" onclick="openReport('pdf')"> 下载 PDF</button>
              <button class="btn btn-sm btn-secondary" onclick="revealProjectBundle()"> 成果文件夹</button>
              <button class="btn btn-sm btn-secondary" onclick="packageProject()"> 打包 ZIP</button>
              <button class="btn btn-sm btn-secondary" onclick="jumpToExplorer()"> 浏览全部事件</button>
              <button class="btn btn-sm btn-danger" onclick="deleteCurrentProject()" style="color:var(--danger);"> 删除项目</button>
            </div>
          </div>
          <div id="detail-bundle-hint" style="font-size:11px;color:var(--text-muted);margin:-6px 0 10px;"></div>
          <div class="grid grid-2" style="gap:20px;">
            <div>
              <div style="font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.8px;color:var(--text-muted);margin-bottom:10px;">样本分组</div>
              <div id="detail-groups" style="display:flex;flex-wrap:wrap;gap:8px;"></div>
              <div style="font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.8px;color:var(--text-muted);margin:20px 0 10px;">事件类型分布</div>
              <div id="detail-types" style="display:flex;flex-wrap:wrap;gap:8px;"></div>
              <div style="font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.8px;color:var(--text-muted);margin:20px 0 10px;">流程日志（最近 12 条）</div>
              <div id="detail-logs" style="max-height:220px;overflow:auto;font-size:12px;line-height:1.7;"></div>
            </div>
            <div>
              <div style="font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.8px;color:var(--text-muted);margin-bottom:10px;">图表（点击放大）</div>
              <div id="detail-figures" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:10px;"></div>
              <div style="font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.8px;color:var(--text-muted);margin:20px 0 10px;">候选事件 Top 10</div>
              <div id="detail-candidates" style="max-height:260px;overflow:auto;font-size:12px;"></div>
            </div>
          </div>
        </section>
      </div>
      <div class="page" id="page-pipeline"><header class="workspace-heading"><div><h1>分析流程</h1><p>查看数据处理、统计分析与解读进度，定位当前执行阶段。</p></div></header>
        <div class="card" style="margin-bottom: 24px;">
          <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px;">
            <div>
              <div style="font-size: 18px; font-weight: 700;">分析进度</div>
              <div style="font-size: 13px; color: var(--text-secondary); margin-top: 4px;" id="pipeline-status-text">等待启动...</div>
            </div>
            <div id="pipeline-progress" style="font-size: 24px; font-weight: 800; color: var(--accent);">0%</div>
          </div>
          <div style="height: 8px; background: var(--gray-100); border-radius: 4px; overflow: hidden; box-shadow: inset 0 1px 2px rgba(0,0,0,0.05);">
            <div id="progress-bar" style="height: 100%; width: 0%; background: var(--black); transition: width 0.5s cubic-bezier(0.4, 0, 0.2, 1); box-shadow: 0 2px 4px rgba(8, 145, 178, 0.3);"></div>
          </div>
        </div>
        
        <div class="card" style="margin-bottom: 24px;">
          <div style="font-size: 14px; font-weight: 700; margin-bottom: 16px; color: var(--text);">Agent 工作流</div>
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
          <div style="font-size: 16px; font-weight: 700; margin-bottom: 20px;">筛选条件</div>
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
                  <select id="filter-order" style="margin-left:6px;padding:6px 8px;border:1px solid var(--border);border-radius:6px;background:transparent;color:var(--text);font-family:inherit;font-size:12px;">
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
                <th>Delta PSI</th>
                <th>FDR</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody id="events-table">
              <tr>
                <td colspan="6" style="text-align: center; padding: 60px; color: var(--text-muted);">
                  <div style="font-size: 48px; margin-bottom: 16px; opacity: 0.3;"></div>
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
              <div style="font-size: 15px; font-weight: 700; margin-bottom: 6px; color: var(--text);"> 核心统计图</div>
              <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 14px;">差异剪接的显著性与效应量</div>
              <div style="display: flex; flex-direction: column; gap: 10px;">
                <button class="btn btn-secondary" onclick="loadChart('volcano')" style="justify-content: flex-start; padding: 12px 16px; text-align: left;">
                  <div><div style="font-weight: 700; margin-bottom: 2px;"> 火山图 Volcano</div><div style="font-size: 11px; color: var(--text-secondary); font-weight: 500;">ΔPSI vs -log10(FDR)，标注显著性阈值</div></div>
                </button>
                <button class="btn btn-secondary" onclick="loadChart('dpsi_waterfall')" style="justify-content: flex-start; padding: 12px 16px; text-align: left;">
                  <div><div style="font-weight: 700; margin-bottom: 2px;"> ΔPSI 瀑布图 Waterfall</div><div style="font-size: 11px; color: var(--text-secondary); font-weight: 500;">Top 25 效应量排序，区分包含上调/下调</div></div>
                </button>
                <button class="btn btn-secondary" onclick="loadChart('dpsi_ecdf')" style="justify-content: flex-start; padding: 12px 16px; text-align: left;">
                  <div><div style="font-weight: 700; margin-bottom: 2px;"> ΔPSI 累积分布 ECDF</div><div style="font-size: 11px; color: var(--text-secondary); font-weight: 500;">效应量经验累积分布与阈值占比</div></div>
                </button>
                <button class="btn btn-secondary" onclick="loadChart('fdr_scree')" style="justify-content: flex-start; padding: 12px 16px; text-align: left;">
                  <div><div style="font-weight: 700; margin-bottom: 2px;"> 显著性碎石图 Scree</div><div style="font-size: 11px; color: var(--text-secondary); font-weight: 500;">候选排名 vs -log10(FDR)，定位显著性拐点</div></div>
                </button>
              </div>
            </div>
            <div class="card" style="margin-bottom: 20px;">
              <div style="font-size: 15px; font-weight: 700; margin-bottom: 6px; color: var(--text);"> 事件组成与机制</div>
              <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 14px;">剪接事件类型构成与分子机制</div>
              <div style="display: flex; flex-direction: column; gap: 10px;">
                <button class="btn btn-secondary" onclick="loadChart('event_type_counts')" style="justify-content: flex-start; padding: 12px 16px; text-align: left;">
                  <div><div style="font-weight: 700; margin-bottom: 2px;"> 事件类型分布</div><div style="font-size: 11px; color: var(--text-secondary); font-weight: 500;">SE/MXE/A5SS/A3SS/RI 五类事件计数</div></div>
                </button>
                <button class="btn btn-secondary" onclick="loadChart('event_significance')" style="justify-content: flex-start; padding: 12px 16px; text-align: left;">
                  <div><div style="font-weight: 700; margin-bottom: 2px;"> 类型×显著性堆叠图</div><div style="font-size: 11px; color: var(--text-secondary); font-weight: 500;">各类型中显著与非显著事件构成</div></div>
                </button>
                <button class="btn btn-secondary" onclick="loadChart('event_schematic')" style="justify-content: flex-start; padding: 12px 16px; text-align: left;">
                  <div><div style="font-weight: 700; margin-bottom: 2px;"> 剪接机制示意图 Schematic</div><div style="font-size: 11px; color: var(--text-secondary); font-weight: 500;">五类可变剪接的外显子-内含子结构模式图</div></div>
                </button>
              </div>
            </div>
            <div class="card" style="margin-bottom: 20px;">
              <div style="font-size: 15px; font-weight: 700; margin-bottom: 6px; color: var(--text);"> 样本与质控</div>
              <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 14px;">队列构成与样本水平 PSI 模式</div>
              <div style="display: flex; flex-direction: column; gap: 10px;">
                <button class="btn btn-secondary" onclick="loadChart('psi_heatmap')" style="justify-content: flex-start; padding: 12px 16px; text-align: left;">
                  <div><div style="font-weight: 700; margin-bottom: 2px;"> PSI 热图 Heatmap</div><div style="font-size: 11px; color: var(--text-secondary); font-weight: 500;">Top 事件逐样本 PSI 聚类热图</div></div>
                </button>
                <button class="btn btn-secondary" onclick="loadChart('psi_distribution')" style="justify-content: flex-start; padding: 12px 16px; text-align: left;">
                  <div><div style="font-weight: 700; margin-bottom: 2px;"> 分组 PSI 箱线图</div><div style="font-size: 11px; color: var(--text-secondary); font-weight: 500;">各组 PSI 分布与离群样本检测</div></div>
                </button>
                <button class="btn btn-secondary" onclick="loadChart('sample_composition')" style="justify-content: flex-start; padding: 12px 16px; text-align: left;">
                  <div><div style="font-weight: 700; margin-bottom: 2px;"> 队列构成图</div><div style="font-size: 11px; color: var(--text-secondary); font-weight: 500;">分组占比与批次分布（QC 必备）</div></div>
                </button>
              </div>
            </div>
            <div class="card">
              <div style="font-size: 15px; font-weight: 700; margin-bottom: 6px; color: var(--text);"> AI 排序与功能富集</div>
              <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 14px;">智能体候选评分与通路注释</div>
              <div style="display: flex; flex-direction: column; gap: 10px;">
                <button class="btn btn-secondary" onclick="loadChart('candidate_ranking')" style="justify-content: flex-start; padding: 12px 16px; text-align: left;">
                  <div><div style="font-weight: 700; margin-bottom: 2px;"> 候选基因排名</div><div style="font-size: 11px; color: var(--text-secondary); font-weight: 500;">综合评分 Top 15 候选事件条形图</div></div>
                </button>
                <button class="btn btn-secondary" onclick="loadChart('score_components')" style="justify-content: flex-start; padding: 12px 16px; text-align: left;">
                  <div><div style="font-weight: 700; margin-bottom: 2px;"> 评分分解堆叠图</div><div style="font-size: 11px; color: var(--text-secondary); font-weight: 500;">显著性/效应/生物学/文献四维贡献</div></div>
                </button>
                <button class="btn btn-secondary" onclick="loadChart('enrichment')" style="justify-content: flex-start; padding: 12px 16px; text-align: left;">
                  <div><div style="font-weight: 700; margin-bottom: 2px;"> 功能富集点图</div><div style="font-size: 11px; color: var(--text-secondary); font-weight: 500;">GO/KEGG 富集倍数 vs FDR 气泡图</div></div>
                </button>
              </div>
            </div>
          </div>
          <div>
            <div class="chart-container" id="chart-display" style="min-height: 600px; position: sticky; top: 88px;">
              <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; color: var(--text-muted);">
                <div style="font-size: 64px; margin-bottom: 20px; opacity: 0.3;"></div>
                <div style="font-size: 18px; font-weight: 600; margin-bottom: 8px;">选择图表类型</div>
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
        <div style="margin-bottom: 24px; padding: 20px; background: var(--gray-100); border-radius: var(--radius); border-left: 2px solid var(--gray-700);">
          <div style="font-size: 13px; font-weight: 700; color: var(--secondary); margin-bottom: 8px;"> 提示</div>
          <div style="font-size: 13px; line-height: 1.8; color: var(--text);">
            输入基因符号查看该基因的所有剪接事件、统计信息和文献证据。支持热门基因如 TP53、BRCA1、MYC、EGFR 等。
          </div>
        </div>
        <div id="gene-details">
          <div class="card">
            <div style="padding: 60px; text-align: center; color: var(--text-muted);">
              <div style="font-size: 64px; margin-bottom: 16px; opacity: 0.3;"></div>
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
              <div style="font-size: 18px; font-weight: 700; margin-bottom: 4px;">生成分析报告</div>
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
              <div style="font-size: 64px; margin-bottom: 20px; opacity: 0.3;"></div>
              <div style="font-size: 16px; font-weight: 600; margin-bottom: 8px;">准备生成报告</div>
              <div style="font-size: 14px;">完成分析后可生成包含统计结果、可视化和生物学解读的专业报告</div>
            </div>
          </div>
          
          <div style="margin-top: 24px; padding: 20px; background: var(--gray-100); border-radius: var(--radius); border-left: 2px solid var(--black);">
            <div style="font-size: 13px; font-weight: 700; color: var(--accent); margin-bottom: 8px;"> 报告内容</div>
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
      
      <div class="page" id="page-settings"><header class="workspace-heading"><div><h1>工作区设置</h1><p>配置 AI 解读服务与外部工具，查看连接状态。</p></div></header>
        <div class="grid grid-2">
          <div class="card">
            <div style="font-size: 18px; font-weight: 700; margin-bottom: 6px;"> 模型配置</div>
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
        <div style="padding:16px;border:1px solid var(--border);border-radius:12px;margin:16px 0;">
          <strong>第一步：检查项目数据</strong>
          <p style="margin:6px 0 12px;">系统会检查剪接事件和生成肽所需的编码序列表。</p>
          <button class="btn btn-secondary" type="button" id="neo-check" onclick="checkNeoReadiness()">检查当前项目</button>
          <div id="neo-readiness" style="white-space:pre-wrap;margin-top:12px;" aria-live="polite">请先选择一个项目。</div>
        </div>
        <div style="padding:16px;border:1px solid var(--border);border-radius:12px;margin:16px 0;">
          <strong>第二步：选择编码序列表，生成候选肽</strong>
          <p style="margin:6px 0 10px;">编码序列表就是「每个剪接事件对应的参考 CDS 与改变后 CDS」。系统按表头自动识别，<b>文件名不限</b>；下面若已列出文件，直接选即可。</p>
          <label for="neo-cds-select">编码序列表</label>
          <select id="neo-cds-select" style="display:block;width:100%;padding:10px;margin:8px 0 10px;"></select>
          <div id="neo-mapping-panel" style="display:none;border:1px solid var(--border);border-radius:10px;padding:12px;margin:0 0 12px;background:rgba(255,255,255,.02);">
            <div style="font-weight:650;margin-bottom:4px;">确认列的含义</div>
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
        <summary style="cursor:pointer;font-weight:650;">高级选项：其他文件和专业分析工具</summary>
        <h3>moPepGen · Docker 变异肽生成</h3>
        <p>自动识别当前项目中的 rMATS JC 文件。请提供版本匹配的参考文件并启动 Docker；生成的是蛋白质组学变异肽，不是 HLA 预测或 CDS 对照表。</p>
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
            <div id="neo-result-title" style="font-size:18px;font-weight:750;color:var(--white);">—</div>
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
            每行一个肽段（8–30 aa）；可直接粘贴 FASTA 序列，<code>&gt;</code> 开头的标题行会被忽略。
            单次最多 200 条肽、8 个 HLA（接口限制），避免触发 IEDB 频率限制。
          </p>
          <textarea id="pep-sequences" rows="7" spellcheck="false"
            style="display:block;width:100%;padding:10px;margin:8px 0 6px;border:1px solid var(--border);border-radius:8px;background:transparent;color:var(--text);font-family:var(--font-mono,monospace);font-size:13px;line-height:1.6;resize:vertical;"
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
            style="display:block;width:100%;padding:10px;border:1px solid var(--border);border-radius:8px;background:transparent;color:var(--text);font-family:inherit;font-size:13px;">
          <datalist id="pep-allele-list"></datalist>
          <div id="pep-allele-hint" style="font-size:12px;color:var(--text-muted);margin-top:6px;">参考表尚未加载。</div>
          <div id="pep-allele-chips" style="display:flex;gap:6px;flex-wrap:wrap;margin-top:8px;"></div>
        </section></div>
        <aside class="pep-options"><section class="pep-section">
          <h3>预测设置</h3><p class="pep-help">先选类别，再选择运行方式。在线预测需要网络连接。</p>
          <div style="display:grid;grid-template-columns:1fr;gap:14px;margin-top:12px;">
            <div>
              <label for="pep-mhc-class" style="display:block;font-size:12px;color:var(--text-secondary);margin-bottom:6px;">MHC 类别</label>
              <select id="pep-mhc-class" style="width:100%;padding:8px;border:1px solid var(--border);border-radius:6px;background:transparent;color:var(--text);font-family:inherit;font-size:13px;">
                <option value="class1">class1（MHC-I，8–11 aa）</option>
                <option value="class2">class2（MHC-II，11–30 aa）</option>
                <option value="both">both（按类别拆分）</option>
              </select>
            </div>
            <div>
              <label for="pep-predictor" style="display:block;font-size:12px;color:var(--text-secondary);margin-bottom:6px;">预测器</label>
              <select id="pep-predictor" style="width:100%;padding:8px;border:1px solid var(--border);border-radius:6px;background:transparent;color:var(--text);font-family:inherit;font-size:13px;">
                <option value="iedb">IEDB（在线）</option>
                <option value="local">MHCflurry（本地，需安装）</option>
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
      <button onclick="closeUploadModal()" style="background: none; border: none; font-size: 24px; cursor: pointer; color: var(--gray-700);">×</button>
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
        <div style="font-size: 48px; margin-bottom: 12px;"></div>
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
    const links = ['splice_peptides.tsv','mhc_i_predictions.tsv','neoantigen_manifest.json'].map(name => '<a href="' + base + encodeURIComponent(name) + '">' + name + '</a>').join(' · ');
    const failures = (result.prediction_errors || []).length;
    const truncated = Number(result.prediction_truncated || 0);
    let summary = '使用编码序列表：' + neoEscape(result.cds_table_name || '自动识别') + '<br>候选肽段 ' + Number(result.candidate_count) + ' 条';
    if (alleles.length) {
      summary += '；HLA 结合预测成功 ' + Number(result.prediction_count) + ' 条';
      if (failures) summary += '，失败 ' + failures + ' 条（详见 manifest 的 prediction_errors）';
      if (truncated) summary += '；超出单次上限的部分（' + truncated + ' 条）未预测，可缩小 CDS 表后重跑';
      summary += '。<br><span style="color:var(--text-muted);font-size:12px;">预测发往 IEDB（NetMHCpan 4.1 EL），结合力不等于免疫原性。</span>';
    } else {
      summary += '；未填写 HLA，只生成候选肽，未做任何外部预测。';
    }
    summary += '<br>' + links;
    status.innerHTML = summary;
    neoResultDir = resultDir;
    document.getElementById('neo-result-panel').style.display = 'block';
    const tabs = document.getElementById('neo-result-tabs');
    tabs.replaceChildren();
    ['splice_peptides.tsv','mhc_i_predictions.tsv','neoantigen_manifest.json'].forEach(name => {
      const button = document.createElement('button'); button.type = 'button'; button.className = 'btn btn-secondary btn-sm'; button.textContent = name;
      button.onclick = () => openNeoResult(name); tabs.appendChild(button);
    });
    await openNeoResult('splice_peptides.tsv');
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
function pepFillExample() {
  const field = document.getElementById('pep-sequences');
  if (field.value.trim() && !window.confirm('填入示例会替换当前肽序列和 HLA 设置，是否继续？')) return;
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
    ['method', '方法'], ['percentile_rank', 'percentile'], ['score', '分数']
  ].map(([column, text]) => {
    const marker = pepState.sortKey === column ? (pepState.sortDir === 1 ? ' ▲' : ' ▼') : '';
    return '<th data-sort="' + column + '" style="cursor:pointer;white-space:nowrap;">'
      + pepEscape(text) + marker + '</th>';
  }).join('');
  const body = rows.map((row, index) => {
    const method = row.method_label || row.method || '';
    const percentile = (row.percentile_rank === null || row.percentile_rank === undefined)
      ? '—' : pepEscape(row.percentile_rank);
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
    + rows.length + ' 行（肽段 × HLA × 方法）。点击表头可排序。</div>';
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
    const suffix = errorCount ? '；有 ' + errorCount + ' 条服务错误，见下方说明' : '；无服务错误';
    pepSetStatus(status, '预测完成：候选 ' + Number(data.candidate_count || 0) + ' 条，预测记录 '
      + Number(data.prediction_count || pepState.predictions.length) + ' 条' + suffix + '。'
      + ' percentile rank 越低越好；预测不等于呈递或免疫原性。', errorCount ? 'error' : 'muted');
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
function navigateTo(page) {
  if (!document.getElementById('page-' + page)) return;
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
    document.getElementById('project-detail').style.display = 'none';
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
async function loadProjectDetail(projectId) {
  const status = await apiCall(`/status/${projectId}`);
  state.detail = status || null;
  const panel = document.getElementById('project-detail');
  if (!status) { panel.style.display = 'none'; return; }
  panel.style.display = 'block';

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
       <span style="margin-left:auto;color:${l.status === 'ok' ? 'var(--success)' : 'var(--danger)'};">${ingestEsc(l.status || '')}</span>
     </div>`).join('') : '<span style="font-size:12px;color:var(--text-muted);">无日志</span>';

  const figures = (status.artifacts || []).filter(a => (a.kind || '').startsWith('figure:'));
  document.getElementById('detail-figures').innerHTML = figures.length ? figures.map(a => {
    const name = a.kind.split(':')[1];
    const url = `/api/figure/${encodeURIComponent(projectId)}/${encodeURIComponent(name)}`;
    return `<a href="${url}" target="_blank" rel="noopener" style="display:block;border:1px solid var(--border);border-radius:8px;overflow:hidden;background:rgba(3,12,17,.5);">
      <img src="${url}" alt="${ingestEsc(name)}" loading="lazy" style="width:100%;height:96px;object-fit:cover;display:block;">
      <div style="font-size:11px;padding:4px 6px;color:var(--text-secondary);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${ingestEsc(name)}</div>
    </a>`;
  }).join('') : '<span style="font-size:12px;color:var(--text-muted);">该项目没有保存图表</span>';

  const candidates = status.candidates || [];
  document.getElementById('detail-candidates').innerHTML = candidates.length ? `<table style="width:100%;border-collapse:collapse;">
      <thead><tr style="text-align:left;color:var(--text-muted);font-size:11px;">
        <th style="padding:4px 6px;">#</th><th style="padding:4px 6px;">基因</th><th style="padding:4px 6px;">类型</th>
        <th style="padding:4px 6px;">ΔPSI</th><th style="padding:4px 6px;">FDR</th></tr></thead>
      <tbody>${candidates.map(c => `<tr style="border-top:1px solid var(--border);">
        <td style="padding:4px 6px;">${ingestEsc(c.rank)}</td>
        <td style="padding:4px 6px;font-weight:600;">${ingestEsc(c.gene_symbol || c.gene_id || '-')}</td>
        <td style="padding:4px 6px;">${ingestEsc(c.event_type || '-')}</td>
        <td style="padding:4px 6px;color:${(c.delta_psi || 0) > 0 ? 'var(--danger)' : 'var(--success)'};">${c.delta_psi === null || c.delta_psi === undefined ? '-' : Number(c.delta_psi).toFixed(3)}</td>
        <td style="padding:4px 6px;">${c.fdr === null || c.fdr === undefined ? '-' : Number(c.fdr).toExponential(2)}</td>
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
    hint.style.color = ok ? 'var(--success)' : 'var(--danger)';
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
    hint.style.color = ok ? 'var(--success)' : 'var(--danger)';
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
  if (!confirm(`确定删除项目「${label}」吗？\n\n会删除数据库记录和该项目的图表/报告目录，无法撤销。\n原始输入数据不会被删除。`)) return;
  const response = await fetch(`/api/projects/${encodeURIComponent(state.currentProject)}`, { method: 'DELETE' });
  if (!response.ok) { alert('删除失败：' + response.status); return; }
  localStorage.removeItem('epitoperank.currentProject');
  state.currentProject = null;
  state.detail = null;
  document.getElementById('project-detail').style.display = 'none';
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
      return `<div style="padding: 11px 12px; border-bottom: 1px solid var(--border); cursor: pointer; ${active ? 'background:var(--gray-100);border-left:3px solid var(--black);' : 'border-left:3px solid transparent;'}" onclick="selectProject('${ingestEsc(p.project_id)}')">
        <div style="display:flex;justify-content:space-between;gap:8px;align-items:baseline;">
          <div style="font-weight:600;font-size:13px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${ingestEsc(p.name || p.project_id)}</div>
          <div style="font-size:11px;color:var(--text-muted);white-space:nowrap;">${ingestEsc(fmtDate(p.created_at).slice(0, 10))}</div>
        </div>
        <div style="font-size:11px;color:var(--text-secondary);margin-top:5px;display:flex;gap:10px;flex-wrap:wrap;">
          <span>${ingestEsc(p.source_format || '-')}</span>
          <span>事件 ${fmtCount(p.event_count)}</span>
          <span style="color:var(--danger);">显著 ${fmtCount(p.significant_count)}</span>
        </div>
        <div style="font-size:11px;color:var(--text-muted);margin-top:3px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${ingestEsc(p.query || '分析查询')}</div>
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
  const data = await apiCall(`/projects/${encodeURIComponent(state.currentProject)}/events?${params.toString()}`);
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
    const fdr = (event.fdr !== null && event.fdr !== undefined) ? Number(event.fdr).toExponential(2) : '-';
    const color = (Number(event.delta_psi) || 0) > 0 ? 'var(--danger)' : 'var(--success)';
    const flag = event.significant ? '' : ' <span style="font-size:10px;color:var(--text-muted);">(不显著)</span>';
    return `<tr>
      <td style="font-family:var(--font-mono);font-size:12px;">${ingestEsc(eventId)}</td>
      <td><strong>${ingestEsc(gene)}</strong>${flag}</td>
      <td>${ingestEsc(eventType)}</td>
      <td style="color:${color};">${dpsi}</td>
      <td>${fdr}</td>
      <td><button class="btn btn-sm btn-secondary" onclick="viewEventDetails('${ingestEsc(eventId)}')">查看</button></td>
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
        <div style="font-size: 48px; margin-bottom: 16px; opacity: 0.3;"></div>
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
      <div style="font-size: 18px; font-weight: 700; margin-bottom: 8px; color: var(--text);">${info[0]}</div>
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
        <div style="font-size: 18px; font-weight: 700; margin-bottom: 8px; color: var(--text);">${info[0]}</div>
        <div style="font-size: 13px; color: var(--text-secondary); margin-bottom: 24px; line-height: 1.6;">${info[1]}</div>
      </div>
    `;
    container.appendChild(img);
  };
  
  img.onerror = function() { 
    container.innerHTML = `
      <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 600px; color: var(--text-muted);">
        <div style="font-size: 48px; margin-bottom: 16px; opacity: 0.3;"></div>
        <div style="font-size: 16px; font-weight: 600; margin-bottom: 8px;">图表不可用</div>
        <div style="font-size: 14px;">该项目可能尚未生成此图表，请完成分析后重试</div>
      </div>
    `; 
  };
}
async function exploreGene() {
  const geneSymbol = document.getElementById('gene-search').value.trim();
  if (!geneSymbol) {
    alert('请输入基因符号');
    return;
  }
  
  const container = document.getElementById('gene-details');
  if (!state.currentProject) {
    container.innerHTML = `
      <div class="card">
        <div style="padding: 40px; text-align: center; color: var(--text-muted);">
          <div style="font-size: 48px; margin-bottom: 12px; opacity: 0.3;"></div>
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
          <div style="font-size: 64px; margin-bottom: 16px; opacity: 0.3;"></div>
          <div style="font-size: 18px; font-weight: 700; margin-bottom: 8px;">未找到 ${geneSymbol} 的剪接事件</div>
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
          <th style="text-align: left; padding: 12px 16px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px; color: var(--text-secondary);">事件 ID</th>
          <th style="text-align: left; padding: 12px 16px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px; color: var(--text-secondary);">类型</th>
          <th style="text-align: left; padding: 12px 16px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px; color: var(--text-secondary);">Delta PSI</th>
          <th style="text-align: left; padding: 12px 16px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px; color: var(--text-secondary);">FDR</th>
          <th style="text-align: left; padding: 12px 16px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px; color: var(--text-secondary);">评分</th>
          <th style="text-align: left; padding: 12px 16px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px; color: var(--text-secondary);">操作</th>
        </tr>
      </thead>
      <tbody>
        ${geneEvents.map(e => {
          const dpsi = Number(e.delta_psi).toFixed(3);
          const fdr = Number(e.fdr).toExponential(2);
          const score = e.score !== undefined ? Number(e.score).toFixed(3) : '-';
          const sigLevel = e.fdr < 0.001 ? '***' : e.fdr < 0.01 ? '**' : e.fdr < 0.05 ? '*' : '';
          const sigColor = e.fdr < 0.001 ? '#dc2626' : e.fdr < 0.01 ? '#f59e0b' : e.fdr < 0.05 ? '#059669' : '#94a3b8';
          
          return `<tr style="border-bottom: 1px solid var(--border);">
            <td style="padding: 12px 16px; font-family: monospace;">${e.event_id || '-'}</td>
            <td style="padding: 12px 16px;"><span style="background: var(--bg); padding: 4px 10px; border-radius: 12px; font-size: 12px; font-weight: 600;">${e.event_type || '-'}</span></td>
            <td style="padding: 12px 16px; font-family: monospace; font-weight: 600;">${dpsi}</td>
            <td style="padding: 12px 16px; font-family: monospace; font-weight: 600; color: ${sigColor};">${fdr} ${sigLevel}</td>
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
        evidence = parsed.map(item => `<div style="margin-bottom: 10px; padding-left: 16px; border-left: 3px solid var(--accent);">• ${typeof item === 'string' ? item : JSON.stringify(item)}</div>`).join(''); 
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
          <div style="font-size: 28px; font-weight: 800; background: var(--black); ">${geneSymbol}</div>
          <div style="font-size: 13px; color: var(--text-secondary); margin-top: 4px;">基因剪接分析报告</div>
        </div>
        <button class="btn btn-secondary" onclick="navigateTo('explorer')">返回事件列表</button>
      </div>
      
      <div class="grid grid-3" style="margin-bottom: 28px;">
        <div style="background: var(--gray-100); padding: 20px; border-radius: var(--radius); text-align: center;">
          <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: #0e7490; font-weight: 700; margin-bottom: 8px;">总事件数</div>
          <div style="font-size: 32px; font-weight: 800; color: #0e7490;">${geneEvents.length}</div>
        </div>
        <div style="background: var(--gray-100); padding: 20px; border-radius: var(--radius); text-align: center;">
          <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: #065f46; font-weight: 700; margin-bottom: 8px;">显著事件</div>
          <div style="font-size: 32px; font-weight: 800; color: #065f46;">${significantEvents.length}</div>
        </div>
        <div style="background: var(--gray-100); padding: 20px; border-radius: var(--radius); text-align: center;">
          <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: #7c3aed; font-weight: 700; margin-bottom: 8px;">平均 |ΔPSI|</div>
          <div style="font-size: 32px; font-weight: 800; color: #7c3aed;">${avgDeltaPSI.toFixed(3)}</div>
        </div>
      </div>
      
      <div style="margin-bottom: 24px; padding: 16px; background: var(--bg); border-radius: var(--radius);">
        <div style="font-size: 12px; font-weight: 700; color: var(--text-secondary); margin-bottom: 8px;">事件类型分布</div>
        <div style="font-size: 14px; line-height: 1.6;">${eventTypeSummary}</div>
      </div>
      
      <div style="margin-bottom: 24px;">
        <div style="font-size: 14px; font-weight: 700; margin-bottom: 16px; color: var(--text);">剪接事件详情</div>
        ${eventsHtml}
      </div>
      
      ${evidence ? `
      <div>
        <div style="font-size: 14px; font-weight: 700; margin-bottom: 16px; color: var(--text);">文献证据</div>
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
    alert('请先选择一个项目'); 
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
      <div style="padding: 24px; background: var(--gray-100); border-radius: var(--radius); border-left: 2px solid var(--gray-900);">
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
          <div style="font-size: 24px;"></div>
          <div>
            <div style="font-size: 16px; font-weight: 700; color: var(--success);">报告生成成功！</div>
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
      <div style="padding: 24px; background: var(--gray-100); border-radius: var(--radius); border-left: 2px solid var(--gray-900);">
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
          <div style="font-size: 24px;"></div>
          <div>
            <div style="font-size: 16px; font-weight: 700; color: var(--error);">报告生成失败</div>
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
    alert('目录中没有找到华大逐样本剪接表（如 OC_001.SE.xls）');
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
        <button onclick="removeFile(${index})" style="background: none; border: none; cursor: pointer; color: var(--error); font-size: 18px;">×</button>
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
    alert('请输入项目名称');
    return;
  }
  
  if (!analysisQuery) {
    alert('请输入分析查询');
    return;
  }
  
  if (selectedFiles.length === 0) {
    alert('请至少选择一个文件');
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
    alert(`操作失败：${error.message}\n\n请检查：\n1. 文件格式是否正确\n2. 文件大小是否过大\n3. 网络连接是否正常`);
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
      alert(`分析失败 (${analyzeResponse.status}): ${errorText}`);
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
    alert('分析完成！可在事件浏览器、可视化和报告页面查看结果。');
  }).catch(fetchError => {
    clearInterval(pollTimer);
    console.error('Analysis request error:', fetchError);
    statusDiv.innerHTML = '<span class="status status-waiting"><span class="status-dot"></span>空闲</span>';
    alert(`分析请求失败：${fetchError.message}（分析可能仍在后台运行，请稍后刷新查看）`);
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
  return num.toExponential(2);
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
    const head = ingestT('事件 ID', 'Event ID') + '</th><th>' + ingestT('基因', 'Gene') + '</th><th>' + ingestT('类型', 'Type') + '</th><th>ΔPSI</th><th>FDR</th><th>' + ingestT('坐标', 'Coordinates');
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
  if (!event) { alert('事件未找到'); return; }
  
  const gene = event.gene_symbol || event.gene || 'Unknown';
  const eventType = event.event_type || event.type || 'Unknown';
  const dpsi = event.delta_psi !== null && event.delta_psi !== undefined ? Number(event.delta_psi).toFixed(4) : 'N/A';
  const fdr = event.fdr !== null && event.fdr !== undefined ? Number(event.fdr).toExponential(3) : 'N/A';
  const pValue = event.p_value !== null && event.p_value !== undefined ? Number(event.p_value).toExponential(3) : 'N/A';
  const score = event.score !== null && event.score !== undefined ? Number(event.score).toFixed(3) : 'N/A';
  
  // Determine significance level
  let sigLevel = 'ns';
  let sigColor = '#94a3b8';
  if (fdr !== 'N/A') {
    const fdrNum = parseFloat(fdr);
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
          <button onclick="closeEventModal()" style="position: absolute; top: 20px; right: 20px; background: rgba(255,255,255,0.2); border: none; width: 36px; height: 36px; border-radius: 50%; color: white; font-size: 24px; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: all 0.2s;" onmouseover="this.style.background='rgba(255,255,255,0.3)'" onmouseout="this.style.background='rgba(255,255,255,0.2)'">×</button>
          <div style="font-size: 28px; font-weight: 600; margin-bottom: 8px;">${gene}</div>
          <div style="display: flex; gap: 12px; align-items: center; flex-wrap: wrap;">
            <span style="background: rgba(255,255,255,0.15); padding: 6px 14px; border-radius: var(--radius); font-size: 13px; font-weight: 500;">${eventType}</span>
            <span style="background: rgba(255,255,255,0.15); padding: 6px 14px; border-radius: var(--radius); font-size: 13px; font-weight: 500;">FDR ${fdr} ${sigLevel}</span>
          </div>
        </div>
        
        <!-- Content -->
        <div style="padding: 32px;">
          <!-- Key Metrics -->
          <div class="grid grid-3" style="margin-bottom: 28px;">
            <div style="background: var(--gray-100); border: 1px solid var(--gray-300); padding: 20px; border-radius: var(--radius); text-align: center;">
              <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 0.8px; color: var(--gray-700); font-weight: 600; margin-bottom: 8px;">Delta PSI</div>
              <div style="font-size: 32px; font-weight: 600; color: var(--black);">${dpsi}</div>
            </div>
            <div style="background: var(--gray-100); border: 1px solid var(--gray-300); padding: 20px; border-radius: var(--radius); text-align: center;">
              <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 0.8px; color: var(--gray-700); font-weight: 600; margin-bottom: 8px;">FDR</div>
              <div style="font-size: 32px; font-weight: 600; color: var(--black);">${fdr}</div>
            </div>
            <div style="background: var(--gray-100); border: 1px solid var(--gray-300); padding: 20px; border-radius: var(--radius); text-align: center;">
              <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 0.8px; color: var(--gray-700); font-weight: 600; margin-bottom: 8px;">评分</div>
              <div style="font-size: 32px; font-weight: 600; color: var(--black);">${score}</div>
            </div>
          </div>
          
          <!-- Biological Impact -->
          <div style="background: var(--gray-100); border-left: 2px solid var(--gray-700); padding: 20px; border-radius: var(--radius); margin-bottom: 24px;">
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
                <td style="padding: 12px 16px; font-family: var(--font-mono); font-size: 14px; color: var(--gray-900);">${pValue}</td>
              </tr>
              <tr style="border-bottom: 1px solid var(--gray-300);">
                <td style="padding: 12px 16px; font-weight: 600; color: var(--gray-700);">Delta PSI</td>
                <td style="padding: 12px 16px; font-family: var(--font-mono); font-size: 14px; color: var(--gray-900);">${dpsi}</td>
              </tr>
              <tr style="border-bottom: 1px solid var(--gray-300);">
                <td style="padding: 12px 16px; font-weight: 600; color: var(--gray-700);">FDR校正值</td>
                <td style="padding: 12px 16px; font-family: var(--font-mono); font-size: 14px; color: var(--gray-900);">${fdr}</td>
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
        window.alert("繁體中文轉換資源載入失敗，已保持簡體顯示。請檢查網路後重新整理。");
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
    " 设置": " Settings",
    " 你": " You",
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
    " 数据 Agent": " Data Agent",
    "加载并验证输入数据，检查文件格式和完整性": "Load and validate input data, checking file format and integrity",
    " 质控 Agent": " QC Agent",
    "执行质量控制检查，过滤低质量样本": "Run quality-control checks and filter low-quality samples",
    " 剪接检测 Agent": " Splicing Detection Agent",
    "使用统计模型检测可变剪接事件": "Detect alternative splicing events with statistical models",
    " 统计 Agent": " Statistics Agent",
    "计算显著性（FDR）和效应量（Delta PSI）": "Compute significance (FDR) and effect size (Delta PSI)",
    " 注释 Agent": " Annotation Agent",
    "功能注释、通路富集和文献证据收集": "Functional annotation, pathway enrichment, and literature evidence collection",
    " 解读 Agent": " Interpretation Agent",
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
    " 应用筛选": " Apply Filters",
    " 探索": " Explore",
    "搜索基因名称、事件ID或染色体位置...": "Search gene name, event ID, or chromosome position...",
    "选择图表类型": "Select chart type",
    "左侧共 13 张专业科研图，点击即可渲染": "13 publication-ready figures on the left; click to render",
    " 核心统计图": " Core Statistics",
    " 样本与质控": " Samples and QC",
    " 事件组成与机制": " Event Composition and Mechanisms",
    " AI 排序与功能富集": " AI Ranking and Functional Enrichment",
    " 火山图 Volcano": " Volcano Plot",
    " ΔPSI 累积分布 ECDF": " ΔPSI ECDF",
    " 显著性碎石图 Scree": " Significance Scree Plot",
    " 类型×显著性堆叠图": " Type × Significance Stacked Plot",
    " 剪接机制示意图 Schematic": " Splicing Mechanism Schematic",
    " PSI 热图 Heatmap": " PSI Heatmap",
    " 分组 PSI 箱线图": " Grouped PSI Box Plot",
    " 队列构成图": " Cohort Composition",
    " 候选基因排名": " Candidate Gene Ranking",
    " 评分分解堆叠图": " Score Decomposition Stacked Plot",
    " 功能富集点图": " Functional Enrichment Dot Plot",
    "差异剪接的显著性与效应量": "Significance and effect size of differential splicing",
    "ΔPSI vs -log10(FDR)，标注显著性阈值": "ΔPSI vs -log10(FDR) with significance thresholds",
    " ΔPSI 瀑布图 Waterfall": " ΔPSI Waterfall",
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
    " 事件类型分布": " Event Type Distribution",
    " 分析结果": " Analysis Results",
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
    " 模型配置": " Model configuration",
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
    " EpitopeRank 智能助手": " EpitopeRank Assistant",
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
    " MCP 工具": " MCP Tools",
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
    " 分析完成": " Analysis complete",
    " 分析失败": " Analysis failed",
    "未知错误": "Unknown error",
    " 通路富集分析结果": " Pathway Enrichment Results",
    " 文献搜索结果": " Literature Search Results",
    " 剪接事件解读": " Splice Event Interpretation",
    " 总结": " Summary",
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
    " 报告内容": " Report Contents",
    " HTML 报告": " HTML Report",
    " PDF 报告": " PDF Report",
    "完成分析后可生成包含统计结果、可视化和生物学解读的专业报告": "Generate a professional report with statistics, visualizations, and biological interpretation after analysis",
    " 提示": " Tip"
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

  var ATTRS = ["placeholder", "title"];
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
    if (Object.prototype.hasOwnProperty.call(DICT, trimmed)) {
      return replaceTrimmed(text, DICT[trimmed]);
    }
    for (var i = 0; i < RULES.length; i++) {
      var out = RULES[i](trimmed);
      if (out) return replaceTrimmed(text, out);
    }
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

  window.alert = function (message) {
    var notice = document.createElement("div");
    notice.setAttribute("role", "status");
    notice.textContent = lang === "zh" ? String(message) : translateText(String(message));
    notice.style.cssText = "position:fixed;right:24px;bottom:24px;z-index:99999;max-width:520px;padding:16px 20px;border-radius:12px;background:#12313b;color:#fff;box-shadow:0 12px 36px #0008;white-space:pre-line;font-size:14px;cursor:pointer";
    notice.onclick = function () { notice.remove(); };
    document.body.appendChild(notice);
    setTimeout(function () { notice.remove(); }, 8000);
  };
  var nativeConfirm = window.confirm.bind(window);
  window.confirm = function (message) {
    return nativeConfirm(lang === "zh" ? String(message) : translateText(String(message)));
  };

  window.__epitoperankI18n = {
    apply: applyLanguage,
    translate: translateOne,
    getLang: function () { return lang; }
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
    button.onclick = () => { dialog.close(); navigateTo(item.dataset.page); };
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
</body>
</html>"""


def render(title: str = "EpitopeRank") -> HTMLResponse:
    """Render the modern EpitopeRank web UI."""
    return HTMLResponse(content=_HTML.replace("__TITLE__", title))
