"""Light and dark colour themes for the matplotlib figure and the Tk controls.

Drawing code keeps its light-theme colour literals and passes them through
``themed()``. In the light theme that is the identity, so the original look is
unchanged; in the dark theme each literal is replaced by its counterpart for a
dark surface.
"""

import matplotlib

LIGHT = "light"
DARK = "dark"

# Light literal -> colour used on the dark surface.
_DARK_COLORS = {
    # Surfaces and separators
    "white": "#1e293b",
    "#f8fafc": "#172033",
    "#e5e7eb": "#334155",
    "#d1d5db": "#3b4a61",
    "#94a3b8": "#64748b",
    # Text
    "#111827": "#f1f5f9",
    "#374151": "#cbd5e1",
    "#334155": "#cbd5e1",
    "#475569": "#b4c0d0",
    "#4b5563": "#b4c0d0",
    "#64748b": "#94a3b8",
    # Status and series colours that are too dark on a dark surface
    "#16a34a": "#22c55e",
    "#65a30d": "#84cc16",
    "#dc2626": "#f87171",
    "#ea580c": "#fb923c",
    "#b45309": "#fbbf24",
    "#2563eb": "#60a5fa",
    "#7c3aed": "#a78bfa",
    "#a855f7": "#c084fc",
    "#0891b2": "#22d3ee",
}

_DARK_RC = {
    "figure.facecolor": "#0f172a",
    "figure.edgecolor": "#0f172a",
    "savefig.facecolor": "#0f172a",
    "axes.facecolor": "#111c30",
    "axes.edgecolor": "#475569",
    "axes.labelcolor": "#cbd5e1",
    "axes.titlecolor": "#f1f5f9",
    "text.color": "#e2e8f0",
    "xtick.color": "#cbd5e1",
    "ytick.color": "#cbd5e1",
    "grid.color": "#94a3b8",
    "legend.edgecolor": "#475569",
    "legend.labelcolor": "#e2e8f0",
    "axes.prop_cycle": matplotlib.cycler(color=[
        "#60a5fa", "#fb923c", "#4ade80", "#f87171", "#c084fc",
        "#d6a37c", "#f9a8d4", "#cbd5e1", "#facc15", "#22d3ee",
    ]),
}
_LIGHT_RC = {key: matplotlib.rcParams[key] for key in _DARK_RC}

# Colours for the ttk controls in the dark theme. The light theme keeps the
# platform's native ttk theme and needs no palette.
DARK_TK = {
    "background": "#0f172a",
    "foreground": "#e2e8f0",
    "field": "#1e293b",
    "border": "#475569",
    "hover": "#334155",
    "pressed": "#475569",
    "accent": "#3b82f6",
    "accent_foreground": "#ffffff",
    "disabled": "#64748b",
}

_active = LIGHT


def set_theme(name: str) -> None:
    """Activate a theme for everything drawn from now on."""
    global _active
    _active = DARK if name == DARK else LIGHT
    matplotlib.rcParams.update(_DARK_RC if _active == DARK else _LIGHT_RC)


def current_theme() -> str:
    return _active


def is_dark() -> bool:
    return _active == DARK


def themed(color: str) -> str:
    """Return the active theme's counterpart of a light-theme colour."""
    if _active != DARK:
        return color
    return _DARK_COLORS.get(color.lower(), color)


def figure_background() -> str:
    return matplotlib.rcParams["figure.facecolor"]
