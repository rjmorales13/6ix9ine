# 6ix9ine Multi-Agent Work Orders

**Project:** 6ix9ine (macOS keep-awake daemon)  
**Status:** Ready for parallel execution  
**Coordination:** Copy each agent's work order below and submit via their respective platforms

---

## Git Workflow Rules (ALL AGENTS MUST FOLLOW)

### Branch Naming Convention
```
feat/[agent-name]-[feature-name]
fix/[agent-name]-[issue]
docs/[agent-name]-[docs-type]
```

**Examples:**
- `feat/fable-marketing-content`
- `feat/opus-integration-claude-code`
- `feat/sonnet-homebrew-formula`
- `fix/opencode-cli-issues`
- `docs/antigravity-architecture`

### Commit Message Format
```
<type>: <description>

<optional body explaining why>
```

**Types:** feat, fix, refactor, docs, test, chore, perf, ci

### PR Requirements (MANDATORY)
- Title: Clear, under 70 characters
- Description: Link to this work order, explain changes
- Branch: Must be from work order's branch name
- Review: Code review agent must pass (security + code quality)
- Tests: Where applicable, include tests
- No force-push to main; use `git merge` after approval

---

## AGENT 1: FABLE

**Role:** Marketing Content & Positioning Strategy  
**Model:** Fable  
**Output:** Blog posts, comparison content, positioning documents  
**Effort Estimate:** 12-16 hours

### Work Order: FableWO-001 - Content Marketing Foundation

**Objective:** Create blog posts and SEO content for long-tail discovery

**Tasks (In Order):**

#### Task 1: Research & Outline Comparison Post
- **File to review:** `/Users/rmorales/PycharmProjects/6ix9ine/docs/planning/STRATEGY-SUMMARY.md` (lines 1-100)
- **Research:** Compare 6ix9ine vs. LidRun, Macchiato, adrafinil on features, cost, transparency
- **Output:** Create outline document `docs/marketing/blog/comparison-outline.md`
- **Branch:** `docs/fable-marketing-content`
- **Deliverable:** Markdown outline (500 words) with structure, key points, differentiators

#### Task 2: Write Comparison Blog Post (PRIMARY)
- **Input:** Use outline from Task 1
- **File to reference:** `/Users/rmorales/PycharmProjects/6ix9ine/docs/planning/step-3-revised-critique-unified-strategy.md` (lines 80-120, "Positioning: The Core Message")
- **Write:** Blog post "Caffeinate vs. LidRun vs. Macchiato vs. 6ix9ine: Which Keep-Awake Tool Should You Use?"
- **Target:** 1200-1500 words, SEO-optimized for "keep mac awake claude code"
- **Sections:**
  - Problem statement (Mac sleep during coding)
  - Free option (caffeinate command)
  - Paid option (LidRun with cost breakdown)
  - Free alternatives (Macchiato, adrafinil with limitations)
  - 6ix9ine positioning (free + transparent + multi-agent)
  - Comparison table (features, cost, trust, support)
  - When to use each
- **Output file:** `docs/marketing/blog/keep-mac-awake-comparison.md`
- **Branch:** Same as Task 1 (`docs/fable-marketing-content`)
- **Deliverable:** Full blog post ready for Dev.to, Medium, or GitHub Pages

#### Task 3: Write Architecture/Transparency Post
- **File to review:** `/Users/rmorales/PycharmProjects/6ix9ine/README.md` (architecture section, if exists)
- **Write:** "How 6ix9ine Manages System Sleep Without Unnecessary Privilege Escalation"
- **Target:** 1000-1200 words, technical audience, explain why transparency matters
- **Sections:**
  - Problem: Why privilege escalation is risky
  - Solution: Reference-counted daemon approach
  - How 6ix9ine keeps privilege minimal (code walkthrough)
  - Why open-source for privilege escalation
  - Code snippet examples (how it works)
  - Trust & auditability for end users
- **Output file:** `docs/marketing/blog/architecture-transparency.md`
- **Branch:** `docs/fable-transparency-post`
- **Deliverable:** Technical blog post suitable for HN/Dev.to

#### Task 4: Create Social Media Content Pack
- **Input:** Use Comparison Post + Architecture Post
- **Create:** File `docs/marketing/social/twitter-threads.md`
- **Content:**
  - 5-tweet thread: Problem → Solution → Features → Transparency → CTA
  - 3 Reddit post templates (for r/macOS, r/devtools, r/programming)
  - 1 Product Hunt tagline (under 100 chars)
  - 1 Indie Hackers pitch
- **Branch:** `docs/fable-social-media`
- **Deliverable:** Ready-to-paste social content (markdown file)

### PR Submission Requirements (FABLE)

**Before submitting PR:**
- [ ] All files follow markdown formatting
- [ ] No hardcoded paths (use relative paths or {{PLACEHOLDER}})
- [ ] Blog posts tested in markdown preview
- [ ] Links verified (where applicable)

**PR Title:** `docs(fable): Add marketing content pack + comparison + architecture posts`

**PR Description Template:**
```
## Summary
Added core marketing content for 6ix9ine launch:
- Comparison blog post (vs. LidRun, Macchiato, adrafinil)
- Architecture/transparency post (trust building)
- Social media content pack (Twitter, Reddit, PH, IH)

## Files Changed
- docs/marketing/blog/keep-mac-awake-comparison.md
- docs/marketing/blog/architecture-transparency.md
- docs/marketing/social/twitter-threads.md

## Related Issues
Links to: step-3-revised-critique-unified-strategy.md positioning guidance

## Testing
- Markdown formatting validated
- SEO keywords verified: "keep mac awake claude code", "mac daemon security"
- Social content tested for character limits

## Checklist
- [ ] No hardcoded secrets
- [ ] Files use relative paths
- [ ] Markdown valid
- [ ] Content reviewed against strategy document
```

**Gate Checks Required:**
- [ ] Code review passes (security-reviewer for no secrets)
- [ ] No merge conflicts
- [ ] Branch is up to date with main

**Post-Approval:**
- Merge to main
- Tag as v0.1-marketing

---

## AGENT 2: OPUS

**Role:** System Architecture & Integration Lead  
**Model:** Opus 4.8  
**Output:** Claude Code plugin, MCP integration, multi-agent support  
**Effort Estimate:** 20-24 hours

### Work Order: OpusWO-001 - Claude Code Plugin + MCP Integration

**Objective:** Build Claude Code skill/plugin and MCP marketplace listing

**Prerequisites:**
- Review: `/Users/rmorales/PycharmProjects/6ix9ine/docs/planning/step-3-revised-critique-unified-strategy.md` (lines 110-140, "Phase 2.5: Early Ecosystem Integration")

**Tasks (In Order):**

#### Task 1: Design Claude Code Plugin Architecture
- **File to review:** `README.md` or main project docs (how 6ix9ine detects agents)
- **Design:** How Claude Code plugin should integrate with 6ix9ine
- **Output:** Architecture document `integrations/claude-code-plugin-design.md`
- **Content:**
  - Hook points (how Claude Code signals session start/end)
  - Plugin API surface
  - Error handling
  - Configuration options
- **Branch:** `feat/opus-claude-integration-design`
- **Deliverable:** Design document (technical, for review by Sonnet)

#### Task 2: Implement Claude Code Plugin
- **Input:** Use design from Task 1
- **Create:** Directory `integrations/claude-code-plugin/`
- **Files to create:**
  - `integrations/claude-code-plugin/plugin.json` (manifest)
  - `integrations/claude-code-plugin/index.ts` or `.js` (main plugin code)
  - `integrations/claude-code-plugin/hooks.json` (hook definitions)
  - `integrations/claude-code-plugin/README.md` (plugin documentation)
- **Requirements:**
  - Auto-detect Claude Code sessions
  - Register with 6ix9ine daemon
  - Clean up on session end
  - Error logging
- **Branch:** `feat/opus-claude-plugin-impl`
- **Code Quality:** Follow ecc/common/coding-style.md rules
  - Max 800 lines per file
  - Clear naming
  - No hardcoded values
- **Deliverable:** Working Claude Code plugin with tests

#### Task 3: Design MCP Marketplace Integration
- **File to review:** MCP specification (external docs, not in repo)
- **Design:** MCP server for 6ix9ine
- **Output:** `integrations/mcp-integration-design.md`
- **Content:**
  - MCP server architecture
  - Protocol handlers
  - Session lifecycle
  - Error states
- **Branch:** `feat/opus-mcp-design`
- **Deliverable:** Design document

#### Task 4: Implement MCP Server
- **Create:** Directory `integrations/mcp-server/`
- **Files:**
  - `integrations/mcp-server/server.go` or `.ts` (main implementation)
  - `integrations/mcp-server/handlers.go` or `.ts` (protocol handlers)
  - `integrations/mcp-server/config.json` (MCP manifest)
  - `integrations/mcp-server/README.md` (documentation)
- **Requirements:**
  - Implements MCP protocol
  - Works with Aider, OpenCode, other MCP clients
  - Session auto-detection
  - Graceful shutdown
- **Branch:** `feat/opus-mcp-server-impl`
- **Code Quality:** ecc standards apply
- **Deliverable:** MCP server ready for registry

#### Task 5: Integration Testing
- **Test:** Claude Code plugin + MCP server together
- **Create:** `integrations/tests/integration-test.md`
- **Manual test cases:**
  - Claude Code session detection
  - MCP client connection
  - Multi-agent concurrent sessions
  - Error scenarios (daemon crash, network loss)
- **Branch:** `feat/opus-integration-tests`
- **Deliverable:** Test report + procedures

### PR Submission Requirements (OPUS)

**Separate PRs for each integration (Claude + MCP):**

**PR 1 Title:** `feat(opus): Add Claude Code plugin for 6ix9ine`

**PR 1 Description:**
```
## Summary
Implements Claude Code plugin/skill that auto-detects Claude sessions and registers with 6ix9ine daemon.

## Architecture
- Hook-based session detection (start/stop events)
- Reference counting protocol
- Auto-cleanup on crash

## Files Changed
- integrations/claude-code-plugin/plugin.json
- integrations/claude-code-plugin/index.ts
- integrations/claude-code-plugin/hooks.json
- integrations/claude-code-plugin/README.md

## How to Test
1. Install 6ix9ine daemon locally
2. Enable plugin in Claude Code settings
3. Run `t69` dashboard to verify session tracking
4. Check logs for hook events

## Checklist
- [ ] Code follows ecc/common/coding-style.md
- [ ] No hardcoded paths
- [ ] Tests pass (if applicable)
- [ ] Plugin registers with daemon
- [ ] Cleanup on session end works
- [ ] Error handling comprehensive
```

**PR 2 Title:** `feat(opus): Add MCP server for multi-agent orchestration`

**PR 2 Description:**
```
## Summary
Implements MCP server allowing Aider, OpenCode, and other MCP clients to integrate with 6ix9ine.

## Architecture
- MCP protocol compliance
- Multi-client session handling
- Graceful degradation

## Files Changed
- integrations/mcp-server/server.go
- integrations/mcp-server/handlers.go
- integrations/mcp-server/config.json
- integrations/mcp-server/README.md
- integrations/mcp-server/tests/*.go

## How to Test
1. Start MCP server: `./mcp-server start`
2. Connect MCP client (Aider): `aider --mcp-config config.json`
3. Run session, check dashboard
4. Test concurrent clients

## Checklist
- [ ] MCP protocol fully implemented
- [ ] Multi-client tested
- [ ] Error recovery works
- [ ] Documentation complete
- [ ] No security vulnerabilities (MCP is IPC/local only)
```

**Gate Checks Required (Both PRs):**
- [ ] Code review passes (must check for: hardcoded secrets, security, protocol compliance)
- [ ] Tests pass (unit + integration if applicable)
- [ ] No merge conflicts
- [ ] Branch up to date with main

**Post-Approval:**
- Merge both PRs
- Tag as v0.2-integrations
- Publish to Claude Code marketplace (manual step, not part of PR)

---

## AGENT 3: SONNET

**Role:** Core Features & Homebrew Distribution  
**Model:** Sonnet 5  
**Output:** Homebrew formula, cross-platform support, build system  
**Effort Estimate:** 16-20 hours

### Work Order: SonnetWO-001 - Homebrew Formula + Build Optimization

**Objective:** Create production-ready Homebrew formula and optimize build

**Prerequisites:**
- Review: `/Users/rmorales/PycharmProjects/6ix9ine/docs/planning/STRATEGY-SUMMARY.md` (lines 140-180, "Phase 1: Foundation")

**Tasks (In Order):**

#### Task 1: Create Homebrew Formula
- **Language:** Ruby
- **Create file:** `Formula/6ix9ine.rb` (or `6ix9ine-keep-awake.rb` if better)
- **Requirements:**
  - Detect macOS version
  - Download latest release tarball (with SHA256 verification)
  - Install binary to `/usr/local/bin`
  - Install man pages (if any)
  - Install helper daemon to `/Library/LaunchDaemons/`
  - Post-install: register daemon with launchctl
  - Pre-uninstall: stop daemon, unregister
  - No external dependencies (keep lightweight)
- **Branch:** `feat/sonnet-homebrew-formula`
- **Testing:**
  - Test locally: `brew install ./Formula/6ix9ine.rb`
  - Test uninstall: `brew uninstall 6ix9ine`
  - Verify daemon registers/unregisters
  - Verify `t69` dashboard works post-install
- **Deliverable:** Working Homebrew formula, tested locally

**File to create:**
```
Formula/6ix9ine.rb
```

**Example structure (reference only, Sonnet to implement):**
```ruby
class SixNineKeepAwake < Formula
  desc "Keep your Mac awake while AI coding agents run"
  homepage "https://github.com/rjmorales13/6ix9ine"
  url "https://github.com/rjmorales13/6ix9ine/releases/download/v#{version}/6ix9ine-v#{version}.tar.gz"
  sha256 "COMPUTE_FROM_RELEASE"
  version "0.1.0"
  
  def install
    bin.install "6ix9ine"
    bin.install "t69"
    # etc
  end
  
  def post_install
    # Register daemon
  end
  
  service do
    # Define LaunchDaemon
  end
end
```

#### Task 2: Create Man Pages
- **Create:** `docs/man/6ix9ine.1` and `docs/man/t69.1`
- **Format:** groff/man page format (standard Unix)
- **Content:**
  - Description
  - Usage examples
  - Options/flags
  - Configuration
  - Troubleshooting
- **Branch:** `docs/sonnet-man-pages`
- **Deliverable:** Man pages installable via Homebrew

#### Task 3: Build System Optimization
- **Review file:** Project's build config (Makefile, build.sh, or equivalent)
- **Optimize:**
  - Build process for release (stripping unnecessary symbols)
  - Cross-platform build (Intel + Apple Silicon)
  - SHA256 hash computation for releases
  - Version injection into binary
- **Create/update:** Build script or Makefile
- **Branch:** `chore/sonnet-build-optimization`
- **Deliverable:** Optimized build system producing minimal, signed binaries

#### Task 4: macOS Version Compatibility Matrix
- **File to create:** `docs/compatibility.md`
- **Content:**
  - Minimum macOS version supported
  - Tested versions (10.15, 11, 12, 13, 14, 15)
  - Known limitations per version
  - Clamshell mode support per version
  - External display support per version
- **Branch:** `docs/sonnet-compatibility`
- **Deliverable:** Compatibility documentation

#### Task 5: Release Automation (Optional, if time)
- **Create:** GitHub Actions workflow for releases
- **File:** `.github/workflows/release.yml`
- **Triggers:** On tag push (v*.*.*)
- **Process:**
  - Build binaries (Intel + Apple Silicon)
  - Compute SHA256 hashes
  - Create GitHub Release with assets
  - Auto-update Homebrew formula SHA256
- **Branch:** `ci/sonnet-release-automation`
- **Deliverable:** Automated release workflow

### PR Submission Requirements (SONNET)

**PR 1 Title:** `feat(sonnet): Add production Homebrew formula for 6ix9ine`

**PR 1 Description:**
```
## Summary
Homebrew formula enabling easy installation: `brew install 6ix9ine`

## Homebrew Distribution
- Installs binary to /usr/local/bin
- Registers LaunchDaemon for auto-start
- Clean uninstall removes daemon
- No external dependencies

## Files Changed
- Formula/6ix9ine.rb
- docs/man/6ix9ine.1
- docs/man/t69.1

## Local Testing
```bash
brew install ./Formula/6ix9ine.rb
which 6ix9ine
t69  # should show dashboard
brew uninstall 6ix9ine
```

## Checklist
- [ ] Formula installs without errors
- [ ] Daemon registers on install
- [ ] Daemon unregisters on uninstall
- [ ] t69 dashboard works post-install
- [ ] Man pages render correctly
- [ ] SHA256 verified in formula
- [ ] No external deps required
```

**PR 2 Title (if applicable):** `chore(sonnet): Optimize build system for release artifacts`

**Gate Checks Required:**
- [ ] Code review passes
- [ ] Local Homebrew install test succeeds
- [ ] Daemon lifecycle (start/stop/restart) works
- [ ] No merge conflicts
- [ ] Branch up to date

**Post-Approval:**
- Merge to main
- Tag as v0.1-homebrew
- (Manual step later) Submit to Homebrew Core

---

## AGENT 4: OPENCODE

**Role:** CLI Tool Robustness & DeepSeek Integration  
**Model:** OpenCode with DeepSeek backend  
**Output:** Production CLI, error handling, documentation  
**Effort Estimate:** 18-22 hours

### Work Order: OpenCodeWO-001 - CLI Robustness + DeepSeek Features

**Objective:** Harden CLI, add DeepSeek-powered features, comprehensive help

**Prerequisites:**
- Review: Project README (main daemon functionality)
- Review: `/Users/rmorales/PycharmProjects/6ix9ine/docs/planning/STRATEGY-SUMMARY.md` (lines 240-290, "Phase 2: Early Ecosystem Moves")

**Tasks (In Order):**

#### Task 1: Audit CLI Error Handling
- **Review:** Main CLI entrypoint (e.g., `cmd/6ix9ine/main.go` or equivalent)
- **Audit:** Every error path (daemon not running, permission denied, config missing, etc.)
- **Create:** Document `docs/cli-error-scenarios.md` listing all error cases
- **Output:** Markdown file with error scenarios and proposed messages
- **Branch:** `docs/opencode-cli-audit`
- **Deliverable:** Comprehensive error scenario documentation

#### Task 2: Implement Production CLI Error Handling
- **Input:** Use audit from Task 1
- **Implement:**
  - User-friendly error messages (no stack traces in user output)
  - Helpful suggestions (e.g., "Daemon not running. Run `sudo launchctl load /Library/LaunchDaemons/...`")
  - Exit codes (0 = success, 1 = general error, 2 = permission, 3 = config, etc.)
  - Color-coded output (errors in red, warnings in yellow, success in green)
  - Verbose mode (`-v`, `-vv`) for debugging
- **Files to modify:** CLI command files
- **Branch:** `feat/opencode-cli-error-handling`
- **Code standards:** ecc/common/coding-style.md
  - Clear naming
  - No hardcoded strings (use message constants)
  - Error messages < 100 chars
- **Deliverable:** Hardened CLI with user-friendly errors

#### Task 3: Add DeepSeek-Powered Diagnostic Command
- **Concept:** `6ix9ine diagnose --analyze` uses DeepSeek to troubleshoot issues
- **Create:** CLI subcommand `diagnose`
- **Features:**
  - Collect system info (macOS version, daemon status, file permissions, etc.)
  - Query DeepSeek API with collected info
  - Return troubleshooting suggestions
  - Suggest next steps to user
- **Files to create/modify:**
  - `cmd/6ix9ine/commands/diagnose.go` (or equivalent)
  - `pkg/deepseek/client.go` (DeepSeek API wrapper)
  - `pkg/diagnostics/collector.go` (system info collection)
- **Configuration:**
  - DeepSeek API key via environment: `DEEPSEEK_API_KEY`
  - Fallback: generic troubleshooting if API unavailable
  - Cache diagnostic results for 1 hour
- **Branch:** `feat/opencode-deepseek-diagnostics`
- **Error handling:** Network errors, API errors, rate limits
- **Deliverable:** Working `6ix9ine diagnose` command with DeepSeek integration

#### Task 4: Implement Comprehensive Help & Documentation
- **Create:** `cmd/6ix9ine/commands/help.go` with detailed help system
- **Features:**
  - `6ix9ine help` (general help)
  - `6ix9ine help [command]` (command-specific help)
  - `6ix9ine examples` (usage examples)
  - `6ix9ine troubleshooting` (common issues)
  - Help text uses colors, formatting
- **Files:**
  - Update all command files to include comprehensive help text
  - Create `docs/cli-reference.md` (reference documentation)
  - Create `docs/cli-examples.md` (practical examples)
- **Branch:** `docs/opencode-cli-help`
- **Deliverable:** Comprehensive CLI help system + documentation

#### Task 5: Add Configuration File Support
- **Create:** `~/.6ix9ine/config.toml` or `.json` support
- **Configuration options:**
  - Default agent timeout
  - Log level
  - Custom session names
  - DeepSeek API key (alternative to env var)
  - Dashboard refresh rate
- **Files:**
  - `pkg/config/loader.go`
  - `pkg/config/schema.go` (type definitions)
  - `docs/configuration.md`
- **Error handling:** Missing config (use defaults), invalid config (show error and suggest fix)
- **Branch:** `feat/opencode-config-support`
- **Deliverable:** Configuration file support with documentation

#### Task 6: Create CLI Testing Suite
- **Create:** Comprehensive CLI tests
- **Files:** `cmd/6ix9ine/commands/*_test.go`
- **Test cases:**
  - Happy path (each command with valid input)
  - Error cases (missing daemon, permission denied, etc.)
  - Help output formatting
  - Config file loading and validation
- **Branch:** `test/opencode-cli-tests`
- **Coverage target:** 80%+
- **Deliverable:** CLI test suite

### PR Submission Requirements (OPENCODE)

**PR 1 Title:** `feat(opencode): Harden CLI error handling and add user-friendly messages`

**PR 1 Description:**
```
## Summary
Production-grade CLI error handling with user-friendly messages, helpful suggestions, and proper exit codes.

## Changes
- All error paths return clear, actionable messages
- Exit codes standardized (0=success, 1=general, 2=permission, 3=config)
- Verbose mode (-v, -vv) for debugging
- Color-coded output (red=error, yellow=warn, green=success)

## Files Changed
- cmd/6ix9ine/commands/*.go (all commands updated)
- pkg/cli/errors.go (new, error definitions)
- docs/cli-error-scenarios.md

## Example Error Message (Before → After)
Before: `Error: daemon not running`
After: `Error: 6ix9ine daemon is not running.
        To start it: sudo launchctl load /Library/LaunchDaemons/com.6ix9ine.daemon.plist
        Or reinstall: brew reinstall 6ix9ine`

## Testing
```bash
6ix9ine status # daemon not running
6ix9ine -v status # verbose output
6ix9ine help # shows all commands
```

## Checklist
- [ ] All errors have helpful messages
- [ ] Exit codes consistent
- [ ] Color output works in terminal
- [ ] Verbose mode helpful for debugging
- [ ] No hardcoded strings in code
- [ ] Messages are user-friendly (< 100 chars)
```

**PR 2 Title:** `feat(opencode): Add DeepSeek-powered diagnostic command`

**PR 2 Description:**
```
## Summary
New `6ix9ine diagnose --analyze` command uses DeepSeek to provide intelligent troubleshooting.

## Features
- Collects system info (macOS version, daemon status, permissions, logs)
- Queries DeepSeek API for analysis
- Returns personalized troubleshooting steps
- Graceful fallback if DeepSeek unavailable

## Configuration
- API key: DEEPSEEK_API_KEY env var
- Or in ~/.6ix9ine/config.toml: `deepseek_api_key = "..."`

## Usage
```bash
6ix9ine diagnose                    # basic system info
6ix9ine diagnose --analyze          # full analysis with DeepSeek
6ix9ine diagnose --verbose          # detailed output
```

## Files Changed
- cmd/6ix9ine/commands/diagnose.go
- pkg/deepseek/client.go
- pkg/diagnostics/collector.go
- docs/cli-reference.md

## Security
- API key never logged or printed
- Diagnostic data sanitized (no sensitive paths logged)
- DeepSeek requests are local troubleshooting only

## Checklist
- [ ] DeepSeek integration tested
- [ ] Fallback to generic help if API fails
- [ ] API key handling secure
- [ ] Diagnostic data privacy respected
- [ ] Error messages helpful
```

**PR 3 Title (if applicable):** `feat(opencode): Add comprehensive CLI help and configuration support`

**Gate Checks Required (All PRs):**
- [ ] Code review passes (security focus: API key handling)
- [ ] CLI tests pass (80%+ coverage)
- [ ] No hardcoded secrets in code
- [ ] Error messages tested with actual failures
- [ ] No merge conflicts
- [ ] Branch up to date

**Post-Approval:**
- Merge all PRs to main
- Tag as v0.3-cli-hardening

---

## AGENT 5: ANTIGRAVITY

**Role:** Advanced Features & Gemini 3.5 Intelligence  
**Model:** AntiGravity with Gemini 3.5 backend  
**Output:** Advanced scheduling, AI-powered optimization, monitoring  
**Effort Estimate:** 20-24 hours

### Work Order: AntiGravityWO-001 - Advanced Features + Gemini Integration

**Objective:** Add smart scheduling, thermal awareness, and Gemini-powered optimization

**Prerequisites:**
- Review: `/Users/rmorales/PycharmProjects/6ix9ine/docs/planning/step-3-revised-critique-unified-strategy.md` (lines 160-200, "What 6ix9ine's Real Edge Is")

**Tasks (In Order):**

#### Task 1: Design Advanced Scheduling System
- **Concept:** Intelligent sleep scheduling based on agent type, time of day, thermal state
- **Create:** Design document `docs/scheduling-system-design.md`
- **Content:**
  - Scheduling modes (always-awake, smart-schedule, calendar-aware)
  - Thermal throttling detection
  - Machine learning inputs (past behavior)
  - Configuration schema
- **Branch:** `feat/antigravity-scheduling-design`
- **Deliverable:** Architecture document for review

#### Task 2: Implement Thermal-Aware Sleep Management
- **Concept:** Don't keep Mac awake if it's overheating
- **Create:** Thermal monitoring module
- **Files:**
  - `pkg/thermal/monitor.go` (read system thermal sensors)
  - `pkg/thermal/policy.go` (thermal policies)
  - `cmd/6ix9ine/commands/thermal.go` (CLI command for thermal status)
- **Features:**
  - Poll thermal sensors every 30 seconds
  - Thermal states: cool, warm, hot, critical
  - Policy: If hot, release sleep block and alert user
  - If very hot, force sleep to protect Mac
  - Show thermal status in `t69` dashboard
- **Configuration:**
  - Thermal threshold customizable in config
  - Alert thresholds configurable
- **Branch:** `feat/antigravity-thermal-awareness`
- **Code standards:** ecc/common/coding-style.md
- **Deliverable:** Thermal monitoring with user alerts

#### Task 3: Calendar-Aware Scheduling
- **Concept:** Automatically release sleep when calendar event ends
- **Integration:** Read from macOS Calendar (local ICS files or Calendar API)
- **Files:**
  - `pkg/calendar/reader.go` (read calendar events)
  - `pkg/scheduling/calendar_scheduler.go` (schedule based on events)
- **Features:**
  - Detect "Focus Time" / "Busy" events in Calendar
  - Auto-release sleep when event ends
  - Customizable event detection (keyword matching)
  - Fallback if calendar unavailable
- **Configuration:**
  - Enable/disable calendar integration
  - Event keywords to watch
  - Grace period after event (e.g., 5 min)
- **Branch:** `feat/antigravity-calendar-scheduling`
- **Privacy:** No calendar data sent externally; all local
- **Deliverable:** Calendar-aware scheduling

#### Task 4: Gemini 3.5-Powered Optimization Advisor
- **Concept:** Gemini suggests optimal sleep policies based on usage patterns
- **Files:**
  - `pkg/gemini/client.go` (Gemini API integration)
  - `pkg/optimization/advisor.go` (usage analysis + recommendations)
  - `cmd/6ix9ine/commands/optimize.go` (CLI command)
- **Features:**
  - Collect last 7 days of session data (duration, frequency, time of day)
  - Send anonymized patterns to Gemini
  - Gemini returns optimization suggestions
  - Examples: "You code most evenings; consider auto-sleep after 11pm"
  - Cache recommendations for 24 hours
- **Security:**
  - No personally identifiable info sent to Gemini
  - Session data anonymized (timestamps only, no names)
  - User approves sending data before use
- **Configuration:**
  - Gemini API key: `GEMINI_API_KEY` env var
  - Or in config file
- **Branch:** `feat/antigravity-gemini-advisor`
- **Deliverable:** Gemini-powered optimization advisor

#### Task 5: Advanced Dashboard Extensions
- **Enhance:** `t69` dashboard with new information
- **Files:** `cmd/t69/dashboard.go` (or equivalent)
- **New displays:**
  - Thermal status (with color coding: green/yellow/red)
  - Calendar events (next 3 events shown)
  - Recommended sleep schedule (from Gemini)
  - Session history (last 10 sessions with duration)
  - Optimization score (how well optimized is current config)
- **Layout:** Add tabs or screens for different views
- **Branch:** `feat/antigravity-dashboard-extensions`
- **Deliverable:** Enhanced terminal dashboard

#### Task 6: Monitoring & Logging
- **Create:** Comprehensive logging system
- **Files:**
  - `pkg/logging/logger.go` (structured logging)
  - `docs/logging-guide.md` (how to access logs)
- **Log locations:**
  - `/var/log/6ix9ine/daemon.log` (daemon activity)
  - `~/.6ix9ine/logs/` (user-level logs)
- **What to log:**
  - Session start/stop events
  - Thermal state changes
  - Sleep blocks added/removed
  - Errors with context
  - Gemini API calls (anonymized)
- **Privacy:** No API keys or sensitive data in logs
- **Branch:** `feat/antigravity-logging`
- **Deliverable:** Structured logging with privacy

#### Task 7: Testing Advanced Features
- **Create:** Tests for all new features
- **Files:** `pkg/thermal/*_test.go`, `pkg/calendar/*_test.go`, `pkg/optimization/*_test.go`
- **Test scenarios:**
  - Thermal monitoring (mock thermal sensors)
  - Calendar integration (mock calendar data)
  - Gemini API integration (mock responses)
  - Sleep policy decisions (various thermal/calendar states)
- **Branch:** `test/antigravity-advanced-features`
- **Coverage target:** 80%+
- **Deliverable:** Comprehensive test suite

### PR Submission Requirements (ANTIGRAVITY)

**PR 1 Title:** `feat(antigravity): Add thermal-aware sleep management`

**PR 1 Description:**
```
## Summary
Prevents Mac from overheating by monitoring thermal state and releasing sleep blocks if Mac gets too hot.

## Features
- Monitors system thermal sensors every 30 seconds
- Thermal states: cool, warm, hot, critical
- Automatic sleep release if thermal threshold exceeded
- User alerts via CLI and dashboard
- Customizable thermal thresholds in config

## Files Changed
- pkg/thermal/monitor.go
- pkg/thermal/policy.go
- cmd/6ix9ine/commands/thermal.go
- cmd/t69/dashboard.go (thermal display added)

## Configuration
```toml
[thermal]
threshold_hot_celsius = 80
threshold_critical_celsius = 95
poll_interval_seconds = 30
```

## Usage
```bash
6ix9ine thermal status          # current thermal state
t69                              # dashboard shows thermal status with color
```

## Testing
- Tested on Mac with various CPU loads
- Thermal sensors successfully polled
- Sleep blocks properly released on high temps

## Checklist
- [ ] Thermal sensors detected on host Mac
- [ ] Thresholds configurable
- [ ] Dashboard shows thermal state clearly
- [ ] Sleep block released properly on hot
- [ ] User gets alert notifications
- [ ] No excessive polling (30s intervals)
```

**PR 2 Title:** `feat(antigravity): Add calendar-aware sleep scheduling`

**PR 2 Description:**
```
## Summary
Integrates with macOS Calendar to auto-release sleep when calendar events end.

## Features
- Reads local macOS Calendar events
- Detects "Focus Time" / "Busy" events
- Auto-releases sleep when event ends
- Configurable event keywords
- Fallback to manual control if calendar unavailable

## Files Changed
- pkg/calendar/reader.go
- pkg/scheduling/calendar_scheduler.go
- cmd/t69/dashboard.go (next calendar events shown)

## Configuration
```toml
[calendar]
enabled = true
event_keywords = ["Focus", "Busy", "Deep Work"]
grace_period_minutes = 5
```

## Privacy
- All calendar data processed locally
- No calendar data sent to external services
- User consent required before calendar access

## Testing
- Tested with sample calendar events
- Auto-release trigger verified
- Grace period works correctly

## Checklist
- [ ] Calendar reading works
- [ ] Event detection accurate
- [ ] Sleep release triggered at event end
- [ ] Privacy respected (no external calls)
- [ ] Fallback works if calendar unavailable
```

**PR 3 Title:** `feat(antigravity): Add Gemini 3.5-powered optimization advisor`

**PR 3 Description:**
```
## Summary
Analyzes usage patterns and uses Gemini 3.5 to suggest optimal sleep policies.

## Features
- Collects anonymized session data (7-day history)
- Sends patterns to Gemini for analysis
- Returns personalized optimization recommendations
- Caches recommendations for 24 hours
- Dashboard shows current optimization score

## Configuration
```toml
[gemini]
api_key = "your-api-key"  # or use GEMINI_API_KEY env var
enabled = true
analysis_frequency_days = 7
cache_duration_hours = 24
```

## Privacy & Security
- No personally identifiable info sent to Gemini
- Session data anonymized (timestamps only)
- API key never logged or printed
- User opt-in required before sending data

## Usage
```bash
6ix9ine optimize --advice           # get recommendations
6ix9ine optimize --history          # show analysis data
t69                                  # dashboard shows optimization score
```

## Example Recommendations
- "You code most evenings 6-10pm; consider auto-sleep after 11pm"
- "Weekend sessions are 2x longer; increase thermal threshold"
- "Schedule deep work on Mondays; enable calendar integration"

## Testing
- Mocked Gemini API responses
- Anonymization verified
- Recommendations validated for usefulness

## Checklist
- [ ] Gemini API integration works
- [ ] Data anonymization complete
- [ ] Recommendations useful and actionable
- [ ] No API key exposure
- [ ] Caching works properly
- [ ] Fallback if Gemini unavailable
```

**PR 4 Title:** `feat(antigravity): Enhance dashboard with advanced features`

**Gate Checks Required (All PRs):**
- [ ] Code review passes (security focus: thermal/calendar/Gemini privacy)
- [ ] Tests pass (80%+ coverage)
- [ ] No API keys hardcoded
- [ ] Anonymization verified (Gemini integration)
- [ ] Dashboard readable with new features
- [ ] No merge conflicts
- [ ] Branch up to date

**Post-Approval:**
- Merge all PRs to main
- Tag as v0.4-advanced-features

---

## Coordination & Merge Order

**Merge sequence (maintain compatibility):**

1. **FABLE** → Marketing content (no code conflicts)
2. **SONNET** → Homebrew formula (provides distribution)
3. **OPUS** → Integrations (adds Claude/MCP support)
4. **OPENCODE** → CLI hardening (improves UX)
5. **ANTIGRAVITY** → Advanced features (extends capabilities)

**Final merge:**
- Create release tag: `v0.5-launch-ready`
- Prepare Product Hunt assets
- Announce on Reddit, Indie Hackers, HN

---

## Testing Checklist (Before Release)

- [ ] All 5 agent PRs merged to main
- [ ] `brew install ./Formula/6ix9ine.rb` works locally
- [ ] `t69` dashboard displays all features
- [ ] Claude Code plugin detected in Claude
- [ ] MCP server connects to Aider
- [ ] DeepSeek diagnostic works (with DEEPSEEK_API_KEY set)
- [ ] Thermal monitoring polling at correct intervals
- [ ] Calendar integration reads events
- [ ] Gemini advisor provides recommendations
- [ ] All error paths tested (daemon down, permission denied, etc.)
- [ ] Logs don't contain API keys
- [ ] Man pages render correctly
- [ ] Uninstall cleanly removes daemon

---

## Emergency Contacts

If agent encounters blockers:

- **FABLE** (marketing): Unclear positioning → refer to step-3-revised-critique-unified-strategy.md
- **OPUS** (integrations): API docs missing → use project README or contact project maintainer
- **SONNET** (build): Binary size too large → optimize with `-ldflags "-s -w"`
- **OPENCODE** (CLI): Permission issues → use `sudo` for LaunchDaemon operations
- **ANTIGRAVITY** (advanced): Thermal sensors not found → fallback to generic mode

---

## Success = All PRs Merged + Release v0.5

After all agents complete work:
- [ ] Product Hunt launch scheduled
- [ ] Blog content published
- [ ] Homebrew formula ready for submission
- [ ] GitHub release prepared with binaries
- [ ] Documentation complete
- [ ] Community channels (Reddit, Aider, Indie Hackers) prepared for launch

**Target launch date:** 4 weeks from now

---
