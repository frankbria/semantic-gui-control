"""Read state from a UIA control.

Duck-typed (mirrors the walker's split) so Linux tests can exercise it
with mock controls that mimic the UIA pattern interfaces.

## Extractor priority

For each control, try these in order. The first one that succeeds
becomes the `source` field of the `ReadResult`:

1. **`ValuePattern.Value`** — text fields, combo boxes, edit controls.
2. **`TextPattern.DocumentRange.GetText(max_length)`** — documents
   (Notepad's editor area). Capped at `max_length`; the response
   reports whether it was truncated.
3. **`TogglePattern.ToggleState`** — checkboxes, toggle buttons.
   Normalized to `"on"` / `"off"` / `"indeterminate"`.
4. **`SelectionPattern.GetSelection()`** — lists, tabs, trees.
   Reports the selected items' names.
5. **Label + aggregated descendant text** — the fallback. Used when
   no pattern fires but the control has an accessible name or
   descendant static text (e.g., Calculator's `NormalOutput`).

If none of those fire (no patterns, no label, no descendant text),
returns `supported: False`. Honesty over guessing.

## ReadResult shape

A flat dataclass with:

- `supported: bool` — `True` when any extractor produced a meaningful
  value; `False` when none did.
- `source: str` — which extractor fired
  (`"value_pattern"`, `"text_pattern"`, `"toggle_pattern"`,
  `"selection_pattern"`, `"label"`, or `"none"`).
- `value: str | None` — canonical string representation (the agent's
  primary interest). For `selection_pattern` it's a comma-separated
  list of selected item labels.
- `details: dict[str, Any]` — source-specific extras (e.g.,
  `{"read_only": True}` from ValuePattern, `{"truncated": True}`
  from TextPattern's length cap, `{"items": [...]}` from
  SelectionPattern).
"""

from __future__ import annotations

# ReadResult is the platform-neutral shape; lives in core so the
# Adapter contract can refer to it without importing adapters.
from sgcl.core.read_result import ReadResult

DEFAULT_MAX_LENGTH = 4096

__all__ = ["ReadResult", "DEFAULT_MAX_LENGTH", "read_value"]


def read_value(ctrl, max_length: int = DEFAULT_MAX_LENGTH) -> ReadResult:
    """Try the extractors in priority order and return the first hit."""
    result = _try_value_pattern(ctrl)
    if result is not None:
        return result

    result = _try_text_pattern(ctrl, max_length)
    if result is not None:
        return result

    result = _try_toggle_pattern(ctrl)
    if result is not None:
        return result

    result = _try_selection_pattern(ctrl)
    if result is not None:
        return result

    result = _try_label_fallback(ctrl)
    if result is not None:
        return result

    return ReadResult(supported=False, source="none", value=None)


# --- ValuePattern ----------------------------------------------------------


def _try_value_pattern(ctrl) -> ReadResult | None:
    try:
        vp = ctrl.GetValuePattern()
    except Exception:
        return None
    if vp is None:
        return None
    try:
        raw_value = vp.Value
    except Exception:
        return None
    if raw_value is None:
        return None
    value = str(raw_value)
    read_only = False
    import contextlib

    with contextlib.suppress(Exception):
        read_only = bool(vp.IsReadOnly)
    return ReadResult(
        supported=True,
        source="value_pattern",
        value=value,
        details={"read_only": read_only},
    )


# --- TextPattern -----------------------------------------------------------


def _try_text_pattern(ctrl, max_length: int) -> ReadResult | None:
    try:
        tp = ctrl.GetTextPattern()
    except Exception:
        return None
    if tp is None:
        return None
    try:
        document_range = tp.DocumentRange
    except Exception:
        return None
    if document_range is None:
        return None
    try:
        text = document_range.GetText(max_length)
    except Exception:
        return None
    if text is None:
        return None
    text_str = str(text)
    truncated = len(text_str) >= max_length
    return ReadResult(
        supported=True,
        source="text_pattern",
        value=text_str,
        details={"truncated": truncated, "max_length": max_length},
    )


# --- TogglePattern ---------------------------------------------------------


_TOGGLE_STATE_MAP = {
    0: "off",
    1: "on",
    2: "indeterminate",
    "off": "off",
    "on": "on",
    "indeterminate": "indeterminate",
}


def _try_toggle_pattern(ctrl) -> ReadResult | None:
    try:
        tp = ctrl.GetTogglePattern()
    except Exception:
        return None
    if tp is None:
        return None
    try:
        raw_state = tp.ToggleState
    except Exception:
        return None
    if raw_state is None:
        return None
    # Strings come in any case; lowercase before lookup. Ints match directly.
    lookup_key = raw_state.lower() if isinstance(raw_state, str) else raw_state
    normalized = _TOGGLE_STATE_MAP.get(lookup_key)
    if normalized is None:
        # Some UIA wrappers return a value with a name attribute; try that.
        name = getattr(raw_state, "name", None)
        if name and isinstance(name, str):
            normalized = _TOGGLE_STATE_MAP.get(name.lower())
    if normalized is None:
        return None
    return ReadResult(
        supported=True,
        source="toggle_pattern",
        value=normalized,
        details={"state": normalized},
    )


# --- SelectionPattern ------------------------------------------------------


def _try_selection_pattern(ctrl) -> ReadResult | None:
    try:
        sp = ctrl.GetSelectionPattern()
    except Exception:
        return None
    if sp is None:
        return None
    try:
        items = sp.GetSelection()
    except Exception:
        return None
    if items is None:
        return None
    labels: list[str] = []
    for item in items:
        try:
            name = getattr(item, "Name", None)
        except Exception:
            name = None
        if name:
            labels.append(str(name))
    return ReadResult(
        supported=True,
        source="selection_pattern",
        value=", ".join(labels) if labels else "",
        details={"items": labels},
    )


# --- Label / aggregated text fallback --------------------------------------


def _try_label_fallback(ctrl) -> ReadResult | None:
    """Reads the control's accessible name plus any descendant static text.

    This is the path that surfaces Calculator's `NormalOutput` value:
    the display is a static_text control whose `Name` IS the current
    readout. ValuePattern / TextPattern don't apply; the label fallback
    is the only thing that can read it.
    """
    label = _safe_name(ctrl)
    descendant_text = _collect_descendant_text(ctrl)
    if not label and not descendant_text:
        return None
    value = label or descendant_text
    return ReadResult(
        supported=True,
        source="label",
        value=value,
        details={
            "label": label,
            "descendant_text": descendant_text,
        },
    )


def _safe_name(ctrl) -> str | None:
    try:
        name = getattr(ctrl, "Name", None)
    except Exception:
        return None
    if name is None:
        return None
    text = str(name).strip()
    return text if text else None


def _collect_descendant_text(ctrl) -> str | None:
    """Concatenate non-empty Names from descendants, depth-first.

    Bounded to avoid runaway walks on huge trees — we stop after 64
    contributing labels, which is plenty for a status bar or labeled
    group without being a denial-of-service for an inspection of
    something very large.
    """
    pieces: list[str] = []
    _walk_text(ctrl, pieces, limit=64)
    if not pieces:
        return None
    return " ".join(pieces)


def _walk_text(ctrl, pieces: list[str], limit: int) -> None:
    try:
        children = ctrl.GetChildren()
    except Exception:
        return
    for child in children:
        if len(pieces) >= limit:
            return
        name = _safe_name(child)
        if name:
            pieces.append(name)
        _walk_text(child, pieces, limit)
