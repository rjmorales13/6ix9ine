# HY3 TASK: v0.4-Advanced-Features (THERMAL FOCUS)

**OFFICIAL CLARIFICATION:** This replaces the generic AntiGravityWO-001. Read this document, ignore conflicting sections in WORK-ORDERS.md.

---

## ⚠️ CRITICAL: Work Order Mismatch Resolved

**Issue Found:** Original work order specified Go + Gemini API + config files, but:
- Project is **Python**, not Go
- Project philosophy: **"no network, no config files"**
- Gemini advisor violates "no network"
- Config files violate "no config" principle

**Resolution:** Implement THIS scope (thermal focus) instead of the generic WO.

---

## 🎯 Your Actual Task: v0.4-Advanced-Features (Thermal)

**Work Order ID:** HY3-v0.4-thermal  
**Branch:** `feat/hy3-thermal-awareness`  
**Status:** In progress  
**Complexity:** ⭐⭐⭐ MEDIUM  
**Effort:** 8-11 hours  
**Target Tests:** 80%+ coverage

---

## ✅ TASKS (IN ORDER)

### Task 1: Add `thermal status` CLI Command
**File:** `bin/cli.py`  
**Objective:** Expose the daemon's existing thermal state via CLI

**Implementation:**
- Add subcommand: `6ix9ine thermal status`
- Read daemon state from `state["thermal"]` (already tracked in daemon.py)
- Print: current temp, peak temp, threshold, cutout status
- Color-code output: green (cool), yellow (warm), orange (hot), red (critical)
- Exit code: 0 for success

**Example output:**
```
Thermal Status: COOL (52°C)
  Current: 52°C
  Peak: 68°C
  Threshold: 80°C (configurable via SIXNINE_THERMAL_THRESHOLD)
  Cutout: Not triggered
```

**Requirements:**
- No new dependencies
- Use existing thermal_monitor.py data
- Follow existing CLI command patterns (bin/cli.py:commands)

**Branch:** `feat/hy3-thermal-awareness`  
**Deliverable:** Working `6ix9ine thermal status` command

---

### Task 2: Add Thermal Panel to t69 Dashboard
**File:** `bin/tui.py`  
**Objective:** Display thermal status in the live dashboard

**Implementation:**
- Add thermal panel to the main dashboard display
- Show current temperature, peak, threshold, and cutout state
- Color-code based on thermal state:
  - 🟢 COOL: < 60°C
  - 🟡 WARM: 60-79°C
  - 🟠 HOT: 80-94°C
  - 🔴 CRITICAL: ≥ 95°C
- Refresh every 5 seconds (same as other dashboard data)
- Place in dashboard layout (suggest top-right or status bar)

**Requirements:**
- Use textual library (already used in TUI)
- Read from daemon state (live updates)
- No new dependencies

**Branch:** Same as Task 1  
**Deliverable:** Thermal panel visible in `t69` dashboard

---

### Task 3: Verify Thermal Policy Action
**File:** `bin/daemon.py`  
**Objective:** Ensure daemon RELEASES sleep blocks when Mac gets too hot

**Current State:**
- `bin/thermal_monitor.py` tracks thermal sensors
- `bin/daemon.py` polls thermal state and notifies if cutout fires
- `state["thermal"]["cutout_fired"]` is set when critical temp reached

**What's Missing:**
- Daemon notifies but doesn't *act* — sleep block stays held even when hot

**Implementation:**
- When `thermal.cutout_fired == True`:
  - Call `release_all_sessions()` immediately
  - Log: "Thermal cutout triggered: releasing all sessions"
  - Emit notification: "Mac too hot, sleep protection released"
- Add test: simulate high temp, verify sleep block is released

**Requirements:**
- No new files
- Modify daemon.py's thermal polling loop
- Respect existing daemon architecture

**Branch:** Same as Task 1  
**Deliverable:** Daemon releases sessions when Mac overheats

---

### Task 4: Write Comprehensive Tests
**Directory:** `tests/unit/`  
**Objective:** 80%+ coverage of new thermal features

**Test Cases:**
1. `test_thermal_status_cli_cool()` — verify output format when temp < 60°C
2. `test_thermal_status_cli_hot()` — verify color output when temp > 80°C
3. `test_thermal_status_cli_critical()` — verify output when cutout fires
4. `test_thermal_dashboard_panel_rendering()` — verify panel displays in TUI
5. `test_thermal_dashboard_color_coding()` — verify colors match state (cool/warm/hot/critical)
6. `test_daemon_releases_on_cutout()` — mock high temp, verify `release_all_sessions()` called
7. `test_env_var_threshold_override()` — verify `SIXNINE_THERMAL_THRESHOLD` env var changes threshold
8. `test_thermal_state_persistence()` — verify thermal state updates in daemon

**Requirements:**
- Follow existing test patterns in `tests/unit/`
- Use mocking for daemon interaction
- Coverage target: 80%+ of thermal-related code
- All tests pass

**Branch:** Same as Task 1  
**Deliverable:** `tests/unit/test_thermal_*.py` files with 80%+ coverage

---

### Task 5: Configuration via Environment Variables
**File:** `bin/shared.py`  
**Objective:** Make thermal behavior tunable via env vars (no config files)

**Implementation:**
- Use existing convention: `SIXNINE_*` environment variables
- `SIXNINE_THERMAL_THRESHOLD` (already exists, line 59)
  - Default: 80°C
  - User can override: `export SIXNINE_THERMAL_THRESHOLD=85`
- `SIXNINE_THERMAL_ALERT` (new, optional)
  - Default: 70°C (warn before cutout)
  - User can override
- Document in `bin/shared.py` with clear defaults

**Requirements:**
- No config files (violates project philosophy)
- No new toggle system
- Use existing `SIXNINE_*` pattern
- Update comments in shared.py with thermal env vars

**Branch:** Same as Task 1  
**Deliverable:** Thermal behavior configurable via env vars

---

## 🔴 DO NOT IMPLEMENT

**These are OUT OF SCOPE for v0.4 and violate project philosophy:**

| Feature | Reason |
|---------|--------|
| **Gemini optimization advisor** | Violates "no network" philosophy |
| **Calendar integration** | Different feature, requires product owner approval |
| **DeepSeek diagnostics** | Belongs to OpenCode agent (PR #2), not this task |
| **Config files** | Project uses env vars only; no config.toml |
| **Configuration UI** | Keep it CLI + env vars |

---

## 📋 Git Workflow

**Branch name:** `feat/hy3-thermal-awareness`  
**Commit format:** `feat(hy3): <description>`  
**Examples:**
- `feat(hy3): Add thermal status CLI command`
- `feat(hy3): Add thermal panel to t69 dashboard`
- `feat(hy3): Implement daemon release-on-cutout policy`
- `feat(hy3): Add comprehensive thermal tests`

**No force-push.** If you need to fix something, create a new commit.

---

## ✅ Verification Checklist

Before submitting PR #6:

- [ ] `6ix9ine thermal status` command works and outputs correctly
- [ ] `t69` dashboard displays thermal panel with color coding
- [ ] Daemon releases sessions when `cutout_fired == True`
- [ ] All 8 tests pass (`pytest tests/unit/test_thermal_*.py`)
- [ ] 80%+ line coverage on thermal code
- [ ] `SIXNINE_THERMAL_THRESHOLD` env var override works
- [ ] All 311 project tests still pass
- [ ] No new dependencies added
- [ ] Branch is up to date with main

---

## 🚀 PR Submission

**When ready:**
1. Ensure all verification checks pass
2. Push branch: `git push origin feat/hy3-thermal-awareness`
3. Create PR #6:
   - **Title:** `feat(hy3): Add thermal awareness to CLI and dashboard`
   - **Description:**
     ```
     ## Summary
     Completes Python implementation of thermal awareness (v0.4-advanced-features).
     Adds `thermal status` CLI command, thermal dashboard panel, daemon release-on-cutout policy, and 80%+ test coverage.
     
     ## Changes
     - CLI: new `thermal status` subcommand
     - Dashboard: thermal panel with color coding
     - Daemon: release sessions when Mac overheats
     - Tests: 8 test cases covering all paths
     - Config: tunable via SIXNINE_* env vars
     
     ## Test Plan
     - Run `pytest tests/unit/test_thermal_*.py` — all pass
     - Run `6ix9ine thermal status` — verify output
     - Run `t69` — verify thermal panel visible
     - All 311 project tests pass
     ```

---

## ⚡ Important Notes

1. **This is NOT the generic work order** — the original AntiGravityWO-001 conflicts with the actual project. This task document is authoritative.

2. **No Gemini, no DeepSeek, no config files** — they violate project philosophy. If you want those features, escalate to product owner for explicit approval first.

3. **Thermal monitoring is already built** — you're completing the user-facing surface, not writing the whole feature.

4. **Env vars are the configuration pattern** — project explicitly avoids config files.

5. **Tests are mandatory** — 80%+ coverage is a gate check before merge.

---

## Questions?

If anything is unclear:
1. Re-read this document (it supersedes WORK-ORDERS.md)
2. Check `/Users/rmorales/PycharmProjects/6ix9ine/bin/thermal_monitor.py` (existing thermal code)
3. Check `/Users/rmorales/PycharmProjects/6ix9ine/bin/daemon.py` (where thermal state is used)
4. Review `/Users/rmorales/PycharmProjects/6ix9ine/README.md:63-109` (project philosophy)

If still unclear, ask the orchestrator BEFORE starting implementation.

---

**Status:** Ready to implement  
**No ambiguity:** This is your complete, final task scope  
**Timeline:** 8-11 hours  
**Go build it.** 🚀
