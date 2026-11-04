"""PyInstaller runtime hook for SpliceGAIP.

Runs before any application code when the frozen executable starts.

Runtime state (SQLite memory, project outputs) deliberately lives in a stable
per-user directory (``%LOCALAPPDATA%\\SpliceGAIP``) rather than next to the
executable: updating the exe in place must not wipe the lab's history.
``splicegaip.storage`` decides the location and migrates older layouts
(``<exe_dir>/splicegaip_runtime`` and ``%TEMP%\\splicegaip``) automatically.

An explicit ``SPLICEGAIP_RUNTIME_ROOT`` still wins, so portable / USB-stick
setups keep working: point it at any writable folder.
"""

import os
import sys
from pathlib import Path

if getattr(sys, "frozen", False):
    try:
        exe_dir = Path(sys.executable).resolve().parent
        # A cache dir for matplotlib font caches (keeps %USERPROFILE% clean
        # and avoids failures on read-only profiles).
        os.environ.setdefault(
            "MPLCONFIGDIR", str(exe_dir / "splicegaip_runtime" / ".mplcache")
        )
    except Exception:  # noqa: BLE001 - never block app startup over this
        pass
