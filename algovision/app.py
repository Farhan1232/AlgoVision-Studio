"""Application bootstrap: QApplication, splash screen, main window."""

from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap, QFont, QIcon
from PyQt6.QtWidgets import QApplication, QSplashScreen, QLabel

from .config import APP_NAME
from .theme.palette import get_theme
from .views.main_window import MainWindow
from .resources import assets_dir

ASSETS = assets_dir()

# Must match the installed .desktop file name (algovision-studio.desktop) so the
# desktop environment shows our logo in the taskbar / dock / Alt-Tab switcher.
DESKTOP_FILE_NAME = "algovision-studio"


def _make_splash() -> QSplashScreen | None:
    logo = ASSETS / "logo.png"
    if not logo.exists():
        return None
    pix = QPixmap(str(logo)).scaledToWidth(
        520, Qt.TransformationMode.SmoothTransformation)
    splash = QSplashScreen(pix)
    splash.showMessage(
        "Loading AlgoVision Studio…",
        Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter,
        Qt.GlobalColor.white,
    )
    return splash


def run(theme_key: str = "dark") -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    # Associate the window with our desktop entry (drives the taskbar/dock icon
    # on GNOME/Wayland) and set an application-wide icon (title bar / X11 / tray).
    app.setDesktopFileName(DESKTOP_FILE_NAME)
    for _name in ("icon.png", "logo.png"):
        _p = ASSETS / _name
        if _p.exists():
            app.setWindowIcon(QIcon(str(_p)))
            break
    app.setFont(QFont("Segoe UI", 10))

    splash = _make_splash()
    if splash:
        splash.show()
        app.processEvents()

    window = MainWindow(theme_key=theme_key)

    def _show():
        window.show()
        if splash:
            splash.finish(window)

    QTimer.singleShot(900 if splash else 0, _show)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(run())
