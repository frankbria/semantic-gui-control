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
    "minus": ("−", "-"),  # U+2212 MINUS SIGN, hyphen-minus
    "multiply by": ("×", "*"),  # U+00D7 MULTIPLICATION SIGN, asterisk
    "divide by": ("÷", "/"),  # U+00F7 DIVISION SIGN, slash
    "equals": ("=",),
    "decimal separator": (".",),
    "left parenthesis": ("(",),
    "right parenthesis": (")",),
    # Common mathematical constants and symbols.
    "pi": ("π",),  # U+03C0 GREEK SMALL LETTER PI
    "square root": ("√",),  # U+221A SQUARE ROOT
}


def _build_reverse_index() -> dict[str, tuple[str, ...]]:
    """Invert the map so symbol-named controls expand to words too.

    Derived at import rather than hand-written: a second map maintained by
    hand drifts from the first the moment anyone adds an entry.

    Many-to-one is expected and fine -- `"minus": ("−", "-")` puts two
    distinct symbols under one word. The reverse case, one symbol claimed
    by two words, would make expansion arbitrary; there is no such entry
    today and `test_no_symbol_maps_to_two_words` fails if one appears.
    """
    reverse: dict[str, tuple[str, ...]] = {}
    for word, symbols in _LABEL_SYNONYMS.items():
        for symbol in symbols:
            reverse[symbol.strip().lower()] = (word,)
    return reverse


_SYMBOL_SYNONYMS: dict[str, tuple[str, ...]] = _build_reverse_index()


def synonyms_for(label: str | None) -> list[str]:
    """Return alternative labels an agent might query with.

    Expansion runs both ways. `"Zero"` yields `["0"]`, and `"0"` yields
    `["zero"]` -- an app that labels a button `"+"` while the agent reasons
    in words is exactly the case this exists for, and it used to have no
    coverage because Calculator (the app the starter set came from) names
    its buttons in words.

    Reverse hits return the lowercase map key. Matching is case-insensitive
    so this does not affect FIND, but it is what an agent sees in the JSON.

    Empty list means no known synonyms. Lookup is case-insensitive and
    trims surrounding whitespace in both directions. Original capitalization
    in the label is preserved on the affordance; this only computes the
    alternates.
    """
    if not label:
        return []
    key = label.strip().lower()
    return list(_LABEL_SYNONYMS.get(key) or _SYMBOL_SYNONYMS.get(key, ()))
