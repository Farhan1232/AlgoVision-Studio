"""Main application window - the single workspace that hosts every mode."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QKeySequence, QShortcut, QIcon
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QStackedWidget, QFileDialog, QMessageBox, QScrollArea, QFrame
)

from ..theme.palette import get_theme
from ..theme.stylesheet import build_qss
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

        self.setWindowTitle(APP_NAME)
        self.resize(1360, 860)
        self.setMinimumSize(960, 640)
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
        self._load_single()

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
        # Wrap single/compare in scroll areas so the workspace stays usable and
        # scrollable at any window size instead of clipping (responsiveness).
        self.single.setMinimumSize(1000, 760)
        self.compare.setMinimumSize(1120, 800)
        self.stack.addWidget(self._scrollable(self.single))   # 0
        self.stack.addWidget(self._scrollable(self.compare))  # 1
        self.stack.addWidget(self.report)                     # 2 (already a QScrollArea)
        mid.addWidget(self.stack, 1)

        outer.addWidget(middle, 1)
        outer.addWidget(self._build_bottombar())

    @staticmethod
    def _scrollable(widget: QWidget) -> QScrollArea:
        sa = QScrollArea()
        sa.setWidgetResizable(True)
        sa.setFrameShape(QFrame.Shape.NoFrame)
        sa.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        sa.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        sa.setWidget(widget)
        return sa

    def _build_topbar(self):
        bar = QWidget()
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

    def _on_speed(self, mult: float):
        self.single.set_speed(mult)
        self.compare.set_speed(mult)

    def _reload_active(self):
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
        self.setStyleSheet(build_qss(self.theme))

    # -- presentation -------------------------------------------------------
    def _enter_presentation(self):
        if self.mode != "single":
            self._set_mode("single")
            self.sidebar.set_mode("single")
        pv = PresentationView(self.theme)
        pv.setStyleSheet(build_qss(self.theme))
        pv.bind(self.single)
        pv.exitRequested.connect(self._exit_presentation)
        pv.controlTriggered.connect(self._on_control)
        pv.speedDelta.connect(self._on_speed_delta)
        self._presentation = pv
        pv.showFullScreen()
        pv.setFocus()

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
        self.sidebar.set_speed(session.speed if session.speed in SPEED_CHOICES else 1.0)
        if session.mode == "compare":
            self.compare.load(session.algorithm, session.compare_algorithm, self.dataset)
            self._set_mode("compare")
        else:
            self._set_mode("single")
        QMessageBox.information(self, "Session Loaded", "Session loaded successfully.")
