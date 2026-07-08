"""Global configuration constants for AlgoVision Studio.

All supported value ranges come straight from the PRD (Section 9).
Nothing here depends on Qt so it can be imported by headless tests too.
"""

APP_NAME = "AlgoVision Studio"
APP_TAGLINE = "Visualize · Understand · Master Algorithms"
APP_VERSION = "v1.0.0"

# --- Supported value ranges (PRD Section 9) -------------------------------
ARRAY_SIZE_MIN = 10
ARRAY_SIZE_MAX = 100
ARRAY_SIZE_DEFAULT = 15

VALUE_MIN = 1
VALUE_MAX = 1000

# Custom-array input validation (PRD 7.3)
CUSTOM_MAX_ELEMENTS = 100

# Animation speed multipliers offered to the user (PRD 9: 0.25x - 5x)
SPEED_CHOICES = [0.25, 0.5, 1.0, 2.0, 5.0]
SPEED_LABELS = {
    0.25: "0.25x (Very Slow)",
    0.5: "0.5x (Slow)",
    1.0: "1.0x (Normal)",
    2.0: "2.0x (Fast)",
    5.0: "5.0x (Very Fast)",
}
SPEED_DEFAULT = 1.0

# Base delay (milliseconds) between frames at 1.0x speed.
BASE_FRAME_MS = 420

# --- Algorithm ordering (matches the navigation panel in the references) ---
ALGO_ORDER = [
    "bubble",
    "selection",
    "insertion",
    "merge",
    "quick",
    "heap",
]

# Default demonstration dataset used by the reference images.
DEFAULT_DATASET = [64, 34, 25, 12, 22, 11, 90, 2, 70, 45, 30, 36, 15, 10, 5]

# Keyboard shortcuts (PRD / reference images).
SHORTCUTS = {
    "play": "F5",
    "pause": "F6",
    "step": "F7",
    "reset": "F8",
    "restart": "F9",
}
