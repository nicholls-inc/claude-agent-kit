#!/usr/bin/env bash

set -euo pipefail

project_dir="${CLAUDE_PROJECT_DIR:-$(pwd)}"
cd "$project_dir"

config_path="${CLAUDE_AGENT_KIT_SAFE_GATE_CONFIG:-claude-agent-kit.safe-gate.json}"

fail() {
  printf '%s\n' "$1" >&2
  exit 2
}

fail_return() {
  printf '%s\n' "$1" >&2
  return 2
}

run_step() {
  local label="$1"
  local cmd="$2"

  printf '\n==> %s\n' "$label" >&2
  printf '    %s\n' "$cmd" >&2

  set +e
  local output
  output=$(bash -lc "$cmd" 2>&1)
  local status=$?
  set -e

  if [ "$status" -ne 0 ]; then
    printf '%s\n' "$output" >&2
    fail "Safe gate failed at: $label"
  fi

  printf '    OK\n' >&2
}

split_semicolon_commands() {
  local raw="$1"
  local -a out=()
  local IFS=';'
  read -r -a out <<< "$raw"
  for i in "${!out[@]}"; do
    out[i]="$(printf '%s' "${out[i]}" | sed -e 's/^ *//' -e 's/ *$//')"
  done

  for c in "${out[@]}"; do
    if [ -n "$c" ]; then
      printf '%s\n' "$c"
    fi
  done
}

load_commands_from_config() {
  if [ ! -f "$config_path" ]; then
    return 1
  fi

  if ! command -v node >/dev/null 2>&1; then
    fail_return "Found $config_path but node is not available to parse it. Set CLAUDE_AGENT_KIT_SAFE_GATE_COMMANDS instead."
    return 2
  fi

  node - <<'NODE'
const fs = require('fs');

const path = process.env.CLAUDE_AGENT_KIT_SAFE_GATE_CONFIG || 'claude-agent-kit.safe-gate.json';
const raw = fs.readFileSync(path, 'utf8');
const json = JSON.parse(raw);
const cmds = json && Array.isArray(json.commands) ? json.commands : null;

if (!cmds || cmds.length === 0) {
  console.error(`Invalid safe gate config at ${path}. Expected: { "commands": ["..."] }`);
  process.exit(2);
}

for (const c of cmds) {
  if (typeof c !== 'string' || c.trim().length === 0) continue;
  process.stdout.write(c.trim() + '\n');
}
NODE
}

discover_package_manager() {
  if [ -f bun.lockb ]; then
    printf 'bun\n'
    return 0
  fi
  if [ -f pnpm-lock.yaml ]; then
    printf 'pnpm\n'
    return 0
  fi
  if [ -f yarn.lock ]; then
    printf 'yarn\n'
    return 0
  fi
  if [ -f package-lock.json ]; then
    printf 'npm\n'
    return 0
  fi
  printf 'npm\n'
}

has_npm_script() {
  local script_name="$1"
  if [ ! -f package.json ]; then
    return 1
  fi
  if ! command -v node >/dev/null 2>&1; then
    return 1
  fi
  node -e "const p=require('./package.json'); process.exit(p.scripts && p.scripts['$script_name'] ? 0 : 1)" >/dev/null 2>&1
}

discover_commands_from_package_json() {
  if [ ! -f package.json ]; then
    return 1
  fi

  local pm
  pm="$(discover_package_manager)"

  local run
  case "$pm" in
    bun) run="bun run" ;;
    pnpm) run="pnpm run" ;;
    yarn) run="yarn" ;;
    npm|*) run="npm run" ;;
  esac

  if ! has_npm_script lint; then
    fail_return "Safe gate could not find a package.json script named 'lint'. Create one, or set CLAUDE_AGENT_KIT_SAFE_GATE_COMMANDS / $config_path."
    return 2
  fi
  if ! has_npm_script test; then
    fail_return "Safe gate could not find a package.json script named 'test'. Create one, or set CLAUDE_AGENT_KIT_SAFE_GATE_COMMANDS / $config_path."
    return 2
  fi
  if ! has_npm_script build; then
    fail_return "Safe gate could not find a package.json script named 'build'. Create one, or set CLAUDE_AGENT_KIT_SAFE_GATE_COMMANDS / $config_path."
    return 2
  fi

  printf '%s\n' "$run lint"
  printf '%s\n' "$run test"
  printf '%s\n' "$run build"
}

main() {
  local -a cmds=()

  if [ -n "${CLAUDE_AGENT_KIT_SAFE_GATE_COMMANDS:-}" ]; then
    while IFS= read -r line; do
      [ -n "$line" ] && cmds+=("$line")
    done < <(split_semicolon_commands "$CLAUDE_AGENT_KIT_SAFE_GATE_COMMANDS")
  else
    local loaded
    loaded=""
    if loaded=$(load_commands_from_config 2>/dev/null); then
      while IFS= read -r line; do
        [ -n "$line" ] && cmds+=("$line")
      done <<< "$loaded"
    else
      rc=$?
      if [ "$rc" -eq 2 ]; then
        exit 2
      fi
      local discovered
      discovered=""
      if discovered=$(discover_commands_from_package_json); then
        while IFS= read -r line; do
          [ -n "$line" ] && cmds+=("$line")
        done <<< "$discovered"
      else
        rc=$?
        if [ "$rc" -eq 2 ]; then
          exit 2
        fi
        fail "Safe gate could not determine commands to run. Provide CLAUDE_AGENT_KIT_SAFE_GATE_COMMANDS or create $config_path."
      fi
    fi
  fi

  if [ "${#cmds[@]}" -lt 3 ]; then
    fail "Safe gate expected at least 3 commands (lint/test/build). Configure CLAUDE_AGENT_KIT_SAFE_GATE_COMMANDS or $config_path."
  fi

  run_step "lint" "${cmds[0]}"
  run_step "test" "${cmds[1]}"
  run_step "build" "${cmds[2]}"
}

main "$@"
