"""Windowed desktop launcher for the local SpliceGAIP application."""

from __future__ import annotations

import ctypes
import sys
import threading
import time
import urllib.request
from ctypes import wintypes

import uvicorn
import webview

from serve_ui import _free_port, _load_local_env, _write_env_templates
from splicegaip.api.app import create_app

WINDOW_TITLE = "SpliceGAIP"

# Title-bar palette mirrored from splicegaip/interface/web_ui.py (:root), so the
# native window chrome continues the app's ocean-lab theme. Without this the
# caption is painted white whenever Windows itself runs a light theme, and the
# bright strip fights the dark UI underneath it.
_CAPTION_BG = "#07151e"  # --bg
_CAPTION_FG = "#e8f5f4"  # --text
_CAPTION_BORDER = "#173944"  # --surface-3

# DwmSetWindowAttribute ids. 20 exists since Windows 10 2004, the colour
# attributes (34/35/36) since Windows 11 21H2.
_DWMWA_USE_IMMERSIVE_DARK_MODE = 20
_DWMWA_BORDER_COLOR = 34
_DWMWA_CAPTION_COLOR = 35
_DWMWA_TEXT_COLOR = 36

_SWP_NOSIZE = 0x0001
_SWP_NOMOVE = 0x0002
_SWP_NOZORDER = 0x0004
_SWP_NOACTIVATE = 0x0010
_SWP_FRAMECHANGED = 0x0020


def _colorref(hex_color: str) -> int:
    """Pack ``#rrggbb`` into the ``0x00BBGGRR`` COLORREF DWM expects."""
    value = hex_color.lstrip("#")
    red, green, blue = (int(value[index : index + 2], 16) for index in (0, 2, 4))
    return red | (green << 8) | (blue << 16)


def _dwm_set(hwnd: int, attribute: int, value: int) -> bool:
    """Apply one DWMWA_* attribute; False when the OS rejects it."""
    try:
        setter = ctypes.windll.dwmapi.DwmSetWindowAttribute
    except (AttributeError, OSError):  # pragma: no cover - non-Windows only
        return False
    setter.argtypes = [wintypes.HWND, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD]
    setter.restype = ctypes.c_long
    packed = ctypes.c_int(value)
    try:
        return setter(wintypes.HWND(hwnd), attribute, ctypes.byref(packed), ctypes.sizeof(packed)) == 0
    except OSError:  # pragma: no cover - dwmapi unavailable (remote session)
        return False


def _apply_dark_window_chrome(hwnd: int) -> bool:
    """Paint the native caption in the app's dark palette. Idempotent."""
    if not hwnd:
        return False
    dark = _dwm_set(hwnd, _DWMWA_USE_IMMERSIVE_DARK_MODE, 1)
    caption = _dwm_set(hwnd, _DWMWA_CAPTION_COLOR, _colorref(_CAPTION_BG))
    _dwm_set(hwnd, _DWMWA_TEXT_COLOR, _colorref(_CAPTION_FG))
    _dwm_set(hwnd, _DWMWA_BORDER_COLOR, _colorref(_CAPTION_BORDER))
    try:
        # Force a frame repaint; without it Windows sometimes keeps the cached
        # light caption until the next resize.
        ctypes.windll.user32.SetWindowPos(
            wintypes.HWND(hwnd),
            None,
            0,
            0,
            0,
            0,
            _SWP_NOSIZE | _SWP_NOMOVE | _SWP_NOZORDER | _SWP_NOACTIVATE | _SWP_FRAMECHANGED,
        )
    except OSError:  # pragma: no cover - defensive
        pass
    return dark or caption


_OWN_PROCESS_ID = ctypes.windll.kernel32.GetCurrentProcessId() if sys.platform == "win32" else 0


def _find_process_window(title: str) -> int:
    """Return the HWND of this process' top-level window named ``title``."""
    user32 = ctypes.windll.user32
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    user32.GetWindowTextLengthW.restype = ctypes.c_int
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetWindowTextW.restype = ctypes.c_int
    user32.EnumWindows.argtypes = [ctypes.c_void_p, wintypes.LPARAM]
    found: list[int] = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def callback(hwnd: int, _param: int) -> bool:
        process_id = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(process_id))
        if process_id.value != _OWN_PROCESS_ID or not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, length + 1)
        if buffer.value == title:
            found.append(int(hwnd))
            return False  # stop enumerating
        return True

    try:
        user32.EnumWindows(ctypes.cast(callback, ctypes.c_void_p), 0)
    except OSError:  # pragma: no cover - defensive
        return 0
    return found[0] if found else 0


def _window_handle(window: webview.Window) -> int:
    """Current HWND for ``window`` (native form first, then enumeration)."""
    native = getattr(window, "native", None)
    if native is not None:
        try:
            handle = int(native.Handle.ToInt64())
            if handle:
                return handle
        except Exception:  # noqa: BLE001 - handle not created yet
            pass
    return _find_process_window(WINDOW_TITLE)


def _install_dark_chrome(window: webview.Window) -> None:
    """Keep the caption dark once the window exists and stops restyling.

    pywebview sets its own title-bar theme from the Windows light/dark
    preference while the form is being built, so the override has to be
    re-applied over the first couple of seconds instead of just once.
    """
    if sys.platform != "win32":
        return

    def worker() -> None:
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            if _apply_dark_window_chrome(_window_handle(window)):
                break
            time.sleep(0.2)
        for _ in range(6):
            time.sleep(0.4)
            _apply_dark_window_chrome(_window_handle(window))

    threading.Thread(target=worker, name="splicegaip-window-chrome", daemon=True).start()


def main() -> int:
    _load_local_env()
    _write_env_templates()
    port = _free_port(8800)
    url = f"http://127.0.0.1:{port}/"
    server = uvicorn.Server(uvicorn.Config(create_app(), host="127.0.0.1", port=port, log_level="error"))
    worker = threading.Thread(target=server.run, name="splicegaip-api", daemon=True)
    worker.start()

    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        if not worker.is_alive():
            raise RuntimeError("本地分析服务未能启动。")
        try:
            with urllib.request.urlopen(url + "api/health", timeout=1) as response:
                if response.status == 200:
                    break
        except Exception:
            time.sleep(0.25)
    else:
        server.should_exit = True
        raise RuntimeError("本地分析服务启动超时。")

    try:
        window = webview.create_window(
            WINDOW_TITLE,
            url,
            width=1440,
            height=900,
            min_size=(1000, 650),
            background_color=_CAPTION_BG,
        )
        _install_dark_chrome(window)
        webview.start(gui="edgechromium", private_mode=False)
    finally:
        server.should_exit = True
        worker.join(timeout=5)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        # A windowed executable has no console in which to show startup errors.
        import ctypes

        ctypes.windll.user32.MessageBoxW(0, str(error), "SpliceGAIP 启动失败", 0x10)
        raise
