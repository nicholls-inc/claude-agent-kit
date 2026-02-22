# Datasets

Test data and baselines for the evaluation suite. All files are version-controlled and used as frozen inputs for deterministic tests and offline LLM judge evaluation.

## Hook Test Data

### ulw-triggers.json

15 test cases for ULW (ultrawork) pattern detection. Each entry has an `input` string and expected `match` boolean.

- **Matches**: bare keyword, case variations, embedded in phrases, with punctuation/newlines
- **No match**: similar words like "bulwark", "skulwark", space-separated "ultra work", empty string

### pretool-cases.json

Two sections for PreToolUse hook testing:

- **standard** (15 cases): destructive Bash commands that must be blocked (`rm -rf`, `mkfs`, `dd if=`, `sudo rm`, piped `rm`), benign commands that must be allowed (`ls`, `git`, `npm`, `cat`, `python`), and non-Bash tools that always pass (`Read`, `Glob`, `Write`)
- **prometheus** (5 cases): Prometheus persona write guard — blocks `Write`/`Edit` to code files (`.ts`, `.js`, `.py`), allows `.md` files and `.agent-kit/` paths

### hook-inputs.json

Frozen JSON payloads simulating hook events:

- **session_start.personas**: 4 entries (sisyphus, hephaestus, atlas, prometheus) for SessionStart injection testing
- **session_start.boulder_resume**: Plan path + resume context injection
- **stop.\***: 4 Stop hook scenarios — ULW enabled (blocks), all disabled (allows), max blocks reached (auto-disables), stopContinuation disabled (allows)

## Baseline Data

### prompt-baseline.json

SHA256 hashes for all 9 agents and 14 skills, computed by `scripts/prompt-version.sh`. Used by `prompt-regression.sh` to detect prompt changes between runs.

### baseline-tasks.json

12 task definitions for plugin vs vanilla comparison. Each entry has a `name`, `description`, `persona` recommendation, and `tags`. Spans task types: bug-fix, feature, planning, exploration, execution, architecture, refactor, testing, documentation, investigation, workflow, config.

## Persona Examples

`persona-examples/` contains 8 frozen trace files (good + bad for each persona):

| File | Persona | Quality | Description |
|---|---|---|---|
| sisyphus-good.json | Sisyphus | Good | Explore-plan-execute-verify workflow |
| sisyphus-bad.json | Sisyphus | Bad | Skipped exploration, no verification |
| hephaestus-good.json | Hephaestus | Good | Deep execution with multi-type verification |
| hephaestus-bad.json | Hephaestus | Bad | Shallow execution, no retry on failure |
| prometheus-good.json | Prometheus | Good | Clean plan output, no code edits |
| prometheus-bad.json | Prometheus | Bad | Edited code files, no checklist format |
| atlas-good.json | Atlas | Good | Boulder reads, task advancement, verification gates |
| atlas-bad.json | Atlas | Bad | No boulder tracking, unbounded execution |

Each file contains: `trace_id`, `description`, `expected_scores`, `messages` (user/assistant pairs), `tool_calls` (name, input, output, timestamp), and `metadata`.

Used for offline evaluation with `--dataset` flag on `persona-trace-analyzer.py` and `judge-persona.py`.

## Plan Examples

`plan-examples/` contains 5 reference plans for `judge-plan.py` calibration:

| File | Quality | Notes |
|---|---|---|
| excellent-plan.md | 5/5 | Clear Context/Tasks/Verification sections, well-scoped tasks |
| good-plan.md | 4/5 | Basic but solid structure, rate limiting feature |
| mediocre-plan.md | 3/5 | Has structure but vague tasks |
| poor-plan.md | 1-2/5 | Stream-of-consciousness, no structure |
| scope-creep-plan.md | 2/5 | Excessive scope beyond original request |
