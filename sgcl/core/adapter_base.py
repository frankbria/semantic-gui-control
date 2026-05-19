"""Adapter contract.

Adapters translate native UI surfaces (UIA, AX, AT-SPI, DOM) into the
schema in `sgcl/core/schema.py`. Core code dispatches through this interface
and never imports platform modules directly.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from sgcl.core.schema import Control, WindowInfo


class Adapter(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Adapter identifier, e.g. 'windows_uia'."""

    @property
    @abstractmethod
    def platform(self) -> str:
        """Platform label, e.g. 'windows'."""

    @abstractmethod
    def list_windows(self) -> list[WindowInfo]:
        """Return the current top-level windows."""

    @abstractmethod
    def active_window(self) -> WindowInfo | None:
        """Return the foreground/active window, or None if unavailable."""

    @abstractmethod
    def inspect_window(self, window_id: str, depth: int) -> Control:
        """Return a hierarchical control tree for a specific window.

        `window_id` must be a value previously produced by this adapter
        in `list_windows()` or `active_window()`.
        """

    @abstractmethod
    def inspect_active(self, depth: int) -> Control:
        """Return a hierarchical control tree for the active window."""
