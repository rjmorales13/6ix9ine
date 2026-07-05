# TUI Redesign Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the `t69` Textual dashboard so it feels more alive while staying terminal-native, with a strong sleep-state hero, clearer session hierarchy, and a cleaner auxiliary process section.

**Architecture:** Keep the existing `bin/tui.py` entry point and IPC behavior, but reorganize the view layer into smaller render helpers so the layout is easier to evolve. The final screen should be inspired by the browser mockup, not copied literally: one top status area, one dominant session/sleep area, one auxiliary area, and a compact action bar.

**Tech Stack:** Python 3.13+, Textual, psutil, pytest

---

## File Structure

- Modify `bin/tui.py`: implement the new Textual layout, add focused render helpers, keep existing commands/bindings, and preserve `--kill` behavior.
- Modify `tests/unit/test_tui.py`: expand coverage for layout data shaping and any new helper functions.
- Create `docs/superpowers/plans/2026-07-04-tui-redesign.md`: implementation plan for the redesign.

## Design Constraints

- This is a terminal TUI, so the browser mockup is only a visual reference.
- Keep the dashboard glanceable on a normal terminal size.
- Do not add new daemon behavior in this change.
- Preserve existing keyboard actions unless a clearer label is needed.
- Prefer modest Textual styling over heavy UI complexity.

## Layout Direction

- Top bar: app title plus live status chips for sleep state and connection state.
- Main hero: make sleep state the strongest visual element, inspired by Option A.
- Session list: keep active sessions visible and sortable by the current state shape.
- Auxiliary panel: use a calmer, cleaner presentation inspired by Option B.
- Footer/action bar: keep compact command hints like Option C.

## Chunk 1: Extract View Helpers

**Files:**
- Modify: `bin/tui.py`
- Test: `tests/unit/test_tui.py`

- [ ] **Step 1: Write the failing test**

Add tests for helper functions that return view-friendly data structures for:
- top status chips
- hero sleep-state summary
- session display rows
- auxiliary display rows

Use deterministic inputs and assert the returned structures are easy to render.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_tui.py -v`
Expected: failures for missing helpers or new assertions.

- [ ] **Step 3: Write minimal implementation**

Add small helper functions in `bin/tui.py` that transform daemon state and psutil data into render-ready structures without touching Textual widgets directly.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_tui.py -v`
Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add bin/tui.py tests/unit/test_tui.py
git commit -m "feat: extract tui view helpers"
```

## Chunk 2: Rebuild the Main Layout

**Files:**
- Modify: `bin/tui.py`
- Test: `tests/unit/test_tui.py`

- [ ] **Step 1: Write the failing test**

Add tests that verify the app composes the intended screen sections in the right order, using widget IDs or explicit composition checks if practical.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_tui.py -v`
Expected: layout-related assertions fail until the new structure exists.

- [ ] **Step 3: Write minimal implementation**

Update `SixNineApp.compose()` to build a stronger hierarchy:
- header/status region
- hero sleep-state region
- session panel
- auxiliary panel
- footer/action bar

Add CSS only as needed to support spacing, emphasis, and terminal readability.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_tui.py -v`
Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add bin/tui.py tests/unit/test_tui.py
git commit -m "feat: redesign tui layout"
```

## Chunk 3: Improve Refresh and Interaction Feedback

**Files:**
- Modify: `bin/tui.py`
- Test: `tests/unit/test_tui.py`

- [ ] **Step 1: Write the failing test**

Add tests for refresh behavior that confirm the dashboard can render a meaningful empty/offline state and still show stable top-level status.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_tui.py -v`
Expected: offline/empty-state assertions fail before implementation.

- [ ] **Step 3: Write minimal implementation**

Adjust `refresh_data()` so the new layout gets the right fallback content when the daemon is unavailable or when there are no active sessions.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_tui.py -v`
Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add bin/tui.py tests/unit/test_tui.py
git commit -m "feat: improve tui refresh states"
```

## Chunk 4: Verify the Experience End-to-End

**Files:**
- Modify: `bin/tui.py` if final polish is needed
- Test: `tests/unit/test_tui.py`

- [ ] **Step 1: Run the full unit test suite**

Run: `pytest tests/unit -v`
Expected: all unit tests pass.

- [ ] **Step 2: Manually launch the dashboard**

Run: `python -m bin.tui` or the project’s normal `t69` entry point.
Expected: the screen shows the new hybrid layout with strong sleep-state emphasis and a calmer auxiliary block.

- [ ] **Step 3: Check keyboard actions**

Verify `q`, `k`, `x`, `a`, and `r` still work.

- [ ] **Step 4: Final commit if needed**

```bash
git add bin/tui.py tests/unit/test_tui.py
git commit -m "feat: polish tui redesign"
```

## Notes for Implementer

- Treat the browser mockup as inspiration only. Match the composition, not the exact HTML styling.
- Keep the code readable enough that future visual changes can happen in one file without a rewrite.
- If the screen gets crowded, reduce decoration before reducing clarity.
