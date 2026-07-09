"""Main application window - the single workspace that hosts every mode."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap, QKeySequence, QShortcut, QIcon, QGuiApplication, QFont
from PyQt6.QtWidgets import QApplication
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QStackedWidget, QFileDialog, QMessageBox
)

from ..theme.palette import get_theme
from ..theme.stylesheet import build_qss
from ..theme import scale as uiscale
from ..config import (
    APP_NAME, APP_TAGLINE, APP_VERSION, DEFAULT_DATASET, ARRAY_SIZE_DEFAULT,
    SHORTCUTS, SPEED_CHOICES, ARRAY_SIZE_MIN,
)
from ..core import registry, dataset
from ..models.session import Session, save_session, load_session
from ..export import csv_export
from ..widgets import Sidebar
from ..resources import assets_dir
from .single_view import SingleView
from .compare_view import CompareView
from .report_view import ReportView
from .presentation_view import PresentationView
from .edit_array_dialog import EditArrayDialog

ASSETS = assets_dir()


class MainWindow(QMainWindow):
    def __init__(self, theme_key: str = "dark"):
        super().__init__()
        self.theme = get_theme(theme_key)
        self.algorithm_key = "bubble"
        self.dataset = list(DEFAULT_DATASET)
        self.dataset_label = "Sample Array"
        self.mode = "single"
        self._presentation: PresentationView | None = None
        self._scale = 1.0
        # Throttle scale recomputation during continuous resizing/maximizing.
        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.setInterval(40)
        self._resize_timer.timeout.connect(self._recompute_scale)

        self.setWindowTitle(APP_NAME)
        # A modest minimum keeps every panel usable; dense panels (Statistics,
        # Code, Insights, Timeline) scroll internally rather than overlap when
        # the window is short, so the app stays comfortable on small laptops too.
        self.setMinimumSize(1024, 620)
        # Open sized to FIT the available screen (never larger than it) and
        # centred, so the window never opens off-screen on small laptops
        # (e.g. 1366x768) and the maximize / restore buttons behave correctly.
        self._open_fit_to_screen(1360, 850)
        icon = ASSETS / "icon.ico"
        if not icon.exists():
            icon = ASSETS / "logo.png"
        if icon.exists():
            self.setWindowIcon(QIcon(str(icon)))

        self._build_ui()
        self._wire()
        self._install_shortcuts()
        self.apply_theme()

        # initial load
        self.sidebar.select_algorithm(self.algorithm_key)
        self.sidebar.set_size(len(self.dataset))
        self.sidebar.set_dataset_text(self.dataset)
        self._load_single()

        # initial proportional scale for the opened window size
        self._scale = uiscale.compute_scale(self.width(), self.height())
        self._apply_scale()

    def _open_fit_to_screen(self, want_w: int, want_h: int) -> None:
        """Resize to the preferred size but never larger than the screen, and
        centre the window on the available desktop area."""
        screen = QGuiApplication.primaryScreen()
        if screen is not None:
            avail = screen.availableGeometry()
            w = max(self.minimumWidth(), min(want_w, avail.width() - 20))
            h = max(self.minimumHeight(), min(want_h, avail.height() - 20))
            self.resize(w, h)
            self.move(avail.x() + (avail.width() - w) // 2,
                      avail.y() + (avail.height() - h) // 2)
        else:
            self.resize(want_w, want_h)

    # -- UI construction ----------------------------------------------------
    def _build_ui(self):
        root = QWidget()
        root.setObjectName("RootWidget")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        outer.addWidget(self._build_topbar())

        middle = QWidget()
        mid = QHBoxLayout(middle)
        mid.setContentsMargins(0, 0, 0, 0)
        mid.setSpacing(0)

        self.sidebar = Sidebar(self.theme)
        mid.addWidget(self.sidebar)

        self.stack = QStackedWidget()
        self.stack.setObjectName("ContentArea")
        self.single = SingleView(self.theme)
        self.compare = CompareView(self.theme)
        self.report = ReportView(self.theme)
        # The single/compare workspaces are fully responsive: they resize with
        # the window via internal stretch factors, so they no longer need a
        # scroll-area wrapper or fixed minimum sizes (which used to clip panels).
        self.stack.addWidget(self.single)    # 0
        self.stack.addWidget(self.compare)   # 1
        self.stack.addWidget(self.report)    # 2 (a QScrollArea - report is long)
        mid.addWidget(self.stack, 1)

        outer.addWidget(middle, 1)
        outer.addWidget(self._build_bottombar())

    def _build_topbar(self):
        bar = QWidget()
        self.topbar = bar
        bar.setObjectName("TopBar")
        bar.setFixedHeight(62)
        h = QHBoxLayout(bar)
        h.setContentsMargins(16, 8, 16, 8)
        h.setSpacing(10)

        self.logo = QLabel()
        logo = ASSETS / "logo.png"
        if logo.exists():
            pix = QPixmap(str(logo)).scaledToHeight(
                38, Qt.TransformationMode.SmoothTransformation)
            self.logo.setPixmap(pix)
        h.addWidget(self.logo)

        titlecol = QVBoxLayout()
        titlecol.setSpacing(0)
        t = QLabel(APP_NAME); t.setObjectName("AppTitle")
        s = QLabel(APP_TAGLINE); s.setObjectName("AppTagline")
        titlecol.addWidget(t); titlecol.addWidget(s)
        h.addLayout(titlecol)
        h.addStretch(1)

        self.theme_btn = QPushButton("☾  Theme")
        self.theme_btn.setProperty("variant", "ghost")
        self.present_btn = QPushButton("🖥  Presentation Mode")
        self.present_btn.setProperty("variant", "ghost")
        h.addWidget(self.theme_btn)
        h.addWidget(self.present_btn)
        return bar

    def _build_bottombar(self):
        bar = QWidget()
        self.bottombar = bar
        bar.setObjectName("BottomBar")
        bar.setFixedHeight(52)
        h = QHBoxLayout(bar)
        h.setContentsMargins(16, 8, 16, 8)
        v = QLabel(f"{APP_NAME}  {APP_VERSION}")
        v.setObjectName("VersionLabel")
        h.addWidget(v)
        h.addStretch(1)

        self.report_btn = QPushButton("📊  Performance Report")
        self.export_btn = QPushButton("⭳  Export Report")
        self.save_btn = QPushButton("💾  Save Session")
        self.load_btn = QPushButton("📂  Load Session")
        self.report_btn.setProperty("variant", "ghost")
        self.export_btn.setProperty("variant", "primary")
        self.save_btn.setProperty("variant", "ghost")
        self.load_btn.setProperty("variant", "ghost")
        for b in (self.report_btn, self.export_btn, self.save_btn, self.load_btn):
            h.addWidget(b)
        return bar

    # -- wiring -------------------------------------------------------------
    def _wire(self):
        sb = self.sidebar
        sb.algorithmSelected.connect(self._on_algorithm)
        sb.modeChanged.connect(self._on_mode)
        sb.controlTriggered.connect(self._on_control)
        sb.randomRequested.connect(self._on_random)
        sb.shuffleRequested.connect(self._on_shuffle)
        sb.sizeChanged.connect(self._on_size)
        sb.speedChanged.connect(self._on_speed)
        sb.customArraySubmitted.connect(self._on_custom_array)

        self.single.editArrayRequested.connect(self._open_edit_array)
        self.single.statusChanged.connect(self._on_status)
        self.single.finished.connect(self._on_finished)
        self.compare.statusChanged.connect(self._on_status)

        self.theme_btn.clicked.connect(self._toggle_theme)
        self.present_btn.clicked.connect(self._enter_presentation)
        self.report_btn.clicked.connect(self._show_report)
        self.export_btn.clicked.connect(self._export)
        self.save_btn.clicked.connect(self._save_session)
        self.load_btn.clicked.connect(self._load_session)

        self.report.runAgainRequested.connect(self._run_again)
        self.report.backRequested.connect(lambda: self._set_mode("single"))
        self.report.exportRequested.connect(self._export)

    def _install_shortcuts(self):
        mapping = {
            SHORTCUTS["play"]: lambda: self._on_control("play"),
            SHORTCUTS["pause"]: lambda: self._on_control("pause"),
            SHORTCUTS["step"]: lambda: self._on_control("step"),
            SHORTCUTS["reset"]: lambda: self._on_control("reset"),
            SHORTCUTS["restart"]: lambda: self._on_control("restart"),
        }
        for seq, fn in mapping.items():
            QShortcut(QKeySequence(seq), self, activated=fn)

    # -- active view helper -------------------------------------------------
    def _active(self):
        return self.compare if self.mode == "compare" else self.single

    # -- loading ------------------------------------------------------------
    def _load_single(self):
        info = registry.get(self.algorithm_key)
        self.single.load(info, self.dataset, self.dataset_label)

    def _load_compare(self):
        self.compare.set_primary(self.algorithm_key)
        self.compare.set_dataset(self.dataset)

    # -- sidebar handlers ---------------------------------------------------
    def _on_algorithm(self, key: str):
        self.algorithm_key = key
        if self.mode == "single":
            self._load_single()
        elif self.mode == "compare":
            self._load_compare()

    def _on_mode(self, mode: str):
        self._set_mode(mode)

    def _set_mode(self, mode: str):
        self.mode = mode
        self.sidebar.set_mode(mode if mode in ("single", "compare") else "single")
        if mode == "single":
            self.stack.setCurrentIndex(0)
            self._load_single()
        elif mode == "compare":
            self.stack.setCurrentIndex(1)
            self._load_compare()
        elif mode == "report":
            self.stack.setCurrentIndex(2)

    def _on_control(self, action: str):
        view = self._active()
        if action == "play":
            view.play()
        elif action == "pause":
            view.pause()
        elif action == "step":
            view.step()
        elif action == "restart":
            view.restart()
        elif action == "reset":
            view.reset()
        elif action == "toggle":
            if self.single.player.is_playing():
                self.single.pause()
            else:
                self.single.play()
        elif action == "prev":
            p = self.single.player
            p.seek(max(0, p.index - 1))

    def _on_random(self):
        size = self.sidebar.current_size()
        self.dataset = dataset.random_dataset(size)
        self.dataset_label = "Random Array"
        self._reload_active()

    def _on_shuffle(self):
        self.dataset = dataset.shuffle_dataset(self.dataset)
        self.dataset_label = "Shuffled Array"
        self._reload_active()

    def _on_size(self, size: int):
        # regenerate a dataset of the requested size (config happens pre-run)
        self.dataset = dataset.random_dataset(size)
        self.dataset_label = "Random Array"
        self._reload_active()

    def _on_custom_array(self, values: list):
        """Apply a validated custom array from the sidebar (available in all
        modes, including Comparison Mode) - PRD 7.3."""
        self.dataset = list(values)
        self.dataset_label = "Custom Array"
        self.sidebar.set_size(len(self.dataset))
        self._reload_active()

    def _on_speed(self, mult: float):
        self.single.set_speed(mult)
        self.compare.set_speed(mult)

    def _reload_active(self):
        self.sidebar.set_dataset_text(self.dataset)
        if self.mode == "compare":
            self._load_compare()
        else:
            self._load_single()

    # -- status / lock ------------------------------------------------------
    def _on_status(self, status: str):
        running = status in ("Running",)
        self.sidebar.set_running_locked(running)

    def _on_finished(self):
        self.sidebar.set_running_locked(False)

    # -- edit array ---------------------------------------------------------
    def _open_edit_array(self):
        dlg = EditArrayDialog(self.theme, self.dataset, self.sidebar.current_size(), self)
        dlg.setStyleSheet(self.styleSheet())
        if dlg.exec() and dlg.result_dataset() is not None:
            self.dataset = dlg.result_dataset()
            self.dataset_label = "Custom Array"
            self.sidebar.set_size(len(self.dataset))
            self._reload_active()

    # -- theme --------------------------------------------------------------
    def _toggle_theme(self):
        self.theme = get_theme("light" if self.theme.is_dark else "dark")
        self.apply_theme()
        for v in (self.single, self.compare, self.report):
            v.set_theme(self.theme)
        self.sidebar.set_theme(self.theme)
        if self._presentation:
            self._presentation.set_theme(self.theme)
        self.theme_btn.setText("☀  Theme" if self.theme.is_dark else "☾  Theme")

    def apply_theme(self):
        self.setStyleSheet(build_qss(self.theme, self._scale))

    # -- responsive scaling -------------------------------------------------
    def resizeEvent(self, e):
        super().resizeEvent(e)
        # Debounce: only recompute once resizing settles.
        self._resize_timer.start()

    def _recompute_scale(self):
        s = uiscale.compute_scale(self.width(), self.height())
        if abs(s - self._scale) < 0.015:
            return
        self._scale = s
        self._apply_scale()

    def _apply_scale(self):
        """Propagate the current scale to the whole UI: stylesheet, base font,
        structural bars and every view/widget that carries inline sizing."""
        s = self._scale
        uiscale.set_scale(s)
        # base application font (drives all text without an explicit size)
        app = QApplication.instance()
        if app is not None:
            f = QFont(app.font())
            f.setPointSizeF(max(6.5, 10.0 * s))
            app.setFont(f)
        self.setStyleSheet(build_qss(self.theme, s))
        # structural bar heights
        self.topbar.setFixedHeight(uiscale.sp(62))
        self.bottombar.setFixedHeight(uiscale.sp(52))
        # the sidebar auto-fits to the middle-area height (no scrolling)
        mid_h = self.height() - self.topbar.height() - self.bottombar.height()
        self.sidebar.apply_scale(s, avail=mid_h)
        # views
        for w in (self.single, self.compare, self.report):
            if hasattr(w, "apply_scale"):
                w.apply_scale(s)
        if self._presentation is not None and hasattr(self._presentation, "apply_scale"):
            self._presentation.apply_scale(s)

    # -- presentation -------------------------------------------------------
    def _enter_presentation(self):
        if self.mode != "single":
            self._set_mode("single")
            self.sidebar.set_mode("single")
        # Presentation is fullscreen: scale it to the actual screen size.
        screen = QGuiApplication.primaryScreen()
        if screen is not None:
            g = screen.geometry()
            pv_scale = uiscale.compute_scale(g.width(), g.height())
        else:
            pv_scale = self._scale
        uiscale.set_scale(pv_scale)
        pv = PresentationView(self.theme)
        pv.setStyleSheet(build_qss(self.theme, pv_scale))
        pv.apply_scale(pv_scale)
        pv.bind(self.single)
        pv.exitRequested.connect(self._exit_presentation)
        pv.controlTriggered.connect(self._on_control)
        pv.speedDelta.connect(self._on_speed_delta)
        self._presentation = pv
        pv.showFullScreen()
        pv.setFocus()
        # restore the main-window scale afterwards
        uiscale.set_scale(self._scale)

    def _exit_presentation(self):
        if self._presentation:
            self._presentation.close()
            self._presentation.deleteLater()
            self._presentation = None

    def _on_speed_delta(self, delta: int):
        cur = self.sidebar.current_speed()
        idx = SPEED_CHOICES.index(cur) if cur in SPEED_CHOICES else 2
        idx = max(0, min(len(SPEED_CHOICES) - 1, idx + delta))
        self.sidebar.set_speed(SPEED_CHOICES[idx])

    # -- report / export ----------------------------------------------------
    def _show_report(self):
        info = registry.get(self.algorithm_key)
        frames = info.trace(list(self.dataset))
        self.report.show_report(info, self.dataset, frames)
        self.mode = "report"
        self.stack.setCurrentIndex(2)

    def _run_again(self):
        self._set_mode("single")
        self.single.restart()

    def _export(self):
        info = registry.get(self.algorithm_key)
        if self.mode == "compare":
            self._export_comparison()
            return
        frames = self.single.player.frames or info.trace(list(self.dataset))
        final = frames[-1]
        default = csv_export.default_filename(info)
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Execution Report", default, "CSV Files (*.csv)")
        if not path:
            return
        csv_export.export_single(info, self.dataset, final, path)
        QMessageBox.information(self, "Export Complete",
                                f"Execution report saved to:\n{path}")

    def _export_comparison(self):
        ia = self.compare.left.info
        ib = self.compare.right.info
        fa = self.compare.left.frames[-1]
        fb = self.compare.right.frames[-1]
        rows_a = csv_export.build_rows(ia, self.compare.original, fa)
        rows_b = csv_export.build_rows(ib, self.compare.original, fb)
        from ..core.player import frame_exec_seconds
        winner = ia.name if (frame_exec_seconds(fa), fa.comparisons + fa.swaps) <= \
            (frame_exec_seconds(fb), fb.comparisons + fb.swaps) else ib.name
        default = f"{ia.name.replace(' ','')}_vs_{ib.name.replace(' ','')}.csv"
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Comparison Report", default, "CSV Files (*.csv)")
        if not path:
            return
        csv_export.export_comparison(rows_a, rows_b, ia, ib, winner, path)
        QMessageBox.information(self, "Export Complete", f"Comparison report saved to:\n{path}")

    # -- session ------------------------------------------------------------
    def _save_session(self):
        session = Session(
            algorithm=self.algorithm_key,
            dataset=list(self.dataset),
            array_size=len(self.dataset),
            speed=self.sidebar.current_speed(),
            theme=self.theme.key,
            mode=self.mode if self.mode in ("single", "compare") else "single",
            compare_algorithm=self.compare.combo_b.currentData(),
        )
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Session", "algovision_session.json", "JSON Files (*.json)")
        if not path:
            return
        save_session(session, path)
        QMessageBox.information(self, "Session Saved", f"Session saved to:\n{path}")

    def _load_session(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Load Session", "", "JSON Files (*.json)")
        if not path:
            return
        try:
            session = load_session(path)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Load Failed", f"Could not load session:\n{exc}")
            return
        if session.theme != self.theme.key:
            self._toggle_theme()
        self.algorithm_key = session.algorithm
        self.dataset = list(session.dataset) or list(DEFAULT_DATASET)
        self.dataset_label = "Loaded Session"
        self.sidebar.select_algorithm(self.algorithm_key)
        self.sidebar.set_size(len(self.dataset))
        self.sidebar.set_dataset_text(self.dataset)
        self.sidebar.set_speed(session.speed if session.speed in SPEED_CHOICES else 1.0)
        if session.mode == "compare":
            self.compare.load(session.algorithm, session.compare_algorithm, self.dataset)
            self._set_mode("compare")
        else:
            self._set_mode("single")
        QMessageBox.information(self, "Session Loaded", "Session loaded successfully.")
