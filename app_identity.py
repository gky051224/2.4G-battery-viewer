"""Window/taskbar identity, separate from dynamic battery tray icons."""
from pathlib import Path
import ctypes

APP_ID = "GM3323DBatteryViewer.Desktop.1"
ICON_PATH = Path(__file__).resolve().parent / "assets" / "app.ico"


def set_process_identity():
    try:
        shell = ctypes.WinDLL("shell32")
        shell.SetCurrentProcessExplicitAppUserModelID.argtypes = [ctypes.c_wchar_p]
        shell.SetCurrentProcessExplicitAppUserModelID.restype = ctypes.c_long
        shell.SetCurrentProcessExplicitAppUserModelID(APP_ID)
    except (OSError, AttributeError):
        pass


def set_window_icon(root):
    if ICON_PATH.is_file():
        root.iconbitmap(default=str(ICON_PATH))
        root.iconbitmap(str(ICON_PATH))
