"""Reader tests against mock UIA controls."""

from __future__ import annotations

from sgcl.adapters.windows_uia._readers import DEFAULT_MAX_LENGTH, ReadResult, read_value


class _MockPattern:
    """Generic pattern holder."""

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class _MockDocumentRange:
    def __init__(self, text):
        self._text = text

    def GetText(self, max_length):
        return self._text[:max_length] if self._text else self._text


class _MockCtrl:
    """Mocks the subset of UIA Control used by the reader."""

    def __init__(
        self,
        *,
        Name=None,
        value_pattern=None,
        text_pattern=None,
        toggle_pattern=None,
        selection_pattern=None,
        children=None,
    ):
        self.Name = Name
        self._value_pattern = value_pattern
        self._text_pattern = text_pattern
        self._toggle_pattern = toggle_pattern
        self._selection_pattern = selection_pattern
        self._children = children or []

    def GetValuePattern(self):
        return self._value_pattern

    def GetTextPattern(self):
        return self._text_pattern

    def GetTogglePattern(self):
        return self._toggle_pattern

    def GetSelectionPattern(self):
        return self._selection_pattern

    def GetChildren(self):
        return self._children


# ---- ValuePattern ---------------------------------------------------------


def test_value_pattern_returns_value_and_read_only():
    ctrl = _MockCtrl(value_pattern=_MockPattern(Value="hello", IsReadOnly=False))
    r = read_value(ctrl)
    assert r.supported is True
    assert r.source == "value_pattern"
    assert r.value == "hello"
    assert r.details == {"read_only": False}


def test_value_pattern_read_only_reflected():
    ctrl = _MockCtrl(value_pattern=_MockPattern(Value="static", IsReadOnly=True))
    r = read_value(ctrl)
    assert r.details == {"read_only": True}


def test_value_pattern_coerces_non_string_value():
    # Some UIA wrappers return numeric or other types for .Value.
    ctrl = _MockCtrl(value_pattern=_MockPattern(Value=42, IsReadOnly=False))
    r = read_value(ctrl)
    assert r.value == "42"


def test_value_pattern_none_value_falls_through():
    # If .Value is None, ValuePattern hasn't actually populated anything;
    # fall through to lower-priority extractors.
    ctrl = _MockCtrl(
        value_pattern=_MockPattern(Value=None, IsReadOnly=False),
        Name="FallbackLabel",
    )
    r = read_value(ctrl)
    assert r.source == "label"
    assert r.value == "FallbackLabel"


def test_value_pattern_raises_falls_through():
    class _Broken:
        @property
        def Value(self):
            raise RuntimeError("COM error")

    ctrl = _MockCtrl(value_pattern=_Broken(), Name="fallback")
    r = read_value(ctrl)
    assert r.source == "label"


# ---- TextPattern ----------------------------------------------------------


def test_text_pattern_returns_document_text():
    text = "Hello SGCL"
    ctrl = _MockCtrl(
        text_pattern=_MockPattern(DocumentRange=_MockDocumentRange(text)),
    )
    r = read_value(ctrl)
    assert r.supported is True
    assert r.source == "text_pattern"
    assert r.value == text
    assert r.details["truncated"] is False
    assert r.details["max_length"] == DEFAULT_MAX_LENGTH


def test_text_pattern_truncates_at_max_length():
    text = "x" * 100
    ctrl = _MockCtrl(
        text_pattern=_MockPattern(DocumentRange=_MockDocumentRange(text)),
    )
    r = read_value(ctrl, max_length=20)
    assert r.value == "x" * 20
    assert r.details["truncated"] is True
    assert r.details["max_length"] == 20


def test_value_pattern_takes_precedence_over_text_pattern():
    # Some controls support both; ValuePattern wins per the priority rule.
    ctrl = _MockCtrl(
        value_pattern=_MockPattern(Value="from_value", IsReadOnly=False),
        text_pattern=_MockPattern(DocumentRange=_MockDocumentRange("from_text")),
    )
    r = read_value(ctrl)
    assert r.source == "value_pattern"
    assert r.value == "from_value"


# ---- TogglePattern --------------------------------------------------------


def test_toggle_pattern_off_state():
    ctrl = _MockCtrl(toggle_pattern=_MockPattern(ToggleState=0))
    r = read_value(ctrl)
    assert r.source == "toggle_pattern"
    assert r.value == "off"
    assert r.details["state"] == "off"


def test_toggle_pattern_on_state():
    ctrl = _MockCtrl(toggle_pattern=_MockPattern(ToggleState=1))
    r = read_value(ctrl)
    assert r.value == "on"


def test_toggle_pattern_indeterminate_state():
    ctrl = _MockCtrl(toggle_pattern=_MockPattern(ToggleState=2))
    r = read_value(ctrl)
    assert r.value == "indeterminate"


def test_toggle_pattern_string_state_accepted():
    # Some wrappers normalize ToggleState to a string already.
    ctrl = _MockCtrl(toggle_pattern=_MockPattern(ToggleState="On"))
    r = read_value(ctrl)
    assert r.value == "on"


def test_toggle_pattern_named_state_accepted():
    # Some UIA enum wrappers expose a `.name` attribute.
    class _StateEnum:
        name = "On"

    ctrl = _MockCtrl(toggle_pattern=_MockPattern(ToggleState=_StateEnum()))
    r = read_value(ctrl)
    assert r.value == "on"


def test_toggle_pattern_unknown_state_falls_through():
    ctrl = _MockCtrl(
        toggle_pattern=_MockPattern(ToggleState=99),
        Name="fallback",
    )
    r = read_value(ctrl)
    assert r.source == "label"


# ---- SelectionPattern -----------------------------------------------------


def test_selection_pattern_returns_selected_item_labels():
    item1 = _MockPattern(Name="Apple")
    item2 = _MockPattern(Name="Banana")
    ctrl = _MockCtrl(
        selection_pattern=_MockPattern(GetSelection=lambda: [item1, item2]),
    )
    r = read_value(ctrl)
    assert r.source == "selection_pattern"
    assert r.value == "Apple, Banana"
    assert r.details["items"] == ["Apple", "Banana"]


def test_selection_pattern_empty_selection():
    ctrl = _MockCtrl(selection_pattern=_MockPattern(GetSelection=lambda: []))
    r = read_value(ctrl)
    assert r.supported is True  # we got a selection — it just happens to be empty
    assert r.source == "selection_pattern"
    assert r.value == ""
    assert r.details["items"] == []


def test_selection_pattern_skips_unnamed_items():
    item1 = _MockPattern(Name="Apple")
    item2 = _MockPattern(Name=None)
    item3 = _MockPattern(Name="")
    ctrl = _MockCtrl(
        selection_pattern=_MockPattern(GetSelection=lambda: [item1, item2, item3]),
    )
    r = read_value(ctrl)
    assert r.details["items"] == ["Apple"]


# ---- Label / aggregated text fallback -------------------------------------


def test_label_fallback_returns_name():
    """Calculator's NormalOutput is a static_text whose Name is the display value."""
    ctrl = _MockCtrl(Name="0")
    r = read_value(ctrl)
    assert r.supported is True
    assert r.source == "label"
    assert r.value == "0"
    assert r.details["label"] == "0"


def test_label_fallback_aggregates_descendants_when_no_self_label():
    child1 = _MockCtrl(Name="UTF-8")
    child2 = _MockCtrl(Name="Line 1, Col 1")
    ctrl = _MockCtrl(Name=None, children=[child1, child2])
    r = read_value(ctrl)
    assert r.source == "label"
    assert r.value == "UTF-8 Line 1, Col 1"
    assert r.details["label"] is None
    assert r.details["descendant_text"] == "UTF-8 Line 1, Col 1"


def test_label_fallback_prefers_self_label_to_descendants():
    child = _MockCtrl(Name="child-content")
    ctrl = _MockCtrl(Name="my-label", children=[child])
    r = read_value(ctrl)
    assert r.value == "my-label"
    assert r.details["label"] == "my-label"
    assert r.details["descendant_text"] == "child-content"


def test_label_fallback_caps_descendant_collection():
    children = [_MockCtrl(Name=f"text-{i}") for i in range(200)]
    ctrl = _MockCtrl(Name=None, children=children)
    r = read_value(ctrl)
    # Should stop at 64; the rest are not in the output.
    assert "text-63" in r.value
    assert "text-100" not in r.value


def test_label_strips_whitespace():
    ctrl = _MockCtrl(Name="  spaced  ")
    r = read_value(ctrl)
    assert r.value == "spaced"


# ---- supported: false -----------------------------------------------------


def test_supported_false_when_nothing_applies():
    """A control with no patterns and no readable text honestly reports unsupported."""
    ctrl = _MockCtrl()
    r = read_value(ctrl)
    assert r.supported is False
    assert r.source == "none"
    assert r.value is None
    assert r.details == {}


def test_get_children_failure_does_not_break_label():
    class _NoKids(_MockCtrl):
        def GetChildren(self):
            raise RuntimeError("UIA timeout")

    ctrl = _NoKids(Name="my-label")
    r = read_value(ctrl)
    # Self-label fallback still works even if descendant walk fails.
    assert r.value == "my-label"


# ---- ReadResult serialization --------------------------------------------


def test_read_result_to_dict_round_trips_through_json():
    import json

    ctrl = _MockCtrl(value_pattern=_MockPattern(Value="abc", IsReadOnly=True))
    r = read_value(ctrl)
    text = json.dumps(r.to_dict())
    loaded = json.loads(text)
    assert loaded == {
        "supported": True,
        "source": "value_pattern",
        "value": "abc",
        "details": {"read_only": True},
    }


def test_read_result_dataclass_constructor():
    r = ReadResult(supported=True, source="label", value="x")
    assert r.details == {}
