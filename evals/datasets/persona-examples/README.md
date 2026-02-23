# Persona Examples

Frozen trace data for offline evaluation of persona behavioral contracts. Each persona has a good and bad example, used to validate scoring logic in `persona-trace-analyzer.py` and calibrate `judge-persona.py`.

## Files

| File | Persona | Quality | Key Characteristics |
|---|---|---|---|
| sisyphus-good.json | Sisyphus | Good | Explore (Task + Glob + Read) before edit, parallel exploration, verification (npm test + tsc) |
| sisyphus-bad.json | Sisyphus | Bad | Skipped exploration, jumped to editing, no verification step |
| hephaestus-good.json | Hephaestus | Good | Deep multi-file execution, multi-type verification (test + typecheck + build + lint), retry after failure |
| hephaestus-bad.json | Hephaestus | Bad | Shallow single edit, no verification, no retry on failure |
| prometheus-good.json | Prometheus | Good | Plan written to `.agent-kit/`, checklist format, no code file edits |
| prometheus-bad.json | Prometheus | Bad | Edited code files directly, no checklist format, artifacts outside `.agent-kit/` |
| atlas-good.json | Atlas | Good | Reads boulder.json early, marks tasks done, verification before boulder update, bounded tool calls |
| atlas-bad.json | Atlas | Bad | No boulder state tracking, unbounded execution, no verification gates |

## Schema

Each JSON file contains:

```json
{
  "trace_id": "offline-{persona}-{quality}",
  "description": "Human-readable description",
  "expected_scores": { "metric_name": expected_value },
  "messages": [
    { "role": "user|assistant", "content": "..." }
  ],
  "tool_calls": [
    {
      "name": "ToolName",
      "input": { "...": "..." },
      "output": "...",
      "timestamp": "ISO-8601",
      "level": "SPAN"
    }
  ],
  "metadata": { "persona": "persona_name" }
}
```

## Usage

```bash
# Rule-based scoring
uv run evals/persona-trace-analyzer.py --dataset evals/datasets/persona-examples/sisyphus-good.json

# LLM judge scoring
uv run evals/llm-judge/judge-persona.py --dataset evals/datasets/persona-examples/sisyphus-good.json
```
