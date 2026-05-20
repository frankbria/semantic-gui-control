# Windows-Side Claude Setup

One-time notes for running a Claude Code session natively on Windows
(PowerShell host) so it can drive SGCL spike runs against real UIA
without manual courier work.

## Prerequisites already in place from Phase 0/1

- Native Windows (not WSL) PowerShell — Windows Terminal with the
  PowerShell profile is fine.
- `uv` installed (`winget install astral-sh.uv` or the official
  installer).
- `git` installed.
- Repo cloned at `$HOME\semantic-gui-control`.
- The Windows env has previously run `uv sync --extra dev --extra
  windows` successfully (this installs `uiautomation`).
- GitHub auth set up for `git push` from the Windows side.

## Recommended PowerShell profile additions

These eliminate the cp437-mojibake trap that bit Phase 1. Add to
`$PROFILE` so every PowerShell tab inherits UTF-8:

```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
```

Why: PowerShell decodes child-process stdout bytes through
`[Console]::OutputEncoding`, which defaults to cp437 on US Windows.
Any UTF-8 byte sequence that includes 0x80–0xFF gets mangled. Setting
the encoding upfront fixes the pipe so even pre-`--output` tooling
behaves.

`sgcl --output PATH` already bypasses the pipe entirely; the profile
setting is belt-and-suspenders for any other tool.

## Starting a Windows Claude session

Open a PowerShell tab inside `$HOME\semantic-gui-control` and start
Claude Code there (whatever invocation you use on Windows — the CLI
or IDE plugin). Then paste the contents of
`docs/windows-handoff-prompt-phase-2.md` as the first message.

That prompt is self-contained: it tells the Windows Claude exactly
which commands to run, where to write outputs, and how to commit and
push. The Windows session does not need any additional context from
chat history.

## What the Windows session can and can't do

**Can:**

- Pull, sync, run the SGCL CLI against live Notepad / Calculator.
- Capture sample JSON outputs.
- Commit and push.
- Make small edits to spike notes or `tasks/todo.md`.

**Should not:**

- Implement new features (that's the Linux session's job).
- Modify the package layout or refactor.
- Run destructive git commands (force push, hard reset, branch
  deletion).

If the Windows session hits a bug in the SGCL code itself, it should
capture the error verbatim in the spike note and push, then the
Linux session picks it up and ships a fix.
