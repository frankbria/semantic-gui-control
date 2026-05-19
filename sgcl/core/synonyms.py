"""Label synonyms.

Calculator and similar apps expose accessible names in words ("Zero",
"Plus", "Decimal separator") even when the visible label is a symbol
("0", "+", "."). An agent prompted with literal symbols will not match
the word-named label. Synonyms close the gap: each affordance carries
the labels an agent is likely to query with, even if UIA's accessible
name uses a different surface.

Phase 1 ships the Calculator-focused starter set. Phase 2 (FIND) will
consume `Control.synonyms` as alternative match keys. Extend the map as
new patterns turn up in spike runs.
"""

from __future__ import annotations

# Lowercased keys; lookup normalizes the input.
_LABEL_SYNONYMS: dict[str, tuple[str, ...]] = {
    # Digits.
    "zero": ("0",),
    "one": ("1",),
    "two": ("2",),
    "three": ("3",),
    "four": ("4",),
    "five": ("5",),
    "six": ("6",),
    "seven": ("7",),
    "eight": ("8",),
    "nine": ("9",),
    # Operators. Include both Unicode and ASCII forms where they differ.
    "plus": ("+",),
    "minus": ("−", "-"),
    "multiply by": ("×", "*"),
    "divide by": ("÷", "/"),
    "equals": ("=",),
    "decimal separator": (".",),
    "left parenthesis": ("(",),
    "right parenthesis": (")",),
    # Common mathematical constants and symbols.
    "pi": ("π",),
    "square root": ("√",),
}


def synonyms_for(label: str | None) -> list[str]:
    """Return alternative labels an agent might query with.

    Empty list means no known synonyms. Lookup is case-insensitive and
    trims surrounding whitespace. Original capitalization in the label
    is preserved on the affordance; this function only computes the
    alternates.
    """
    if not label:
        return []
    return list(_LABEL_SYNONYMS.get(label.strip().lower(), ()))
