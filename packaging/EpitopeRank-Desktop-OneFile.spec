# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller **onefile** spec for the EpitopeRank desktop window (desktop_ui.py).

Produces a single self-contained EpitopeRank-Desktop.exe: double-click -> the
local server starts -> the pywebview window opens with the dark ocean-lab
chrome (see desktop_ui.py for the title-bar colouring).

Trade-off: onefile ships as one file, but every launch unpacks ~145 MB into
%TEMP% (a few extra seconds before the window appears).

Build:
    python -m PyInstaller packaging/EpitopeRank-Desktop-OneFile.spec \
        --distpath dist --workpath packaging/build-temp --noconfirm
"""

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

import os

HERE = SPECPATH
ROOT = os.path.dirname(HERE)

datas = [
    (os.path.join(ROOT, "config"), "config"),
    # shipped so the launcher can drop a fill-in template next to the exe
    (os.path.join(ROOT, ".env.example"), "."),
    (os.path.join(ROOT, "epitoperank", "interface", "opencc-cn2t.js"), "epitoperank/interface"),
    (os.path.join(ROOT, "epitoperank", "interface", "OPENCC-JS-LICENSE.txt"), "epitoperank/interface"),
    (os.path.join(ROOT, "epitoperank", "interface", "OPENCC-DATA-LICENSE.txt"), "epitoperank/interface"),
    (os.path.join(ROOT, "epitoperank", "interface", "OPENCC-NOTICE.txt"), "epitoperank/interface"),
    # Bundled peptide reference tables (HLA allele catalogues + IEDB assay extract).
    (os.path.join(ROOT, "epitoperank", "peptide", "reference"), "epitoperank/peptide/reference"),
]
datas += collect_data_files("matplotlib")
datas += collect_data_files("reportlab")

hiddenimports = []
for package in (
    # the platform itself: several modules are imported lazily (inside
    # functions) so collecting everything keeps the frozen build complete
    "epitoperank",
    "autogen_agentchat",
    "autogen_agentchat.agents",
    "autogen_agentchat.teams",
    "autogen_core",
    "autogen_core.models",
    "autogen_ext",
    "autogen_ext.models",
    "autogen_ext.models.openai",
    # Agentic copilot: OpenAI-compatible native tool calling. These are
    # imported lazily inside epitoperank.llm.chat, so they must be collected
    # explicitly or the frozen build loses the copilot at runtime.
    "openai",
    "httpx",
    "httpcore",
    "jiter",
    "distro",
    "sniffio",
    "pymed",
    "uvicorn",
    "fastapi",
    "starlette",
    "python_multipart",
    "webview",
    "webview.platforms.winforms",
):
    hiddenimports += collect_submodules(package)

hiddenimports += [
    "matplotlib.backends.backend_agg",
    "matplotlib.backends.backend_svg",
    "matplotlib.backends.backend_pdf",
    "matplotlib.backends.backend_ps",
    "reportlab",
    "yaml",
    "httptools",
    "watchfiles",
    "websockets",
    "click",
    "dotenv",
    "multipart",
    "email",
    "mimetypes",
    # Hypothesis tests import scipy.stats lazily inside functions; the
    # statistics capability must be available in the frozen build.
    "scipy",
    "scipy.stats",
    "openpyxl",
    "xlrd",
]

# Explicitly add report submodules since collect_submodules may miss them
hiddenimports += [
    "epitoperank.report",
    "epitoperank.report.generator",
    # 运行时动态导入的新能力，显式列出避免冻结包漏掉。
    "epitoperank.splicing.orf_builder",
    "epitoperank.peptide.binding_tiers",
    "epitoperank.web_fetch",
]

excludes = [
    "streamlit",
    "pytest",
    "pandas",
    "seaborn",
    "plotly",
    "sqlalchemy",
    "tkinter",
    "PyQt5",
    "PySide2",
    "IPython",
    "notebook",
    # Browser automation is only used by the maintenance scripts under
    # scripts/ (tutorial screenshots). It drags a 33 MB node.exe into the
    # archive and no shipped module imports it.
    "playwright",
    "pyee",
]

block_cipher = None

a = Analysis(
    [os.path.join(ROOT, "desktop_ui.py")],
    pathex=[ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[os.path.join(HERE, "rthook_runtime.py")],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# `excludes` above stops PyInstaller's import analysis, but third-party hooks
# may still hand binaries/datas over for a package we never ship. Drop them
# explicitly so the onefile archive stays lean.
_DROP_PREFIXES = ("playwright", "pyee")


def _drop(entries):
    kept = []
    dropped = 0
    for entry in entries:
        name = str(entry[0]).replace("\\", "/").lower()
        if any(name == prefix or name.startswith(prefix + "/") for prefix in _DROP_PREFIXES):
            dropped += 1
            continue
        kept.append(entry)
    if dropped:
        print(f"[spec] dropped {dropped} playwright/pyee archive entries")
    return kept


# --- Font compliance / bundle size -----------------------------------------
# matplotlib and reportlab ship their whole font collections. All of them are
# free-licensed (DejaVu/Bitstream Vera, STIX OFL, reportlab samples), so there
# is no licensing risk, but bundling ~9 MB of unused glyphs is pure waste.
# Charts use matplotlib's default DejaVu Sans; PDF output uses reportlab's
# built-in standard-14 metrics, never an embedded TrueType font. Keep only the
# files those two paths can reach, so the executable stays smaller.
_FONT_KEEP_EXACT = {
    "dejavusans.ttf", "dejavusans-bold.ttf", "dejavusans-oblique.ttf",
    "dejavusans-boldoblique.ttf", "dejavusansdisplay.ttf",
    "dejavusansmono.ttf", "dejavusansmono-bold.ttf",
}
# matplotlib 的 font_manager 会按硬编码路径打开 LastResortHE-Regular.ttf，
# mathtext 也可能回退到 STIX/cm 系列：这些字体必须保留，删掉会导致出图失败。
_FONT_DROP_NAMES = ()


def _keep_bundled_font(name):
    """Return False for third-party font files the application never loads."""
    lowered = name.replace("\\", "/").lower()
    normalized = "/" + lowered.lstrip("/")
    if "/mpl-data/fonts/" not in normalized and "/reportlab/fonts/" not in normalized:
        return True
    base = lowered.rsplit("/", 1)[-1]
    # reportlab: keep the standard-14 AFM metrics, drop sample outline fonts.
    if "/reportlab/fonts/" in normalized:
        return base.endswith(".afm") or base.endswith(".txt")
    if base.endswith((".afm", ".txt", ".map")):
        return True
    if base in _FONT_KEEP_EXACT:
        return True
    if any(base.startswith(prefix) for prefix in _FONT_DROP_NAMES):
        return False
    # DejaVu Serif 从不作为默认字体加载，可安全移除。
    if base.startswith("dejavuserif") and base not in _FONT_KEEP_EXACT:
        return False
    # 其余（DejaVu Sans / Mono、LastResortHE、STIX、cm、AFM）全部保留。
    return True


def _drop_fonts(entries):
    kept = []
    dropped = 0
    for entry in entries:
        if _keep_bundled_font(str(entry[0])):
            kept.append(entry)
        else:
            dropped += 1
    if dropped:
        print(f"[spec] dropped {dropped} unused bundled font files")
    return kept


a.binaries = _drop(a.binaries)
a.datas = _drop(a.datas)
a.datas = _drop_fonts(a.datas)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="EpitopeRank-Desktop",
    icon=os.path.join(HERE, "icon.ico"),
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
