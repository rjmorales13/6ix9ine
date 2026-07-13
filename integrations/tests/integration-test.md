# Integration Tests

## Prerequisites

- 6ix9ine installed and daemon running
- Node.js 18+
- npm

## Test Suites

### MCP Server

```bash
cd integrations/mcp-server
npm install

# Unit tests
npm test

# Manual TCP smoke test
SIXNINE_MCP_PORT=9100 npm start &
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | nc 127.0.0.1 9100
kill %1
```

### Claude Code Plugin

```bash
cd integrations/claude-code-plugin
npm install

# Unit tests
npm test

# Integration: install hooks
npm run install:plugin

# Verify hooks present
python3 -c "
import json
s = json.load(open(os.path.expanduser('~/.claude/settings.json')))
h = s.get('hooks', {})
assert 'UserPromptSubmit' in h, 'Missing UserPromptSubmit'
assert 'Stop' in h, 'Missing Stop'
print('hooks verified')
"

# Integration: uninstall hooks
npm run uninstall:plugin
```

## Test Cases

| # | Test | Automated | Type |
|---|------|-----------|------|
| 1 | MCP protocol initialize | jest | unit |
| 2 | MCP tool list contains 4 tools | jest | unit |
| 3 | MCP acquire requires session_id | jest | unit |
| 4 | MCP acquire calls daemon socket | jest | unit |
| 5 | MCP release calls daemon socket | jest | unit |
| 6 | MCP status returns daemon state | jest | unit |
| 7 | MCP hold validates required args | jest | unit |
| 8 | MCP release handles not-found gracefully | jest | unit |
| 9 | Plugin manifest valid | jest | unit |
| 10 | Plugin calls acquire on prompt submit | jest | unit |
| 11 | Plugin calls release on stop | jest | unit |
| 12 | Plugin swallows daemon errors | jest | unit |
| 13 | Plugin no-op when daemon unreachable | jest | unit |
| 14 | Plugin handles empty session_id | jest | unit |

## Gate Check

- [ ] All unit tests pass (npm test in both directories)
- [ ] No shell execution in daemon communication path
- [ ] MCP protocol version 2025-03-26 compliance verified
- [ ] Plugin hooks install/uninstall verified on real settings.json
- [ ] No hardcoded secrets in any file
- [ ] Branches up to date with main
