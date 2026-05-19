"""Phase 0 data shapes.

Intentionally a subset of the full affordance model in docs/affordance-model.md.
Phase 1 (Normalize) will tighten and expand these.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Bounds:
    x: int
    y: int
    width: int
    height: int

    def to_dict(self) -> dict[str, int]:
        return {"x": self.x, "y": self.y, "width": self.width, "height": self.height}


@dataclass
class WindowInfo:
    id: str
    title: str
    process_name: str | None
    pid: int
    bounds: Bounds | None
    visible: bool
    is_active: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "process_name": self.process_name,
            "pid": self.pid,
            "bounds": self.bounds.to_dict() if self.bounds else None,
            "visible": self.visible,
            "is_active": self.is_active,
        }


@dataclass
class Control:
    id: str
    role: str
    native_role: str
    label: str | None
    enabled: bool
    visible: bool
    focused: bool
    bounds: Bounds | None
    actions: list[str]
    children: list[Control] = field(default_factory=list)
    raw_ref: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "role": self.role,
            "native_role": self.native_role,
            "label": self.label,
            "enabled": self.enabled,
            "visible": self.visible,
            "focused": self.focused,
            "bounds": self.bounds.to_dict() if self.bounds else None,
            "actions": list(self.actions),
            "children": [c.to_dict() for c in self.children],
            "raw_ref": self.raw_ref,
        }
