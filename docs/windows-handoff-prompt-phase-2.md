# Windows Claude Handoff — Phase 2 (Find + Read)

Paste **everything below the line** as the first message in a fresh
Claude Code session running natively on Windows (PowerShell host)
with the working directory set to `$HOME\semantic-gui-control`.

The Linux session writing this prompt will not be active while you
work. When you're done (or stuck), commit and push. The Linux session
will pull, review, and either ship a fix or close the slice out.

---

You are running on a Windows 11 machine with native PowerShell. The
working directory is the user's clone of
`github.com/frankbria/semantic-gui-control`. Your job is the
Windows-side spike runs for Phase 2 (Find + Read) of the SGCL
project. The Linux-side dev session has already shipped slices F.1–
F.6 to `main`. Your task is slice F.7: run the spike commands,
commit the sample outputs, and write a first draft of the spike
report. Do **not** implement new SGCL features — that is the Linux
session's job.

## Read first

Before doing anything, read these three files to load context (under
about 5 minutes total):

1. `docs/phase-2-find-read-spike.md` — the approved Phase 2 plan,
   including F.7's specific spike commands.
2. `spikes/normalize-results.md` — the Phase 1 spike report, which
   defines the patterns you should follow when writing F.7's report.
3. `docs/windows-claude-setup.md` — confirms env setup. If your
   PowerShell `[Console]::OutputEncoding` is not UTF-8, set it for
   this session at minimum:
   ```powershell
   [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
   $OutputEncoding = [System.Text.Encoding]::UTF8
   ```

## Toolchain refresh

```powershell
cd $HOME\semantic-gui-control
git checkout main
git pull
uv sync --extra dev --extra windows
uv run sgcl --help    # sanity check; should list `find` and `read`
```

If `find` or `read` aren't in the help output, the Linux session
hasn't finished F.4 / F.5 yet. Stop and report; do not improvise.

## Prepare the test apps

Before the spike commands, open both apps and leave them visible:

- **Notepad** — open with a tiny amount of text, like `Hello SGCL`.
  Don't worry about which Notepad version; whatever Windows 11 gives
  you when you launch "Notepad" is fine.
- **Calculator** — open in **Scientific mode** so the keypad has the
  full set of buttons. If it opens in Standard, click the hamburger
  menu and switch.

You do **not** need to focus either app before running commands.
SGCL Phase 1+ targets windows by HWND, not by focus.

## Spike commands

Each command writes its output to a sample file via `--output` to
avoid any shell-pipe encoding surprises. Use this helper at the top
of the session to resolve HWNDs by title:

```powershell
function Get-SgclHwnd($title) {
    $w = uv run sgcl windows --include-system |
         ConvertFrom-Json |
         Where-Object { $_.title -eq $title } |
         Select-Object -First 1
    if (-not $w) {
        Write-Error "No window with title '$title' found. Is it open?"
        return $null
    }
    return $w.id
}

$calc    = Get-SgclHwnd 'Calculator'
$notepad = (uv run sgcl windows | ConvertFrom-Json |
            Where-Object { $_.title -like '*Notepad*' } |
            Select-Object -First 1).id

if (-not $calc -or -not $notepad) {
    Write-Error 'Need both Calculator and Notepad open before continuing.'
    return
}

mkdir -Force spikes\samples | Out-Null
```

Then run the spike commands. Each one writes a sample file; comments
explain what each is proving.

```powershell
# F.7-A: synonym match. Should return exactly one match for the
# Equals button (UIA accessible name is "Equals"; synonym "=").
uv run sgcl --pretty find --window $calc --label "=" `
    --output spikes\samples\f7-a-find-equals-by-synonym.json

# F.7-B: digit synonym. Should return one match for "Zero" via "0".
uv run sgcl --pretty find --window $calc --label "0" `
    --output spikes\samples\f7-b-find-zero-by-synonym.json

# F.7-C: role-only filter. Should return ALL buttons in Calculator.
uv run sgcl --pretty find --window $calc --role button `
    --output spikes\samples\f7-c-find-all-buttons.json

# F.7-D: Notepad's editable area. Should find a text_field / document.
uv run sgcl --pretty find --window $notepad --role text_field `
    --output spikes\samples\f7-d-find-notepad-editor.json
# If empty, try --role document.

# F.7-E: read Calculator's display. Should return the current value
# of the NormalOutput static text (e.g., "0").
uv run sgcl --pretty read --window $calc --label "Display is 0" `
    --output spikes\samples\f7-e-read-calc-display.json
# If that exact label doesn't match, try:
#   uv run sgcl --pretty find --window $calc --role static_text
# to discover the real AutomationId/label for the readout.

# F.7-F: read Notepad's document. Should return the typed text.
uv run sgcl --pretty read --window $notepad --role document `
    --max-length 200 `
    --output spikes\samples\f7-f-read-notepad-document.json
```

For each command, eyeball the resulting JSON file. Two things to
sanity-check:

1. **Non-ASCII characters survived** (e.g., `π`, `√` in synonyms).
   If you see `╧Ç` or similar, the PowerShell encoding profile
   wasn't set. Set it and re-run.
2. **Match counts make sense.** Synonym lookups should return 1
   match. Role-only filters can return many.

If a command errors with "no window matched" or "N windows matched",
add `--include-system` or use a different selector — don't disable
the ambiguity check.

## Write the first draft of the spike report

Create `spikes/find-read-results.md` following the same skeleton as
`spikes/normalize-results.md`. At minimum cover:

- **Date / environment** (Windows build, terminal host, Python
  version, working directory).
- **Commands run** — exactly what was executed.
- **What worked** — synonym match, role filter, READ value
  extraction. Cite specific sample files.
- **What failed / surprised** — anything that didn't match the
  expected behavior in the plan. Capture verbatim error text.
- **Match-confidence calibration evidence** — for at least one
  ambiguous query you tried (or contrived), what `match_confidence`
  did each result get? Does it feel right?
- **READ pattern hit-rate** — for each of the 6 commands, which
  reader path (`ValuePattern` / `TextPattern` / `TogglePattern` /
  `SelectionPattern` / fallback) fired? You can tell from the
  shape of the output (`{value, read_only}` vs `{value, truncated}`
  vs `{state: "on" | "off"}` etc.).
- **Performance notes** — rough wall-clock for the slowest
  command, especially Notepad's document read.
- **New questions for Phase 3** — anything you noticed that
  Phase 3 (Act + Verify + Risk) should think about.

Keep it under 400 lines. The Linux session will refine and
expand it before closing the GitHub issues.

## Commit and push

```powershell
git add spikes\samples spikes\find-read-results.md
git commit -m "Phase 2 / F.7: Windows spike runs + first-draft report"
git push
```

If `git push` fails because main moved (the Linux session pushed
something in parallel), do a `git pull --rebase` and try again.
Don't force-push.

## When you're stuck

If a command fails in a way you don't understand, or the SGCL code
itself seems wrong (not the spike's fault):

1. Capture the verbatim output to `spikes/samples/f7-error-<step>.txt`.
2. Note the failure in `spikes/find-read-results.md` under "What
   failed."
3. Commit and push what you have.
4. Stop. The Linux session will pick up the failure and ship a fix.

Don't edit SGCL source files. Don't add new modules. Don't refactor.
Phase 2 implementation is the Linux session's job.

## When you're done

Confirm:

- [ ] All 6 sample files in `spikes/samples/f7-*.json` exist and
      contain valid JSON with non-ASCII preserved.
- [ ] `spikes/find-read-results.md` exists and covers the sections
      above.
- [ ] Everything is committed and pushed.
- [ ] No SGCL source files modified.

Then post a one-paragraph summary in chat for the user, listing
which spike commands worked end-to-end and which (if any) need
follow-up from the Linux session. The Linux session will pick up
from there.
