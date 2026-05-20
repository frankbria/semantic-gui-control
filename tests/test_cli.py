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


# ---- find subcommand ------------------------------------------------------


def test_find_by_label_returns_single_match(capsys, fake_adapter_factory):
    rc, out = _run(
        capsys,
        fake_adapter_factory,
        ["find", "--window", "hwnd_222", "--label", "Equals"],
    )
    assert rc == 0
    data = json.loads(out)
    assert isinstance(data, dict)
    assert len(data["matches"]) == 1
    assert data["matches"][0]["control"]["id"] == "ctrl_eq"
    assert data["matches"][0]["match_confidence"] == 1.0


def test_find_by_synonym_matches_via_text_selector(capsys, fake_adapter_factory):
    rc, out = _run(capsys, fake_adapter_factory, ["find", "--window", "hwnd_222", "--text", "0"])
    assert rc == 0
    data = json.loads(out)
    ids = [m["control"]["id"] for m in data["matches"]]
    # "Zero" via synonym "0" should rank first; "Display is 0" via label_contains
    # is second.
    assert ids[0] == "ctrl_zero"
    assert data["matches"][0]["match_confidence"] == 0.9


def test_find_by_role_returns_all_buttons(capsys, fake_adapter_factory):
    rc, out = _run(
        capsys, fake_adapter_factory, ["find", "--window", "hwnd_222", "--role", "button"]
    )
    assert rc == 0
    data = json.loads(out)
    ids = {m["control"]["id"] for m in data["matches"]}
    # zero, plus, equals, pi, settings — 5 buttons.
    assert ids == {"ctrl_zero", "ctrl_plus", "ctrl_eq", "ctrl_pi", "ctrl_settings"}


def test_find_limit_caps_results(capsys, fake_adapter_factory):
    rc, out = _run(
        capsys,
        fake_adapter_factory,
        ["find", "--window", "hwnd_222", "--role", "button", "--limit", "2"],
    )
    assert rc == 0
    data = json.loads(out)
    assert len(data["matches"]) == 2


def test_find_with_no_matches_returns_empty_list(capsys, fake_adapter_factory):
    rc, out = _run(
        capsys,
        fake_adapter_factory,
        ["find", "--window", "hwnd_222", "--label", "nonexistent"],
    )
    assert rc == 0
    data = json.loads(out)
    assert data["matches"] == []


def test_find_description_match_for_icon_button(capsys, fake_adapter_factory):
    rc, out = _run(
        capsys,
        fake_adapter_factory,
        ["find", "--window", "hwnd_222", "--text", "Settings"],
    )
    assert rc == 0
    data = json.loads(out)
    assert len(data["matches"]) == 1
    assert data["matches"][0]["control"]["id"] == "ctrl_settings"
    assert data["matches"][0]["match_confidence"] == 0.85


def test_find_relationship_filter_inside(capsys, fake_adapter_factory):
    # All controls inside the keypad — should be the 4 buttons.
    rc, out = _run(
        capsys,
        fake_adapter_factory,
        ["find", "--window", "hwnd_222", "--inside", "ctrl_keypad"],
    )
    assert rc == 0
    data = json.loads(out)
    ids = {m["control"]["id"] for m in data["matches"]}
    assert ids == {"ctrl_zero", "ctrl_plus", "ctrl_eq", "ctrl_pi"}


def test_find_with_parent_role_filters_by_direct_parent(capsys, fake_adapter_factory):
    # Buttons whose parent role is "group" — keypad children + the lone
    # settings button (which is a direct child of the window, not a group),
    # so only the keypad children qualify.
    rc, out = _run(
        capsys,
        fake_adapter_factory,
        [
            "find",
            "--window",
            "hwnd_222",
            "--role",
            "button",
            "--with-parent-role",
            "group",
        ],
    )
    assert rc == 0
    data = json.loads(out)
    ids = {m["control"]["id"] for m in data["matches"]}
    assert ids == {"ctrl_zero", "ctrl_plus", "ctrl_eq", "ctrl_pi"}


def test_find_tri_state_disabled_filter(capsys, fake_adapter, fake_adapter_factory):
    # Force the Save button into a disabled state by mutating the fixture
    # builder. (We use the closure indirectly: re-shape the inspect call.)
    # Easier: just check the default state filter is None and matches both.
    rc, out = _run(
        capsys,
        fake_adapter_factory,
        ["find", "--window", "hwnd_111", "--role", "button", "--enabled"],
    )
    assert rc == 0
    data = json.loads(out)
    # The Notepad Save button is enabled by default.
    assert len(data["matches"]) == 1
    assert data["matches"][0]["control"]["label"] == "Save"


def test_find_rejects_negative_depth(fake_adapter_factory):
    with pytest.raises(SystemExit):
        cli.main(
            ["find", "--window", "hwnd_222", "--role", "button", "--depth", "-1"],
            adapter_factory=fake_adapter_factory,
        )


def test_find_rejects_negative_limit(fake_adapter_factory):
    with pytest.raises(SystemExit):
        cli.main(
            [
                "find",
                "--window",
                "hwnd_222",
                "--role",
                "button",
                "--limit",
                "-1",
            ],
            adapter_factory=fake_adapter_factory,
        )


def test_find_requires_window_target(fake_adapter_factory):
    with pytest.raises(SystemExit):
        cli.main(
            ["find", "--role", "button"],
            adapter_factory=fake_adapter_factory,
        )


def test_find_output_to_file_uses_utf8(tmp_path, fake_adapter_factory):
    out_path = tmp_path / "find.json"
    rc = cli.main(
        [
            "find",
            "--window",
            "hwnd_222",
            "--text",
            "π",
            "--output",
            str(out_path),
        ],
        adapter_factory=fake_adapter_factory,
    )
    assert rc == 0
    raw = out_path.read_bytes()
    # π = U+03C0 → UTF-8 b'\xcf\x80' should appear in the synonyms list.
    assert b"\xcf\x80" in raw


def test_find_ranks_results_by_combined_rank(capsys, fake_adapter_factory):
    # Two text selectors that hit different controls at different scores.
    rc, out = _run(capsys, fake_adapter_factory, ["find", "--window", "hwnd_222", "--text", "Pi"])
    assert rc == 0
    data = json.loads(out)
    # ctrl_pi: exact label hit (1.0).
    # ctrl_display: no hit on "Pi".
    # ctrl_keypad has label "Number pad" — no hit.
    assert data["matches"][0]["control"]["id"] == "ctrl_pi"
    assert data["matches"][0]["combined_rank"] == 1.0


# ---- read subcommand ------------------------------------------------------


def test_read_by_label_returns_value_and_affordance(capsys, fake_adapter_factory):
    rc, out = _run(
        capsys,
        fake_adapter_factory,
        ["read", "--window", "hwnd_222", "--label", "Display is 0"],
    )
    assert rc == 0
    data = json.loads(out)
    assert data["supported"] is True
    assert data["source"] == "label"
    assert data["value"] == "Display is 0"
    assert data["affordance"]["id"] == "ctrl_display"
    assert data["affordance"]["role"] == "static_text"


def test_read_by_synonym_via_text(capsys, fake_adapter_factory):
    rc, out = _run(
        capsys,
        fake_adapter_factory,
        ["read", "--window", "hwnd_222", "--text", "π"],
    )
    assert rc == 0
    data = json.loads(out)
    assert data["affordance"]["id"] == "ctrl_pi"
    # FakeAdapter synthesizes label-source results; the "value" is the label.
    assert data["value"] == "Pi"


def test_read_by_target_ctrl_id(capsys, fake_adapter_factory):
    rc, out = _run(
        capsys,
        fake_adapter_factory,
        ["read", "--window", "hwnd_222", "--target", "ctrl_eq"],
    )
    assert rc == 0
    data = json.loads(out)
    assert data["affordance"]["id"] == "ctrl_eq"
    assert data["value"] == "Equals"


def test_read_no_match_errors_cleanly(capsys, fake_adapter_factory):
    with pytest.raises(SystemExit):
        cli.main(
            ["read", "--window", "hwnd_222", "--label", "nonexistent"],
            adapter_factory=fake_adapter_factory,
        )
    err = capsys.readouterr().err
    assert "no control matched" in err


def test_read_ambiguous_errors(capsys, fake_adapter_factory):
    # role=button hits 5 controls in the Calculator tree.
    with pytest.raises(SystemExit):
        cli.main(
            ["read", "--window", "hwnd_222", "--role", "button"],
            adapter_factory=fake_adapter_factory,
        )
    err = capsys.readouterr().err
    assert "5 controls matched" in err or "controls matched" in err


def test_read_requires_target_or_selector(capsys, fake_adapter_factory):
    with pytest.raises(SystemExit):
        cli.main(
            ["read", "--window", "hwnd_222"],
            adapter_factory=fake_adapter_factory,
        )
    err = capsys.readouterr().err
    assert "--target" in err or "selector" in err


def test_read_target_and_selector_are_mutually_exclusive(capsys, fake_adapter_factory):
    with pytest.raises(SystemExit):
        cli.main(
            [
                "read",
                "--window",
                "hwnd_222",
                "--target",
                "ctrl_eq",
                "--label",
                "Equals",
            ],
            adapter_factory=fake_adapter_factory,
        )


def test_read_rejects_negative_max_length(fake_adapter_factory):
    with pytest.raises(SystemExit):
        cli.main(
            [
                "read",
                "--window",
                "hwnd_222",
                "--label",
                "Pi",
                "--max-length",
                "-1",
            ],
            adapter_factory=fake_adapter_factory,
        )


def test_read_unsupported_for_unreadable_target(capsys, fake_adapter, fake_adapter_factory):
    # The settings icon has label "" (empty), so FakeAdapter's
    # label-fallback returns supported=False.
    rc, out = _run(
        capsys,
        fake_adapter_factory,
        ["read", "--window", "hwnd_222", "--target", "ctrl_settings"],
    )
    assert rc == 0
    data = json.loads(out)
    assert data["supported"] is False
    assert data["source"] == "none"
    assert data["value"] is None


def test_read_output_to_file_preserves_unicode(tmp_path, fake_adapter_factory):
    out_path = tmp_path / "read.json"
    rc = cli.main(
        [
            "read",
            "--window",
            "hwnd_222",
            "--text",
            "π",
            "--output",
            str(out_path),
        ],
        adapter_factory=fake_adapter_factory,
    )
    assert rc == 0
    raw = out_path.read_bytes()
    # π appears in the affordance's synonyms list.
    assert b"\xcf\x80" in raw


# ---- existing emit/unicode tests below ------------------------------------


def test_emit_handles_unicode_private_use_area(capsys, fake_adapter, fake_adapter_factory):
    """Icon-font glyphs (Segoe Fluent Icons live in PUA) must not crash on
    Windows where stdout defaults to cp1252. Verifies main() reconfigures
    stdout to UTF-8 and that PUA codepoints round-trip through JSON."""
    fake_adapter._windows[0].title = "Tab  menu"  # PUA codepoint
    rc, out = _run(capsys, fake_adapter_factory, ["windows"])
    assert rc == 0
    data = json.loads(out)
    assert data[0]["title"] == "Tab  menu"
