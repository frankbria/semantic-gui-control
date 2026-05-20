"""Adapter contract.

Adapters translate native UI surfaces (UIA, AX, AT-SPI, DOM) into the
schema in `sgcl/core/schema.py`. Core code dispatches through this interface
and never imports platform modules directly.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from sgcl.core.matcher import Query
from sgcl.core.read_result import ReadResult
from sgcl.core.schema import Control, WindowInfo


@dataclass
class ReadResolution:
    """Pair returned by Adapter.read — the value and the affordance it came from."""

    result: ReadResult
    control: Control


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
    def read(
        self,
        window_id: str,
        *,
        query: Query | None = None,
        target_id: str | None = None,
        depth: int = 8,
        max_length: int = 4096,
    ) -> ReadResolution:
        """Resolve to a single control and read its value.

        Exactly one of `query` / `target_id` must be supplied:

        - `query`: a `Query` selector. The adapter walks the window's tree,
          matches, requires exactly one hit, and reads the matched control.
          Multiple matches → `LookupError` (the caller decides whether to
          surface as a CLI ambiguity error).
        - `target_id`: a `ctrl_X` id from a recent `inspect_window`. The
          adapter walks the tree, finds the control with that id, and reads
          it. Fragile across invocations — the id is per-walk.

        Returns a `ReadResolution` carrying both the `ReadResult` and the
        normalized affordance that was read.
        """
