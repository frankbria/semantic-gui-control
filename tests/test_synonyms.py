from __future__ import annotations

import pytest

from sgcl.core.synonyms import _LABEL_SYNONYMS, synonyms_for


def test_empty_or_none_label():
    assert synonyms_for(None) == []
    assert synonyms_for("") == []
    assert synonyms_for("   ") == []


def test_unknown_label():
    assert synonyms_for("Save") == []
    assert synonyms_for("Open Navigation") == []


@pytest.mark.parametrize(
    "label,expected",
    [
        ("Zero", ["0"]),
        ("One", ["1"]),
        ("Two", ["2"]),
        ("Three", ["3"]),
        ("Four", ["4"]),
        ("Five", ["5"]),
        ("Six", ["6"]),
        ("Seven", ["7"]),
        ("Eight", ["8"]),
        ("Nine", ["9"]),
    ],
)
def test_digit_words(label, expected):
    assert synonyms_for(label) == expected


def test_plus():
    assert synonyms_for("Plus") == ["+"]


def test_minus_has_unicode_and_ascii_forms():
    # Calculator may surface either; agents may type either.
    assert synonyms_for("Minus") == ["−", "-"]


def test_multiply_and_divide():
    assert synonyms_for("Multiply by") == ["×", "*"]
    assert synonyms_for("Divide by") == ["÷", "/"]


def test_equals_and_decimal():
    assert synonyms_for("Equals") == ["="]
    assert synonyms_for("Decimal separator") == ["."]


def test_parens():
    assert synonyms_for("Left parenthesis") == ["("]
    assert synonyms_for("Right parenthesis") == [")"]


def test_pi_and_square_root():
    assert synonyms_for("Pi") == ["π"]
    assert synonyms_for("Square root") == ["√"]


def test_case_insensitive():
    assert synonyms_for("zero") == ["0"]
    assert synonyms_for("ZERO") == ["0"]
    assert synonyms_for("Plus") == synonyms_for("plus")


def test_strips_surrounding_whitespace():
    assert synonyms_for("  Zero  ") == ["0"]


def test_does_not_partial_match():
    # "Positive negative" (the ± toggle) is a different button than Plus/Minus.
    # Must not return synonyms.
    assert synonyms_for("Positive negative") == []


def test_returns_independent_list():
    a = synonyms_for("Zero")
    a.append("999")
    assert synonyms_for("Zero") == ["0"]


# ---- reverse direction ----
#
# The map keys every entry on the word form, so expansion used to run one
# way only: a control named "Zero" carried ["0"] and was findable by
# --text "0", but a control named "0" carried [] and was unreachable by
# --text "Zero". Calculator names its buttons in words, which is why the
# covered direction was the one that got tested. An app that labels a
# button "+" while the agent reasons in words had no coverage at all, and
# the gap was invisible in output because `synonyms` was simply empty.


@pytest.mark.parametrize(
    "symbol,expected",
    [
        ("0", ["zero"]),
        ("1", ["one"]),
        ("9", ["nine"]),
        ("+", ["plus"]),
        ("=", ["equals"]),
        (".", ["decimal separator"]),
        ("(", ["left parenthesis"]),
        (")", ["right parenthesis"]),
        ("π", ["pi"]),
        ("√", ["square root"]),
    ],
)
def test_symbol_expands_to_word(symbol, expected):
    assert synonyms_for(symbol) == expected


@pytest.mark.parametrize(
    "symbol,word",
    [
        ("−", "minus"),  # U+2212
        ("-", "minus"),  # hyphen-minus
        ("×", "multiply by"),
        ("*", "multiply by"),
        ("÷", "divide by"),
        ("/", "divide by"),
    ],
)
def test_each_form_of_a_multi_symbol_operator_resolves(symbol, word):
    """Both spellings of an operator reverse to the same word.

    `"minus": ("−", "-")` means two distinct symbols map to one word. That
    is many-to-one and fine; the collision that would *not* be fine is one
    symbol under two words, which `test_no_symbol_maps_to_two_words` rules
    out at import time.
    """
    assert synonyms_for(symbol) == [word]


def test_reverse_results_use_the_lowercase_map_key():
    """Pinned deliberately: reverse hits return the dictionary key verbatim.

    Matching is case-insensitive, so this does not affect FIND -- but it is
    what an agent sees in the JSON, so it should be consistent rather than
    incidental.
    """
    assert synonyms_for("0") == ["zero"]
    assert synonyms_for("0")[0].islower()


def test_no_symbol_maps_to_two_words():
    """A symbol under two words would make the reverse expansion arbitrary.

    There is no such entry today. If one is ever added, this fails loudly
    rather than silently picking whichever the dict happened to yield --
    the map's author has to decide what the reverse should mean.
    """
    seen: dict[str, str] = {}
    collisions = []
    for word, symbols in _LABEL_SYNONYMS.items():
        for symbol in symbols:
            if symbol in seen:
                collisions.append((symbol, seen[symbol], word))
            seen[symbol] = word
    assert collisions == [], f"symbol claimed by two words: {collisions}"


def test_forward_direction_is_unchanged():
    """The reverse index must not disturb what already worked."""
    assert synonyms_for("Zero") == ["0"]
    assert synonyms_for("Minus") == ["−", "-"]
    assert synonyms_for("Square root") == ["√"]


def test_reverse_lookup_trims_whitespace():
    assert synonyms_for("  0  ") == ["zero"]


def test_unknown_symbol_still_returns_empty():
    assert synonyms_for("%") == []
    assert synonyms_for("^") == []
