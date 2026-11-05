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


a.binaries = _drop(a.binaries)
a.datas = _drop(a.datas)

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
