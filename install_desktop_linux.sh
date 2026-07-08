#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Register AlgoVision Studio with the Linux desktop so its logo appears in the
# taskbar / dock / Alt-Tab switcher and app menu (like Chrome, VS Code, etc.).
#
# Installs (per-user, no sudo needed):
#   * the logo into the hicolor icon theme
#   * an algovision-studio.desktop launcher
# ---------------------------------------------------------------------------
set -e

APP_ID="algovision-studio"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Pick the interpreter: prefer the project venv, else python3.
if [ -x "$PROJECT_DIR/.venv/bin/python" ]; then
    PYTHON="$PROJECT_DIR/.venv/bin/python"
else
    PYTHON="$(command -v python3)"
fi

ICON_SRC="$PROJECT_DIR/assets/icon.png"
DESKTOP_DIR="$HOME/.local/share/applications"
ICON_BASE="$HOME/.local/share/icons/hicolor"

echo "Installing icons into the hicolor theme..."
for SIZE in 48 64 128 256 512; do
    DEST="$ICON_BASE/${SIZE}x${SIZE}/apps"
    mkdir -p "$DEST"
    if command -v convert >/dev/null 2>&1; then
        convert "$ICON_SRC" -resize ${SIZE}x${SIZE} "$DEST/$APP_ID.png"
    else
        # no ImageMagick: just copy the 512px icon (the DE will scale it)
        cp "$ICON_SRC" "$DEST/$APP_ID.png"
    fi
done

echo "Writing $DESKTOP_DIR/$APP_ID.desktop ..."
mkdir -p "$DESKTOP_DIR"
cat > "$DESKTOP_DIR/$APP_ID.desktop" <<EOF
[Desktop Entry]
Type=Application
Version=1.0
Name=AlgoVision Studio
GenericName=Sorting Algorithm Visualizer
Comment=Offline desktop app for learning sorting algorithms
Exec=$PYTHON $PROJECT_DIR/main.py
Path=$PROJECT_DIR
Icon=$APP_ID
Terminal=false
Categories=Education;Science;Development;
Keywords=sorting;algorithm;visualizer;education;
StartupNotify=true
StartupWMClass=$APP_ID
EOF
chmod +x "$DESKTOP_DIR/$APP_ID.desktop"

# Refresh caches (best effort; safe to ignore failures).
command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$DESKTOP_DIR" || true
command -v gtk-update-icon-cache   >/dev/null 2>&1 && gtk-update-icon-cache -f -t "$ICON_BASE" >/dev/null 2>&1 || true

echo
echo "Done. AlgoVision Studio is registered."
echo "You can now launch it from your app menu, and its logo will show in the"
echo "taskbar / dock / Alt-Tab switcher."
