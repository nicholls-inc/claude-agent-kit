# Evaluation Suite

Three-phase evaluation system for the claude-agent-kit plugin. Phase 1-2 runs deterministic tests suitable for CI. Phase 3 adds Langfuse-integrated trace analysis and LLM-as-judge scoring.

## Directory Structure

```
evals/
├── run-evals.sh                 # Main orchestrator (Phase 1-2)
├── hook-evals.sh                # Hook behavioral contract tests
├── state-evals.sh               # State I/O tests
├── prompt-regression.sh         # Prompt change detection
├── session-signals.py           # Deterministic session quality signals
├── persona-trace-analyzer.py    # Rule-based persona scoring
├── baseline-comparison.py       # Plugin vs vanilla comparison
├── reports/                     # Generated comparison reports
├── datasets/                    # Test data and baselines
└── llm-judge/                   # LLM-as-judge evaluations
```

## Quick Start

### Deterministic Tests (CI-safe, no external dependencies)

```bash
./evals/run-evals.sh
```

Runs `hook-evals.sh`, `state-evals.sh`, and `prompt-regression.sh` in sequence. Requires only `jq` and `bash`. Exit 0 on all-pass, 1 on any failure.

### Trace Analysis (requires Langfuse)

```bash
uv run evals/session-signals.py --days 7
uv run evals/persona-trace-analyzer.py --days 7
uv run evals/baseline-comparison.py --days 30
```

Fetches live traces from Langfuse and computes deterministic quality signals. No LLM calls.

### LLM-as-Judge (requires Langfuse + Anthropic API)

```bash
./evals/llm-judge/run-judges.sh --days 7
```

Runs session signals, persona trace analysis, then LLM-based persona contract evaluation.

## Phase 1-2: Deterministic Tests

### hook-evals.sh

Tests hook-router.sh behavioral contracts with frozen test data. No LLM, 100% deterministic.

| Section | Cases | What it tests |
|---|---|---|
| ULW Detection | 15 | Pattern matching for ultrawork triggers via `detect-ulw.sh` |
| PreToolUse Blocking | 20 | Destructive command blocking, benign command allow, Prometheus write guard |
| SessionStart Injection | 4 | Persona-specific system prompt injection for all four personas |
| Boulder Resume | 1 | Plan context + current task injection on session restart |
| Stop Continuation | 4 | ULW blocking, auto-disable after 8 blocks, stopContinuation flag |

### state-evals.sh

Tests `state-read.sh` and `state-write.sh` edge cases.

- **state-read**: missing file, empty path, corrupt JSON, empty file, valid JSON, parent directory creation
- **state-write**: basic write, round-trip, nested parent directories, stdin input, empty path/content failures
- **Concurrent safety**: rapid sequential writes remain valid JSON

### prompt-regression.sh

Detects when agent or skill prompts change by computing SHA256 hashes and comparing against `datasets/prompt-baseline.json`. On change detection: re-runs hook-evals, logs diffs, updates baseline on success.

## Phase 3: Trace Analysis

### session-signals.py

Computes 12 deterministic quality signals from Langfuse traces:

- `turn_count`, `efficiency_score` (exponential decay above 5 turns)
- `repair_count`, `repair_ratio` (user correction detection)
- `repetition_count` (bigram Jaccard similarity >= 0.5)
- `frustration_severity` (0-3 scale), `positive_feedback`, `escalation_requested`
- `tool_call_count`, `tool_failure_rate`, `verification_present`
- `overall_quality` (categorical: Severe/Poor/Neutral/Good/Excellent)

### persona-trace-analyzer.py

Rule-based scoring of persona adherence from tool-call sequences:

- **Sisyphus**: workflow_sequence, parallel_exploration, verification_present, no_nested_orchestration
- **Hephaestus**: execution_depth, verification_depth, retry_quality, no_nested_orchestration, persistence
- **Prometheus**: plan_produced, no_code_edits, artifact_location, checklist_format
- **Atlas**: boulder_read, task_advancement, verification_before_done, bounded_continuation, single_slice_focus

Supports offline evaluation with `--dataset`.

### baseline-comparison.py

Compares plugin-enabled vs vanilla Claude Code on 12 baseline tasks. Fetches paired traces tagged `plugin:true`/`plugin:false`, computes metrics (turns, tokens, tool calls, verification), and generates a markdown report in `reports/`.

## Dependencies

Deterministic tests require only `bash` and `jq`. Python scripts are managed via `uv` with deps declared in `pyproject.toml`:

- `langfuse>=2.0.0`
- `anthropic>=0.40.0` (LLM judges only)

## Environment Variables

Phase 3 scripts require:

- `LANGFUSE_PUBLIC_KEY`
- `LANGFUSE_SECRET_KEY`
- `LANGFUSE_HOST` (optional, defaults to cloud)
- `ANTHROPIC_API_KEY` (LLM judges only)
