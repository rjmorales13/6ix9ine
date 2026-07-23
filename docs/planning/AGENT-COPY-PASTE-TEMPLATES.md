# 6ix9ine Work Orders: Copy-Paste Templates for Windows

Copy each template below to your agent's interface. Replace {{PLACEHOLDER}} with values as needed.

---

## TEMPLATE 1: FABLE - Marketing Content (Copy-Paste Ready)

```
PROJECT: 6ix9ine Marketing Content Foundation
MODEL: Fable
BRANCH PREFIX: docs/fable-marketing-content

WORK ORDER ID: FableWO-001

FILES TO REVIEW (Windows paths):
- C:\Users\{{USERNAME}}\PycharmProjects\6ix9ine\docs\sharing-is-good\STRATEGY-SUMMARY.md (lines 1-100)
- C:\Users\{{USERNAME}}\PycharmProjects\6ix9ine\docs\sharing-is-good\step-3-revised-critique-unified-strategy.md (lines 80-120)

TASK 1: Research & Outline Comparison Post
- Create file: blog-posts\comparison-outline.md
- Content: Markdown outline (500 words) comparing 6ix9ine vs LidRun, Macchiato, adrafinil
- Branch: docs/fable-marketing-content
- Deliverable: Outline structure ready for blog post

TASK 2: Write Comparison Blog Post (PRIMARY)
- Create file: blog-posts\keep-mac-awake-comparison.md
- Length: 1200-1500 words
- Target keyword: "keep mac awake claude code"
- Sections: Problem, Free option (caffeinate), Paid (LidRun), Free alternatives, 6ix9ine, Comparison table, When to use each
- Branch: docs/fable-marketing-content
- Publish on: Dev.to, Medium, or GitHub Pages

TASK 3: Write Architecture/Transparency Post
- Create file: blog-posts\architecture-transparency.md
- Length: 1000-1200 words
- Audience: Technical (HN, Dev.to)
- Sections: Why privilege escalation is risky, Reference-counted daemon approach, Code walkthrough, Why open-source, Code snippets, Trust & auditability
- Branch: docs/fable-transparency-post

TASK 4: Create Social Media Content Pack
- Create file: social-media\twitter-threads.md
- Content:
  * 5-tweet thread (Problem → Solution → Features → Transparency → CTA)
  * 3 Reddit post templates (r/macOS, r/devtools, r/programming)
  * 1 Product Hunt tagline (< 100 chars)
  * 1 Indie Hackers pitch
- Branch: docs/fable-social-media

PR SUBMISSION REQUIREMENTS:
- Title: docs(fable): Add marketing content pack + comparison + architecture posts
- Description must include: Summary, Files Changed, Testing (markdown validation, links verified), Checklist (no secrets, valid markdown, SEO keywords verified)
- Gate checks: Code review passes, no merge conflicts, branch up to date with main
- Post-merge tag: v0.1-marketing

GIT WORKFLOW:
Branch naming: docs/fable-[feature-name]
Commit format: docs: <description>
No force-push to main; use git merge after approval
```

---

## TEMPLATE 2: OPUS - System Architecture & Integrations (Copy-Paste Ready)

```
PROJECT: 6ix9ine Claude Code Plugin + MCP Server
MODEL: Opus 4.8
BRANCH PREFIX: feat/opus-[feature]

WORK ORDER ID: OpusWO-001

FILES TO REVIEW (Windows paths):
- C:\Users\{{USERNAME}}\PycharmProjects\6ix9ine\README.md (architecture section)
- C:\Users\{{USERNAME}}\PycharmProjects\6ix9ine\docs\sharing-is-good\step-3-revised-critique-unified-strategy.md (lines 110-140)

TASK 1: Design Claude Code Plugin Architecture
- Create file: integrations\claude-code-plugin-design.md
- Content: Hook points, plugin API, error handling, configuration
- Branch: feat/opus-claude-integration-design
- Deliverable: Design document for review

TASK 2: Implement Claude Code Plugin
- Create directory: integrations\claude-code-plugin\
- Files:
  * integrations\claude-code-plugin\plugin.json (manifest)
  * integrations\claude-code-plugin\index.ts (main plugin)
  * integrations\claude-code-plugin\hooks.json (hook definitions)
  * integrations\claude-code-plugin\README.md (documentation)
- Requirements: Auto-detect Claude sessions, register with daemon, cleanup on end
- Branch: feat/opus-claude-plugin-impl
- Testing: Local install, verify registration, verify cleanup
- Code standards: Max 800 lines per file, clear naming, no hardcoded values

TASK 3: Design MCP Marketplace Integration
- Create file: integrations\mcp-integration-design.md
- Content: MCP server architecture, protocol handlers, session lifecycle
- Branch: feat/opus-mcp-design
- Deliverable: Design document

TASK 4: Implement MCP Server
- Create directory: integrations\mcp-server\
- Files:
  * integrations\mcp-server\server.go (or .ts)
  * integrations\mcp-server\handlers.go (protocol handlers)
  * integrations\mcp-server\config.json (MCP manifest)
  * integrations\mcp-server\README.md (documentation)
- Requirements: MCP protocol compliant, multi-client support, session auto-detection, graceful shutdown
- Branch: feat/opus-mcp-server-impl
- Testing: MCP client connection, multi-agent sessions, error scenarios

TASK 5: Integration Testing
- Create file: integrations\tests\integration-test.md
- Test cases: Claude detection, MCP connection, concurrent sessions, error scenarios
- Branch: feat/opus-integration-tests
- Deliverable: Test procedures and report

PR SUBMISSIONS (2 separate PRs):

PR #1 - Claude Code Plugin
- Title: feat(opus): Add Claude Code plugin for 6ix9ine
- Description: Link to FableWO-001, explain hook-based detection, reference counting, auto-cleanup
- Files: integrations\claude-code-plugin\*
- Testing steps: Install plugin, run t69 dashboard, verify session tracking

PR #2 - MCP Server
- Title: feat(opus): Add MCP server for multi-agent orchestration
- Description: Explain MCP protocol compliance, multi-client handling
- Files: integrations\mcp-server\*
- Testing steps: Start server, connect MCP client (Aider), verify session handling

Gate checks (both PRs):
- [ ] Code review passes (check for hardcoded secrets, protocol compliance)
- [ ] Tests pass (unit + integration)
- [ ] No merge conflicts, branch up to date
- Post-merge tag: v0.2-integrations

GIT WORKFLOW:
Branch naming: feat/opus-[feature-name]
Commit format: feat: <description>
No force-push; use git merge
```

---

## TEMPLATE 3: SONNET - Homebrew & Build System (Copy-Paste Ready)

```
PROJECT: 6ix9ine Homebrew Formula + Build Optimization
MODEL: Sonnet 5
BRANCH PREFIX: feat/sonnet-[feature]

WORK ORDER ID: SonnetWO-001

FILES TO REVIEW (Windows paths):
- C:\Users\{{USERNAME}}\PycharmProjects\6ix9ine\docs\sharing-is-good\STRATEGY-SUMMARY.md (lines 140-180)

TASK 1: Create Homebrew Formula
- Create file: Formula\6ix9ine.rb
- Language: Ruby
- Requirements:
  * Detect macOS version
  * Download release tarball with SHA256 verification
  * Install binary to /usr/local/bin
  * Install man pages
  * Install helper daemon to /Library/LaunchDaemons/
  * Post-install: register daemon with launchctl
  * Pre-uninstall: stop daemon, unregister
  * No external dependencies (lightweight)
- Branch: feat/sonnet-homebrew-formula
- Testing: Local install (brew install ./Formula/6ix9ine.rb), verify daemon, test uninstall
- Deliverable: Working formula tested locally

TASK 2: Create Man Pages
- Create files:
  * docs\man\6ix9ine.1 (groff/man format)
  * docs\man\t69.1
- Content: Description, usage examples, options, configuration, troubleshooting
- Branch: docs/sonnet-man-pages
- Deliverable: Man pages installable via Homebrew

TASK 3: Build System Optimization
- Create/update: Build script or Makefile
- Optimize:
  * Release build (strip unnecessary symbols)
  * Cross-platform (Intel + Apple Silicon)
  * SHA256 hash computation
  * Version injection into binary
- Branch: chore/sonnet-build-optimization
- Deliverable: Optimized build system

TASK 4: macOS Compatibility Matrix
- Create file: docs\compatibility.md
- Content:
  * Minimum macOS version
  * Tested versions (10.15, 11, 12, 13, 14, 15)
  * Known limitations per version
  * Clamshell mode support
  * External display support
- Branch: docs/sonnet-compatibility
- Deliverable: Compatibility documentation

TASK 5: Release Automation (Optional)
- Create file: .github\workflows\release.yml
- GitHub Actions workflow:
  * Trigger: On tag push (v*.*.*)
  * Build binaries (Intel + Apple Silicon)
  * Compute SHA256 hashes
  * Create GitHub Release with assets
  * Auto-update Homebrew formula SHA256
- Branch: ci/sonnet-release-automation
- Deliverable: Automated release workflow

PR SUBMISSION:
- Title: feat(sonnet): Add production Homebrew formula for 6ix9ine
- Description: Explain distribution strategy, testing results, no external deps
- Files Changed: Formula\6ix9ine.rb, docs\man\*, docs\compatibility.md
- Testing: Provide brew install commands, verify daemon registration
- Checklist: Install without errors, daemon registers/unregisters, t69 works, man pages render

Gate checks:
- [ ] Code review passes
- [ ] Local Homebrew install test succeeds
- [ ] Daemon lifecycle works (start/stop/restart)
- [ ] No merge conflicts, branch up to date
- Post-merge tag: v0.1-homebrew

GIT WORKFLOW:
Branch naming: feat/sonnet-[feature-name] or docs/sonnet-[docs]
Commit format: feat/docs: <description>
No force-push; merge via PR
```

---

## TEMPLATE 4: OPENCODE - CLI Robustness with DeepSeek (Copy-Paste Ready)

```
PROJECT: 6ix9ine CLI Hardening + DeepSeek Diagnostics
MODEL: OpenCode with DeepSeek backend
BRANCH PREFIX: feat/opencode-[feature]

WORK ORDER ID: OpenCodeWO-001

FILES TO REVIEW (Windows paths):
- C:\Users\{{USERNAME}}\PycharmProjects\6ix9ine\README.md (main daemon functionality)
- C:\Users\{{USERNAME}}\PycharmProjects\6ix9ine\docs\sharing-is-good\STRATEGY-SUMMARY.md (lines 240-290)

TASK 1: Audit CLI Error Handling
- Review main CLI entrypoint (cmd\6ix9ine\main.go or equivalent on Windows)
- Audit all error paths: daemon not running, permission denied, config missing, etc.
- Create file: docs\cli-error-scenarios.md
- Branch: docs/opencode-cli-audit
- Deliverable: Comprehensive error scenario documentation

TASK 2: Implement Production CLI Error Handling
- Files to modify: CLI command files
- Implement:
  * User-friendly error messages (no stack traces)
  * Helpful suggestions for each error
  * Exit codes (0=success, 1=general, 2=permission, 3=config)
  * Color-coded output (red=error, yellow=warn, green=success)
  * Verbose mode (-v, -vv) for debugging
- Code standards: Clear naming, no hardcoded strings (use constants)
- Branch: feat/opencode-cli-error-handling
- Deliverable: Hardened CLI

TASK 3: Add DeepSeek-Powered Diagnostic Command
- Concept: 6ix9ine diagnose --analyze uses DeepSeek for troubleshooting
- Create CLI subcommand: diagnose
- Files to create:
  * cmd\6ix9ine\commands\diagnose.go (or .ts)
  * pkg\deepseek\client.go (DeepSeek API wrapper)
  * pkg\diagnostics\collector.go (system info collection)
- Features:
  * Collect system info (macOS version, daemon status, permissions)
  * Query DeepSeek API with collected info
  * Return troubleshooting suggestions
  * Fallback if API unavailable
- Configuration: DEEPSEEK_API_KEY environment variable
- Branch: feat/opencode-deepseek-diagnostics
- Error handling: Network errors, API errors, rate limits
- Deliverable: Working diagnose command

TASK 4: Implement Comprehensive Help System
- Create file: cmd\6ix9ine\commands\help.go
- Features:
  * 6ix9ine help (general)
  * 6ix9ine help [command] (command-specific)
  * 6ix9ine examples (usage examples)
  * 6ix9ine troubleshooting (common issues)
- Create documentation files:
  * docs\cli-reference.md
  * docs\cli-examples.md
- Branch: docs/opencode-cli-help
- Deliverable: Help system + documentation

TASK 5: Add Configuration File Support
- Support: ~/.6ix9ine/config.toml or .json
- Configuration options:
  * Default agent timeout
  * Log level
  * Custom session names
  * DeepSeek API key (alternative to env var)
  * Dashboard refresh rate
- Files to create:
  * pkg\config\loader.go
  * pkg\config\schema.go (type definitions)
  * docs\configuration.md
- Branch: feat/opencode-config-support
- Deliverable: Configuration file support

TASK 6: Create CLI Testing Suite
- Create files: cmd\6ix9ine\commands\*_test.go
- Test cases:
  * Happy path (each command with valid input)
  * Error cases (missing daemon, permission denied)
  * Help output formatting
  * Config file loading and validation
- Branch: test/opencode-cli-tests
- Coverage target: 80%+
- Deliverable: CLI test suite

PR SUBMISSIONS (Multiple):

PR #1 - Error Handling
- Title: feat(opencode): Harden CLI error handling and add user-friendly messages
- Files: cmd\6ix9ine\commands\*.go, pkg\cli\errors.go
- Example: Show before/after error messages
- Checklist: All errors have helpful messages, exit codes consistent, color output works

PR #2 - DeepSeek Diagnostics
- Title: feat(opencode): Add DeepSeek-powered diagnostic command
- Files: cmd\6ix9ine\commands\diagnose.go, pkg\deepseek\*, pkg\diagnostics\*
- Security: API key never logged, diagnostic data sanitized
- Checklist: DeepSeek integration tested, fallback works, API key secure

PR #3 - Help & Config
- Title: feat(opencode): Add comprehensive CLI help and configuration support
- Files: cmd\6ix9ine\commands\help.go, pkg\config\*
- Deliverables: Help system, configuration docs

Gate checks (all PRs):
- [ ] Code review passes (security focus: API key handling)
- [ ] CLI tests pass (80%+ coverage)
- [ ] No hardcoded secrets in code
- [ ] Error messages tested with actual failures
- [ ] No merge conflicts, branch up to date
- Post-merge tag: v0.3-cli-hardening

GIT WORKFLOW:
Branch naming: feat/opencode-[feature] or docs/opencode-[docs]
Commit format: feat/docs: <description>
No force-push; merge via PR
```

---

## TEMPLATE 5: ANTIGRAVITY - Advanced Features with Gemini (Copy-Paste Ready)

```
PROJECT: 6ix9ine Advanced Features + Gemini 3.5 Integration
MODEL: AntiGravity with Gemini 3.5 backend
BRANCH PREFIX: feat/antigravity-[feature]

WORK ORDER ID: AntiGravityWO-001

FILES TO REVIEW (Windows paths):
- C:\Users\{{USERNAME}}\PycharmProjects\6ix9ine\docs\sharing-is-good\step-3-revised-critique-unified-strategy.md (lines 160-200)

TASK 1: Design Advanced Scheduling System
- Create file: docs\scheduling-system-design.md
- Content:
  * Scheduling modes (always-awake, smart-schedule, calendar-aware)
  * Thermal throttling detection
  * Machine learning inputs (past behavior)
  * Configuration schema
- Branch: feat/antigravity-scheduling-design
- Deliverable: Architecture document

TASK 2: Implement Thermal-Aware Sleep Management
- Concept: Don't keep Mac awake if overheating
- Files to create:
  * pkg\thermal\monitor.go (read thermal sensors)
  * pkg\thermal\policy.go (thermal policies)
  * cmd\6ix9ine\commands\thermal.go (CLI thermal status)
- Features:
  * Poll thermal sensors every 30 seconds
  * Thermal states: cool, warm, hot, critical
  * Release sleep block if hot
  * Force sleep if critical
  * Show status in t69 dashboard
- Configuration:
  * Thermal threshold (customizable)
  * Alert thresholds
- Branch: feat/antigravity-thermal-awareness
- Deliverable: Thermal monitoring

TASK 3: Calendar-Aware Scheduling
- Concept: Auto-release sleep when calendar event ends
- Files to create:
  * pkg\calendar\reader.go (read calendar events)
  * pkg\scheduling\calendar_scheduler.go (schedule based on events)
- Features:
  * Detect "Focus Time" / "Busy" events
  * Auto-release sleep when event ends
  * Customizable event detection
  * Fallback if calendar unavailable
- Configuration:
  * Enable/disable calendar integration
  * Event keywords to watch
  * Grace period after event
- Privacy: No calendar data sent externally
- Branch: feat/antigravity-calendar-scheduling
- Deliverable: Calendar-aware scheduling

TASK 4: Gemini 3.5-Powered Optimization Advisor
- Concept: Gemini analyzes usage patterns and suggests optimal sleep policies
- Files to create:
  * pkg\gemini\client.go (Gemini API integration)
  * pkg\optimization\advisor.go (usage analysis + recommendations)
  * cmd\6ix9ine\commands\optimize.go (CLI command)
- Features:
  * Collect last 7 days of session data
  * Send anonymized patterns to Gemini
  * Get optimization suggestions
  * Cache recommendations for 24 hours
- Example recommendations:
  * "You code evenings 6-10pm; auto-sleep after 11pm"
  * "Weekend sessions 2x longer; increase thermal threshold"
- Security:
  * No PII sent to Gemini
  * Data anonymized (timestamps only)
  * User approval before sending
- Configuration:
  * Gemini API key: GEMINI_API_KEY env var or config file
- Branch: feat/antigravity-gemini-advisor
- Deliverable: Gemini-powered advisor

TASK 5: Advanced Dashboard Extensions
- Enhance: t69 dashboard (cmd\t69\dashboard.go)
- New displays:
  * Thermal status (color: green/yellow/red)
  * Calendar events (next 3)
  * Recommended schedule (from Gemini)
  * Session history (last 10 sessions)
  * Optimization score
- Layout: Add tabs or screens
- Branch: feat/antigravity-dashboard-extensions
- Deliverable: Enhanced dashboard

TASK 6: Monitoring & Logging
- Create: Structured logging system
- Files to create:
  * pkg\logging\logger.go
  * docs\logging-guide.md
- Log locations:
  * /var/log/6ix9ine/daemon.log (daemon)
  * ~/.6ix9ine/logs/ (user level)
- What to log:
  * Session start/stop
  * Thermal state changes
  * Sleep blocks added/removed
  * Errors with context
  * Gemini API calls (anonymized)
- Privacy: No API keys in logs
- Branch: feat/antigravity-logging
- Deliverable: Structured logging

TASK 7: Testing Advanced Features
- Create files: pkg\thermal\*_test.go, pkg\calendar\*_test.go, pkg\optimization\*_test.go
- Test scenarios:
  * Thermal monitoring (mock sensors)
  * Calendar integration (mock data)
  * Gemini API (mock responses)
  * Sleep policy decisions (various states)
- Branch: test/antigravity-advanced-features
- Coverage target: 80%+
- Deliverable: Test suite

PR SUBMISSIONS (Multiple):

PR #1 - Thermal Awareness
- Title: feat(antigravity): Add thermal-aware sleep management
- Files: pkg\thermal\*, cmd\6ix9ine\commands\thermal.go
- Checklist: Sensors detected, thresholds configurable, dashboard shows status, sleep released properly

PR #2 - Calendar Scheduling
- Title: feat(antigravity): Add calendar-aware sleep scheduling
- Files: pkg\calendar\*, pkg\scheduling\calendar_scheduler.go
- Privacy: All local, no external calls, user consent
- Checklist: Calendar reading works, events detected, auto-release triggered

PR #3 - Gemini Advisor
- Title: feat(antigravity): Add Gemini 3.5-powered optimization advisor
- Files: pkg\gemini\*, pkg\optimization\*, cmd\6ix9ine\commands\optimize.go
- Security: No API key exposure, data anonymized
- Example: Show sample recommendations from Gemini
- Checklist: API integration works, anonymization complete, caching works, fallback if unavailable

PR #4 - Dashboard & Logging
- Title: feat(antigravity): Enhance dashboard and add comprehensive logging
- Files: cmd\t69\dashboard.go, pkg\logging\*
- Checklist: Dashboard readable, thermal color-coded, calendar events shown, logs don't contain API keys

Gate checks (all PRs):
- [ ] Code review passes (security: thermal, calendar, Gemini privacy)
- [ ] Tests pass (80%+ coverage)
- [ ] No API keys hardcoded
- [ ] Anonymization verified (Gemini)
- [ ] Dashboard readable with new features
- [ ] No merge conflicts, branch up to date
- Post-merge tag: v0.4-advanced-features

GIT WORKFLOW:
Branch naming: feat/antigravity-[feature-name]
Commit format: feat: <description>
No force-push; merge via PR
```

---

## WINDOWS-SPECIFIC NOTES

1. **File paths:** Replace `C:\Users\{{USERNAME}}\` with your actual Windows username
2. **Git commands:** All git commands work identically on Windows (Git Bash or PowerShell with git)
3. **Line endings:** Ensure `.gitattributes` has `* text=auto` to handle Windows/Unix line endings
4. **Environment variables:** Use `set DEEPSEEK_API_KEY=your-key` (Command Prompt) or `$env:DEEPSEEK_API_KEY = "your-key"` (PowerShell)
5. **Directory separators:** Windows uses `\` but git commands accept both `/` and `\`

---

## MERGE ORDER & FINAL CHECKS

After all agents complete and PRs are approved:

1. Merge FABLE → v0.1-marketing
2. Merge SONNET → v0.1-homebrew
3. Merge OPUS → v0.2-integrations
4. Merge OPENCODE → v0.3-cli-hardening
5. Merge ANTIGRAVITY → v0.4-advanced-features
6. Create final tag: v0.5-launch-ready

Final checklist before release:
- [ ] All PRs merged to main
- [ ] brew install ./Formula/6ix9ine.rb works
- [ ] t69 dashboard displays all features
- [ ] All tests pass
- [ ] No API keys in logs
- [ ] Documentation complete
- [ ] Product Hunt assets ready
