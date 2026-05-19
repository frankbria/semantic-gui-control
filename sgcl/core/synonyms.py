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
#
# Non-ASCII values use \uXXXX escapes rather than literal Unicode characters.
# Phase 1 Run 4 revealed that some Windows Python environments re-interpret
# UTF-8 source bytes through a legacy code page, turning a literal pi into a
# two-character mojibake string. Escapes are decoded by the Python tokenizer
# itself and are therefore code-page-independent.
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
    "minus": ("\u2212", "-"),  # U+2212 MINUS SIGN, hyphen-minus
    "multiply by": ("\u00d7", "*"),  # U+00D7 MULTIPLICATION SIGN, asterisk
    "divide by": ("\u00f7", "/"),  # U+00F7 DIVISION SIGN, slash
    "equals": ("=",),
    "decimal separator": (".",),
    "left parenthesis": ("(",),
    "right parenthesis": (")",),
    # Common mathematical constants and symbols.
    "pi": ("\u03c0",),  # U+03C0 GREEK SMALL LETTER PI
    "square root": ("\u221a",),  # U+221A SQUARE ROOT
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
