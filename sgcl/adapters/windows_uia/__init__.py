"""Windows UI Automation adapter package.

The duck-typed walker (`_walker`) and the system-surface heuristic
(`_system`) are platform-neutral and importable from any platform —
that's how the Linux test suite exercises them. The adapter class
itself (`_adapter`) only imports successfully on Windows because it
pulls in `uiautomation`.
"""

from __future__ import annotations

import sys

if sys.platform == "win32":
    from sgcl.adapters.windows_uia._adapter import WindowsUIAAdapter

    __all__ = ["WindowsUIAAdapter"]
else:
    __all__: list[str] = []
