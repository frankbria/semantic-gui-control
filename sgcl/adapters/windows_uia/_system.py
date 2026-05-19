"""Shell/system-surface detection for the Windows UIA adapter.

Phase 0 surfaced these as top-level windows because they are top-level
windows. Agents almost never want to inspect them by default. Filtering
is applied by the CLI, not the adapter — the adapter just tags.
"""

from __future__ import annotations

# Known shell window titles. All run inside `explorer.exe`.
_SHELL_TITLES: frozenset[str] = frozenset(
    {
        "Program Manager",
        "Taskbar",
        "Action Center",
        "Notification Center",
        "Search",
        "Cortana",
        "Start",
    }
)


def is_system_surface(title: str, process_name: str | None) -> bool:
    """True for known shell windows (Taskbar, Program Manager, etc.).

    Heuristic: a window owned by `explorer.exe` whose title is empty or
    matches a known shell-window title. Empty-title `explorer.exe` windows
    are typically secondary taskbars or shell artifacts on multi-monitor
    setups. A real Explorer folder window has a folder name as its title
    (e.g., "Documents") and so won't be tagged.
    """
    if not process_name:
        return False
    if process_name.lower() != "explorer.exe":
        return False
    if not title:
        return True
    return title in _SHELL_TITLES
