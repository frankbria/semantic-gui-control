"""Contract suite: invariants every adapter must satisfy.

Blunt win 9's exit criterion is "the contract test suite runs against two
adapters with the same expectations and the same JSON shape"
(`docs/roadmap-blunt-wins.md`). This is that suite. It exists now, with one
real adapter, because building it later alongside a second adapter means
debugging the harness and the adapter at the same time.

On Linux only `FakeAdapter` is exercised -- `windows_uia` raises ImportError
off-Windows by design. That is still worth having: when `macos_ax` lands, it
implements the ABC and inherits every assertion here for free, and the
Windows adapter is already covered whenever the suite runs on Windows.

**These assert the contract, not the implementation.** Anything that depends
on a specific tree shape, id scheme, or window belongs in an adapter's own
test file. What belongs here is what `sgcl/core/adapter_base.py` promises a
caller, in the words of its own docstrings: the exactly-one-of precondition,
the LookupError policy, and the shapes that come back.
"""

from __future__ import annotations

import pytest

from sgcl.core.adapter_base import Adapter, ReadResolution
from sgcl.core.matcher import Query
from sgcl.core.read_result import ReadResult
from sgcl.core.schema import Control, WindowInfo


def _available_adapters() -> list[pytest.param]:
    """Every adapter importable on this platform, as pytest params.

    Adapters that cannot be imported here are reported as skips rather than
    silently omitted -- a suite that quietly exercises nothing is worse than
    one that says so.
    """
    params: list = []

    from tests.conftest import FakeAdapter

    params.append(pytest.param(FakeAdapter, id="fake"))

    try:
        from sgcl.adapters.windows_uia._adapter import WindowsUIAAdapter
    except ImportError as exc:
        params.append(
            pytest.param(
                None,
                id="windows_uia",
                marks=pytest.mark.skip(reason=f"not importable here: {exc}"),
            )
        )
    else:
        params.append(pytest.param(WindowsUIAAdapter, id="windows_uia"))

    return params


@pytest.fixture(params=_available_adapters())
def adapter(request) -> Adapter:
    return request.param()


def _some_window_id(adapter: Adapter) -> str:
    windows = adapter.list_windows()
    if not windows:
        pytest.skip("adapter reports no windows on this machine")
    return windows[0].id


# ---- identity ----


def test_declares_a_name_and_platform(adapter):
    """Both are emitted once per response, so neither may be blank."""
    assert isinstance(adapter.name, str) and adapter.name.strip()
    assert isinstance(adapter.platform, str) and adapter.platform.strip()


def test_is_an_adapter(adapter):
    assert isinstance(adapter, Adapter)


# ---- window enumeration ----


def test_list_windows_returns_window_infos(adapter):
    windows = adapter.list_windows()
    assert isinstance(windows, list)
    assert all(isinstance(w, WindowInfo) for w in windows)
    assert all(isinstance(w.id, str) and w.id for w in windows)


def test_active_window_is_a_window_info_or_none(adapter):
    active = adapter.active_window()
    assert active is None or isinstance(active, WindowInfo)


# ---- inspect_window ----


def test_inspect_returns_a_tree_rooted_at_the_requested_window(adapter):
    tree = adapter.inspect_window(_some_window_id(adapter), depth=2)
    assert isinstance(tree, Control)
    assert isinstance(tree.id, str) and tree.id
    assert tree.parent_id is None, "the root of a walk has no parent"


def test_inspect_unknown_window_raises_lookup_error(adapter):
    """The ABC documents LookupError for a well-formed but unresolvable id."""
    with pytest.raises(LookupError):
        adapter.inspect_window("no_such_window_id", depth=1)


# ---- read: the exactly-one-of precondition ----


def test_read_with_neither_selector_raises_value_error(adapter):
    with pytest.raises(ValueError):
        adapter.read(_some_window_id(adapter))


def test_read_with_both_selectors_raises_value_error(adapter):
    with pytest.raises(ValueError):
        adapter.read(_some_window_id(adapter), query=Query(role="button"), target_id="ctrl_0")


def test_precondition_is_checked_before_the_window_is_resolved(adapter):
    """A malformed request reports the argument error, not a window error.

    Order matters for the CLI's reason codes: this must surface as
    `missing_selector`, never as `window_not_found`.
    """
    with pytest.raises(ValueError):
        adapter.read("no_such_window_id")


# ---- read: the LookupError policy ----


def test_read_unknown_target_id_raises_lookup_error(adapter):
    with pytest.raises(LookupError):
        adapter.read(_some_window_id(adapter), target_id="ctrl_nonexistent_99999")


def test_read_unmatched_query_raises_lookup_error(adapter):
    with pytest.raises(LookupError):
        adapter.read(
            _some_window_id(adapter),
            query=Query(label="a label no control could plausibly have"),
        )


# ---- read: the shape that comes back ----


def test_read_returns_a_resolution_pairing_value_and_affordance(adapter):
    """Whatever an adapter reads, it says which affordance it read."""
    window_id = _some_window_id(adapter)
    tree = adapter.inspect_window(window_id, depth=8)

    resolution = adapter.read(window_id, target_id=tree.id)

    assert isinstance(resolution, ReadResolution)
    assert isinstance(resolution.result, ReadResult)
    assert isinstance(resolution.control, Control)
    assert resolution.control.id == tree.id


def test_unsupported_read_is_distinguishable_from_an_empty_value(adapter):
    """`supported=False` must never carry a value.

    The distinction is the whole reason the field exists -- "could not
    extract" is a different statement from "the value was empty", which
    surfaces as `value=""` with `supported=True`.
    """
    window_id = _some_window_id(adapter)
    tree = adapter.inspect_window(window_id, depth=8)
    result = adapter.read(window_id, target_id=tree.id).result

    assert isinstance(result.supported, bool)
    assert isinstance(result.source, str) and result.source
    if not result.supported:
        assert result.value is None
