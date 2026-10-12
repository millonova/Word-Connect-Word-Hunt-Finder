"""Path utilities for resolving bundled assets and user configuration.

Handles paths for both raw source execution and PyInstaller frozen executable environments.
"""

import sys
import os


def get_resource_path(relative_path: str) -> str:
    """Resolve dynamic asset paths for both dev and PyInstaller frozen runtime.

    When running inside PyInstaller, sys._MEIPASS holds the unpacked directory.
    When running in development, assets reside relative to word_connect package root.
    """
    if getattr(sys, "frozen", False):
        base_dir = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    else:
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    return os.path.normpath(os.path.join(base_dir, relative_path))


def get_app_dir() -> str:
    """Get writable root directory for user config and output files.

    In frozen mode, writes next to the executable (portable mode).
    In dev mode, writes in the word_connect project directory.
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
