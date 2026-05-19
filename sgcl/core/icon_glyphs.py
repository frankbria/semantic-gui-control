"""Icon-font glyph handling.

WinUI and modern Windows apps put accessible names that consist entirely
of Unicode Private Use Area (PUA) codepoints when a button is rendered
as an icon-font glyph (Segoe Fluent Icons, Segoe MDL2 Assets). For an
agent, ``""`` is opaque; the human-readable role is "hamburger menu" or
"settings."

This module:

1. Recognizes when a label is **entirely** PUA codepoints.
2. Maps known codepoints to human-readable names sourced from
   Microsoft's Segoe MDL2 Assets / Segoe Fluent Icons references.
3. Returns a ``description`` string the walker can attach to the
   affordance, while leaving the raw ``label`` intact in ``raw_ref``.

The map is intentionally small at first. Extend as new icons turn up in
spike runs. Codepoints whose names we don't know yet produce no
description (we prefer "no information" to "made up information"); the
PUA char is still preserved in the label and ``raw_ref``.

References:
- https://learn.microsoft.com/en-us/windows/apps/design/style/segoe-fluent-icons-font
- https://learn.microsoft.com/en-us/windows/apps/design/style/segoe-ui-symbol-font
"""

from __future__ import annotations

PUA_START = 0xE000
PUA_END = 0xF8FF


# Subset of Segoe MDL2 Assets / Segoe Fluent Icons. Each entry is the
# Microsoft-published symbolic name. Extend as we observe new codepoints in
# spike runs.
_ICON_NAMES: dict[int, str] = {
    0xE700: "GlobalNavButton",  # hamburger menu
    0xE701: "Wifi",
    0xE702: "Bluetooth",
    0xE706: "Brightness",
    0xE707: "MapPin",
    0xE70D: "ChevronDown",
    0xE70E: "ChevronUp",
    0xE70F: "Edit",
    0xE710: "Add",
    0xE711: "Cancel",
    0xE712: "More",
    0xE713: "Settings",
    0xE715: "Mail",
    0xE716: "People",
    0xE71B: "Link",
    0xE721: "Search",
    0xE72B: "Forward",
    0xE72C: "Refresh",
    0xE738: "PaginationDotOutline10",
    0xE74D: "Delete",
    0xE74E: "Save",
    0xE76B: "ChevronLeft",
    0xE76C: "ChevronRight",
    0xE783: "ZoomIn",
    0xE7A8: "Library",
    0xE801: "Tools",
    0xE8A7: "OpenFile",
    0xE8BB: "ChromeClose",
    0xE921: "Pinned",
    0xE9F5: "Stopwatch",
}


def _is_pua(codepoint: int) -> bool:
    return PUA_START <= codepoint <= PUA_END


def describe_label(label: str | None) -> str | None:
    """Return a description for a label that is entirely PUA codepoints.

    Returns ``None`` when:

    - the label is empty or not provided,
    - the label contains any non-PUA characters (then the label itself
      is meaningful — don't second-guess it),
    - the label is all PUA but at least one codepoint isn't in the map
      (we'd rather say nothing than guess).

    For an all-PUA label whose glyphs are all known, returns a string of
    the form ``"icon: Settings"`` or ``"icon: GlobalNavButton, Settings"``.
    """
    if not label:
        return None
    label = label.strip()
    if not label:
        return None

    # Must contain at least one PUA char and zero non-PUA chars.
    saw_pua = False
    names: list[str] = []
    for ch in label:
        cp = ord(ch)
        if _is_pua(cp):
            saw_pua = True
            name = _ICON_NAMES.get(cp)
            if name is None:
                return None
            names.append(name)
        else:
            return None

    if not saw_pua:
        return None
    return "icon: " + ", ".join(names)
