"""Native Desktop Application Launcher for Personal AI Workspace (Windows & macOS).

- Configures per-user persistent local storage in packaged mode.
- Runs Alembic migrations automatically (preserving existing user data).
- Starts FastAPI + compiled React frontend on a free localhost port in a background thread.
- Opens a real native desktop window using pywebview (Windows WebView2 / macOS Cocoa WKWebView)
  with no browser address bar, tabs, or bookmarks.
"""

import os
from pathlib import Path
import platform
import socket
import sys
import threading
import time
import urllib.request

from alembic import command as alembic_command
from alembic.config import Config as AlembicConfig
import uvicorn
import webview


def _resolve_user_storage_dir() -> Path:
    system = platform.system()
    if system == "Windows":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return base / "PersonalAIWorkspace" / "storage"
    if system == "Darwin":
        return Path.home() / "Library" / "Application Support" / "PersonalAIWorkspace" / "storage"
    return Path.home() / ".local" / "share" / "PersonalAIWorkspace" / "storage"


def _find_free_port(preferred: int = 8000) -> int:
    for port in (preferred, *range(8001, 8050)):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    return preferred


def _run_migrations() -> None:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base_dir = Path(sys._MEIPASS)  # type: ignore[attr-defined]
    else:
        base_dir = Path(__file__).resolve().parent

    cfg = AlembicConfig(str(base_dir / "alembic.ini"))
    cfg.set_main_option("script_location", str(base_dir / "alembic"))
    alembic_command.upgrade(cfg, "head")


def _wait_for_server(health_url: str, timeout_seconds: float = 15.0) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(health_url, timeout=1.0) as resp:
                if resp.status == 200:
                    return
        except Exception:
            time.sleep(0.2)


APP_USER_MODEL_ID = "PersonalAIWorkspace.Desktop"


def _find_icon_path() -> Path | None:
    candidates = []
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        candidates.append(Path(sys._MEIPASS) / "app_icon.ico")  # type: ignore[attr-defined]
    here = Path(__file__).resolve().parent
    candidates.append(here.parent / "packaging" / "icons" / "app_icon.ico")
    return next((p for p in candidates if p.exists()), None)


def _set_windows_app_id() -> None:
    """Give the process its own taskbar identity so Windows shows our icon, not python's."""
    if platform.system() != "Windows":
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
    except Exception:
        pass


def _apply_window_icon(title: str, icon_path: Path | None) -> None:
    """Set the native window + taskbar icon via Win32 (WM_SETICON)."""
    if platform.system() != "Windows" or icon_path is None:
        return
    try:
        import ctypes

        user32 = ctypes.windll.user32
        user32.FindWindowW.restype = ctypes.c_void_p
        user32.LoadImageW.restype = ctypes.c_void_p
        user32.SendMessageW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p]
        hwnd = None
        for _ in range(50):
            hwnd = user32.FindWindowW(None, title)
            if hwnd:
                break
            time.sleep(0.1)
        if not hwnd:
            return
        IMAGE_ICON, LR_LOADFROMFILE, WM_SETICON = 1, 0x10, 0x80
        big = user32.LoadImageW(None, str(icon_path), IMAGE_ICON, 256, 256, LR_LOADFROMFILE)
        small = user32.LoadImageW(None, str(icon_path), IMAGE_ICON, 32, 32, LR_LOADFROMFILE)
        if big:
            user32.SendMessageW(hwnd, WM_SETICON, 1, big)
        if small:
            user32.SendMessageW(hwnd, WM_SETICON, 0, small)
    except Exception:
        pass


def main() -> None:
    _set_windows_app_id()
    if getattr(sys, "frozen", False):
        storage_dir = _resolve_user_storage_dir()
        storage_dir.mkdir(parents=True, exist_ok=True)
        os.environ.setdefault("STORAGE_DIR", str(storage_dir))
        os.environ.setdefault("ENVIRONMENT", "production")

    port = _find_free_port(int(os.environ.get("BACKEND_PORT", "8000")))
    url = f"http://127.0.0.1:{port}"
    os.environ["BACKEND_PORT"] = str(port)
    os.environ["CORS_ORIGINS"] = f"{url},http://localhost:{port}"

    _run_migrations()

    from app.main import app  # Import after env vars are configured

    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)

    server_thread = threading.Thread(target=server.run, daemon=True)
    server_thread.start()

    _wait_for_server(f"{url}/api/v1/health")

    # Open a true native desktop application window (WebView2 on Windows, WKWebView on macOS)
    window = webview.create_window(
        title="Personal AI Workspace",
        url=url,
        width=1340,
        height=860,
        min_size=(960, 640),
        background_color="#141413",
    )
    icon_path = _find_icon_path()
    window.events.shown += lambda: _apply_window_icon("Personal AI Workspace", icon_path)
    webview.start()

    # Gracefully stop local FastAPI server when the desktop window is closed
    server.should_exit = True


if __name__ == "__main__":
    main()
