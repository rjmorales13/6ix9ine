# 6ix9ine Launch Checklist — Verified Status & Pending Actions

**Date:** 2026-07-23 (updated twice today — see §2 for the full v1.0.0 → v1.0.2 story)
**Verified against:** live repo state, GitHub remote, and this Mac — including a real, maintainer-run end-to-end test of v1.0.2 (clean install, brew upgrade, hooks, daemon, helper all confirmed working)
**Legend:**
- ✅ Done and independently verified
- ⬜ Pending
- **[CLI]** = can be executed by Claude/agents via terminal (`gh`, `git`, `npm`, `brew`) — just say go
- **[MANUAL]** = requires a human (account signup, identity verification, or platform has no publish API)

---

## 1. Engineering — COMPLETE ✅

| Item | Status | Evidence |
|------|--------|----------|
| 5 PRs merged (marketing, plugin, MCP, homebrew, thermal) | ✅ | Merged into main, tags v0.1–v0.5 on remote |
| Test suite | ✅ | 353 tests passing (was 332 on 2026-07-13; +21 across the hooks-lockout, daemon-staleness, and helper-staleness fixes) |
| Claude Code plugin | ✅ **working live** | Hooks active in `~/.claude/settings.json`, daemon running (acquire/release firing on real sessions) |
| Thermal awareness (PR #6) | ✅ **verified live** | `6ix9ine thermal status` returns real data (COOL 40°C / 85°C threshold). Cutout auto-release is test-verified only (would require overheating the Mac) |
| Git attribution fix | ✅ | `main` force-replaced with corrected history 2026-07-13; zero "Claude Code" authored commits; all tags point into corrected history |

> Detail: [SESSION-COMPLETION.md](SESSION-COMPLETION.md), [COMPLETION-STATUS.md](COMPLETION-STATUS.md)
> ⚠️ SESSION-COMPLETION.md overstates readiness — trust THIS file for launch status.

---

## 2. Homebrew Public Distribution — ✅ COMPLETE and confirmed working end-to-end (v1.0.2)

**`brew install rjmorales13/6ix9ine/6ix9ine` is real, public, and fully verified.** Getting here took three patch releases in one day, each fixing a real bug found by insisting on live-machine testing over trusting reported success. Full story, in order:

- ✅ `v1.0.0` published 2026-07-22: real GitHub release, real tap, real SHA256s, verified via a real `brew install`.
- 🔴 **`v1.0.0` bugs found during re-testing**: (1) `install-hooks`/`uninstall-hooks` crashed with `ModuleNotFoundError: No module named 'hooks'` — the `hooks/` package sits outside PyInstaller's default bundling scope (fixed: PR #12, `--paths .`). (2) Far more serious: hooks were installed as `sys.executable -c "<code>"`, which in the frozen binary resolves to the binary itself and can't run `-c` — exit code 2, and Claude Code hard-blocks `UserPromptSubmit` on exit 2. **This actually locked the maintainer out of every Claude Code prompt during live testing**, requiring manual `~/.claude/settings.json` surgery to recover. Fixed via new `hook-acquire`/`hook-release` subcommands plus migration logic so the fix *repairs* an already-broken config, not just prevents new breakage (PR #13).
- ✅ `v1.0.1` published 2026-07-23 with both hook fixes, verified via a real `brew install` + isolated-temp-HOME hook execution tests (never the real settings.json).
- 🔴 **`v1.0.1` bug found during upgrade testing**: `daemon-start` reported `{"ok": true}` while the daemon wasn't actually running — the LaunchAgent plist only regenerated "if the file doesn't exist," so `brew upgrade` (which deletes the old version's Cellar path) left it pointing at a dead binary forever, and `launchctl load`'s exit code (0, even when it silently did nothing) was trusted blindly. Fixed by regenerating the plist whenever stale and verifying the daemon actually answers its real socket before reporting success (PR #15).
- 🔴 **Same pattern, a third time, caught by independent Opus review before implementation**: `setup-privileged-helper`/`uninstall-helper` had the identical exit-code-trust issue, plus a subtler trap — a naive "poll until reachable" fix (mirroring PR #15) would have been *wrong*, because a stale already-running root helper answers the same fixed socket path; only a version handshake (confirming the *current* version answers, not just *something*) proves the new process actually replaced the old one. Fixed and verified live on this machine via a real `sudo launchctl bootout`+`bootstrap` cycle confirming the process PID actually changed (PR #16).
- ✅ `v1.0.2` published 2026-07-23 with both daemon/helper fixes.
- ✅ **Full end-to-end confirmed working, by the maintainer, in their own terminal**: clean uninstall → `brew install` v1.0.2 → `setup-privileged-helper` (`helper_version: "1.0.2"`, confirming the version-handshake fix) → `install-hooks --all` (clean, no crash, no lockout risk) → `daemon-start` (`regenerated_plist: true`, confirming the staleness fix) → `daemon-status`/`helper-status` both healthy and correctly versioned.
- ✅ Repo hygiene: `main-1` deleted (local + remote), 18 merged local branches cleaned up. `feat/opus-integration-tests` intentionally kept — real unmerged content relevant to §3.

**Process note for future releases, reinforced three times today**: any code that shells out to `launchctl` (or similar OS-state-changing commands) and reports success based on exit code alone is suspect — `launchctl load`/`bootstrap` can return 0 while doing nothing if a label is already registered. The fix pattern each time was: don't trust the exit code; verify the actual resulting state (a real socket/process check); if something might already be running under a stale registration, unload it *first* or a bare reachability check will falsely pass by talking to the old process. Same elevated rigor applies to anything touching `hooks/*.py` (writes into a real user's agent config — a mistake can lock them out of their tool). Treat all of this like release-infra changes: Opus design/implementation, independent Opus review, real empirical verification (ideally on the maintainer's real machine, not just mocks) before merge.

**Still not done:**
- ⬜ **[CLI]** `t69` auto-bootstrap on first launch — daemon auto-starts silently, privileged helper setup prompts explicitly (never silently) before requesting `sudo`. Agreed design, not yet built.
- ⬜ **[CLI]** `install.sh` still targets `~/.local/bin` — re-running it for from-source dev work would recreate the exact PATH-shadowing bug fixed on this machine earlier today. Not yet addressed.
- ⬜ **[CLI]** `macos-14` (the arm64 CI runner) enters its own GitHub deprecation window 2026-07-06–2026-11-02 — same class of fix as the `macos-13`→`macos-15-intel` swap already done for the x86_64 leg.
- ⬜ **[MANUAL — decision only]** Submitting to `homebrew-core` for `formulae.brew.sh` searchability — separate, heavier process, not a blocker to installing today, a goal for once there's wider adoption.

> Detail: `Formula/6ix9ine.rb`, `.github/workflows/release.yml`, `scripts/uninstall.sh`, `scripts/verify-state.sh`

---

## 3. MCP Server Verification — PENDING ⬜ (mostly CLI-able, untouched today)

Unit tests exist (51) but the server has **never been verified against a real client** (Aider/OpenCode). No `node_modules` in `integrations/mcp-server/` — tests not runnable as-is on this machine.

- ⬜ **[CLI]** `cd integrations/mcp-server && npm install && npm test`
- ⬜ **[CLI]** TCP smoke test against the live daemon (start server, send `tools/list` JSON-RPC, confirm 4 tools)
- ⬜ **[CLI]** Wire into a real client config (Aider or OpenCode) and confirm acquire/release hits the daemon
- ⬜ **[MANUAL — optional]** Sanity-check inside an actual Aider session if you use one day-to-day

Note: local branch `feat/opus-integration-tests` has an unmerged 338-line `integration-test.md` relevant to this section — review before starting this work, may already cover some of it.

> Detail: [../../integrations/tests/integration-test.md](../../integrations/tests/integration-test.md) — exact commands, under one page

---

## 4. Marketing Publication — PENDING ⬜ (content written, NOTHING posted, NO accounts created)

**Confidence has improved materially since this was last written, but read the full pattern before deciding.** `v1.0.2` is now confirmed working end-to-end on a real machine, through a real `brew install` → `brew upgrade` cycle, with all three rounds of bugs fixed and independently reviewed. That said, this was genuinely three rounds — a new real bug surfaced at each release (`v1.0.0`→`v1.0.1`→`v1.0.2`), each one only found because of live-machine testing rather than trusting reported success. That's a real signal about how much surface area this project still has, not just bad luck. Whether that's enough runway to promote is a judgment call for the maintainer, not something to infer from "the CI is green now."

All content exists as markdown only: `blog-posts/` (2 posts + outline), `docs/marketing/social/twitter-threads.md` (Twitter thread, 3 Reddit templates, PH tagline, IH pitch).

### Blog posts
- ⬜ **[CLI]** dev.to — has a publish API (`api-key` + POST); Claude can publish once you create an account and API key **[MANUAL: account]**
- ⬜ **[CLI]** GitHub Pages / repo README linking — fully CLI-able, no new account
- ⬜ **[MANUAL]** Medium/Substack — no practical publish API for new accounts

### Social / launch platforms — realistic assessment
| Platform | CLI possible? | Reality |
|----------|--------------|---------|
| Product Hunt | ❌ | **MANUAL.** No submission API for makers. Create account, submit via web UI. Assets ready in twitter-threads.md §Product Hunt |
| Hacker News | ❌ | **MANUAL.** No submission API. Show HN post via web UI. Fresh accounts get flagged — post from an aged account if you have one |
| Reddit | ⚠️ | Technically has an API, but new-account + API posting = instant spam filter. **Treat as MANUAL.** Templates ready for r/macOS, r/devtools, r/programming |
| Twitter/X | ⚠️ | API requires paid tier ($100+/mo Basic). **Manual posting is cheaper.** Thread ready (5 tweets) |
| Indie Hackers | ❌ | **MANUAL.** No API. Pitch ready in twitter-threads.md §Indie Hackers |

**Bottom line: platform launch posting is yours to do by hand.** Account creation involves identity/phone verification Claude cannot and should not do.

> Content: [../marketing/social/twitter-threads.md](../marketing/social/twitter-threads.md), [../marketing/blog/](../marketing/blog/)
> Sequencing detail: [step-1-promotion-distribution-strategy.md](step-1-promotion-distribution-strategy.md)

---

## 5. Repo Hygiene — ✅ COMPLETE (2026-07-23)

- ✅ **[CLI]** `main-1` deleted (local + remote) — was identical/behind `main`, confirmed safe before deleting.
- ✅ **[CLI]** Merged feature branches cleaned up — 18 local branches deleted after confirming each was fully merged into `main` via `git branch --merged`. One branch (`feat/opus-integration-tests`) intentionally kept — has real unmerged content, see §3.
- ⬜ **[CLI]** Branch protection on `main` (block force pushes) — not yet done, still worth doing given the git-history-correction incident on 2026-07-13.

---

## Critical Path Summary (updated)

```
[DONE]   Homebrew release + tap, v1.0.0 -> v1.0.1 -> v1.0.2, three real bugs found and fixed each round
[DONE]   Full end-to-end confirmed working on a real machine: clean install, brew upgrade, hooks, daemon, helper
[DONE]   Repo hygiene (branches)
[PENDING, CLI]   MCP smoke test
[PENDING, CLI]   t69 auto-bootstrap, install.sh PATH-shadow fix, macos-14 CI deprecation
[JUDGMENT CALL, then MANUAL]   Marketing/promotion — mechanically ready; three release rounds each turning
                                 up a new real bug is a signal worth weighing before deciding
```

The distribution mechanism itself is no longer the blocker, and it's no longer just "probably fine" — it's been proven end-to-end on real hardware. The open question now is the maintainer's own risk tolerance given the pattern of what testing kept finding, not CLI-vs-manual mechanics.
