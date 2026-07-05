# Status View Implementation Plan (2026-07-04)

Tech plan for building the final `status-view-spec.md` design. Written for
review **before** any code is touched. Companion docs: `status-view-spec.md`
(what it looks like), `../handoff-road-to-gummo.md` (state of the world).

---

## 1. Scope

**In scope**

- Rebuild `bin/tui.py` presentation to the final spec (Option A layout,
  wordmark header, ghost palette, held-time tiers, holds rows, inspector,
  quiet aux pane, footer keys)
- New pure-logic modules + full unit coverage
- Keep all existing behavior: 2s refresh, `k/x/a/r/q` keys, ignore filter
  persistence, `t69 --kill`, graceful daemon-down rendering

**Out of scope (future)**

- Layouts B and C + view-switch key (structure must allow them later)
- Codex/antigravity hook integrations, thermal bug #4, menu bar app

## 2. Data contract (already verified against the code)

`STATUS` response (daemon `to_state_dict` + daemon fields):

- `active_sessions: {key → {agent, timestamp, pid, reason, held_for}}` —
  `key` is the session UUID; `pid` is always `None` today (bug #6 fix);
  held-time math uses raw `timestamp`, never the formatted `held_for`
- `holds: [{id, reason, expires_in}]`
- `status: ACTIVE|IDLE`, `sleep_blocked: bool`, `lid`, `thermal`

No daemon changes are needed. One optional daemon nicety (decide at review):
adding raw `expires_at` to holds so the TUI can count down between refreshes
— **default: not needed**, `expires_in` refreshes every 2s anyway.

## 3. File layout (per 800-line / small-files rules)

```
bin/
├── tui.py            # Textual app: widgets, layout, bindings, refresh loop
├── tui_theme.py      # NEW: palette constants, agent emoji, held-time tiers,
│                     #      stable session-color assignment, chip styles
├── tui_wordmark.py   # NEW: pixel-font banner (half-block glyphs for
│                     #      6/9 mono + ix/ine slant style), collapse logic
tests/unit/
├── test_tui.py           # extend existing: row builders incl. holds, pid "—"
├── test_tui_theme.py     # NEW: tier boundaries, color stability/uniqueness
└── test_tui_wordmark.py  # NEW: banner renders, widths, collapse threshold
```

Pure functions stay free of Textual imports (same philosophy as
`session_registry.py`) so they unit-test without a terminal.

## 4. Build phases

**Phase 0 — prep**: feature branch `feat/status-view`; baseline `pytest
tests/ -q` green (186 tests).

**Phase 1 — data/theme layer (TDD, tests first)**
`tui_theme.py`: `held_tier(seconds) → (style, suffix)` with boundary values
locked to spec; `session_color(key) → color` (stable across refreshes,
spread across palette, never equal to the row's held color); agent emoji
map incl. `🚀 antigravity` / `✋ manual`; chip style table.
`tui.py` row builders: sessions + holds merged, uuid shortening, dim `—`
for missing pid, reason passthrough.

**Phase 2 — wordmark banner (TDD)**
`tui_wordmark.py`: glyph maps for `6 9` (4-row chunky) and `i x n e`
(3-row slant), `render(width) → Rich Text`, `collapsed() → Text` one-liner,
threshold decision from terminal size.

**Phase 3 — Textual layout**
Rebuild `SixNineApp.compose()`: header block (wordmark + status lines),
top line with chips, dense monitor `DataTable`, inspector `Static`, module
dash `DataTable`, footer. Textual CSS for the dark base, square borders,
pane titles, Option A grid. Row-selection drives the inspector. Resize
handler applies the collapse rule.

**Phase 4 — review + verification** (sections 5–6).

**Phase 5 — docs + commit**: update `README.md` dashboard section +
handoff doc; conventional commit on the feature branch; no push until
you say so.

## 5. Agent workflow (how this gets executed)

Orchestrator: this Claude Code session. Delegation follows the
cost/capability ladder (Haiku for mechanical work, Sonnet for judgment):

| Step | Who | Model | Why |
|------|-----|-------|-----|
| Write failing unit tests (Phases 1–2) | orchestrator | — | tests encode the spec; too important to delegate |
| Implement `tui_theme.py` + `tui_wordmark.py` to green | worker agents, parallel | **Haiku 4.5** | well-specified, mechanical, cheap; tests already define done |
| Wordmark glyph pixel maps | worker agent | **Haiku 4.5** | bounded artistic-mechanical task with a visual check after |
| Textual layout rebuild (Phase 3) | orchestrator | — | layout/UX judgment, cross-file integration; NOT delegated to Haiku (Textual CSS quirks + mock fidelity need iteration against a live render) |
| Code review pass | `code-reviewer` + `python-reviewer` agents | **Opus** | strongest independent review on the user-facing surface; orchestrator verifies findings and takes over anything flagged as difficult |
| Build/regression triage if suite breaks | `build-error-resolver` agent | Sonnet | minimal-diff fixes only |

Flow: tests (orchestrator) → parallel Haiku workers to green → orchestrator
integrates Phase 3 → parallel Sonnet reviewers → fix CRITICAL/HIGH →
verification below. Worker output is never trusted on assertion: the
orchestrator reruns the full suite after every hand-back.

## 6. Testing plan

**A. Unit tests (pytest, must all pass; 80% coverage on new modules)**

- Held-tier boundaries: `4:59→green`, `5:00→orange`, `29:59→orange`,
  `30:00→red`, `44:59→red`, `45:00→hot`, `59:59→hot no 🔥`, `1:00:01→hot+🔥`
- Session color assignment: deterministic for same key, distinct for small
  N, never equals the held color in the same row
- Row builders: sessions+holds ordering, uuid shortening, pid `—`, empty
  state, malformed/missing fields (daemon-down dict)
- Wordmark: every glyph defined, consistent row heights (4 vs 3), collapse
  at threshold, no crash at width 40
- Existing `test_tui.py` cases keep passing (filter save/load, hard-kill)

**B. Full regression suite** — `pytest tests/ -q`: all 186 existing tests
stay green throughout; new total grows with A.

**C. Textual pilot tests** — `App.run_test()` smoke: app mounts, tables
have the spec'd columns, `k/x/a/r/q` bindings fire their actions with a
fake `send_request`, resize below threshold collapses the header.

**D. Human-simulation suite** — `pytest human-simulation-tests/ -v`
against the real daemon/helper: expected result unchanged (6 pass, 1 known
thermal failure, bug #4 — not part of this work).

**E. Human (manual) testing — you and me together**

Checklist to run in a real terminal (I drive what I can, you confirm what
your eyes see; screenshots go into this folder):

1. `t69` in a ~120×40 terminal: wordmark shadows/script colors match the
   approved mock; header ~7 rows
2. Shrink to 80×24: header collapses to one line, no overflow/clipping
3. With a real Claude Code session running: row appears with 🤖, distinct
   color, green held time; leave it 5+ min → flips orange
4. `6ix9ine hold --for 2m`: quiet ⏱ row shows, expires off the table
5. Chips flip `SLEEP BLOCKED` → `💤 SLEEP AVAILABLE` when last session ends
   (verify against `pmset -g` like the handoff smoke tests)
6. Select rows: inspector follows; `k` releases the selected session;
   `x` purges; `a` hides an aux process; `r` restores it; `q` exits clean
7. Daemon stopped: dashboard renders IDLE/empty gracefully, no traceback
8. Both Terminal.app and iTerm2 (font/emoji rendering differs)

Item 3/5 double as the first-ever live visual launch of `t69` (the handoff
doc flags it has never been run on screen).

## 7. Acceptance criteria

- Spec doc satisfied point-by-point (walk the spec against a screenshot)
- All suites in section 6 A–D green (D: known thermal failure only)
- Manual checklist E signed off by you
- No regressions in `t69 --kill`, filter persistence, refresh cadence
- New files ≤ ~400 lines each; no Textual imports in pure-logic modules

## 8. Risks / notes

- **Emoji width in terminals** (⌘, 🔥, 💤) can break column alignment —
  mitigated by Rich's cell-width handling + manual check E.8
- **Half-block banner in non-truecolor terminals**: colors degrade to the
  nearest 256-color; acceptable, verified in E.8
- **Textual version pinned in the runtime venv** (`~/Library/Application
  Support/6ix9ine/venv`): the runtime copy must be re-synced after the
  change (`install.sh` re-run) or `t69` keeps running the old UI — this
  bit us before (handoff doc, "runtime copy" note)
- The repo test venv is Python 3.9 while runtime is 3.13 — new code stays
  3.9-compatible syntax-wise, same as the existing modules
