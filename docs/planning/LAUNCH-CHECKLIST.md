# 6ix9ine Launch Checklist — Verified Status & Pending Actions

**Date:** 2026-07-31 (current release: **v1.0.5**)
**Verified against:** live repo state, GitHub remote, and this Mac — including a maintainer-run clean-machine `brew install` of the current release, and a re-verification of every open item below on 2026-07-31
**Legend:**
- ✅ Done and independently verified
- ⬜ Pending
- **[CLI]** = can be executed by Claude/agents via terminal (`gh`, `git`, `npm`, `brew`) — just say go
- **[MANUAL]** = requires a human (account signup, identity verification, or platform has no publish API)

---

## 0. Resume here 📍

**This file is the single entry point for resuming launch work.** Point a new session at
`docs/planning/LAUNCH-CHECKLIST.md` and it has everything below without re-explanation.

**Where things stand:** the product is shipped and installable. `brew install rjmorales13/6ix9ine/6ix9ine`
is public and confirmed working on a clean machine at v1.0.5. Claude Code and OpenCode hooks are live.
Launch has *started* — the X/Twitter thread is posted (§4).

**What's actually left, shortest path first:**

| # | Item | Type | Where |
|---|------|------|-------|
| 1 | Show HN post — the highest-leverage channel, still undrafted | [MANUAL] | §4 |
| 2 | Reddit posts + pre-written objection replies | [MANUAL] | §4 |
| 3 | Automate the tap push in `release.yml` (root cause known, one-line-ish fix) | [CLI] | §2 |
| 4 | Branch protection on `main` | [CLI] | §5 |
| 5 | MCP server has never been run against a real client | [CLI] | §3 |
| 6 | `macos-14` CI runner deprecation (deadline 2026-11-02) | [CLI] | §2 |
| 7 | `t69` auto-bootstrap, `install.sh` PATH shadowing | [CLI] | §2 |

**Changed on 2026-07-31:** X thread posted; README first-visitor pass done — the misleading
`Python 3.13+` badge was removed (Homebrew ships frozen PyInstaller binaries and needs **no** Python;
verified by running the full 389-test suite on 3.12), Requirements split by install method, and a
macOS-only disclaimer added pointing Linux/Windows interest at a GitHub feature request.

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

## 2. Homebrew Public Distribution — ✅ COMPLETE and confirmed working end-to-end (v1.0.5)

**`brew install rjmorales13/6ix9ine/6ix9ine` is real, public, and fully verified.** Getting here took three patch releases in one day, each fixing a real bug found by insisting on live-machine testing over trusting reported success. Full story, in order:

- ✅ `v1.0.0` published 2026-07-22: real GitHub release, real tap, real SHA256s, verified via a real `brew install`.
- 🔴 **`v1.0.0` bugs found during re-testing**: (1) `install-hooks`/`uninstall-hooks` crashed with `ModuleNotFoundError: No module named 'hooks'` — the `hooks/` package sits outside PyInstaller's default bundling scope (fixed: PR #12, `--paths .`). (2) Far more serious: hooks were installed as `sys.executable -c "<code>"`, which in the frozen binary resolves to the binary itself and can't run `-c` — exit code 2, and Claude Code hard-blocks `UserPromptSubmit` on exit 2. **This actually locked the maintainer out of every Claude Code prompt during live testing**, requiring manual `~/.claude/settings.json` surgery to recover. Fixed via new `hook-acquire`/`hook-release` subcommands plus migration logic so the fix *repairs* an already-broken config, not just prevents new breakage (PR #13).
- ✅ `v1.0.1` published 2026-07-23 with both hook fixes, verified via a real `brew install` + isolated-temp-HOME hook execution tests (never the real settings.json).
- 🔴 **`v1.0.1` bug found during upgrade testing**: `daemon-start` reported `{"ok": true}` while the daemon wasn't actually running — the LaunchAgent plist only regenerated "if the file doesn't exist," so `brew upgrade` (which deletes the old version's Cellar path) left it pointing at a dead binary forever, and `launchctl load`'s exit code (0, even when it silently did nothing) was trusted blindly. Fixed by regenerating the plist whenever stale and verifying the daemon actually answers its real socket before reporting success (PR #15).
- 🔴 **Same pattern, a third time, caught by independent Opus review before implementation**: `setup-privileged-helper`/`uninstall-helper` had the identical exit-code-trust issue, plus a subtler trap — a naive "poll until reachable" fix (mirroring PR #15) would have been *wrong*, because a stale already-running root helper answers the same fixed socket path; only a version handshake (confirming the *current* version answers, not just *something*) proves the new process actually replaced the old one. Fixed and verified live on this machine via a real `sudo launchctl bootout`+`bootstrap` cycle confirming the process PID actually changed (PR #16).
- ✅ `v1.0.2` published 2026-07-23 with both daemon/helper fixes.
- ✅ **Full end-to-end confirmed working, by the maintainer, in their own terminal**: clean uninstall → `brew install` v1.0.2 → `setup-privileged-helper` (`helper_version: "1.0.2"`, confirming the version-handshake fix) → `install-hooks --all` (clean, no crash, no lockout risk) → `daemon-start` (`regenerated_plist: true`, confirming the staleness fix) → `daemon-status`/`helper-status` both healthy and correctly versioned.
- 🔴 **A fourth real bug found after v1.0.2, this time via OpenCode rather than Claude Code**: the maintainer reported `/bin/sh: .../6ix9ine: No such file or directory` printing after every OpenCode turn, following an unrelated `opencode` app update. Root cause: `hooks/opencode.py`'s generated plugin hardcoded the CLI as an absolute `~/.local/bin/6ix9ine` path (the source-install location), which went stale the moment the maintainer's own install moved to Homebrew — the same class of mistake as the v1.0.0 Claude Code lockout (Case study 3), just never retroactively applied to the OpenCode installer. Fixed by resolving the CLI via PATH at call time (a bare `"6ix9ine"` command name, self-healing across install-method changes) instead of baking in an absolute path at install time, plus switching `execSync`+shell-string to `execFileSync`+array-args+`stdio: "ignore"` (closes a minor shell-injection surface and silences the leaked stderr as defense-in-depth). Diagnosed and reviewed independently by Opus twice (pre-implementation and final-diff review) before merging PR #20. Full writeup: [TROUBLESHOOTING-HOOKS.md](../TROUBLESHOOTING-HOOKS.md) Case study 4.
- ✅ `v1.0.3` published 2026-07-23 with the OpenCode hook fix: tag pushed, `release.yml` built both arches clean, GitHub Release published, `Formula/6ix9ine.rb` updated on `main`, and the `rjmorales13/homebrew-6ix9ine` tap pushed to match (still a manual step from a local clone — see note below).
- 🔴 **A fifth bug, found after v1.0.3 — the OpenCode sleep-block leak**: when `session.idle` never fired, the daemon held the block indefinitely. Fixed in PR #22 (`bf0a16d`).
- ✅ `v1.0.4` published with that fix.
- 🔴 **A sixth bug, and the subtlest of the set — a timeout shorter than the binary's own cold start**: the OpenCode plugin called `acquire`/`release` via `execFileSync` with a 3s timeout, but the *frozen Homebrew binary* cold-starts in ~3.2–3.7s. So every call was SIGTERM'd before its IPC request reached the daemon, and the plugin's own `try/catch` swallowed the failure silently — it looked like nothing was wrong. Raised to 10s in PR #23 (`5a16ef7`). Writeup: [HOOKS.md](../HOOKS.md) Case study 6. Note the pattern: this is the *third* separate bug caused by the source-install and Homebrew-install environments behaving differently.
- ✅ `v1.0.5` published with the timeout fix — current release.
- ✅ **Clean-machine `brew install` confirmed by the maintainer** (2026-07-31) on the current release.
- ✅ Repo hygiene: `main-1` deleted (local + remote), 18 merged local branches cleaned up. `feat/opus-integration-tests` intentionally kept — real unmerged content relevant to §3.
- ✅ GitHub repo description + 20 topics set (was blank, so every search result and link preview rendered an empty repo). Homepage field still blank, pending a GitHub Pages landing page.
- ✅ Demo GIF recorded and wired into the README hero slot.

**Process note for future releases, reinforced three times today**: any code that shells out to `launchctl` (or similar OS-state-changing commands) and reports success based on exit code alone is suspect — `launchctl load`/`bootstrap` can return 0 while doing nothing if a label is already registered. The fix pattern each time was: don't trust the exit code; verify the actual resulting state (a real socket/process check); if something might already be running under a stale registration, unload it *first* or a bare reachability check will falsely pass by talking to the old process. Same elevated rigor applies to anything touching `hooks/*.py` (writes into a real user's agent config — a mistake can lock them out of their tool). Treat all of this like release-infra changes: Opus design/implementation, independent Opus review, real empirical verification (ideally on the maintainer's real machine, not just mocks) before merge.

**Still not done:**
- ⬜ **[CLI]** `t69` auto-bootstrap on first launch — daemon auto-starts silently, privileged helper setup prompts explicitly (never silently) before requesting `sudo`. Agreed design, not yet built.
- ⬜ **[CLI]** `install.sh` still targets `~/.local/bin` — re-running it for from-source dev work would recreate the exact PATH-shadowing bug fixed on this machine earlier today. Not yet addressed.
- ⬜ **[CLI]** `macos-14` (the arm64 CI runner) enters its own GitHub deprecation window 2026-07-06–2026-11-02 — same class of fix as the `macos-13`→`macos-15-intel` swap already done for the x86_64 leg.
- ⬜ **[MANUAL — decision only]** Submitting to `homebrew-core` for `formulae.brew.sh` searchability — separate, heavier process, not a blocker to installing today, a goal for once there's wider adoption.
- ⬜ **[CLI]** **Tap push is still manual — root cause now identified.** `release.yml`'s "Update Homebrew formula" step regenerates `Formula/6ix9ine.rb` correctly but pushes it to the wrong place: the job's `actions/checkout` never specifies a `repository:`, so the closing `git push origin main` lands in **this** repo instead of the real tap (`rjmorales13/homebrew-6ix9ine`, a separate repo that `brew tap`/`brew upgrade` actually read). The workflow goes green either way, because it did successfully push to *a* repo. Every release to date (v1.0.0 → v1.0.5) has needed a manual follow-up. Fix: check out the tap repo explicitly with a PAT that has write access to it, then push there. Manual workaround, step by step, is in [INSTALL.md](../INSTALL.md) § "Cutting a Release (For Maintainers)". **This is the highest-value CLI item left** — a release can currently ship "successfully" while leaving every user on the old formula.

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

## 4. Marketing Publication — 🟡 IN PROGRESS (X posted; HN, Reddit, PH, IH still to go)

**Launch has started.** The decision this section used to frame as an open judgment call has been made — v1.0.5 is confirmed working on a clean machine, and the X thread went out 2026-07-31.

**Worth keeping in view while promoting:** six real bugs surfaced across v1.0.0 → v1.0.5, each found only by live-machine testing rather than trusting a green CI run, and three of them came from the same root cause — the Homebrew (frozen binary) environment behaving differently from the source-install environment. Traffic from a launch means first-time Homebrew installs specifically, which is exactly that surface. Be available to respond fast for the first few days.

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
| Twitter/X | ⚠️ | ✅ **POSTED 2026-07-31.** 5-post chained thread, GIF on the hero, GitHub link held to the final post. App account created and used. API was never needed — posted by hand via the web composer (API requires a $100+/mo paid tier) |
| Indie Hackers | ❌ | **MANUAL.** No API. Pitch ready in twitter-threads.md §Indie Hackers |

**Bottom line: platform launch posting is yours to do by hand.** Account creation involves identity/phone verification Claude cannot and should not do.

**Next up, in priority order:** Show HN (highest leverage for auditable OSS dev tools, and the architecture/trust-boundary story lands best there — post ~9am ET on a weekday), then Reddit staggered one subreddit per day, then Product Hunt once there's some star count to show. Full rationale in the launch-sequence table at the top of [twitter-threads.md](../marketing/social/twitter-threads.md).

> Content: [../marketing/social/twitter-threads.md](../marketing/social/twitter-threads.md), [../marketing/blog/](../marketing/blog/)
> Sequencing detail: [step-1-promotion-distribution-strategy.md](step-1-promotion-distribution-strategy.md)

---

## 5. Repo Hygiene — 🟡 one item left

- ✅ **[CLI]** `main-1` deleted (local + remote) — was identical/behind `main`, confirmed safe before deleting.
- ✅ **[CLI]** Merged feature branches cleaned up — 18 local branches deleted after confirming each was fully merged into `main` via `git branch --merged`. One branch (`feat/opus-integration-tests`) intentionally kept — has real unmerged content, see §3.
- ⬜ **[CLI]** Branch protection on `main` (block force pushes) — **re-verified still absent on 2026-07-31** (`gh api repos/rjmorales13/6ix9ine/branches/main/protection` returns `404 Branch not protected`). Still worth doing given the git-history-correction incident on 2026-07-13, and more so now that the repo is publicly launched.
- ⬜ **[CLI]** Six merged local branches are still hanging around from the v1.0.3–v1.0.5 fixes (`fix/opencode-plugin-timeout`, `fix/opencode-sleep-leak-no-pid`, `docs/*`, …) — same cleanup as before, just accumulated again. Also `.claude/worktrees/` shows up untracked and probably wants a `.gitignore` entry.

---

## Critical Path Summary (updated)

```
[DONE]   Homebrew release + tap, v1.0.0 -> v1.0.5, six real bugs found and fixed along the way
[DONE]   Clean-machine brew install confirmed on v1.0.5
[DONE]   Demo GIF, repo description + topics, README first-visitor pass
[DONE]   LAUNCH STARTED -- X thread posted 2026-07-31

[NEXT, MANUAL]   Show HN  <-- highest leverage, still undrafted, ~9am ET weekday
[NEXT, MANUAL]   Reddit (one sub/day) + pre-written objection replies
[NEXT, CLI]      Automate tap push in release.yml -- root cause known (missing `repository:`
                   on actions/checkout); today a release can go green without updating the tap
[THEN, CLI]      Branch protection on main
[THEN, CLI]      MCP smoke test -- never run against a real client
[THEN, CLI]      macos-14 CI deprecation (2026-11-02), t69 auto-bootstrap, install.sh PATH shadow
```

Distribution is proven and the launch is underway. The remaining work splits cleanly: the manual
half is promotion (HN and Reddit are where an auditable-OSS trust story actually lands), and the
CLI half is release-infrastructure debt — of which the tap-push bug is the one that can bite a real
user, since it lets a release report success while leaving everyone on the old formula.
