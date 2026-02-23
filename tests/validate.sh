#!/usr/bin/env bash

set -euo pipefail

# Validation test suite for claude-agent-kit plugin structure.
# Checks frontmatter contracts, JSON validity, cross-references, and scripts.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

passes=0
failures=0
warnings=0

pass() {
  printf '  \033[32mPASS\033[0m %s\n' "$1"
  passes=$((passes + 1))
}

fail() {
  printf '  \033[31mFAIL\033[0m %s\n' "$1"
  failures=$((failures + 1))
}

warn() {
  printf '  \033[33mWARN\033[0m %s\n' "$1"
  warnings=$((warnings + 1))
}

# Extract a frontmatter field value from a file.
# Usage: get_field <file> <field>
get_field() {
  local file="$1" field="$2"
  sed -n '/^---$/,/^---$/p' "$file" | grep -i "^${field}:" | head -1 | sed "s/^${field}:[[:space:]]*//" || true
}

# Check that a file has valid frontmatter delimiters.
has_frontmatter() {
  local file="$1"
  local count
  count=$(grep -c '^---$' "$file" 2>/dev/null || true)
  [ "$count" -ge 2 ]
}

# Get body after frontmatter (everything after the second --- line).
get_body() {
  local file="$1"
  awk 'BEGIN{n=0} /^---$/{n++; next} n>=2' "$file"
}

# ─── Agent frontmatter ────────────────────────────────────────────────

printf '\n\033[1m=== Agent frontmatter (agents/*.md) ===\033[0m\n'

for agent_file in "$ROOT_DIR"/agents/*.md; do
  basename="$(basename "$agent_file")"

  # Has frontmatter delimiters
  if has_frontmatter "$agent_file"; then
    pass "$basename: has frontmatter delimiters"
  else
    fail "$basename: missing frontmatter delimiters (---)"
    continue
  fi

  # Required fields
  for field in name description model tools maxTurns; do
    value="$(get_field "$agent_file" "$field")"
    if [ -n "$value" ]; then
      pass "$basename: has '$field' field"
    else
      fail "$basename: missing required field '$field'"
    fi
  done

  # model is valid
  model="$(get_field "$agent_file" model)"
  if echo "$model" | grep -qiE '^(haiku|sonnet|opus)$'; then
    pass "$basename: model '$model' is valid"
  else
    fail "$basename: model '$model' is not one of haiku/sonnet/opus"
  fi

  # maxTurns is a positive integer
  max_turns="$(get_field "$agent_file" maxTurns)"
  if echo "$max_turns" | grep -qE '^[1-9][0-9]*$'; then
    pass "$basename: maxTurns '$max_turns' is a positive integer"
  else
    fail "$basename: maxTurns '$max_turns' is not a positive integer"
  fi

  # Body is non-empty
  body="$(get_body "$agent_file")"
  if [ -n "$(echo "$body" | tr -d '[:space:]')" ]; then
    pass "$basename: body is non-empty"
  else
    fail "$basename: body is empty"
  fi
done

# ─── Skill frontmatter ────────────────────────────────────────────────

printf '\n\033[1m=== Skill frontmatter (skills/*/SKILL.md) ===\033[0m\n'

for skill_file in "$ROOT_DIR"/skills/*/SKILL.md; do
  rel="$(echo "$skill_file" | sed "s|$ROOT_DIR/||")"

  # Has frontmatter delimiters
  if has_frontmatter "$skill_file"; then
    pass "$rel: has frontmatter delimiters"
  else
    fail "$rel: missing frontmatter delimiters (---)"
    continue
  fi

  # Required fields
  for field in name description; do
    value="$(get_field "$skill_file" "$field")"
    if [ -n "$value" ]; then
      pass "$rel: has '$field' field"
    else
      fail "$rel: missing required field '$field'"
    fi
  done

  # If agent: field present, corresponding agents/<name>.md exists (case-insensitive)
  agent_ref="$(get_field "$skill_file" agent)"
  if [ -n "$agent_ref" ]; then
    agent_lower="$(echo "$agent_ref" | tr '[:upper:]' '[:lower:]')"
    if [ -f "$ROOT_DIR/agents/${agent_lower}.md" ]; then
      pass "$rel: agent ref '$agent_ref' -> agents/${agent_lower}.md exists"
    else
      fail "$rel: agent ref '$agent_ref' -> agents/${agent_lower}.md not found"
    fi
  fi

  # If context: fork, agent: must be present
  context_val="$(get_field "$skill_file" context)"
  if [ "$context_val" = "fork" ]; then
    if [ -n "$agent_ref" ]; then
      pass "$rel: context=fork has agent field"
    else
      fail "$rel: context=fork but no agent field"
    fi
  fi

  # If model: field present, it's valid
  model="$(get_field "$skill_file" model)"
  if [ -n "$model" ]; then
    if echo "$model" | grep -qiE '^(haiku|sonnet|opus)$'; then
      pass "$rel: model '$model' is valid"
    else
      fail "$rel: model '$model' is not one of haiku/sonnet/opus"
    fi
  fi
done

# ─── Hooks validation ─────────────────────────────────────────────────

printf '\n\033[1m=== Hooks validation (hooks/hooks.json) ===\033[0m\n'

hooks_file="$ROOT_DIR/hooks/hooks.json"

if [ -f "$hooks_file" ]; then
  # Valid JSON
  if python3 -m json.tool "$hooks_file" > /dev/null 2>&1; then
    pass "hooks.json: valid JSON"
  else
    fail "hooks.json: invalid JSON"
  fi

  # Has hooks top-level key
  if python3 -c "import json,sys; d=json.load(open('$hooks_file')); sys.exit(0 if 'hooks' in d else 1)" 2>/dev/null; then
    pass "hooks.json: has 'hooks' top-level key"
  else
    fail "hooks.json: missing 'hooks' top-level key"
  fi

  # hooks value is an array
  if python3 -c "import json,sys; d=json.load(open('$hooks_file')); sys.exit(0 if isinstance(d.get('hooks'), list) else 1)" 2>/dev/null; then
    pass "hooks.json: 'hooks' is an array"
  else
    fail "hooks.json: 'hooks' is not an array"
  fi

  # Each hook entry has required fields (type, event, command)
  python3 -c "
import json, sys
d = json.load(open('$hooks_file'))
hooks = d.get('hooks', [])
errors = []
for i, hook in enumerate(hooks):
    for field in ['type', 'event', 'command']:
        if field not in hook:
            errors.append(f'hook[{i}]: missing required field \"{field}\"')
for e in errors:
    print(e)
sys.exit(0)
" 2>/dev/null | while IFS= read -r line; do
    if [ -n "$line" ]; then
      fail "hooks.json: $line"
    fi
  done

  # Each hook event is a known CC hook event
  python3 -c "
import json, sys
VALID_EVENTS = {'SessionStart', 'UserPromptSubmit', 'PreToolUse', 'Stop', 'PostToolUse', 'Notification', 'SubagentStop', 'SubagentTool'}
d = json.load(open('$hooks_file'))
for i, hook in enumerate(d.get('hooks', [])):
    event = hook.get('event', '')
    if event in VALID_EVENTS:
        print(f'PASS hook[{i}]: event \"{event}\" is valid')
    else:
        print(f'FAIL hook[{i}]: event \"{event}\" is not a known CC hook event')
" 2>/dev/null | while IFS= read -r line; do
    if echo "$line" | grep -q '^PASS'; then
      msg="$(echo "$line" | sed 's/^PASS //')"
      pass "hooks.json: $msg"
    elif echo "$line" | grep -q '^FAIL'; then
      msg="$(echo "$line" | sed 's/^FAIL //')"
      fail "hooks.json: $msg"
    fi
  done

  # Hook commands reference existing scripts
  commands=$(python3 -c "
import json, re
d = json.load(open('$hooks_file'))
for hook in d.get('hooks', []):
    cmd = hook.get('command', '')
    # Resolve \${CLAUDE_PLUGIN_ROOT} to the repo root for validation
    cmd = re.sub(r'\\\$\{CLAUDE_PLUGIN_ROOT\}', '.', cmd)
    if cmd:
        print(cmd)
" 2>/dev/null || true)

  for cmd_path in $commands; do
    resolved="$ROOT_DIR/${cmd_path#./}"
    if [ -f "$resolved" ]; then
      pass "hooks.json: command script '$(basename "$resolved")' exists"
    else
      fail "hooks.json: command script '$cmd_path' not found"
    fi
  done
else
  fail "hooks.json: file not found"
fi

# ─── Shell scripts validation ────────────────────────────────────────

printf '\n\033[1m=== Shell scripts (scripts/*.sh) ===\033[0m\n'

for script_file in "$ROOT_DIR"/scripts/*.sh; do
  [ -f "$script_file" ] || continue
  basename="$(basename "$script_file")"

  # Is executable
  if [ -x "$script_file" ]; then
    pass "$basename: is executable"
  else
    fail "$basename: is not executable"
  fi

  # Has shebang
  first_line="$(head -1 "$script_file")"
  if [ "$first_line" = "#!/usr/bin/env bash" ]; then
    pass "$basename: has correct shebang"
  else
    fail "$basename: shebang is '$first_line', expected '#!/usr/bin/env bash'"
  fi

  # Passes bash -n syntax check
  if bash -n "$script_file" 2>/dev/null; then
    pass "$basename: bash -n syntax check passes"
  else
    fail "$basename: bash -n syntax check fails"
  fi

  # ShellCheck
  if command -v shellcheck > /dev/null 2>&1; then
    if shellcheck "$script_file" > /dev/null 2>&1; then
      pass "$basename: shellcheck passes"
    else
      fail "$basename: shellcheck reports issues"
    fi
  else
    warn "$basename: shellcheck not installed, skipping"
  fi
done

# ─── Cross-reference integrity ────────────────────────────────────────

printf '\n\033[1m=== Cross-reference integrity ===\033[0m\n'

mapping_file="$ROOT_DIR/docs/agent-mapping.md"

if [ -f "$mapping_file" ]; then
  # Extract agent names from mapping table: claude-agent-kit:<name>
  mapped_agents=$(grep -oE 'claude-agent-kit:[a-z0-9-]+' "$mapping_file" | sed 's/claude-agent-kit://' | sort -u)

  # All agents in mapping have corresponding files
  for agent_name in $mapped_agents; do
    if [ -f "$ROOT_DIR/agents/${agent_name}.md" ]; then
      pass "agent-mapping.md: '$agent_name' -> agents/${agent_name}.md exists"
    else
      fail "agent-mapping.md: '$agent_name' listed but agents/${agent_name}.md not found"
    fi
  done

  # All agent files are listed in mapping
  for agent_file in "$ROOT_DIR"/agents/*.md; do
    agent_name="$(basename "$agent_file" .md)"
    if echo "$mapped_agents" | grep -qx "$agent_name"; then
      pass "agents/${agent_name}.md: listed in agent-mapping.md"
    else
      fail "agents/${agent_name}.md: not listed in agent-mapping.md"
    fi
  done
else
  fail "docs/agent-mapping.md: file not found"
fi

# Every skills/*/ directory has a SKILL.md
for skill_dir in "$ROOT_DIR"/skills/*/; do
  dir_name="$(basename "$skill_dir")"
  if [ -f "${skill_dir}SKILL.md" ]; then
    pass "skills/${dir_name}/: has SKILL.md"
  else
    fail "skills/${dir_name}/: missing SKILL.md"
  fi
done

# ─── Summary ──────────────────────────────────────────────────────────

printf '\n\033[1m=== Summary ===\033[0m\n'
printf '  Passed:   %d\n' "$passes"
printf '  Failed:   %d\n' "$failures"
printf '  Warnings: %d\n' "$warnings"

if [ "$failures" -gt 0 ]; then
  printf '\n\033[31m%d check(s) failed.\033[0m\n' "$failures"
  exit 1
else
  printf '\n\033[32mAll checks passed.\033[0m\n'
  exit 0
fi
