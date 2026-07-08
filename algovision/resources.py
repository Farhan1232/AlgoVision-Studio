"""Locate bundled assets in both development and PyInstaller-frozen modes."""

from __future__ import annotations

import sys
from pathlib import Path


def assets_dir() -> Path:
    """Return the assets directory, whether running from source or a bundle."""
    if getattr(sys, "frozen", False):
        # PyInstaller: onefile extracts to _MEIPASS; onedir sits next to the exe
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
        candidate = base / "assets"
        if candidate.exists():
            return candidate
        return Path(sys.executable).resolve().parent / "assets"
    # running from source: <project_root>/assets
    return Path(__file__).resolve().parent.parent / "assets"


def asset(name: str) -> Path:
    return assets_dir() / name
