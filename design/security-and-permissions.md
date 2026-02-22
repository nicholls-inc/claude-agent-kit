# Security and Permissions (CC Plugin)

## Threat Model

This plugin runs hook scripts locally on the user's machine. Key risks:
- Prompt injection via hook input JSON.
- Command injection via unsafe shell interpolation.
- Secret exfiltration through network tools.
- Hook output corruption (non-JSON stdout when JSON is expected).

## Guardrail Principles

1. Treat hook stdin JSON as untrusted.
2. Never `eval` any content derived from hook input.
3. For decision hooks, write only JSON to stdout (or only plain text for context-injection hooks).
4. Fail open on state parse errors in continuation hooks.

## Recommended Permissions Posture

Baseline:
- Allow: Read/Grep/Glob/LSP.
- Ask: Bash/Edit/Write/WebFetch/MCP.
- Deny: known-destructive Bash patterns.

## Recommended `.claude/settings.json` Snippet (documented only)

This is a conceptual template; exact schema may vary by CC version.

```json
{
  "permissions": {
    "deny": [
      {"tool": "Bash", "pattern": "(?i)\\brm\\s+-rf\\b"},
      {"tool": "Bash", "pattern": "(?i)\\bmkfs\\b|\\bdd\\s+if="}
    ],
    "ask": [
      {"tool": "Bash"},
      {"tool": "Edit"},
      {"tool": "Write"},
      {"tool": "WebFetch"},
      {"tool": "mcp__.*"}
    ],
    "allow": [
      {"tool": "Read"},
      {"tool": "Grep"},
      {"tool": "Glob"}
    ]
  }
}
```

## Hook Script Hardening Requirements

All command hooks should:
- use `set -euo pipefail`
- parse stdin with `jq -e` and safe defaults
- avoid printing debug logs to stdout

## Continuation Safety

Stop-hook continuation requires:
- circuit breakers (max blocks, cooldown)
- global escape hatch (`/omo:stop-continuation`)
- fail-open on corruption
