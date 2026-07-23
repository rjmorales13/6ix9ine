# 6ix9ine Launch Checklist — Verified Status & Pending Actions

**Date:** 2026-07-23 (updated from the 2026-07-13 version — see §2 for what changed)
**Verified against:** live repo state, GitHub remote, and this Mac (not doc claims)
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
| Test suite | ✅ | 342 tests passing (was 332 on 2026-07-13; +10 from the hooks-lockout fix below) |
| Claude Code plugin | ✅ **working live** | Hooks active in `~/.claude/settings.json`, daemon running (acquire/release firing on real sessions) |
| Thermal awareness (PR #6) | ✅ **verified live** | `6ix9ine thermal status` returns real data (COOL 40°C / 85°C threshold). Cutout auto-release is test-verified only (would require overheating the Mac) |
| Git attribution fix | ✅ | `main` force-replaced with corrected history 2026-07-13; zero "Claude Code" authored commits; all tags point into corrected history |

> Detail: [SESSION-COMPLETION.md](SESSION-COMPLETION.md), [COMPLETION-STATUS.md](COMPLETION-STATUS.md)
> ⚠️ SESSION-COMPLETION.md overstates readiness — trust THIS file for launch status.

---

## 2. Homebrew Public Distribution — ✅ COMPLETE (but read this before promoting it)

**This is the section that changed the most since 2026-07-13.** `brew install rjmorales13/6ix9ine/6ix9ine` is real and public now — but the first release (`v1.0.0`) shipped with two real bugs, one of which caused actual damage during testing. Full story, in order:

- ✅ **[CLI]** `v1.0.0` published 2026-07-22: real GitHub release, real tap (`rjmorales13/homebrew-6ix9ine`), real SHA256s, end-to-end verified via an actual `brew install` on this Mac.
- ⚠️ **Bug found in `v1.0.0`**: `6ix9ine install-hooks`/`uninstall-hooks` crashed with `ModuleNotFoundError: No module named 'hooks'` in the Homebrew-distributed binary — the `hooks/` package sits at the repo root, outside PyInstaller's default bundling scope. Fixed on `main` via `--paths .` on the PyInstaller build commands (PR #12).
- 🔴 **Much more serious bug found while re-testing**: `hooks/claude.py` installed Claude Code hooks as `sys.executable -c "<code>"`. In the frozen binary, `sys.executable` resolves to the binary itself, which can't run `-c` — argparse rejects it, **exit code 2**, and Claude Code treats exit 2 from `UserPromptSubmit` as a hard block. **This actually locked the maintainer out of every Claude Code prompt during live testing on this machine**, requiring manual surgery on `~/.claude/settings.json` to recover. Fixed via new `hook-acquire`/`hook-release` subcommands that work identically frozen or from source, plus migration logic so the fix can *repair* an already-broken settings.json, not just prevent new breakage (PR #13). The Bash/`PreToolUse` PID-tracking hook was removed entirely rather than patched — it never worked even from source and its Claude Code output contract was never verified.
- ✅ **[CLI]** Both fixes verified independently and interactively before shipping: real frozen-binary rebuilds, hook execution tested against isolated temp `HOME` directories (never the real `~/.claude/settings.json`), and a simulated repair of the exact broken state the maintainer hit.
- ✅ **[CLI]** `v1.0.1` published 2026-07-23 with both fixes, same dry-run-first process as `v1.0.0`.
- ✅ **[CLI]** Repo hygiene: `main-1` deleted (local + remote), 18 merged local branches cleaned up. `feat/opus-integration-tests` intentionally kept — has real unmerged content relevant to §3 below.

**Process note for future releases**: anything touching `hooks/*.py` or how hooks get installed is safety-sensitive — it writes into a real user's agent config, and a mistake can lock them out of their tool. Treat with the same rigor as release-infra changes (Opus design/implementation, independent Opus review, real empirical verification before merge) and never test hook installation against a real `~/.claude/settings.json`.

**Still not done:**
- ⬜ **[CLI]** `t69` auto-bootstrap on first launch — daemon auto-starts silently, privileged helper setup prompts explicitly (never silently) before requesting `sudo`. Agreed design, not yet built.
- ⬜ **[CLI]** `install.sh` still targets `~/.local/bin` — re-running it for from-source dev work would recreate the exact PATH-shadowing bug fixed on this machine today. Not yet addressed.
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

**Hold off on this until the release has had more real-world runway.** Given today's findings — a first release that shipped a bug capable of locking users out of their own coding tool — driving traffic at `v1.0.1` on day one carries real risk of the same class of bug surfacing again in front of an audience. Consider this section blocked on confidence, not just on the mechanics below.

All content exists as markdown only: `blog-posts/` (2 posts + outline), `social-media/twitter-threads.md` (Twitter thread, 3 Reddit templates, PH tagline, IH pitch).

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

> Content: [../../social-media/twitter-threads.md](../../social-media/twitter-threads.md), [../../blog-posts/](../../blog-posts/)
> Sequencing detail: [step-1-promotion-distribution-strategy.md](step-1-promotion-distribution-strategy.md)

---

## 5. Repo Hygiene — ✅ COMPLETE (2026-07-23)

- ✅ **[CLI]** `main-1` deleted (local + remote) — was identical/behind `main`, confirmed safe before deleting.
- ✅ **[CLI]** Merged feature branches cleaned up — 18 local branches deleted after confirming each was fully merged into `main` via `git branch --merged`. One branch (`feat/opus-integration-tests`) intentionally kept — has real unmerged content, see §3.
- ⬜ **[CLI]** Branch protection on `main` (block force pushes) — not yet done, still worth doing given the git-history-correction incident on 2026-07-13.

---

## Critical Path Summary (updated)

```
[DONE]   Homebrew release + tap, v1.0.0 → v1.0.1 with real bugs found and fixed
[DONE]   Repo hygiene (branches)
[PENDING, CLI]   MCP smoke test
[PENDING, CLI]   t69 auto-bootstrap, install.sh PATH-shadow fix, macos-14 CI deprecation
[BLOCKED ON CONFIDENCE, then MANUAL]   Marketing/promotion — hold until v1.0.1 has real-world runway
```

The distribution mechanism itself is no longer the blocker. The open question now is confidence in the release, not CLI-vs-manual mechanics.
