# 6ix9ine Multi-Agent Quick Reference

**Use this to track progress, manage parallel work, and coordinate merges.**

---

## Agent Status Dashboard — ACTUAL COMPLETION

| Release | Agent | Model | Status | Branch | PR | Completed |
|---------|-------|-------|--------|--------|----|----|
| **v0.1-marketing** | FABLE | Fable | ✅ COMPLETE | docs/fable-marketing-content | #4 | 2026-07-12 |
| **v0.2-claude-plugin** | DeepSeek | DeepSeek | ✅ COMPLETE | feat/opus-pr-claude-plugin | #2 | 2026-07-13 |
| **v0.3-mcp-server** | DeepSeek | DeepSeek | ✅ COMPLETE | feat/opus-pr-mcp-server | #3 | 2026-07-13 |
| **v0.5-homebrew** | AntiGravity | Gemini 3.5 | ✅ COMPLETE | feat/sonnet-homebrew-formula | #5 | 2026-07-13 |
| **v0.4-advanced-features** | HY3 | HY3 | ⏳ IN PROGRESS | feat/antigravity-* | #6? | TBD |

---

## Agent Work Orders (One-Line Summary)

### FABLE (Marketing)
**Work Order:** FableWO-001  
**Tasks:** Blog post (comparison), blog post (architecture), social media pack  
**Output:** 3 markdown files (blog-posts/, social-media/)  
**PR Title:** `docs(fable): Add marketing content pack + comparison + architecture posts`  
**Branch:** `docs/fable-marketing-content`  

→ **Copy-paste template:** See AGENT-COPY-PASTE-TEMPLATES.md "TEMPLATE 1"

---

### OPUS (Integrations)
**Work Order:** OpusWO-001  
**Tasks:** Claude Code plugin, MCP server, integration tests  
**Output:** 2 plugin directories (integrations/claude-code-plugin, integrations/mcp-server)  
**PR Titles:** 
- `feat(opus): Add Claude Code plugin for 6ix9ine`
- `feat(opus): Add MCP server for multi-agent orchestration`  
**Branch:** `feat/opus-*`  

→ **Copy-paste template:** See AGENT-COPY-PASTE-TEMPLATES.md "TEMPLATE 2"

---

### SONNET (Build & Distribution)
**Work Order:** SonnetWO-001  
**Tasks:** Homebrew formula, man pages, build optimization, compatibility matrix  
**Output:** Formula/6ix9ine.rb, docs/man/*, docs/compatibility.md  
**PR Title:** `feat(sonnet): Add production Homebrew formula for 6ix9ine`  
**Branch:** `feat/sonnet-*`  

→ **Copy-paste template:** See AGENT-COPY-PASTE-TEMPLATES.md "TEMPLATE 3"

---

### OPENCODE (CLI & DeepSeek)
**Work Order:** OpenCodeWO-001  
**Tasks:** Error handling, DeepSeek diagnostics, CLI help, config file support, testing  
**Output:** Enhanced CLI, diagnose command, help system, config support  
**PR Titles:**
- `feat(opencode): Harden CLI error handling...`
- `feat(opencode): Add DeepSeek-powered diagnostic command`
- `feat(opencode): Add comprehensive CLI help...`  
**Branch:** `feat/opencode-*`  

→ **Copy-paste template:** See AGENT-COPY-PASTE-TEMPLATES.md "TEMPLATE 4"

---

### ANTIGRAVITY (Advanced Features & Gemini)
**Work Order:** AntiGravityWO-001  
**Tasks:** Thermal awareness, calendar scheduling, Gemini advisor, dashboard extensions, logging  
**Output:** pkg/thermal/, pkg/calendar/, pkg/gemini/, enhanced dashboard  
**PR Titles:**
- `feat(antigravity): Add thermal-aware sleep management`
- `feat(antigravity): Add calendar-aware sleep scheduling`
- `feat(antigravity): Add Gemini 3.5-powered optimization advisor`
- `feat(antigravity): Enhance dashboard and add comprehensive logging`  
**Branch:** `feat/antigravity-*`  

→ **Copy-paste template:** See AGENT-COPY-PASTE-TEMPLATES.md "TEMPLATE 5"

---

## How to Invoke Each Agent

### FABLE
```
Platform: Claude.ai, Claude Code (Fable model)
Prompt: Copy TEMPLATE 1 from AGENT-COPY-PASTE-TEMPLATES.md
Expected Output: 3 markdown files in blog-posts/ and social-media/
Time: ~4-5 hours
```

### OPUS
```
Platform: Claude.ai, Claude Code (Opus 4.8 model)
Prompt: Copy TEMPLATE 2 from AGENT-COPY-PASTE-TEMPLATES.md
Expected Output: plugin.json, index.ts, server.go, tests
Time: ~8-10 hours
```

### SONNET
```
Platform: Claude.ai, Claude Code (Sonnet 5 model)
Prompt: Copy TEMPLATE 3 from AGENT-COPY-PASTE-TEMPLATES.md
Expected Output: Formula/6ix9ine.rb, man pages, build config
Time: ~6-8 hours
```

### OPENCODE
```
Platform: OpenCode (with DeepSeek backend)
Prompt: Copy TEMPLATE 4 from AGENT-COPY-PASTE-TEMPLATES.md
Expected Output: Enhanced CLI, diagnose.go, help.go, config support
Time: ~7-9 hours
```

### ANTIGRAVITY
```
Platform: AntiGravity (with Gemini 3.5 backend)
Prompt: Copy TEMPLATE 5 from AGENT-COPY-PASTE-TEMPLATES.md
Expected Output: thermal/, calendar/, gemini/, enhanced dashboard
Time: ~8-10 hours
```

---

## Git Workflow Checklist (Every Agent Must Follow)

### Before Starting
- [ ] Clone/update repo: `git clone https://github.com/rjmorales13/6ix9ine.git`
- [ ] Create local branch: `git checkout -b [branch-name-from-template]`
- [ ] Ensure you're on main first: `git checkout main && git pull origin main`

### While Working
- [ ] Follow branch naming: `feat/[agent]-[feature]` or `docs/[agent]-[feature]`
- [ ] Commit message format: `<type>: <description>` (type = feat/fix/docs/chore/test)
- [ ] No hardcoded secrets, API keys, or credentials
- [ ] Follow ecc/common/coding-style.md (max 800 lines per file, clear naming)
- [ ] Add tests for new code (80%+ coverage target)

### Before Submitting PR
- [ ] Verify local tests pass: `pytest`, `npm test`, `go test ./...` (language-specific)
- [ ] Check no merge conflicts: `git fetch origin && git merge origin/main`
- [ ] Ensure branch is up to date: `git pull origin main`
- [ ] Stage files: `git add [specific-files]` (NOT `git add .`)
- [ ] Create commit: `git commit -m "$(cat <<'EOF'\ntype: description\nEOF\n)"`

### Submitting PR
- [ ] Push branch: `git push -u origin [branch-name]`
- [ ] Create PR on GitHub with template description
- [ ] Link to work order in PR description
- [ ] Wait for code review (security-reviewer agent will check)
- [ ] Address any review comments in new commits (don't amend)
- [ ] Get approval before merging

### Merging
- [ ] Use "Merge pull request" (not rebase)
- [ ] Delete remote branch after merge
- [ ] Pull main locally: `git pull origin main`
- [ ] Tag release: `git tag v0.X-[feature-name]` (provided in template)

---

## File Paths Reference (Windows)

All paths relative to project root. Replace `C:\Users\{{USERNAME}}\PycharmProjects\6ix9ine\` prefix:

```
Project root: C:\Users\{{USERNAME}}\PycharmProjects\6ix9ine\

FABLE outputs:
- blog-posts\keep-mac-awake-comparison.md
- blog-posts\architecture-transparency.md
- social-media\twitter-threads.md

OPUS outputs:
- integrations\claude-code-plugin\plugin.json
- integrations\claude-code-plugin\index.ts
- integrations\mcp-server\server.go
- integrations\mcp-server\handlers.go

SONNET outputs:
- Formula\6ix9ine.rb
- docs\man\6ix9ine.1
- docs\man\t69.1
- docs\compatibility.md

OPENCODE outputs:
- cmd\6ix9ine\commands\diagnose.go
- pkg\deepseek\client.go
- pkg\config\loader.go
- docs\cli-reference.md

ANTIGRAVITY outputs:
- pkg\thermal\monitor.go
- pkg\calendar\reader.go
- pkg\gemini\client.go
- cmd\t69\dashboard.go (enhanced)

Code to review during work:
- README.md (architecture)
- cmd\6ix9ine\main.go (entrypoint)
```

---

## Gate Checks Required for All PRs

Every PR must pass these checks before merge:

```
SECURITY:
- [ ] No hardcoded API keys, secrets, or credentials
- [ ] No authentication bypass vulnerabilities
- [ ] Input validation present where needed

CODE QUALITY:
- [ ] Code review passes (code-reviewer agent)
- [ ] No console.log / debug statements
- [ ] Functions < 50 lines (except setup/config)
- [ ] Files < 800 lines
- [ ] Naming is clear and descriptive
- [ ] No deep nesting (> 4 levels)

TESTING:
- [ ] Tests written for new code (80%+ coverage)
- [ ] All tests pass locally
- [ ] No test-only code in main codebase

GIT:
- [ ] No merge conflicts
- [ ] Branch is up to date with main
- [ ] Commit messages follow format
- [ ] No force-push to main

DOCUMENTATION:
- [ ] Code comments explain WHY, not WHAT
- [ ] README updated if needed
- [ ] Configuration documented
```

---

## Merge Order (CRITICAL)

Execute in this order to avoid conflicts:

1. **FABLE** (Week 1) → Marketing files, no code conflicts
   - Tag: v0.1-marketing
   
2. **SONNET** (Week 2) → Homebrew, build system
   - Tag: v0.1-homebrew
   
3. **OPUS** (Week 2) → Integrations (Claude, MCP)
   - Tag: v0.2-integrations
   
4. **OPENCODE** (Week 2) → CLI enhancements
   - Tag: v0.3-cli-hardening
   
5. **ANTIGRAVITY** (Week 3) → Advanced features (last, extends all above)
   - Tag: v0.4-advanced-features

6. **FINAL RELEASE TAG** → v0.5-launch-ready
   - Merge to production
   - Prepare for Product Hunt, HN, launch

---

## Conflict Resolution Strategy

If merges conflict:

1. **FABLE conflicts with anything?** — No code, unlikely. Merge FABLE first.
2. **SONNET conflicts with OPUS?** — Both touch different dirs (Formula vs integrations). Merge SONNET, then rebase OPUS.
3. **OPUS conflicts with OPENCODE?** — OPUS adds integrations, OPENCODE enhances CLI. Different dirs, but both may touch main.go. Rebase later PR.
4. **OPENCODE conflicts with ANTIGRAVITY?** — Both enhance CLI / dashboard. Rebase ANTIGRAVITY after OPENCODE merged.

**General rule:** When in doubt, merge the earlier work order first, then rebase the later one.

---

## Test Execution Checklist

Before each merge:

```bash
# General tests (all agents)
git status                                  # Ensure clean working dir
git log --oneline -5                       # Verify commit messages

# Language-specific
go test ./... -v -cover                    # Go projects
npm test -- --coverage                     # Node/TypeScript
python -m pytest --cov                     # Python

# Manual testing
brew install ./Formula/6ix9ine.rb          # SONNET: Homebrew
6ix9ine status                              # OPENCODE: CLI
t69                                         # ANTIGRAVITY: Dashboard
6ix9ine diagnose --analyze                 # OPENCODE: DeepSeek

# Security
grep -r "password\|secret\|key\|token" .   # No hardcoded secrets
grep -r "TODO\|FIXME\|HACK" .              # No debug markers
```

---

## Troubleshooting Quick Links

| Issue | Solution |
|-------|----------|
| Merge conflict on main.go | Rebase current branch: `git rebase origin/main`, resolve conflicts |
| Test coverage below 80% | Add more test cases (see ecc/common/testing.md) |
| Code review fails | Address comments in new commit (don't amend published commits) |
| DeepSeek API not responding | Add fallback logic; gracefully degrade (see TEMPLATE 4) |
| Homebrew formula SHA256 wrong | Recompute from release tarball; update Formula/6ix9ine.rb |
| Daemon registration fails (macOS) | Check /Library/LaunchDaemons/ permissions; test locally before PR |
| Dashboard rendering broken | Test in terminal; verify color codes work |
| Calendar integration reads old events | Invalidate cache; test with fresh Calendar.app data |

---

## Success Metrics

Track progress:

```
WEEK 1:
- [ ] FABLE completes marketing content
- [ ] SONNET completes Homebrew formula
- [ ] OPUS design documents reviewed

WEEK 2:
- [ ] FABLE PR merged (v0.1-marketing)
- [ ] SONNET PR merged (v0.1-homebrew)
- [ ] OPUS PRs submitted (Claude plugin + MCP)
- [ ] OPENCODE PRs submitted (CLI + DeepSeek)

WEEK 3:
- [ ] All PRs merged
- [ ] ANTIGRAVITY PRs submitted
- [ ] Release tag v0.5-launch-ready created
- [ ] Product Hunt assets prepared

WEEK 4:
- [ ] Launch day (Product Hunt + HN)
- [ ] Social media rollout
- [ ] Blog post published
```

---

## Important Notes

1. **No parallel commits to main** — Only one agent merges at a time (use merge queue if available)
2. **API keys** — DeepSeek and Gemini keys should be in `.env` locally, never committed
3. **File paths** — Use relative paths in code, never hardcode user directories
4. **Testing** — Run tests locally before pushing; CI should verify, not discover issues
5. **Code review** — Don't skip; security-reviewer agent is mandatory for all PRs
6. **Documentation** — Every feature needs docs (inline comments + README)
7. **Commits** — Use descriptive messages; future-you will appreciate it

---

## Questions?

If an agent gets stuck:

1. **Review the work order again** (WORK-ORDERS.md)
2. **Check the copy-paste template** (AGENT-COPY-PASTE-TEMPLATES.md)
3. **Consult the strategy docs** (step-1, step-2, step-3, STRATEGY-SUMMARY.md)
4. **Post error in task comments** — Include full error, what you tried, what failed

---

## Final Checklist Before v0.5-launch-ready

```
FEATURES:
- [ ] Marketing content published (FABLE)
- [ ] Homebrew formula working locally (SONNET)
- [ ] Claude Code plugin auto-detects sessions (OPUS)
- [ ] MCP server connects to Aider (OPUS)
- [ ] CLI error handling user-friendly (OPENCODE)
- [ ] DeepSeek diagnostics working (OPENCODE)
- [ ] Thermal monitoring active (ANTIGRAVITY)
- [ ] Calendar scheduling functional (ANTIGRAVITY)
- [ ] Gemini advisor provides recommendations (ANTIGRAVITY)
- [ ] Dashboard shows all features (ANTIGRAVITY)

QUALITY:
- [ ] All tests pass (80%+ coverage)
- [ ] No hardcoded secrets
- [ ] All PRs reviewed and approved
- [ ] No merge conflicts
- [ ] Documentation complete

RELEASE:
- [ ] Release notes prepared
- [ ] GitHub Release created with assets
- [ ] Product Hunt landing page ready
- [ ] Blog posts published
- [ ] Social media content scheduled
- [ ] v0.5-launch-ready tag created
```

Done! 🚀
