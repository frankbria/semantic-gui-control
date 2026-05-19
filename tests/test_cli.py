from __future__ import annotations

import json
import sys

import pytest

from sgcl import cli


def _run(capsys, fake_adapter_factory, argv):
    rc = cli.main(argv, adapter_factory=fake_adapter_factory)
    out = capsys.readouterr().out
    return rc, out


# ---- windows ----


def test_windows_returns_list(capsys, fake_adapter_factory):
    rc, out = _run(capsys, fake_adapter_factory, ["windows"])
    assert rc == 0
    data = json.loads(out)
    assert isinstance(data, list)
    # 3 non-system windows visible; Taskbar is hidden by default.
    assert len(data) == 3
    titles = [w["title"] for w in data]
    assert "Calculator" in titles
    assert "Taskbar" not in titles


def test_windows_include_system_shows_shell_windows(capsys, fake_adapter_factory):
    rc, out = _run(capsys, fake_adapter_factory, ["windows", "--include-system"])
    assert rc == 0
    data = json.loads(out)
    assert len(data) == 4
    titles = [w["title"] for w in data]
    assert "Taskbar" in titles
    taskbar = next(w for w in data if w["title"] == "Taskbar")
    assert taskbar["is_system_surface"] is True


# ---- active ----


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


# ---- inspect: targeting ----


def test_inspect_active(capsys, fake_adapter_factory):
    rc, out = _run(capsys, fake_adapter_factory, ["inspect", "--active"])
    assert rc == 0
    data = json.loads(out)
    assert data["raw_ref"]["window_id"] == "hwnd_111"  # the active window


def test_inspect_specific_window(capsys, fake_adapter_factory):
    rc, out = _run(capsys, fake_adapter_factory, ["inspect", "--window", "hwnd_222"])
    assert rc == 0
    data = json.loads(out)
    assert data["raw_ref"]["window_id"] == "hwnd_222"
    assert data["label"] == "Calculator"


def test_inspect_by_process_unique_match(capsys, fake_adapter_factory):
    rc, out = _run(capsys, fake_adapter_factory, ["inspect", "--process", "Calculator"])
    assert rc == 0
    data = json.loads(out)
    assert data["raw_ref"]["window_id"] == "hwnd_222"


def test_inspect_by_process_accepts_exe_suffix(capsys, fake_adapter_factory):
    rc, out = _run(capsys, fake_adapter_factory, ["inspect", "--process", "calculator.exe"])
    assert rc == 0
    data = json.loads(out)
    assert data["raw_ref"]["window_id"] == "hwnd_222"


def test_inspect_by_process_is_case_insensitive(capsys, fake_adapter_factory):
    rc, out = _run(capsys, fake_adapter_factory, ["inspect", "--process", "CALCULATOR"])
    assert rc == 0
    data = json.loads(out)
    assert data["raw_ref"]["window_id"] == "hwnd_222"


def test_inspect_by_title_substring(capsys, fake_adapter_factory):
    rc, out = _run(capsys, fake_adapter_factory, ["inspect", "--title", "second"])
    assert rc == 0
    data = json.loads(out)
    assert data["raw_ref"]["window_id"] == "hwnd_333"


def test_inspect_by_pid(capsys, fake_adapter_factory):
    rc, out = _run(capsys, fake_adapter_factory, ["inspect", "--pid", "5678"])
    assert rc == 0
    data = json.loads(out)
    assert data["raw_ref"]["window_id"] == "hwnd_222"


def test_inspect_skips_system_surfaces_by_default(capsys, fake_adapter_factory):
    # The Taskbar (hwnd_444) is process_name=explorer.exe + is_system_surface.
    # `--process explorer.exe` would normally match it, but it must be hidden.
    with pytest.raises(SystemExit):
        cli.main(
            ["inspect", "--process", "explorer.exe"],
            adapter_factory=fake_adapter_factory,
        )


def test_inspect_include_system_reaches_shell_windows(capsys, fake_adapter_factory):
    rc, out = _run(
        capsys,
        fake_adapter_factory,
        ["inspect", "--include-system", "--process", "explorer.exe"],
    )
    assert rc == 0
    data = json.loads(out)
    assert data["raw_ref"]["window_id"] == "hwnd_444"


def test_inspect_window_id_works_even_for_system_surface(capsys, fake_adapter_factory):
    # Explicit --window is always honored, no filter applied.
    rc, out = _run(capsys, fake_adapter_factory, ["inspect", "--window", "hwnd_444"])
    assert rc == 0
    data = json.loads(out)
    assert data["raw_ref"]["window_id"] == "hwnd_444"


def test_inspect_ambiguous_process_errors(capsys, fake_adapter_factory):
    # Two Notepad windows match.
    with pytest.raises(SystemExit):
        cli.main(
            ["inspect", "--process", "Notepad"],
            adapter_factory=fake_adapter_factory,
        )
    err = capsys.readouterr().err
    assert "2 windows matched" in err
    assert "hwnd_111" in err and "hwnd_333" in err


def test_inspect_no_match_errors(capsys, fake_adapter_factory):
    with pytest.raises(SystemExit):
        cli.main(
            ["inspect", "--process", "nonsuch.exe"],
            adapter_factory=fake_adapter_factory,
        )
    err = capsys.readouterr().err
    assert "no window matched" in err


def test_inspect_requires_target(fake_adapter_factory):
    with pytest.raises(SystemExit):
        cli.main(["inspect"], adapter_factory=fake_adapter_factory)


def test_inspect_rejects_multiple_targets(fake_adapter_factory):
    with pytest.raises(SystemExit):
        cli.main(
            ["inspect", "--active", "--window", "hwnd_111"],
            adapter_factory=fake_adapter_factory,
        )
    with pytest.raises(SystemExit):
        cli.main(
            ["inspect", "--process", "Notepad", "--title", "Notepad"],
            adapter_factory=fake_adapter_factory,
        )


# ---- inspect: depth and delay ----


def test_inspect_depth_zero_drops_children(capsys, fake_adapter_factory):
    rc, out = _run(capsys, fake_adapter_factory, ["inspect", "--active", "--depth", "0"])
    assert rc == 0
    data = json.loads(out)
    assert data["children"] == []


def test_inspect_rejects_negative_depth(fake_adapter_factory):
    with pytest.raises(SystemExit):
        cli.main(
            ["inspect", "--active", "--depth", "-1"],
            adapter_factory=fake_adapter_factory,
        )


def test_inspect_delay_sleeps(capsys, fake_adapter_factory, monkeypatch):
    calls: list[float] = []
    monkeypatch.setattr(cli.time, "sleep", lambda s: calls.append(s))
    rc = cli.main(
        ["inspect", "--active", "--delay", "2.5"],
        adapter_factory=fake_adapter_factory,
    )
    captured = capsys.readouterr()
    assert rc == 0
    assert calls == [2.5]
    assert "waiting 2.5s" in captured.err


def test_inspect_delay_zero_does_not_sleep(capsys, fake_adapter_factory, monkeypatch):
    calls: list[float] = []
    monkeypatch.setattr(cli.time, "sleep", lambda s: calls.append(s))
    rc, _ = _run(capsys, fake_adapter_factory, ["inspect", "--active"])
    assert rc == 0
    assert calls == []


def test_inspect_rejects_negative_delay(fake_adapter_factory):
    with pytest.raises(SystemExit):
        cli.main(
            ["inspect", "--active", "--delay", "-1"],
            adapter_factory=fake_adapter_factory,
        )


# ---- output formatting ----


def test_pretty_flag_indents_output(capsys, fake_adapter_factory):
    rc, out = _run(capsys, fake_adapter_factory, ["--pretty", "active"])
    assert rc == 0
    assert "\n  " in out
    json.loads(out)


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


def test_output_writes_file_directly_in_utf8(tmp_path, capsys, fake_adapter_factory):
    """Bypassing the shell pipe avoids cp437 mojibake on Windows."""
    out_path = tmp_path / "out.json"
    rc = cli.main(
        ["windows", "--output", str(out_path)],
        adapter_factory=fake_adapter_factory,
    )
    assert rc == 0
    # Nothing should hit stdout when --output is given.
    assert capsys.readouterr().out == ""
    # File exists and parses as JSON.
    text = out_path.read_text(encoding="utf-8")
    data = json.loads(text)
    assert isinstance(data, list)
    assert any(w["title"] == "Calculator" for w in data)


def test_output_preserves_non_ascii_bytes(tmp_path, fake_adapter, fake_adapter_factory):
    """The whole point of --output: non-ASCII codepoints survive intact."""
    fake_adapter._windows[0].title = "Pi=π and √2"
    out_path = tmp_path / "out.json"
    rc = cli.main(
        ["windows", "--output", str(out_path)],
        adapter_factory=fake_adapter_factory,
    )
    assert rc == 0
    raw = out_path.read_bytes()
    # No BOM (we asked for UTF-8 without BOM explicitly).
    assert not raw.startswith(b"\xef\xbb\xbf")
    # The Greek pi (U+03C0) should appear as the canonical 2-byte UTF-8.
    assert b"\xcf\x80" in raw
    # And we should NOT see the cp437 round-trip mojibake bytes.
    assert b"\xe2\x95\xa7\xc3\x87" not in raw


def test_output_works_before_subcommand(tmp_path, fake_adapter_factory):
    out_path = tmp_path / "out.json"
    rc = cli.main(
        ["--output", str(out_path), "windows"],
        adapter_factory=fake_adapter_factory,
    )
    assert rc == 0
    assert out_path.exists()


def test_emit_handles_unicode_private_use_area(capsys, fake_adapter, fake_adapter_factory):
    """Icon-font glyphs (Segoe Fluent Icons live in PUA) must not crash on
    Windows where stdout defaults to cp1252. Verifies main() reconfigures
    stdout to UTF-8 and that PUA codepoints round-trip through JSON."""
    fake_adapter._windows[0].title = "Tab  menu"  # PUA codepoint
    rc, out = _run(capsys, fake_adapter_factory, ["windows"])
    assert rc == 0
    data = json.loads(out)
    assert data[0]["title"] == "Tab  menu"
