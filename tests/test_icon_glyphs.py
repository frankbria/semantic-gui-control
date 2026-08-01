from __future__ import annotations

import pytest

from sgcl.core.icon_glyphs import describe_label, glyph_names


def test_plain_text_label_yields_no_description():
    assert describe_label("Save") is None
    assert describe_label("Bold (Ctrl+B)") is None


def test_empty_or_none_label_yields_no_description():
    assert describe_label(None) is None
    assert describe_label("") is None
    assert describe_label("   ") is None


def test_single_known_glyph_label():
    label = chr(0xE713)  # Settings
    assert describe_label(label) == "icon: Settings"


def test_multiple_known_glyphs():
    label = chr(0xE700) + chr(0xE713)  # GlobalNavButton + Settings
    assert describe_label(label) == "icon: GlobalNavButton, Settings"


def test_unknown_pua_yields_no_description():
    # We refuse to invent a name for codepoints we don't have in the map.
    label = chr(0xE9FF)  # not currently mapped
    assert describe_label(label) is None


def test_mixed_text_and_glyph_yields_no_description():
    # A label like "Save " — the text is meaningful; don't second-guess it.
    label = "Save " + chr(0xE74E)
    assert describe_label(label) is None


def test_mixed_known_and_unknown_glyphs_yields_no_description():
    # All-PUA but one unknown — prefer silence to a half-truth.
    label = chr(0xE700) + chr(0xE9FF)
    assert describe_label(label) is None


def test_known_glyph_with_surrounding_whitespace():
    label = "  " + chr(0xE74E) + "  "  # Save icon padded with whitespace
    assert describe_label(label) == "icon: Save"


# ---- glyph_names: strips the presentational prefix for matching ------------


def test_glyph_names_strips_the_icon_prefix():
    assert glyph_names("icon: Settings") == "Settings"


def test_glyph_names_handles_multiple_names():
    assert glyph_names("icon: GlobalNavButton, Settings") == "GlobalNavButton, Settings"


def test_glyph_names_round_trips_describe_label():
    assert glyph_names(describe_label(chr(0xE713))) == "Settings"


@pytest.mark.parametrize(
    "description",
    [None, "", "a user-supplied description", "iconic"],
    ids=["none", "empty", "foreign", "prefix-lookalike"],
)
def test_glyph_names_returns_none_for_foreign_descriptions(description):
    """Only descriptions this module wrote are stripped; others pass through."""
    assert glyph_names(description) is None
