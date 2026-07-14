# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for AlgoVision Studio.

Build (from the project root):

    Windows :  pyinstaller --noconfirm algovision.spec
    Linux   :  pyinstaller --noconfirm algovision.spec   (produces a Linux binary)

Produces a single-file, windowed executable named "AlgoVisionStudio" in dist/.
The whole `assets/` folder (logo, icon, sample datasets) is bundled.
"""

import glob
import os
import sys

block_cipher = None

# Only bundle our own assets explicitly; PyInstaller's bundled matplotlib hook
# collects mpl-data automatically.  We avoid collect_data_files/collect_submodules
# here because their isolated-subprocess probing crashes under Wine.
datas = [("assets", "assets")]

# --- Qt plugins (platform, styles, image/icon loaders) --------------------
# PyInstaller's PyQt6 hook auto-collects these ONLY when the build host can load
# the Qt DLLs for introspection.  When cross-building under Wine that load fails
# ("QtLibraryInfo(PyQt6): failed to obtain Qt library info: DLL load ..."), so
# the hook silently ships NO plugins - and the resulting .exe then dies on real
# Windows with "no Qt platform plugin could be initialized (windows)".  Bundle
# the essential plugin groups explicitly, preserving the PyQt6/Qt6/plugins/<grp>
# layout that the pyi_rth_pyqt6 runtime hook points QT_PLUGIN_PATH at.
def _pyqt6_plugins_dir():
    try:
        import PyQt6  # package __init__ only - does not load the Qt DLLs
        cand = os.path.join(os.path.dirname(PyQt6.__file__), "Qt6", "plugins")
        if os.path.isdir(cand):
            return cand
    except Exception:
        pass
    # Fallback: derive from the interpreter location (works under Wine, where
    # sys.executable is C:\PythonXX\python.exe with a global site-packages).
    root = os.path.dirname(sys.executable)
    for base in (
        os.path.join(root, "Lib", "site-packages", "PyQt6", "Qt6", "plugins"),
        os.path.join(root, "lib", "site-packages", "PyQt6", "Qt6", "plugins"),
    ):
        if os.path.isdir(base):
            return base
    return None

binaries = []
_plugins_dir = _pyqt6_plugins_dir()
if _plugins_dir:
    for _grp in ("platforms", "styles", "imageformats", "iconengines", "tls"):
        _src = os.path.join(_plugins_dir, _grp)
        for _dll in glob.glob(os.path.join(_src, "*.dll")):
            binaries.append((_dll, os.path.join("PyQt6", "Qt6", "plugins", _grp)))
    print("algovision.spec: bundling %d Qt plugin DLL(s) from %s"
          % (len(binaries), _plugins_dir))
else:
    print("algovision.spec: WARNING - PyQt6 Qt6/plugins dir not found; "
          "relying on the auto-hook (the .exe may fail to start on Windows).")

# The Qt Agg backend is imported dynamically by matplotlib, so name it explicitly.
hiddenimports = [
    "matplotlib.backends.backend_qtagg",
    "matplotlib.backends.backend_agg",
]

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "PyQt5", "PySide6", "PySide2", "pytest"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

icon_file = "assets/icon.ico"

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="AlgoVisionStudio",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # windowed / GUI app (no console window)
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_file,
)
