#!/usr/bin/env bash
set -euo pipefail

# prompt-version.sh — Compute SHA256 hashes of all agent and skill prompt files.
#
# CONTRACT:
#   - Scans agents/*.md and skills/*/SKILL.md.
#   - Outputs JSON: {"agent:<name>": "<sha256>", "skill:<name>": "<sha256>", ...}
#   - Used for prompt regression detection.
#
# USAGE:
#   ./prompt-version.sh              # outputs JSON to stdout
#   ./prompt-version.sh > baseline.json

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Collect hashes
declare -A hashes

# Agent prompts
for agent_file in "${ROOT_DIR}"/agents/*.md; do
  [[ -f "${agent_file}" ]] || continue
  name="$(basename "${agent_file}" .md)"
  hash="$(shasum -a 256 "${agent_file}" | awk '{print $1}')"
  hashes["agent:${name}"]="${hash}"
done

# Skill prompts
for skill_file in "${ROOT_DIR}"/skills/*/SKILL.md; do
  [[ -f "${skill_file}" ]] || continue
  dir_name="$(basename "$(dirname "${skill_file}")")"
  hash="$(shasum -a 256 "${skill_file}" | awk '{print $1}')"
  hashes["skill:${dir_name}"]="${hash}"
done

# Output as JSON
if command -v jq >/dev/null 2>&1; then
  # Build JSON via jq
  json="{}"
  for key in $(printf '%s\n' "${!hashes[@]}" | sort); do
    json=$(printf '%s' "${json}" | jq -c --arg k "${key}" --arg v "${hashes[${key}]}" '. + {($k): $v}')
  done
  printf '%s\n' "${json}" | jq .
else
  # Fallback: manual JSON construction
  printf '{\n'
  first=true
  for key in $(printf '%s\n' "${!hashes[@]}" | sort); do
    if [[ "${first}" == "true" ]]; then
      first=false
    else
      printf ',\n'
    fi
    printf '  "%s": "%s"' "${key}" "${hashes[${key}]}"
  done
  printf '\n}\n'
fi
