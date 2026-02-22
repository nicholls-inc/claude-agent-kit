---
name: agentic-workflows
description: Create, update, or debug GitHub Agentic Workflows in .github/workflows/*.md. Manual invocation only.
disable-model-invocation: true
model: sonnet
allowed-tools: Read, Edit, Write, Bash, Grep, Glob, WebFetch
---

Work with GitHub Agentic Workflows (gh-aw) in this repository: $ARGUMENTS

## Workflow file format

Workflow source files live at `.github/workflows/<workflow-id>.md`. Each has:
- **YAML frontmatter** (between `---`): triggers, permissions, tools, safe-outputs, engine
- **Markdown body**: the agent prompt (instructions for what the workflow does at runtime)

Existing workflows in this repo to use as reference:
- `.github/workflows/daily-repo-status.md`
- `.github/workflows/maintain-claude-md.md`

## Frontmatter fields

```yaml
description: |            # Required. What the workflow does.
  Brief description.

on:                       # Required. Triggers.
  schedule: weekly        # Fuzzy: daily, daily on weekdays, weekly
  workflow_dispatch:      # Manual trigger (auto-added for fuzzy schedules)
  issues:                 # types: [opened, edited, closed, reopened]
  pull_request:           # types: [opened, synchronize, closed, reopened]

permissions:              # Minimal required. No write permissions allowed (use safe-outputs).
  contents: read
  pull-requests: read
  issues: read

network: defaults         # Use 'defaults' unless extra domains needed.

tools:
  github:
    toolsets: [repos, issues, pull_requests]  # Pick only what's needed.
    lockdown: false       # Optional. Set false to read 3rd-party content in public repos.

safe-outputs:             # All GitHub write operations go through safe-outputs.
  create-issue:
    max: 1
    title-prefix: "[prefix] "
    labels: [label1, label2]
  create-pull-request:
    max: 1
  add-comment:
    max: 5
  update-issue:
    max: 3

engine: claude            # Required for this repo. All workflows use Claude.
```

## Key rules

- Write permissions are **not allowed** in `permissions:`. All GitHub writes go through `safe-outputs`.
- `bash` and `edit` tools are enabled by default (sandboxed by AWF). Do not restrict them.
- After creating or editing a `.md` file, always compile: `gh aw compile <workflow-id>`
- Both the `.md` source and the generated `.lock.yml` must be committed.
- `.gitattributes` already marks `*.lock.yml` as `linguist-generated=true merge=ours`.
- Produce exactly one `.md` file per workflow. Do not create separate docs.

## Commands

```bash
gh aw compile <workflow-id>    # Compile .md to .lock.yml (required after changes)
gh aw compile --validate       # Validate all workflows without writing
gh aw list                     # List all workflows
gh aw logs <workflow-id>       # View execution logs
gh aw audit <run-id>           # Debug a specific run
gh aw fix --write              # Apply automatic fixes
```

## Debugging

If `gh aw compile` fails, read the error carefully — common issues:
- Write permissions in `permissions:` (must use safe-outputs instead)
- Unknown fields in `safe-outputs` (check valid sub-fields for each output type)
- Missing required fields like `description` or `on`

For runtime failures, use `gh aw logs` and `gh aw audit` to inspect what happened.
