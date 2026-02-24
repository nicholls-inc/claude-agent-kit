# Langfuse Observability Setup

Langfuse is an open-source LLM observability platform. The claude-agent-kit plugin emits hook events and evaluation scores to Langfuse to enable tracing, debugging, and monitoring of agent sessions.

Tracing is **opt-in**: nothing is sent unless all three environment variables are set.

## Prerequisites

- A Langfuse instance — either [Langfuse Cloud](https://cloud.langfuse.com) or [self-hosted](https://langfuse.com/docs/deployment/self-host)
- A Langfuse project with a **public key** and a **secret key** (available in Project Settings → API Keys)

## Configuration

The plugin reads the following environment variables:

| Variable | Description |
|---|---|
| `LANGFUSE_PUBLIC_KEY` | Public API key from your Langfuse project |
| `LANGFUSE_SECRET_KEY` | Secret API key from your Langfuse project |
| `LANGFUSE_BASE_URL` | Base URL of your Langfuse instance (e.g. `https://cloud.langfuse.com` or `http://localhost:3000`) |

### `.claude/settings.json` (shared / team)

Claude Code plugins receive environment variables from the `env` key in `.claude/settings.json`. Add the three keys to that file:

```json
{
  "env": {
    "LANGFUSE_PUBLIC_KEY": "pk-lf-...",
    "LANGFUSE_SECRET_KEY": "sk-lf-...",
    "LANGFUSE_BASE_URL": "https://cloud.langfuse.com"
  }
}
```

### `.claude/settings.local.json` (personal / gitignored)

To keep credentials out of version control, use the local settings file instead (add it to `.gitignore`):

```json
{
  "env": {
    "LANGFUSE_PUBLIC_KEY": "pk-lf-...",
    "LANGFUSE_SECRET_KEY": "sk-lf-...",
    "LANGFUSE_BASE_URL": "https://cloud.langfuse.com"
  }
}
```

### CI secrets

In GitHub Actions, add repository secrets and expose them as environment variables in your workflow:

```yaml
env:
  LANGFUSE_PUBLIC_KEY: ${{ secrets.LANGFUSE_PUBLIC_KEY }}
  LANGFUSE_SECRET_KEY: ${{ secrets.LANGFUSE_SECRET_KEY }}
  LANGFUSE_BASE_URL: ${{ secrets.LANGFUSE_BASE_URL }}
```

## What Gets Traced

The `scripts/telemetry.py` module sends events and scores to Langfuse via a fire-and-forget daemon thread. It never blocks the hook or the user.

### Hook events

Each hook handler emits an event on every invocation:

| Event name | Emitted by |
|---|---|
| `hook.session_start` | `SessionStart` handler |
| `hook.user_prompt_submit` | `UserPromptSubmit` handler |
| `hook.pretool` | `PreToolUse` handler |
| `hook.stop` | `Stop` handler |

Event metadata includes contextual fields such as `decision` (block/allow), `reason`, `ulw_triggered`, and `boulder_active`.

### Scores

Numeric and boolean scores are attached to a trace identified by the session. Categories include:

- **Hook latency** — `hook.latency_ms`: handler execution time in milliseconds
- **Persona behavior** — `sisyphus.*`, `hephaestus.*`, `prometheus.*`, `atlas.*`: whether each persona followed its behavioral contract (booleans and counts)
- **LLM-as-judge** — `judge.<persona>.<dimension>` and `judge.<persona>.overall`: per-dimension quality scores (1–5) from automated evaluation runs
- **Plan quality** — `plan_quality.<dimension>`: planning output quality (1–5)
- **Session signals** — `signal.*`: heuristic session health metrics (turn count, efficiency, repair ratio, frustration severity, overall quality)

See [`eval-dashboard-setup.md`](eval-dashboard-setup.md) for the full score name reference and recommended Langfuse dashboards.

## Viewing Traces

1. Log in to your Langfuse instance.
2. Select your project.
3. Navigate to **Traces** to see all recorded sessions. Each trace corresponds to one hook invocation and carries the events and scores emitted during that call.
4. Use the **Scores** tab to filter or sort by any score dimension (e.g. `judge.sisyphus.overall` to find poorly-behaved sessions).
5. Click into a trace to inspect the full event timeline, metadata, and latency breakdown.

Use the **Dashboards** feature to build charts across traces — refer to [`eval-dashboard-setup.md`](eval-dashboard-setup.md) for a complete set of recommended dashboard specifications.

## Disabling Tracing

Tracing is automatically disabled when any of the three environment variables is missing or empty. To disable tracing, remove the Langfuse keys from the `env` block in your `.claude/settings.json` or `.claude/settings.local.json` file, or delete the `env` block entirely.

Hooks continue to operate normally when Langfuse is not configured — the telemetry calls are no-ops.
