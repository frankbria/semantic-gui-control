from __future__ import annotations

import pytest

from sgcl.core.synonyms import synonyms_for


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
