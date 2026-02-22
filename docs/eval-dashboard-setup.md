# Evaluation Dashboard Setup Guide

Configuration guide for Langfuse dashboards that visualize evaluation data from the claude-agent-kit plugin.

## Prerequisites

- Langfuse instance running at `http://192.168.68.101:3000` (or your configured `LANGFUSE_BASE_URL`)
- Plugin telemetry enabled (Phase 2 hooks emitting events)
- Evaluation scripts run at least once (to populate scores)

## Dashboard 1: Persona Performance

The most important dashboard — tracks whether each persona follows its behavioral contract.

### Charts to create:

**Persona Score Radar** (Table)
- Data source: Scores where name starts with `judge.`
- Group by: persona name (extract from score name: `judge.<persona>.<dimension>`)
- Columns: each dimension score (1-5)
- Filter: last 30 days
- Purpose: at-a-glance view of whether sisyphus is exploring, hephaestus is verifying, etc.

**Persona Quality Trend** (Line chart, weekly)
- Data source: Scores named `judge.<persona>.overall`
- X-axis: week
- Y-axis: average score (1-5)
- Series: one per persona
- Purpose: detect when prompt changes improve or degrade behavior

**Persona Verification Rate** (Bar chart)
- Data source: Scores named `*.verification_present` or `*.verification_depth`
- Group by: persona
- Purpose: which personas consistently verify vs skip

**Persona Workflow Compliance** (Stacked bar)
- Data source: Boolean scores (`sisyphus.workflow_sequence`, `prometheus.no_code_edits`, `atlas.boulder_read`, etc.)
- Group by: persona
- Stacked: compliant vs non-compliant
- Purpose: proportion of sessions following expected workflow

## Dashboard 2: Hook Health

### Charts to create:

**Hook Latency P50/P95** (Line chart, daily)
- Data source: Scores named `hook.latency_ms`
- Group by: event type (from `hook.*` event metadata)
- Y-axis: P50 and P95 latency in ms
- Purpose: ensure hooks aren't slowing down the experience

**Block vs Allow Decisions** (Stacked bar, daily)
- Data source: Events named `hook.pretool` and `hook.stop`
- Split by: `decision` metadata field (block/allow)
- Purpose: monitor safety guardrail activity

**ULW Trigger Rate** (Line chart, weekly)
- Data source: Events named `hook.user_prompt_submit` where `ulw_triggered=true`
- Y-axis: count per week
- Purpose: track ultrawork adoption

**Circuit Breaker Activations** (Counter)
- Data source: Events named `hook.stop` where `reason=max_blocks_auto_disabled`
- Purpose: monitor when continuation limits are hit

## Dashboard 3: Subagent Quality

### Charts to create:

**Latest Scores per Subagent** (Table)
- Data source: Scores named `plan_quality.*`, `explore.*`, `oracle.*`, `momus.*`
- Group by: subagent
- Conditional formatting: green >=4, yellow 3, red <=2

**Quality Trend** (Line chart, weekly)
- Data source: Same score names, averaged weekly
- Purpose: detect quality changes over time

**Token Usage per Subagent** (Bar chart)
- Data source: Trace token usage, grouped by subagent tag
- Purpose: cost monitoring

## Dashboard 4: Skill Usage

### Charts to create:

**Skill Invocation Counts** (Bar chart, monthly)
- Data source: Events or traces tagged with skill name
- Purpose: which skills are most/least used

**Plan Creation Funnel** (Funnel chart)
- Steps: plan invoked → boulder initialized → start-work invoked → completed
- Data source: Events named `hook.session_start` (boulder_active), skill invocations

**Continuation Mechanism Usage** (Pie chart)
- Data source: Events named `hook.stop` grouped by active mechanism (ULW/ralph/boulder)

**Escape Hatch Usage** (Counter)
- Data source: Skill invocations for `stop-continuation` and `cancel-ralph`

## Dashboard 5: Session Signals (Heuristics)

### Charts to create:

**Overall Quality Distribution** (Pie chart)
- Data source: Scores named `signal.overall_quality`
- Segments: Excellent / Good / Neutral / Poor / Severe
- Purpose: bird's-eye view of session quality

**Efficiency Score Trend** (Line chart, weekly)
- Data source: Scores named `signal.efficiency_score`
- Y-axis: average efficiency (0-1)
- Purpose: are sessions getting more efficient?

**Frustration Severity Distribution** (Stacked bar, weekly)
- Data source: Scores named `signal.frustration_severity`
- Stacked by: severity level (0-3)
- Purpose: monitor user experience

**Repair Ratio Trend** (Line chart, weekly)
- Data source: Scores named `signal.repair_ratio`
- Y-axis: average ratio (0-1)
- Purpose: are users needing to rephrase less?

**Repetition/Looping Events** (Counter, weekly)
- Data source: Scores where `signal.repetition_count >= 3`
- Purpose: detect stuck sessions

## Dashboard 6: Plugin vs Vanilla Baseline

### Charts to create:

**Task Completion Comparison** (Grouped bar)
- Data source: Traces tagged `plugin:true` and `plugin:false` with matching `baseline_task`
- Y-axis: completion rate
- Purpose: does the plugin help complete more tasks?

**Turn Count Comparison** (Grouped bar)
- Data source: `signal.turn_count` for paired traces
- Groups: plugin vs vanilla, per task type
- Purpose: fewer turns = better efficiency

**Token Efficiency Comparison** (Grouped bar)
- Data source: Token usage from paired traces
- Purpose: fewer tokens = lower cost

**Quality Score Comparison** (Grouped bar)
- Data source: `judge.*.overall` or `signal.overall_quality` for paired traces
- Purpose: overall quality delta

## Dashboard 7: Efficiency & Cost

### Charts to create:

**Tokens per Session** (Box plot, weekly)
- Data source: Total tokens per trace
- Purpose: track cost trends

**Tokens by Model Tier** (Stacked area, weekly)
- Data source: Token usage grouped by model (haiku/sonnet/opus)
- Purpose: understand model mix

**Estimated Cost per Session** (Line chart, weekly)
- Derived: haiku tokens × $0.25/1M + sonnet tokens × $3/1M + opus tokens × $15/1M
- Purpose: cost monitoring

## Setup Steps

1. **Log into Langfuse** at your configured base URL
2. **Create a new project** (or use existing) for claude-agent-kit
3. **For each dashboard above**:
   - Navigate to Dashboards → New Dashboard
   - Add charts using the specifications above
   - Set default time range to "Last 30 days"
4. **Set up alerts** (optional):
   - Alert when `signal.overall_quality` drops below "Good" for >50% of sessions
   - Alert when `hook.latency_ms` P95 exceeds 500ms
   - Alert when any `judge.*.overall` drops below 3.0

## Score Name Reference

### Hook Events
- `hook.session_start` — SessionStart handler invoked
- `hook.user_prompt_submit` — UserPromptSubmit handler invoked
- `hook.pretool` — PreToolUse handler invoked
- `hook.stop` — Stop handler invoked
- `hook.latency_ms` — Handler execution time

### Automated Persona Scores
- `sisyphus.workflow_sequence` — Explored before editing (BOOLEAN)
- `sisyphus.parallel_exploration` — Used Task for delegation (BOOLEAN)
- `sisyphus.verification_present` — Ran verification after edits (BOOLEAN)
- `sisyphus.no_nested_orchestration` — No persona agents spawned (BOOLEAN)
- `hephaestus.execution_depth` — Count of edit/write calls (NUMERIC)
- `hephaestus.verification_depth` — Distinct verification types (0-4)
- `hephaestus.retry_quality` — Targeted fixes after failures (BOOLEAN)
- `hephaestus.persistence` — Completed edits + verification (BOOLEAN)
- `prometheus.plan_produced` — Created .md under .agent-kit/ (BOOLEAN)
- `prometheus.no_code_edits` — No code file edits (BOOLEAN)
- `prometheus.artifact_location` — All writes in safe locations (BOOLEAN)
- `prometheus.checklist_format` — Plan has `- [ ]` items (BOOLEAN)
- `atlas.boulder_read` — Read boulder.json early (BOOLEAN)
- `atlas.task_advancement` — Updated plan + boulder (BOOLEAN)
- `atlas.verification_before_done` — Verified before completing (BOOLEAN)

### LLM-as-Judge Scores
- `judge.<persona>.<dimension>` — Per-dimension score (1-5)
- `judge.<persona>.overall` — Overall persona score (1-5)
- `plan_quality.<dimension>` — Plan quality dimension (1-5)
- `explore.<dimension>` — Search quality (mixed types)
- `oracle.<dimension>` — Oracle quality (mixed types)

### Session Signals
- `signal.turn_count` — User-assistant exchanges (NUMERIC)
- `signal.efficiency_score` — Session efficiency (0-1)
- `signal.repair_count` — User correction count (NUMERIC)
- `signal.repair_ratio` — Corrections per turn (0-1)
- `signal.repetition_count` — Near-duplicate responses (NUMERIC)
- `signal.frustration_severity` — User frustration level (0-3)
- `signal.positive_feedback` — Positive user messages (NUMERIC)
- `signal.escalation_requested` — User gave up (BOOLEAN)
- `signal.tool_call_count` — Total tool invocations (NUMERIC)
- `signal.tool_failure_rate` — Tool error rate (0-1)
- `signal.verification_present` — Verification after edits (BOOLEAN)
- `signal.overall_quality` — Aggregate rating (1-5, maps to Severe/Poor/Neutral/Good/Excellent)
