"""Windows-gated: do the mocks promise more than `uiautomation` delivers?

**This file is skipped on Linux. A skip is not a pass.** Every other test in
this suite runs against hand-written doubles, and those doubles are uniformly
*more capable* than the real library -- `_FakeCtrl` and `_MockCtrl` define all
six `Get*Pattern` methods and every attribute the walker reads, unconditionally.
A real control that omits a getter, or raises a COM error on attribute access,
is simulated in only a couple of hand-written cases.

So the Linux suite certifies the mocks' contract, not `uiautomation`'s. If an
upstream release renames a method or changes a signature, nothing here fails:
the duck-typed access means it does not even fail to import. It surfaces as a
silently empty tree during a manual Windows session -- the project's slowest
and most expensive feedback loop, and the one Phase 3 depends on.

This module is the only detector, and it only runs on Windows. The dependency
is also now capped below 3.0, which blocks the most likely form of that break
without needing anyone to run it.

The expected surface is **derived from the mocks themselves** rather than
written out again. A third hand-maintained list would drift from both. The
direction of the check is what matters: everything a mock fakes must exist on
a real control. The reverse is fine -- the real library may have plenty the
adapter never touches.

Follow-up worth doing: define a `Protocol` for the control surface the walker
and readers actually use. It would document the contract in one place, make
this test mechanical rather than introspective, and give a type checker
something to verify. Noted rather than done -- it is its own change.
"""

from __future__ import annotations

import sys

import pytest

requires_windows = pytest.mark.skipif(
    sys.platform != "win32",
    reason="needs a real `uiautomation` control; runs only in a Windows session",
)


def _mock_surface(mock_cls: type) -> tuple[set[str], set[str]]:
    """Split a mock's public surface into (methods, attributes).

    Instantiating rather than reading the class is deliberate: both doubles
    set their attributes in `__init__`, so the class body alone would report
    only the methods.
    """
    instance = mock_cls()
    methods, attributes = set(), set()
    for name in dir(instance):
        if name.startswith("_"):
            continue
        (methods if callable(getattr(instance, name)) else attributes).add(name)
    return methods, attributes


def _real_control():
    """A real UIA control that certainly exists: the desktop root."""
    import uiautomation as auto

    return auto.GetRootControl()


@requires_windows
def test_real_control_has_every_method_the_walker_mock_fakes():
    from tests.test_walker import _FakeCtrl

    methods, _ = _mock_surface(_FakeCtrl)
    # GetChildren plus the six pattern getters the walker probes.
    missing = [m for m in sorted(methods) if not hasattr(_real_control(), m)]
    assert not missing, (
        f"`uiautomation` no longer provides: {missing}. The walker accesses these "
        "duck-typed, so this would not raise on import -- it would produce an "
        "empty or degraded tree at runtime."
    )


@requires_windows
def test_real_control_has_every_attribute_the_walker_mock_fakes():
    from tests.test_walker import _FakeCtrl

    _, attributes = _mock_surface(_FakeCtrl)
    missing = [a for a in sorted(attributes) if not hasattr(_real_control(), a)]
    assert not missing, f"`uiautomation` no longer provides attributes: {missing}"


@requires_windows
def test_real_control_has_every_method_the_reader_mock_fakes():
    from tests.test_readers import _MockCtrl

    methods, _ = _mock_surface(_MockCtrl)
    missing = [m for m in sorted(methods) if not hasattr(_real_control(), m)]
    assert not missing, f"`uiautomation` no longer provides: {missing}"


@requires_windows
def test_real_bounding_rectangle_exposes_the_edges_the_walker_reads():
    """`extract_bounds` reads left/top/right/bottom and optional width/height.

    The width/height fallback exists for exactly this object. On Linux all
    three rect flavours are simulated; here we find out which one is real.
    """
    rect = _real_control().BoundingRectangle
    for edge in ("left", "top", "right", "bottom"):
        assert hasattr(rect, edge), f"real rect has no {edge!r}"


@requires_windows
def test_real_control_type_name_is_a_string_the_role_map_can_key_on():
    """`normalize_role` keys `_UIA_TO_ROLE` on this exact value."""
    name = _real_control().ControlTypeName
    assert isinstance(name, str) and name


# ---- the machinery, checked where it can be checked ----


def test_mock_surface_reports_a_real_surface():
    """Runs on every platform, unlike everything above it.

    If `_mock_surface` ever returned empty sets, every Windows assertion in
    this module would pass vacuously -- `not []` is true. Nobody would
    notice, because the only place they run is a manual session where a
    green result is what you expect. This is the guard for that.
    """
    from tests.test_readers import _MockCtrl
    from tests.test_walker import _FakeCtrl

    methods, attributes = _mock_surface(_FakeCtrl)
    assert "GetChildren" in methods
    assert {"GetInvokePattern", "GetValuePattern", "GetTogglePattern"} <= methods
    assert {"ControlTypeName", "Name", "BoundingRectangle"} <= attributes
    assert not any(n.startswith("_") for n in methods | attributes)

    reader_methods, _ = _mock_surface(_MockCtrl)
    assert {"GetValuePattern", "GetTextPattern"} <= reader_methods


def test_mock_surface_separates_methods_from_attributes():
    """A method mis-sorted as an attribute would weaken the real check."""

    class _Sample:
        def __init__(self):
            self.plain = 1

        def callable_one(self):
            return None

    methods, attributes = _mock_surface(_Sample)
    assert methods == {"callable_one"}
    assert attributes == {"plain"}
