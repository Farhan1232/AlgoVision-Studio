"""Builds a Qt Style Sheet (QSS) string for a given :class:`Theme` and scale.

Every pixel value (font sizes, paddings, radii, control sizes) is multiplied by
the scale factor so the whole chrome scales proportionally with the window.
Object names / classes used throughout the widgets:

    #Sidebar #TopBar #BottomBar #ContentArea
    QLabel[role="section"|"title"|"muted"|"value"|...]
    QFrame[role="card"|"info"|"divider"]
    QPushButton[variant="primary"|"ghost"|"control"|"mode"|"nav"|"milestone"]
"""

from __future__ import annotations

from .palette import Theme


def build_qss(t: Theme, s: float = 1.0) -> str:
    def p(v: float) -> int:      # scaled px
        return max(1, round(v * s))

    def f(v: float) -> int:      # scaled font px
        return max(7, round(v * s))

    return f"""
/* ---- base ------------------------------------------------------------ */
QWidget {{
    background-color: {t.window_bg};
    color: {t.text_primary};
    font-family: 'Segoe UI', 'Inter', 'DejaVu Sans', sans-serif;
    font-size: {f(13)}px;
}}
QMainWindow, #RootWidget {{ background-color: {t.window_bg}; }}
QToolTip {{
    background-color: {t.elevated_bg};
    color: {t.text_primary};
    border: 1px solid {t.border};
    padding: {p(4)}px {p(8)}px;
    border-radius: {p(6)}px;
}}

/* ---- structural bars -------------------------------------------------- */
#TopBar {{ background-color: {t.sidebar_bg}; border-bottom: 1px solid {t.border}; }}
#BottomBar {{ background-color: {t.sidebar_bg}; border-top: 1px solid {t.border}; }}
#Sidebar {{ background-color: {t.sidebar_bg}; border-right: 1px solid {t.border}; }}
#ContentArea {{ background-color: {t.window_bg}; }}
#AppTitle {{ font-size: {f(17)}px; font-weight: 700; color: {t.text_primary}; }}
#AppTagline {{ font-size: {f(10)}px; color: {t.text_muted}; letter-spacing: 1px; }}
#VersionLabel {{ color: {t.text_muted}; font-size: {f(11)}px; }}

/* ---- section headers & text ------------------------------------------ */
QLabel[role="section"] {{
    color: {t.accent}; font-size: {f(11)}px; font-weight: 700; letter-spacing: 1px;
}}
QLabel[role="title"] {{
    color: {t.text_primary}; font-size: {f(13)}px; font-weight: 700; letter-spacing: 0.5px;
}}
QLabel[role="muted"] {{ color: {t.text_secondary}; }}
QLabel[role="value"] {{ color: {t.text_primary}; font-weight: 600; }}
QLabel[role="accent"] {{ color: {t.accent}; font-weight: 700; }}
QLabel[role="ok"] {{ color: {t.success}; font-weight: 700; }}

/* ---- cards / panels --------------------------------------------------- */
QFrame[role="card"] {{
    background-color: {t.card_bg}; border: 1px solid {t.border}; border-radius: {p(12)}px;
}}
QFrame[role="info"] {{
    background-color: {t.elevated_bg}; border: 1px solid {t.border}; border-radius: {p(10)}px;
}}
QFrame[role="divider"] {{ background-color: {t.divider}; max-height: 1px; border: none; }}

/* ---- buttons ---------------------------------------------------------- */
QPushButton {{
    background-color: {t.card_bg}; color: {t.text_primary};
    border: 1px solid {t.border}; border-radius: {p(8)}px; padding: {p(7)}px {p(12)}px;
}}
QPushButton:hover {{ border-color: {t.accent}; }}
QPushButton:disabled {{ color: {t.text_muted}; border-color: {t.divider}; }}

QPushButton[variant="primary"] {{
    background-color: {t.accent}; color: #FFFFFF; border: none; font-weight: 600;
}}
QPushButton[variant="primary"]:hover {{ background-color: {t.accent_2}; }}
QPushButton[variant="primary"]:disabled {{ background-color: {t.border}; color: {t.text_muted}; }}

QPushButton[variant="ghost"] {{
    background-color: transparent; border: 1px solid {t.border}; color: {t.text_secondary};
}}
QPushButton[variant="ghost"]:hover {{ color: {t.text_primary}; border-color: {t.accent}; }}

QPushButton[variant="control"] {{
    background-color: transparent; border: 1px solid transparent; text-align: left;
    padding: {p(8)}px {p(10)}px; border-radius: {p(8)}px; color: {t.text_primary};
}}
QPushButton[variant="control"]:hover {{ background-color: {t.elevated_bg}; }}
QPushButton[variant="control"]:disabled {{ color: {t.text_muted}; }}
QPushButton[variant="control"][active="true"] {{ background-color: {t.accent}; color: #FFFFFF; }}

QPushButton[variant="mode"] {{
    background-color: transparent; border: 1px solid transparent; text-align: left;
    padding: {p(8)}px {p(10)}px; color: {t.text_secondary}; border-radius: {p(8)}px;
}}
QPushButton[variant="mode"]:hover {{ background-color: {t.elevated_bg}; color: {t.text_primary}; }}
QPushButton[variant="mode"]:checked {{ background-color: {t.accent_2}; color: #FFFFFF; font-weight: 600; }}

/* ---- timeline milestone rows ----------------------------------------- */
QPushButton[variant="milestone"] {{
    background-color: transparent; border: 1px solid transparent;
    border-radius: {p(8)}px; text-align: left; padding: 0px;
}}
QPushButton[variant="milestone"]:hover {{ background-color: {t.elevated_bg}; }}

/* ---- algorithm nav list ---------------------------------------------- */
QPushButton[variant="nav"] {{
    background-color: transparent; border: 1px solid transparent; text-align: left;
    padding: {p(8)}px {p(10)}px; border-radius: {p(8)}px; color: {t.text_primary};
}}
QPushButton[variant="nav"]:hover {{ background-color: {t.elevated_bg}; }}
QPushButton[variant="nav"]:checked {{ background-color: {t.accent_2}; color: #FFFFFF; font-weight: 600; }}

/* ---- inputs ----------------------------------------------------------- */
QComboBox, QLineEdit, QSpinBox {{
    background-color: {t.card_bg}; border: 1px solid {t.border}; border-radius: {p(8)}px;
    padding: {p(6)}px {p(10)}px; color: {t.text_primary}; selection-background-color: {t.accent};
}}
QComboBox:hover, QLineEdit:focus, QSpinBox:hover {{ border-color: {t.accent}; }}
QComboBox::drop-down {{ border: none; width: {p(22)}px; }}
QComboBox QAbstractItemView {{
    background-color: {t.panel_bg}; border: 1px solid {t.border};
    selection-background-color: {t.accent}; selection-color: #FFFFFF; outline: none;
}}
QLineEdit[state="error"] {{ border: 1px solid {t.danger}; }}

/* ---- sliders ---------------------------------------------------------- */
QSlider::groove:horizontal {{ height: {p(5)}px; border-radius: {p(3)}px; background: {t.border}; }}
QSlider::sub-page:horizontal {{ background: {t.accent}; border-radius: {p(3)}px; }}
QSlider::handle:horizontal {{
    background: {t.accent}; width: {p(15)}px; height: {p(15)}px;
    margin: -{p(6)}px 0; border-radius: {p(8)}px; border: 2px solid {t.window_bg};
}}
QSlider::handle:horizontal:hover {{ background: {t.accent_2}; }}

/* ---- progress bar ----------------------------------------------------- */
QProgressBar {{
    background-color: {t.border}; border: none; border-radius: {p(5)}px;
    height: {p(8)}px; text-align: center; color: transparent;
}}
QProgressBar::chunk {{ background-color: {t.accent_2}; border-radius: {p(5)}px; }}

/* ---- scrollbars ------------------------------------------------------- */
QScrollBar:vertical {{ background: transparent; width: {p(10)}px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {t.border}; border-radius: {p(5)}px; min-height: {p(24)}px; }}
QScrollBar::handle:vertical:hover {{ background: {t.text_muted}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
QScrollBar:horizontal {{ background: transparent; height: {p(10)}px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {t.border}; border-radius: {p(5)}px; min-width: {p(24)}px; }}
QScrollArea {{ border: none; background: transparent; }}

/* ---- badges ----------------------------------------------------------- */
QLabel[role="badge-running"] {{
    background-color: {t.accent_2}; color: #FFFFFF; border-radius: {p(10)}px;
    padding: {p(3)}px {p(12)}px; font-weight: 600; font-size: {f(11)}px;
}}
QLabel[role="badge-completed"] {{
    background-color: {t.success}; color: #FFFFFF; border-radius: {p(10)}px;
    padding: {p(3)}px {p(12)}px; font-weight: 600; font-size: {f(11)}px;
}}
QLabel[role="badge-paused"] {{
    background-color: {t.warning}; color: #1E293B; border-radius: {p(10)}px;
    padding: {p(3)}px {p(12)}px; font-weight: 600; font-size: {f(11)}px;
}}
QLabel[role="badge-reset"] {{
    background-color: {t.text_muted}; color: #FFFFFF; border-radius: {p(10)}px;
    padding: {p(3)}px {p(12)}px; font-weight: 600; font-size: {f(11)}px;
}}
"""
