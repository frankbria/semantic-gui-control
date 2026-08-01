"""Phase 0/1 data shapes.

The normalized affordance model. `docs/affordance-model.md` is the
agent-facing contract for these shapes and is kept in step with
`Control.to_dict()` by `tests/test_docs_contract.py`.

The Phase 1 (Normalize) fields are all populated now:

- `Control.confidence` — scored by `sgcl.core.confidence.score_control`.
  Required, not defaulted; see ADR-0002.
- `Control.description` — icon-font glyph names.
- `Control.synonyms` — alternative labels an agent may query with.
- `WindowInfo.is_system_surface` — shell/system window filter.

`Control.value` and `Control.risk` are specified in the affordance model
but not implemented; they land with Phase 3 (Act + Verify + Risk).
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
    # Adapter's confidence (0..1) that role/label/actions were correctly
    # identified. Required, not defaulted: it used to default to 1.0 as a
    # placeholder before scoring existed, which meant any unscored node
    # silently claimed maximum confidence and outranked every honestly
    # scored control. Adapters call `score_control`; see ADR-0002.
    confidence: float
    children: list[Control] = field(default_factory=list)
    # Id of the enclosing affordance, or None at the root. Makes the graph
    # traversable upward: without it a consumer holding a match has to
    # re-walk the whole tree to find its context.
    parent_id: str | None = None
    raw_ref: dict[str, Any] | None = None
    # Optional human-readable description (e.g., for icon-font glyph labels
    # the adapter could not render meaningfully). Populated by E.4.
    description: str | None = None
    # Alternative labels an agent might query with (e.g., Calculator names
    # buttons "Zero"/"Plus"; synonyms includes "0"/"+"). Populated by E.6.
    synonyms: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "parent_id": self.parent_id,
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
