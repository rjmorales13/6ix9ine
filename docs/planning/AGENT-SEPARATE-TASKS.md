# Agent Task Documents: Create These Separately

**Status:** Recommended structure for posting work to agents on Windows

**Goal:** Each agent gets ONE focused document with hard stopping lines. No distractions.

---

## Recommendation: CREATE 6 SEPARATE FILES

### Files to Create:

1. **OPUS-TASK-integrations.md** (Opus 4.8)
2. **SONNET-TASK-build.md** (Sonnet 5)
3. **OPENCODE-TASK-cli.md** (DeepSeek)
4. **ANTIGRAVITY-TASK-advanced.md** (Gemini 3.5)
5. **FABLE-TASK-marketing.md** (Fable)
6. **GIT-WORKFLOW-SHARED.md** (ALL agents read this)

### Why Separate Files?

| Benefit | With Combined WORK-ORDERS.md | With Separate Files |
|---------|---|---|
| Agent focus | ❌ 50kb doc, 5 agents' work | ✅ 5kb doc, just your work |
| Clarity | ❌ "Where do I stop?" | ✅ Clear hard line at end |
| Copy-paste | ❌ Must extract your section | ✅ Copy entire file |
| Assumption risk | ❌ Might read other agents' tasks | ✅ Isolated, no cross-contamination |
| Stopping point | ❌ Implicit | ✅ EXPLICIT at end |

---

## Template for Each Agent Document

Here's the structure (use for all 5):

```markdown
# [AGENT NAME] TASK: [FEATURE]

## ⚠️ COMPLEXITY & MODEL ASSESSMENT

**Complexity Level:** [LOWEST/LOW/MEDIUM/MEDIUM-HIGH/HIGHEST]
**Model Assignment:** [Model Name] 
**Why this model:** [1-2 sentence justification]
**Risk Level:** [LOW/MEDIUM/HIGH]
**Expected effort:** [X hours]

---

## 📋 YOUR WORK ORDER

**Work Order ID:** [ID]
**Branch name:** [branch-name]
**Expected deliverable:** [what you're producing]
**Timeline:** [when it's due]

---

## ✅ TASKS (IN ORDER)

### Task 1: [Task name]
- **Objective:** [What you're doing]
- **Files to review:** [C:\path\to\file.md] (lines 10-50)
- **Output file:** [C:\path\to\output.md]
- **Requirements:** [Specific requirements]
- **Branch:** [branch name]
- **Deliverable:** [What you produce]

### Task 2: [Task name]
[...repeat format]

---

## 🎯 CRITICAL: STOPPING CONDITIONS

**IF YOU ARE NOT 95% CONFIDENT on ANY of these, STOP and ASK:**

- [ ] [Item 1 - specific thing]
- [ ] [Item 2 - specific thing]
- [ ] [Item 3 - specific thing]

**DO NOT GUESS on:**
- ❌ [Critical thing 1]
- ❌ [Critical thing 2]
- ❌ [Critical thing 3]

**IF YOU HIT A STOPPING CONDITION:**
1. Post your question in the task comment
2. Quote the requirement you're unclear on
3. Wait for clarification
4. Do not proceed with assumptions

---

## 📤 PR SUBMISSION

**PR Title:** [title]

**PR Description Template:**
[...paste description template]

**Gate Checks (Must all pass):**
- [ ] Code review passes
- [ ] Tests pass (XX% coverage)
- [ ] No merge conflicts
- [ ] [Other checks specific to this task]

---

## 🛑 END OF YOUR WORK

**When you're done:**
1. All tasks completed ✅
2. All stopping conditions addressed
3. PR submitted with correct title
4. Gate checks passing
5. **STOP — Do not start new work**
6. Wait for merge approval

Do not:
- ❌ Add features not listed
- ❌ Refactor unrelated code
- ❌ Merge to main yourself
- ❌ Make assumptions if unclear

---

[End of task document]
```

---

## Here's Each Agent's Specific Document:

---

## 1️⃣ OPUS-TASK-integrations.md

```markdown
# OPUS TASK: Claude Code Plugin + MCP Server Integration

## ⚠️ COMPLEXITY & MODEL ASSESSMENT

**Complexity Level:** HIGHEST ⭐⭐⭐⭐⭐
**Model Assignment:** Opus 4.8
**Why this model:** System architecture + protocol compliance. Needs best reasoning for multi-agent coordination.
**Risk Level:** MEDIUM (protocols must be correct)
**Expected effort:** 20-24 hours

---

## 📋 YOUR WORK ORDER

**Work Order ID:** OpusWO-001
**Branch names:** 
- feat/opus-claude-integration-design
- feat/opus-claude-plugin-impl
- feat/opus-mcp-design
- feat/opus-mcp-server-impl
- feat/opus-integration-tests

**Expected deliverables:** 
- Claude Code plugin (plugin.json, index.ts, hooks.json)
- MCP server (server.go, handlers.go, config.json)
- Integration tests (procedures + report)

**Timeline:** Week 2 (parallel with SONNET, after FABLE)

---

## ✅ TASKS (IN ORDER)

### Task 1: Design Claude Code Plugin Architecture
- **Objective:** Document how 6ix9ine hooks into Claude Code lifecycle
- **Files to review:** 
  - C:\Users\rmorales\PycharmProjects\6ix9ine\README.md (architecture section)
  - C:\Users\rmorales\PycharmProjects\6ix9ine\docs\sharing-is-good\step-3-revised-critique-unified-strategy.md (lines 110-140)
- **Output file:** integrations\claude-code-plugin-design.md
- **Requirements:**
  - Hook points (session start, session end, error scenarios)
  - Plugin API surface (what methods does daemon expose?)
  - Error handling strategy
  - Configuration options
  - Privilege requirements (if any)
- **Branch:** feat/opus-claude-integration-design
- **Deliverable:** Architecture document (markdown, 2-3 pages)

### Task 2: Implement Claude Code Plugin
- **Objective:** Build working plugin that auto-detects Claude Code sessions
- **Files to create:**
  - integrations\claude-code-plugin\plugin.json (manifest)
  - integrations\claude-code-plugin\index.ts (main plugin logic)
  - integrations\claude-code-plugin\hooks.json (hook definitions for Claude)
  - integrations\claude-code-plugin\README.md (installation + usage docs)
- **Requirements:**
  - Auto-detect when Claude Code session starts
  - Register session with 6ix9ine daemon (call daemon API)
  - Clean up session when Claude Code ends or crashes
  - Handle errors gracefully (daemon down, permission denied, etc.)
  - No hardcoded paths or secrets
  - Follow ecc/common/coding-style.md (max 800 lines per file)
- **Branch:** feat/opus-claude-plugin-impl
- **Testing:**
  - Install plugin locally in Claude Code
  - Start Claude Code session
  - Verify session appears in daemon
  - Check `t69` dashboard shows session active
  - End session, verify cleanup
  - Test daemon crash scenario (auto-cleanup)
- **Deliverable:** Working plugin + tests passing

### Task 3: Design MCP Server Architecture
- **Objective:** Document how 6ix9ine acts as MCP server for Aider, OpenCode, etc.
- **Files to review:** 
  - MCP specification (external; reference mcp.run or official docs)
  - C:\Users\rmorales\PycharmProjects\6ix9ine\README.md
- **Output file:** integrations\mcp-integration-design.md
- **Requirements:**
  - MCP protocol compliance (what messages does it handle?)
  - Multi-client handling (concurrent Aider + OpenCode sessions)
  - Session lifecycle (start, end, error states)
  - Error recovery (network loss, client crash)
  - Configuration for MCP registry
- **Branch:** feat/opus-mcp-design
- **Deliverable:** Architecture document (2-3 pages)

### Task 4: Implement MCP Server
- **Objective:** Build MCP server that Aider, OpenCode can connect to
- **Files to create:**
  - integrations\mcp-server\server.go (or .ts) (main server)
  - integrations\mcp-server\handlers.go (protocol handlers)
  - integrations\mcp-server\config.json (MCP manifest/config)
  - integrations\mcp-server\README.md (setup instructions)
- **Requirements:**
  - Fully MCP protocol compliant
  - Accept connections from multiple MCP clients
  - Track sessions per client
  - Implement required MCP methods (list_resources, read_resource, etc.)
  - Graceful shutdown on client disconnect
  - Error logging without exposing internal state
  - No hardcoded values
  - Follow ecc/common/coding-style.md
- **Branch:** feat/opus-mcp-server-impl
- **Testing:**
  - Start MCP server locally
  - Connect MCP client (Aider or mock client)
  - Send protocol messages
  - Verify correct responses
  - Test concurrent clients (2+ connections)
  - Test error scenarios (bad requests, client crash)
- **Deliverable:** Working MCP server + tests passing

### Task 5: Integration Testing
- **Objective:** Test Claude plugin + MCP server together
- **Files to create:** integrations\tests\integration-test.md
- **Test cases (manual procedures):**
  1. Claude Code plugin + MCP server both running
  2. Start Claude Code session → verify appears in daemon
  3. Start Aider with MCP client → verify connects to server
  4. Both tools active simultaneously → check reference counting works
  5. Kill Claude → verify auto-cleanup
  6. Network loss → verify graceful recovery
  7. Daemon crash → verify both plugins recover
- **Branch:** feat/opus-integration-tests
- **Deliverable:** Test procedures document + results

---

## 🎯 CRITICAL: STOPPING CONDITIONS

**IF YOU ARE NOT 95% CONFIDENT on ANY of these, STOP and ASK:**

- [ ] MCP protocol specification (exact message format required?)
- [ ] Claude Code plugin hook API (what events does Claude Code fire? how do we register?)
- [ ] Daemon API contract (how does plugin call daemon? what if daemon isn't running?)
- [ ] Session lifecycle (when do we register? when cleanup? what about crashes?)
- [ ] Error scenarios (permission denied, daemon timeout, etc. — what's expected behavior?)

**DO NOT GUESS on:**
- ❌ MCP protocol details (look up official spec, don't assume)
- ❌ Claude Code hook API (review Claude docs or contact support, don't invent)
- ❌ Daemon API contract (review existing daemon code, confirm interface)
- ❌ Reference counting semantics (confirm with strategy docs how multi-agent counting works)

**IF YOU HIT A STOPPING CONDITION:**
1. Quote the exact requirement you're unsure about
2. Post: "Question: [requirement]. I'm not 95% confident on [specific aspect]."
3. Wait for clarification
4. Do not code until clear

---

## 📤 PR SUBMISSION

**PR 1 Title:** `feat(opus): Add Claude Code plugin for 6ix9ine`

**PR 1 Description:**
```
## Summary
Implements Claude Code plugin that auto-detects sessions and registers with 6ix9ine daemon for coordinated sleep management.

## Architecture
- Hook-based session lifecycle (start/stop events)
- Reference counting protocol
- Auto-cleanup on crash

## Files Changed
- integrations/claude-code-plugin/plugin.json
- integrations/claude-code-plugin/index.ts
- integrations/claude-code-plugin/hooks.json
- integrations/claude-code-plugin/README.md

## How to Test
1. Install 6ix9ine locally
2. Install plugin via Claude Code settings
3. Start Claude session
4. Run `t69` to verify session appears in dashboard
5. End session, verify cleanup

## Checklist
- [ ] Plugin registers with daemon on start
- [ ] Cleanup on session end works
- [ ] Crash recovery works (process death)
- [ ] No hardcoded secrets
- [ ] Follows ecc/common/coding-style.md
```

**PR 2 Title:** `feat(opus): Add MCP server for multi-agent orchestration`

**PR 2 Description:**
```
## Summary
Implements MCP server allowing Aider, OpenCode, and other MCP clients to integrate with 6ix9ine.

## Architecture
- MCP protocol compliant
- Multi-client session handling
- Graceful error recovery

## Files Changed
- integrations/mcp-server/server.go
- integrations/mcp-server/handlers.go
- integrations/mcp-server/config.json
- integrations/mcp-server/README.md

## How to Test
1. Start MCP server: ./mcp-server start
2. Connect MCP client: aider --mcp-config config.json
3. Run coding session
4. Check dashboard for concurrent session tracking

## Checklist
- [ ] MCP protocol fully implemented
- [ ] Multi-client tested
- [ ] Error recovery works
- [ ] No API key exposure
```

**Gate Checks (Must all pass):**
- [ ] Code review passes (check: protocol compliance, concurrency safety, error handling)
- [ ] Integration tests pass (all 7 test cases)
- [ ] No hardcoded secrets or paths
- [ ] Follows ecc/common/coding-style.md (max 800 lines, clear naming)
- [ ] No merge conflicts, branch up to date with main
- [ ] Tests show 80%+ coverage

**Post-Approval Actions:**
- Merge both PRs to main
- Tag as v0.2-integrations
- Do not proceed to next step until explicitly told

---

## 🛑 END OF YOUR WORK

**When you're done:**
1. ✅ Both plugins implemented (Claude + MCP)
2. ✅ Integration tests passing
3. ✅ Both PRs submitted with correct titles
4. ✅ All gate checks passing
5. ✅ STOP — Do not start new work
6. ✅ Wait for merge approval

Do not:
- ❌ Add features not listed (thermal awareness, Gemini, etc. — that's ANTIGRAVITY's work)
- ❌ Refactor unrelated daemon code
- ❌ Merge to main yourself (wait for approval)
- ❌ Make assumptions if unclear on protocol or API contract
```

---

## Repeat This Structure for Other 4 Agents

Use the template above for:
- **SONNET-TASK-build.md** (Homebrew, build, release)
- **OPENCODE-TASK-cli.md** (Error handling, DeepSeek diagnostics)
- **ANTIGRAVITY-TASK-advanced.md** (Thermal, calendar, Gemini, dashboard)
- **FABLE-TASK-marketing.md** (Blog posts, social content)

---

## Shared File ALL Agents Read:

### GIT-WORKFLOW-SHARED.md

```markdown
# GIT WORKFLOW: Required for ALL Agents

**Read this first. All agents must follow these rules.**

---

## Branch Naming

```
feat/[agent-name]-[feature-name]
docs/[agent-name]-[docs-type]
fix/[agent-name]-[issue]
test/[agent-name]-[test-type]
```

**Examples:**
- feat/opus-claude-plugin-impl
- docs/sonnet-man-pages
- test/opencode-cli-tests

---

## Commit Format

```
<type>: <description>
```

**Types:** feat, fix, docs, test, chore, refactor, perf, ci

**Examples:**
- `feat: Add Claude Code plugin for 6ix9ine`
- `docs: Add man pages for 6ix9ine and t69`
- `test: Add CLI error handling tests`

---

## Before Pushing

```bash
git status                           # Verify you're on your branch
git diff main --stat                # See what you changed
git log --oneline -3                # Verify your commits
```

---

## Pushing to Remote

```bash
git push -u origin [branch-name]
```

---

## Creating PR

On GitHub:
1. Title: Copy from your task document's "PR Title" section
2. Description: Copy from your task document's "PR Description" section
3. Link your task document
4. Assign to code-reviewer for gate checks

---

## Gate Checks Required

Every PR must pass:
- ✅ Code review (security, style, architecture)
- ✅ Tests pass (80%+ coverage)
- ✅ No hardcoded secrets
- ✅ No merge conflicts
- ✅ Branch up to date with main

---

## After Approval

```bash
# Merge via GitHub UI (don't force push)
# Or locally:
git checkout main
git pull origin main
git merge [branch-name]
git push origin main
git tag v0.X-[feature] origin main
```

---

## Rules

- ❌ No `git push --force` to main
- ❌ No `git commit --amend` after push
- ❌ No hardcoded paths, secrets, credentials
- ✅ Use relative paths only
- ✅ Create new commits for review feedback (don't amend)
```

---

## Summary: 6 Files to Create

1. **OPUS-TASK-integrations.md** (copy template above, fill in OPUS details)
2. **SONNET-TASK-build.md** (copy template above, fill in SONNET details)
3. **OPENCODE-TASK-cli.md** (copy template above, fill in OPENCODE details)
4. **ANTIGRAVITY-TASK-advanced.md** (copy template above, fill in ANTIGRAVITY details)
5. **FABLE-TASK-marketing.md** (copy template above, fill in FABLE details)
6. **GIT-WORKFLOW-SHARED.md** (use template above, same for all)

---

## How to Post Work to Agents

**For OPUS:**
```
Read this: C:\...\OPUS-TASK-integrations.md
Also read: C:\...\GIT-WORKFLOW-SHARED.md

Do all tasks in OPUS-TASK-integrations.md
If not 95% confident on anything in the STOPPING CONDITIONS section, ask.
Do not proceed past the 🛑 END OF YOUR WORK marker.
```

**For SONNET, OPENCODE, ANTIGRAVITY, FABLE:** Same format, different task file.

---

## Advantages of Separate Task Files

✅ Each agent knows exactly where to stop  
✅ No cross-contamination (won't read SONNET's work if you're OPUS)  
✅ Clear "END OF YOUR WORK" boundary  
✅ Easy copy-paste to Windows terminal/chat window  
✅ Self-contained (everything they need in one file)  
✅ Hard stopping conditions explicit
