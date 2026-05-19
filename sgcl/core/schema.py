"""Phase 0/1 data shapes.

Tracking toward the full affordance model in `docs/affordance-model.md`.
The Phase 1 (Normalize) slices fill in the still-defaulted fields:

- `Control.confidence` — placeholder 1.0 until E.2 scores it.
- `Control.description` — populated by E.4 (icon-font handling).
- `Control.synonyms` — populated by E.6 (label synonyms).
- `WindowInfo.is_system_surface` — populated by E.3 (system filter).
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
    is_system_surface: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "process_name": self.process_name,
            "pid": self.pid,
            "bounds": self.bounds.to_dict() if self.bounds else None,
            "visible": self.visible,
            "is_active": self.is_active,
            "is_system_surface": self.is_system_surface,
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
    # Adapter's confidence (0..1) that role/label/actions were correctly
    # identified. Defaults to 1.0 until E.2 wires in real scoring.
    confidence: float = 1.0
    # Optional human-readable description (e.g., for icon-font glyph labels
    # the adapter could not render meaningfully). Populated by E.4.
    description: str | None = None
    # Alternative labels an agent might query with (e.g., Calculator names
    # buttons "Zero"/"Plus"; synonyms includes "0"/"+"). Populated by E.6.
    synonyms: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "role": self.role,
            "native_role": self.native_role,
            "label": self.label,
            "description": self.description,
            "synonyms": list(self.synonyms),
            "enabled": self.enabled,
            "visible": self.visible,
            "focused": self.focused,
            "bounds": self.bounds.to_dict() if self.bounds else None,
            "actions": list(self.actions),
            "confidence": self.confidence,
            "children": [c.to_dict() for c in self.children],
            "raw_ref": self.raw_ref,
        }
