# TUI Status View Spec — FINAL (v2, 2026-07-04)

Locked after 10 mock-driven design rounds. The approved mock lives at the
Claude artifact "t69 status view" (round-10-shadow-digits); this doc is the
repo source of truth for what gets built.

## Goal

Make the `t69` dashboard simple, alive, colorful, and easy to scan in a
terminal. Color clarifies meaning; it never decorates whole sections.

## Outcome / Expectations

When done, launching `t69` in a normal terminal shows, top to bottom:

1. **Wordmark header** (~7 rows total)
2. **Top state line** with chips
3. **Option A body**: full-width session monitor, then inspector + module
   dash side by side
4. **Footer** with compact action keys

Layouts B (split column) and C (stacked rows) are **future work** — the
widget structure must not preclude adding them behind a view-switch key
later, but nothing beyond Option A ships now.

## Wordmark Header (final design)

`6ix9ine — the snitch that rats on sleep` rendered as a pixel-font banner
using `▀` half-blocks:

- **`6` and `9`**: chunky terminal-mono style glyphs, 4 banner rows tall,
  colored as near-black *embossed shadows*:
  - `6` → `#1f1a18`
  - `9` → `#18201b`
- **`ix` / `ine`**: thin, slanted (script-flavored) glyphs, 3 banner rows
  tall, carrying muted hues:
  - `i` `#8a6c48` · `x` `#88824c` · `i` `#4c688a` · `n` `#6f5a88` · `e` `#845270`
- **Tagline** `— the snitch that rats on sleep`: normal font size, gray
  `#565e68`, same baseline region as the wordmark.
- Below the wordmark, two quiet status lines (gray `#5c6570`):
  - `status view · daemon connected · helper ok` (reflect real state)
  - `watching: 🤖 claude · 🧰 opencode · ⌘ codex`
- **Collapse rule**: if the terminal has fewer than ~30 rows, the banner
  collapses to a single normal-size text line (`6ix9ine — the snitch that
  rats on sleep`, same colors) so the dashboard always fits.

Visual intent: dashboard data brightest → script letters quietly colorful →
digit shadows barely there. *There, but not there.*

## Layout (Option A — monitor-dominant)

- **Top line**: `status view` label + state chips + right-aligned meta
  (`N sessions · N holds · lid <state> · HH:MM:SS`)
- **dense monitor** (full width): all active sessions + timed holds
- **split inspector** (bottom left): selected row detail — agent, full uuid,
  acquired time, held-for, sleep blocked-since, lid state, thermal state
- **module dash** (bottom right): auxiliary background processes
- **Footer**: `q quit · k kill · x purge · a ignore · r restore · ↑↓ select`

## Required Visual Rules

- Dark base `#0b0d10`, square borders `#2c333c`, minimal decoration
- Pane titles sit on the border, e.g. `dense monitor · 4 active`
- Use the label `status view`; no `btop`-ish wording anywhere
- No pink/purple washes across a pane or the dashboard; pink appears only
  as the narrow `SLEEP BLOCKED` chip emphasis (`#ff8fab` on `#3a1220`)
- Each active session row gets a distinct identity color, assigned stably
  (hash of session key → palette), e.g. `#7cc4ff`, `#f5d76e`, `#b3e07c`,
  `#e8e6e1`
- A session's name color and its held-time color must differ in the same row
- Reason column stays wide (it holds task descriptions/prompts). Textual's
  DataTable renders single-line cells, so long reasons truncate in the table;
  the inspector pane always shows the full reason text (accepted deviation)
- Session table columns: `AGENT · UUID (short) · PID · HELD · REASON`
- **PID**: no current code path supplies a session PID (see handoff doc,
  bug #6 fix) — render a dim `—` (`#4a525c`) when absent
- Agent identity emoji:
  - `🤖 claude` · `🧰 opencode` · `⌘ codex`
  - `🚀 antigravity` · `✋ manual` (defaults; not in original spec, both are
    valid agents in `shared.VALID_AGENTS`)

## Timed Holds

Holds (`6ix9ine hold --for 30m`) block sleep like sessions and appear in the
dense monitor as **quieter rows**: `⏱ hold · <hold-id> · — · <expires-in>
left · <reason>`, all in muted gray (`#6a7380`).

## Held Time Rules (computed from raw `timestamp`, never parsed from text)

| Held for            | Color                  |
|---------------------|------------------------|
| under 5 min         | green `#6ee7a0`        |
| 5 to under 30 min   | orange `#ffb454`       |
| 30 to under 45 min  | red `#ff6b5e`          |
| 45 min and over     | hot red `#ff3b30` bold |
| over 1 hour         | hot red + `🔥` suffix  |

## Sleep State Rules

- Blocked: chip `SLEEP BLOCKED` — `#ff8fab` on `#3a1220`
- Available: chip `💤 SLEEP AVAILABLE` — `#7cc4ff` on `#12283a`
- `ACTIVE`/`IDLE` chip: `#6ee7a0` on `#123524` when active
- Inspector shows `sleep: BLOCKED since HH:MM:SS` / `💤 available`

## Auxiliary Processes (module dash)

- Pane label: `module dash · auxiliary background processes running`
- Columns: `PROCESS · PID · STATUS · CPU · MEM`
- All rows in quiet gray (`#4a525c`) — visibly quieter than sessions
- Existing ignore/restore filter behavior (`a` / `r` keys) is kept

## Acceptance Notes

- Terminal-native, not browser-like; readable at real terminal sizes
  (80×24 collapsed-header minimum, 120×40 target)
- Refresh cadence: every 2s (current behavior), daemon-down state renders
  gracefully (`IDLE`, sleep available, empty monitor)
- `t69 --kill` hard-kill flag unchanged
