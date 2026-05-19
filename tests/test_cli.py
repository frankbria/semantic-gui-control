from __future__ import annotations

import json
import sys

import pytest

from sgcl import cli


def _run(capsys, fake_adapter_factory, argv):
    rc = cli.main(argv, adapter_factory=fake_adapter_factory)
    out = capsys.readouterr().out
    return rc, out


def test_windows_returns_list(capsys, fake_adapter_factory):
    rc, out = _run(capsys, fake_adapter_factory, ["windows"])
    assert rc == 0
    data = json.loads(out)
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]["title"] == "Untitled - Notepad"
    assert data[0]["is_active"] is True
    assert data[1]["title"] == "Calculator"


def test_active_returns_window_object(capsys, fake_adapter_factory):
    rc, out = _run(capsys, fake_adapter_factory, ["active"])
    assert rc == 0
    data = json.loads(out)
    assert isinstance(data, dict)
    assert data["title"] == "Untitled - Notepad"


def test_active_returns_null_when_no_foreground(capsys, fake_adapter, fake_adapter_factory):
    fake_adapter.active_returns = None
    rc, out = _run(capsys, fake_adapter_factory, ["active"])
    assert rc == 0
    assert json.loads(out) is None


def test_inspect_active(capsys, fake_adapter_factory):
    rc, out = _run(capsys, fake_adapter_factory, ["inspect", "--active"])
    assert rc == 0
    data = json.loads(out)
    assert data["id"] == "ctrl_0"
    assert data["role"] == "window"
    assert len(data["children"]) == 1
    assert data["children"][0]["role"] == "text_field"


def test_inspect_depth_zero_drops_children(capsys, fake_adapter_factory):
    rc, out = _run(capsys, fake_adapter_factory, ["inspect", "--active", "--depth", "0"])
    assert rc == 0
    data = json.loads(out)
    assert data["children"] == []


def test_inspect_specific_window(capsys, fake_adapter_factory):
    rc, out = _run(capsys, fake_adapter_factory, ["inspect", "--window", "hwnd_111"])
    assert rc == 0
    data = json.loads(out)
    assert data["role"] == "window"


def test_inspect_requires_target(capsys, fake_adapter_factory):
    with pytest.raises(SystemExit):
        cli.main(["inspect"], adapter_factory=fake_adapter_factory)


def test_inspect_rejects_both_targets(capsys, fake_adapter_factory):
    with pytest.raises(SystemExit):
        cli.main(
            ["inspect", "--active", "--window", "hwnd_111"],
            adapter_factory=fake_adapter_factory,
        )


def test_inspect_rejects_negative_depth(capsys, fake_adapter_factory):
    with pytest.raises(SystemExit):
        cli.main(
            ["inspect", "--active", "--depth", "-1"],
            adapter_factory=fake_adapter_factory,
        )


def test_pretty_flag_indents_output(capsys, fake_adapter_factory):
    rc, out = _run(capsys, fake_adapter_factory, ["--pretty", "active"])
    assert rc == 0
    assert "\n  " in out  # indented
    json.loads(out)  # still valid JSON


def test_pretty_flag_after_subcommand(capsys, fake_adapter_factory):
    rc, out = _run(capsys, fake_adapter_factory, ["active", "--pretty"])
    assert rc == 0
    assert "\n  " in out


def test_no_command_errors():
    with pytest.raises(SystemExit):
        cli.main([])


def test_default_adapter_factory_refuses_non_windows():
    if sys.platform == "win32":
        pytest.skip("This test only meaningful off Windows.")
    with pytest.raises(SystemExit) as exc:
        cli._default_adapter_factory()
    assert "Windows" in str(exc.value)
