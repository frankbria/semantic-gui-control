from __future__ import annotations

import json
import sys

import pytest

from sgcl import cli


def _run(capsys, fake_adapter_factory, argv):
    rc = cli.main(argv, adapter_factory=fake_adapter_factory)
    out = capsys.readouterr().out
    return rc, out


def _run_failing(capsys, factory, argv):
    """Run a command expected to fail; return (exit_code, parsed envelope).

    Runtime failures no longer raise SystemExit -- they return a non-zero
    code and write a JSON envelope to stdout, so an agent can branch on
    `reason` instead of regex-matching prose. See docs/command-vocabulary.md.
    """
    rc = cli.main(argv, adapter_factory=factory)
    return rc, json.loads(capsys.readouterr().out)


# ---- windows ----


def test_windows_returns_list(capsys, fake_adapter_factory):
    rc, out = _run(capsys, fake_adapter_factory, ["windows"])
    assert rc == 0
    data = json.loads(out)["windows"]
    assert isinstance(data, list)
    # 3 non-system windows visible; Taskbar is hidden by default.
    assert len(data) == 3
    titles = [w["title"] for w in data]
    assert "Calculator" in titles
    assert "Taskbar" not in titles


def test_windows_include_system_shows_shell_windows(capsys, fake_adapter_factory):
    rc, out = _run(capsys, fake_adapter_factory, ["windows", "--include-system"])
    assert rc == 0
    data = json.loads(out)["windows"]
    assert len(data) == 4
    titles = [w["title"] for w in data]
    assert "Taskbar" in titles
    taskbar = next(w for w in data if w["title"] == "Taskbar")
    assert taskbar["is_system_surface"] is True


# ---- active ----


def test_active_returns_window_object(capsys, fake_adapter_factory):
    rc, out = _run(capsys, fake_adapter_factory, ["active"])
    assert rc == 0
    data = json.loads(out)["window"]
    assert isinstance(data, dict)
    assert data["title"] == "Untitled - Notepad"


def test_active_returns_null_when_no_foreground(capsys, fake_adapter, fake_adapter_factory):
    fake_adapter.active_returns = None
    rc, out = _run(capsys, fake_adapter_factory, ["active"])
    assert rc == 0
    assert json.loads(out)["window"] is None


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
    rc, env = _run_failing(capsys, fake_adapter_factory, ["inspect", "--process", "explorer.exe"])
    assert rc != 0
    assert env["status"] == "error"
    assert env["reason"] == "window_not_found"


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
    rc, env = _run_failing(capsys, fake_adapter_factory, ["inspect", "--process", "Notepad"])
    assert rc != 0
    assert env["reason"] == "ambiguous_window"
    assert "2 windows matched" in env["message"]
    ids = [c["id"] for c in env["candidates"]]
    assert ids == ["hwnd_111", "hwnd_333"]
    assert all("title" in c for c in env["candidates"])


def test_inspect_no_match_errors(capsys, fake_adapter_factory):
    rc, env = _run_failing(capsys, fake_adapter_factory, ["inspect", "--process", "nonsuch.exe"])
    assert rc != 0
    assert env["reason"] == "window_not_found"
    assert "no window matched" in env["message"]


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


def test_inspect_rejects_negative_depth(capsys, fake_adapter_factory):
    rc, env = _run_failing(capsys, fake_adapter_factory, ["inspect", "--active", "--depth", "-1"])
    assert rc != 0
    assert env["reason"] == "invalid_argument"


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


def test_inspect_rejects_negative_delay(capsys, fake_adapter_factory):
    rc, env = _run_failing(capsys, fake_adapter_factory, ["inspect", "--active", "--delay", "-1"])
    assert rc != 0
    assert env["reason"] == "invalid_argument"


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
    data = json.loads(text)["windows"]
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


def test_output_captures_error_envelope_too(tmp_path, capsys, fake_adapter_factory):
    """--output redirects *the response*, and an error envelope is one.

    Routing failures around --output back to stdout would push them through
    the very pipe the flag exists to bypass. One channel, always.
    """
    out_path = tmp_path / "out.json"
    rc = cli.main(
        ["inspect", "--process", "nonsuch.exe", "--output", str(out_path)],
        adapter_factory=fake_adapter_factory,
    )
    assert rc == 1
    assert capsys.readouterr().out == ""
    envelope = json.loads(out_path.read_text(encoding="utf-8"))
    assert envelope["status"] == "error"
    assert envelope["reason"] == "window_not_found"


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


def test_find_rejects_negative_depth(capsys, fake_adapter_factory):
    rc, env = _run_failing(
        capsys,
        fake_adapter_factory,
        ["find", "--window", "hwnd_222", "--role", "button", "--depth", "-1"],
    )
    assert rc != 0
    assert env["reason"] == "invalid_argument"


def test_find_rejects_negative_limit(capsys, fake_adapter_factory):
    rc, env = _run_failing(
        capsys,
        fake_adapter_factory,
        [
            "find",
            "--window",
            "hwnd_222",
            "--role",
            "button",
            "--limit",
            "-1",
        ],
    )
    assert rc != 0
    assert env["reason"] == "invalid_argument"


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
    rc, env = _run_failing(
        capsys, fake_adapter_factory, ["read", "--window", "hwnd_222", "--label", "nonexistent"]
    )
    assert rc != 0
    assert env["reason"] == "target_not_resolved"
    assert "no control matched" in env["message"]


def test_read_ambiguous_errors(capsys, fake_adapter_factory):
    # role=button hits 5 controls in the Calculator tree.
    rc, env = _run_failing(
        capsys, fake_adapter_factory, ["read", "--window", "hwnd_222", "--role", "button"]
    )
    assert rc != 0
    assert env["reason"] == "target_not_resolved"
    assert "5 controls matched" in env["message"]


def test_read_requires_target_or_selector(capsys, fake_adapter_factory):
    rc, env = _run_failing(capsys, fake_adapter_factory, ["read", "--window", "hwnd_222"])
    assert rc != 0
    assert env["reason"] == "missing_selector"


def test_read_target_and_selector_are_mutually_exclusive(capsys, fake_adapter_factory):
    argv = [
        "read",
        "--window",
        "hwnd_222",
        "--target",
        "ctrl_eq",
        "--label",
        "Equals",
    ]
    rc, env = _run_failing(capsys, fake_adapter_factory, argv)
    assert rc != 0
    assert env["reason"] == "target_and_selectors"


def test_read_rejects_negative_max_length(capsys, fake_adapter_factory):
    rc, env = _run_failing(
        capsys,
        fake_adapter_factory,
        [
            "read",
            "--window",
            "hwnd_222",
            "--label",
            "Pi",
            "--max-length",
            "-1",
        ],
    )
    assert rc != 0
    assert env["reason"] == "invalid_argument"


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


# ---- adapter failures reach the user as errors, not tracebacks -------------
#
# The adapter contract (sgcl/core/adapter_base.py) allows LookupError for an
# unresolvable window/control and ValueError for a malformed id. Neither may
# escape main() as an unhandled exception: an agent consuming stdout would get
# a traceback and exit 1 instead of a structured failure. The realistic trigger
# is a window that closed between `sgcl windows` and the next command.


_FAILING_COMMANDS = [
    ["inspect", "--window", "hwnd_999999"],
    ["find", "--window", "hwnd_999999", "--role", "button"],
    ["read", "--window", "hwnd_999999", "--role", "button"],
]


@pytest.mark.parametrize("argv", _FAILING_COMMANDS, ids=["inspect", "find", "read"])
def test_stale_window_id_exits_cleanly(capsys, fake_adapter_factory, argv):
    """A window id the adapter cannot resolve must be reported, not raised."""
    rc, env = _run_failing(capsys, fake_adapter_factory, argv)
    assert rc != 0
    assert env["status"] == "error"
    assert "hwnd_999999" in env["message"]


@pytest.mark.parametrize(
    "exc",
    [LookupError("window is gone"), ValueError("Invalid window id: 'hwnd_abc'")],
    ids=["lookup-error", "value-error"],
)
@pytest.mark.parametrize(
    "argv",
    [
        ["inspect", "--window", "hwnd_111"],
        ["find", "--window", "hwnd_111", "--role", "button"],
        ["read", "--window", "hwnd_111", "--role", "button"],
    ],
    ids=["inspect", "find", "read"],
)
def test_adapter_contract_exceptions_exit_cleanly(capsys, fake_adapter, argv, exc):
    """Both exception types in the adapter contract become CLI errors.

    ValueError is the real adapter's response to a malformed window id (see
    `_resolve_window` in sgcl/adapters/windows_uia/_adapter.py). FakeAdapter
    raises LookupError there instead, so ValueError is injected explicitly
    rather than assumed unreachable.
    """

    def _raise(*_args, **_kwargs):
        raise exc

    fake_adapter.inspect_window = _raise
    fake_adapter.read = _raise

    rc, env = _run_failing(capsys, lambda: fake_adapter, argv)
    assert rc != 0
    assert env["status"] == "error"
    assert env["message"] == str(exc)
    # ValueError always means a malformed id. LookupError's meaning depends on
    # what was being resolved: inspect/find are resolving a window, read a
    # control -- so the reason code differs by command, not by exception type.
    if isinstance(exc, ValueError):
        expected = "invalid_argument"
    else:
        expected = "target_not_resolved" if argv[0] == "read" else "window_not_found"
    assert env["reason"] == expected


def test_emit_handles_unicode_private_use_area(capsys, fake_adapter, fake_adapter_factory):
    """Icon-font glyphs (Segoe Fluent Icons live in PUA) must not crash on
    Windows where stdout defaults to cp1252. Verifies main() reconfigures
    stdout to UTF-8 and that PUA codepoints round-trip through JSON."""
    fake_adapter._windows[0].title = "Tab  menu"  # PUA codepoint
    rc, out = _run(capsys, fake_adapter_factory, ["windows"])
    assert rc == 0
    data = json.loads(out)["windows"]
    assert data[0]["title"] == "Tab  menu"


# ---- every response says which adapter produced it -------------------------
#
# Adapter.name / Adapter.platform are mandatory members of the ABC that had
# no consumer at all, so output from two adapters was indistinguishable --
# a blocker for the cross-platform contract work (blunt win 9).


@pytest.mark.parametrize(
    "argv",
    [
        ["windows"],
        ["active"],
        ["inspect", "--window", "hwnd_222"],
        ["find", "--window", "hwnd_222", "--role", "button"],
        ["read", "--window", "hwnd_222", "--target", "ctrl_display"],
    ],
    ids=["windows", "active", "inspect", "find", "read"],
)
def test_every_response_carries_adapter_origin(capsys, fake_adapter_factory, argv):
    rc, out = _run(capsys, fake_adapter_factory, argv)
    assert rc == 0
    data = json.loads(out)
    assert data["adapter"] == "fake"
    assert data["platform"] == "fake"


def test_origin_does_not_clobber_the_payload(capsys, fake_adapter_factory):
    """Merging the origin must not drop or overwrite response keys."""
    argv = ["find", "--window", "hwnd_222", "--role", "button"]
    rc, out = _run(capsys, fake_adapter_factory, argv)
    assert rc == 0
    data = json.loads(out)
    assert "matches" in data
    assert len(data["matches"]) > 0


def test_inspect_emits_parent_id(capsys, fake_adapter_factory):
    """The affordance graph is traversable upward, not just downward."""
    rc, out = _run(capsys, fake_adapter_factory, ["inspect", "--window", "hwnd_222"])
    assert rc == 0
    tree = json.loads(out)
    assert tree["parent_id"] is None
    assert tree["children"][0]["parent_id"] == tree["id"]


# ---- the envelope itself ---------------------------------------------------


@pytest.mark.parametrize(
    "argv",
    [
        ["windows"],
        ["active"],
        ["inspect", "--window", "hwnd_222"],
        ["find", "--window", "hwnd_222", "--role", "button"],
        ["read", "--window", "hwnd_222", "--target", "ctrl_display"],
    ],
    ids=["windows", "active", "inspect", "find", "read"],
)
def test_success_responses_carry_status_ok(capsys, fake_adapter_factory, argv):
    rc, out = _run(capsys, fake_adapter_factory, argv)
    assert rc == 0
    assert json.loads(out)["status"] == "ok"


def test_error_envelope_goes_to_stdout_not_stderr(capsys, fake_adapter_factory):
    """The agent's normal channel must carry the failure."""
    rc = cli.main(["inspect", "--window", "hwnd_999999"], adapter_factory=fake_adapter_factory)
    captured = capsys.readouterr()
    assert rc != 0
    assert captured.out.strip(), "nothing on stdout"
    assert json.loads(captured.out)["status"] == "error"


def test_argparse_errors_keep_the_prose_path(capsys, fake_adapter_factory):
    """Parse-time failures predate the JSON contract and stay with argparse."""
    with pytest.raises(SystemExit) as exc_info:
        cli.main(["find", "--role", "button"], adapter_factory=fake_adapter_factory)
    assert exc_info.value.code == 2
    assert "one of the arguments" in capsys.readouterr().err


def test_every_documented_reason_code_is_reachable(capsys, fake_adapter, fake_adapter_factory):
    """Each code in docs/command-vocabulary.md has a trigger that emits it."""
    seen = set()

    cases = [
        ["inspect", "--process", "nonsuch.exe"],  # window_not_found
        ["inspect", "--process", "Notepad"],  # ambiguous_window
        ["read", "--window", "hwnd_222", "--role", "button"],  # target_not_resolved
        ["inspect", "--window", "hwnd_222", "--depth", "-1"],  # invalid_argument
        ["read", "--window", "hwnd_222"],  # missing_selector
        ["read", "--window", "hwnd_222", "--target", "ctrl_eq", "--label", "Equals"],
    ]
    for argv in cases:
        cli.main(argv, adapter_factory=fake_adapter_factory)
        seen.add(json.loads(capsys.readouterr().out)["reason"])

    assert seen == {
        "window_not_found",
        "ambiguous_window",
        "target_not_resolved",
        "invalid_argument",
        "missing_selector",
        "target_and_selectors",
    }


# ---- tri-state flags ----
#
# `_add_tri_state_pair` generates a positive/negative flag pair per criterion.
# The negative flags set the field to `False`, which is distinct from the
# default `None`: `False` filters for the absent flag, `None` ignores the
# criterion entirely (sgcl/core/matcher.py). None of `--disabled`,
# `--hidden` or `--unfocused` was ever passed by a test, and the one test
# named for the feature only exercised `--enabled` -- its own comment said so.


@pytest.mark.parametrize(
    "flag,field,expected",
    [
        ("--enabled", "enabled", True),
        ("--disabled", "enabled", False),
        ("--visible", "visible", True),
        ("--hidden", "visible", False),
        ("--focused", "focused", True),
        ("--unfocused", "focused", False),
    ],
)
def test_tri_state_flags_parse_to_true_or_false_never_none(flag, field, expected):
    """The parsed value is the contract; match counts are downstream of it.

    A negative flag that silently parsed to `None` would make the criterion
    ignored rather than inverted, and every match-count assertion would
    still pass -- the unfiltered result set contains the filtered one.
    """
    args = cli._build_parser().parse_args(["find", "--window", "hwnd_111", flag])
    assert getattr(args, field) is expected


def test_tri_state_defaults_to_none_when_no_flag_given():
    args = cli._build_parser().parse_args(["find", "--window", "hwnd_111", "--role", "button"])
    assert args.enabled is None
    assert args.visible is None
    assert args.focused is None


def test_find_disabled_returns_only_disabled_controls(capsys, fake_adapter_factory):
    rc, out = _run(
        capsys,
        fake_adapter_factory,
        ["find", "--window", "hwnd_111", "--role", "button", "--disabled"],
    )
    assert rc == 0
    labels = [m["control"]["label"] for m in json.loads(out)["matches"]]
    assert labels == ["Redo"]


def test_find_hidden_returns_only_invisible_controls(capsys, fake_adapter_factory):
    rc, out = _run(capsys, fake_adapter_factory, ["find", "--window", "hwnd_111", "--hidden"])
    assert rc == 0
    matches = json.loads(out)["matches"]
    assert [m["control"]["label"] for m in matches] == ["Find what"]
    assert all(m["control"]["visible"] is False for m in matches)


def test_find_unfocused_excludes_the_focused_control(capsys, fake_adapter_factory):
    rc, out = _run(capsys, fake_adapter_factory, ["find", "--window", "hwnd_111", "--unfocused"])
    assert rc == 0
    ids = [m["control"]["id"] for m in json.loads(out)["matches"]]
    assert "ctrl_editor" not in ids, "ctrl_editor is the focused control"
    assert ids, "--unfocused should still return the rest of the tree"


def test_find_focused_returns_exactly_the_focused_control(capsys, fake_adapter_factory):
    rc, out = _run(capsys, fake_adapter_factory, ["find", "--window", "hwnd_111", "--focused"])
    assert rc == 0
    assert [m["control"]["id"] for m in json.loads(out)["matches"]] == ["ctrl_editor"]


def test_neither_flag_is_ignore_not_require_true(capsys, fake_adapter_factory):
    """The tri-state's whole point: unset must be wider than either setting.

    If the default were `True` rather than `None`, the unfiltered count would
    equal the positive-filtered count and the distinction would be fiction.
    """

    def count(*flags):
        rc, out = _run(capsys, fake_adapter_factory, ["find", "--window", "hwnd_111", *flags])
        assert rc == 0
        return len(json.loads(out)["matches"])

    unset = count()
    assert unset > count("--enabled") > 0
    assert unset > count("--disabled") > 0
    assert count("--enabled") + count("--disabled") == unset
    assert count("--visible") + count("--hidden") == unset
    assert count("--focused") + count("--unfocused") == unset


def test_read_honours_negative_tri_state_flags(capsys, fake_adapter_factory):
    """`read` wires the same helper as `find`, so it gets the same coverage.

    This is the strongest form of the assertion: `--role button` alone is
    ambiguous in this tree, and only a genuine `enabled=False` filter
    narrows it to exactly one control. A flag parsed as `None` would leave
    the read ambiguous and error.
    """
    rc, out = _run(
        capsys,
        fake_adapter_factory,
        ["read", "--window", "hwnd_111", "--role", "button", "--disabled"],
    )
    assert rc == 0
    assert json.loads(out)["affordance"]["label"] == "Redo"


def test_read_without_the_negative_flag_is_ambiguous(capsys, fake_adapter_factory):
    """The control case for the test above -- proving the filter did the work."""
    rc, env = _run_failing(
        capsys, fake_adapter_factory, ["read", "--window", "hwnd_111", "--role", "button"]
    )
    assert rc != 0
    assert env["reason"] == "target_not_resolved"
