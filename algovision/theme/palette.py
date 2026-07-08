"""Colour tokens for AlgoVision Studio.

Two families of colours live here:

* STATE_COLORS  - the "visual language" for array element states.  These are
  intentionally *theme independent* so that a green "sorted" block means the
  same thing in the light and dark themes (PRD 5.3 / sorting-block-states.png).
* Theme         - UI chrome colours (backgrounds, text, borders, accents) that
  DO change between the Light and Dark themes (light-theme.png / dark-theme.png).
"""

from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Visual language for array element states (PRD Section 5.3).
# Keys are used everywhere a block/node state is referenced.
# ---------------------------------------------------------------------------
STATE_DEFAULT = "default"
STATE_COMPARING = "comparing"
STATE_SWAPPING = "swapping"
STATE_PIVOT = "pivot"
STATE_SORTED = "sorted"
STATE_SELECTED = "selected"      # active minimum / key / root-max
STATE_TARGET = "target"          # target / found (teal)
STATE_DISABLED = "disabled"      # out of range / out of heap

STATE_COLORS = {
    STATE_DEFAULT:  "#2E6CE0",   # Blue   - not yet processed
    STATE_COMPARING: "#EAB308",  # Yellow - being compared
    STATE_SWAPPING: "#F97316",   # Orange - moving to a new position
    STATE_PIVOT:    "#EF4444",   # Red    - Quick Sort pivot
    STATE_SORTED:   "#22C55E",   # Green  - final sorted position
    STATE_SELECTED: "#8B5CF6",   # Purple - selected / root / key
    STATE_TARGET:   "#14B8A6",   # Teal   - target / found
    STATE_DISABLED: "#64748B",   # Gray   - out of range / out of heap
}

# The legend rows shown under the visualization for a *generic* algorithm.
LEGEND_STANDARD = [
    (STATE_DEFAULT, "Default"),
    (STATE_COMPARING, "Comparing"),
    (STATE_SWAPPING, "Swapping"),
    (STATE_SORTED, "Sorted"),
]
# Quick Sort adds the pivot; Heap Sort uses its own legend (see below).
LEGEND_PIVOT = LEGEND_STANDARD + [(STATE_PIVOT, "Pivot")]
LEGEND_SELECTED = LEGEND_STANDARD + [(STATE_SELECTED, "Selected")]
LEGEND_HEAP = [
    (STATE_SELECTED, "Root / Max"),
    (STATE_COMPARING, "Comparing"),
    (STATE_SWAPPING, "Swapping"),
    (STATE_DEFAULT, "Heap"),
    (STATE_SORTED, "Sorted"),
    (STATE_DISABLED, "Out of Heap"),
]


@dataclass(frozen=True)
class Theme:
    """UI chrome colours for one theme."""
    key: str
    name: str

    # window / surfaces
    window_bg: str
    sidebar_bg: str
    panel_bg: str
    card_bg: str
    canvas_bg: str          # matplotlib figure background
    elevated_bg: str        # info / explanation boxes

    # text
    text_primary: str
    text_secondary: str
    text_muted: str

    # lines
    border: str
    divider: str

    # accents
    accent: str             # primary blue used for section headings/links
    accent_2: str           # purple accent
    accent_soft: str        # translucent accent fill for selections

    # semantic
    success: str
    warning: str
    danger: str

    # block text colour that sits on top of the state colours
    block_text: str
    block_index_text: str

    # matplotlib grid / axis colour
    grid: str

    @property
    def is_dark(self) -> bool:
        return self.key == "dark"


DARK = Theme(
    key="dark",
    name="Dark",
    window_bg="#0A0E1A",
    sidebar_bg="#0D1324",
    panel_bg="#111A2E",
    card_bg="#0F1728",
    canvas_bg="#0F1728",
    elevated_bg="#152039",
    text_primary="#E7ECF5",
    text_secondary="#9FB0CC",
    text_muted="#6B7A99",
    border="#22304C",
    divider="#1A2740",
    accent="#3B82F6",
    accent_2="#8B5CF6",
    accent_soft="rgba(139, 92, 246, 0.18)",
    success="#22C55E",
    warning="#EAB308",
    danger="#EF4444",
    block_text="#FFFFFF",
    block_index_text="#9FB0CC",
    grid="#22304C",
)

LIGHT = Theme(
    key="light",
    name="Light",
    window_bg="#FFFFFF",
    sidebar_bg="#FBFCFE",
    panel_bg="#FFFFFF",
    card_bg="#F8FAFC",
    canvas_bg="#FFFFFF",
    elevated_bg="#EFF4FB",
    text_primary="#1E293B",
    text_secondary="#546178",
    text_muted="#8A97AC",
    border="#E2E8F0",
    divider="#EDF1F6",
    accent="#2563EB",
    accent_2="#7C3AED",
    accent_soft="rgba(124, 58, 237, 0.12)",
    success="#16A34A",
    warning="#CA8A04",
    danger="#DC2626",
    block_text="#FFFFFF",
    block_index_text="#64748B",
    grid="#E2E8F0",
)

THEMES = {"dark": DARK, "light": LIGHT}


def get_theme(key: str) -> Theme:
    return THEMES.get(key, DARK)
