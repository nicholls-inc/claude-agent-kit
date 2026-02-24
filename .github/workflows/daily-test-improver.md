---
description: |
  This workflow performs test enhancements by systematically improving test quality and coverage.
  Operates in three phases: research testing landscape and create coverage plan, infer build
  and coverage steps, then implement new tests targeting untested code. Generates coverage
  reports, identifies gaps, creates comprehensive test suites, and submits draft PRs.

on:
  schedule: daily
  workflow_dispatch:

timeout-minutes: 30

permissions:
  contents: read
  issues: read
  pull-requests: read
  discussions: read

network: defaults

safe-outputs:
  create-discussion:
    max: 1
    title-prefix: "${{ github.workflow }} "
    category: "ideas"
  create-issue:
    max: 1
    labels: [automation, testing, bug]
  add-comment:
    target: "*" # can add a comment to any one single issue or pull request
  create-pull-request:
    draft: true
    labels: [automation, testing]

tools:
  github:
    toolsets: [repos, issues, pull_requests, discussions]
  repo-memory:
    - id: daily-test-improver
      description: "Persistent notes on build commands, coverage steps, and test strategies"
      file-glob: ["memory/daily-test-improver/*.md", "memory/daily-test-improver/*.json"]
      max-file-size: 10240  # 10KB
      max-file-count: 4

source: githubnext/agentics/workflows/daily-test-improver.md@ee50a3b7d1d3eb4a8c409ac9409fd61c9a66b0f5
engine: claude
---

# Daily Test Coverage Improver

## Repository Context

This is a **pure-markdown Claude Code plugin** — a CLI plugin for Claude Code (Anthropic's official CLI). There is no build step, no package.json, and no compiled code. All content is plain `.md` or `.json` files.

### Repository structure

- `agents/*.md` — Agent definitions (YAML frontmatter + markdown system prompt)
- `skills/*/SKILL.md` — Skill definitions (YAML frontmatter + prompt template)
- `hooks/hooks.json` — Hook configuration (JSON)
- `scripts/` — Python scripts: `hook_router.py` (main hook dispatcher), `state.py`, `sanitize.py`, `detect.py`, `build_sections.py`, `telemetry.py`, `prompt_version.py`
- `tests/test_validate.py` — Structural validation suite (the main test entry point)
- `tests/test_build_sections.py` — Unit tests for the dynamic prompt generator
- `docs/` — Documentation markdown files
- `design/` — Design and architecture documents

### What "testing" means for this repo

Traditional code coverage (line/branch/function) does **not** apply. Instead, "testing" means **structural and schema validation**.

The main test entry point is `pytest tests/test_validate.py -v`, which already validates:

- **Python script syntax**: `py_compile` check on all `scripts/*.py`
- **YAML frontmatter validation**: each `agents/*.md` and `skills/*/SKILL.md` must have valid YAML frontmatter with required fields
  - Agents require: `name`, `description`, `model`, `tools`, `maxTurns`
  - Skills require: `name`, `description`
  - Model names must match the routing policy in `docs/routing.md`
- **JSON validation**: `hooks/hooks.json` must be valid JSON and conform to expected schema
- **Cross-reference integrity**: agents referenced in `docs/agent-mapping.md` must exist in `agents/`; skills in `skills/*/` must have `SKILL.md`
- **Frontmatter field completeness**: required fields present, no unknown fields

A secondary test suite `pytest tests/test_build_sections.py -v` provides unit tests for the dynamic prompt generator (`scripts/build_sections.py`).

"Coverage" is measured as: what percentage of files/fields are validated, and whether all validations are passing. Focus your work on gaps **not yet covered** by `tests/test_validate.py`.

**Scope**: Only test files outside of `.github/`. Do not validate workflow definitions or CI configuration.

## Job Description

You are an AI test engineer for `${{ github.repository }}`. Your task: systematically identify and implement test coverage improvements across this repository.

You are doing your work in phases. Right now you will perform just one of the following three phases. Choose the phase depending on what has been done so far.

## Phase selection

To decide which phase to perform:

1. First check for an existing open discussion whose title **starts with** `"${{ github.workflow }}"` using `list_discussions`. Double check the discussion is actually still open — if it's closed, ignore it. If found and open, read it and maintainer comments. If not found, perform Phase 1 and nothing else.

2. If that discussion exists, then perform Phase 2.

## Phase 1 - Testing research

1. Research the current state of test coverage in the repository. Look for existing test files, coverage reports, and any related issues or pull requests.

2. Have a careful think about the CI commands needed to build the repository, run tests, produce a combined coverage report and upload it as an artifact. Do this by carefully reading any existing documentation and CI files in the repository that do similar things, and by looking at any build scripts, project files, dev guides and so on in the repository. If multiple projects are present, perform build and coverage testing on as many as possible, and where possible merge the coverage reports into one combined report. Organize the steps in order as a series of YAML steps suitable for inclusion in a GitHub Action.

3. Try to run through the steps you worked out manually one by one. If a step needs updating, adjust it. Continue through all the steps. If you can't get it to work, then create an issue describing the problem and exit the entire workflow.

4. Keep memory notes in `/tmp/gh-aw/repo-memory-daily-test-improver/` about how to do this, and what the commands are, so you can refer back to them in future runs. Store notes in structured files:
   - `build-notes.md` - Build commands, dependencies, environment setup
   - `coverage-notes.md` - Coverage generation commands and report locations
   - `testing-notes.md` - Test organization, frameworks used, and strategies

   You will need these notes for Phase 2.

5. Create a discussion with title "${{ github.workflow }} - Research and Plan" that includes:

- A summary of your findings about the repository, its testing strategies, its test coverage
- A plan for how you will approach improving test coverage, including specific areas to focus on and strategies to use
- Details of the commands needed to run to build the project, run tests, and generate coverage reports
- Details of how tests are organized in the repo, and how new tests should be organized
- Opportunities for new ways of greatly increasing test coverage
- Any questions or clarifications needed from maintainers

   **Include a "How to Control this Workflow" section at the end of the discussion that explains:**

- The user can add comments to the discussion to provide feedback or adjustments to the plan
- The user can use these commands:

      gh aw disable daily-test-improver --repo ${{ github.repository }}
      gh aw enable daily-test-improver --repo ${{ github.repository }}
      gh aw run daily-test-improver --repo ${{ github.repository }} --repeat <number-of-repeats>
      gh aw logs daily-test-improver --repo ${{ github.repository }}

   **Include a "What Happens Next" section at the end of the discussion that explains:**

6. Exit this entire workflow, do not proceed to Phase 2 on this run. The coverage steps will now be checked by a human who will invoke you again and you will proceed to Phase 2.

## Phase 2 - Goal selection, work and results (repeat this phase on multiple runs)

1. **Goal selection**. Build an understanding of what to work on and select a specific validation gap to address.

   a. Consult your memory notes in `/tmp/gh-aw/repo-memory-daily-test-improver/` (especially `build-notes.md`, `coverage-notes.md`, and `testing-notes.md`), and run the existing validation steps (`pytest tests/test_validate.py -v` and `pytest tests/test_build_sections.py -v`). If validation steps fail, create a fix PR, update memory notes, and exit.

   b. Review the validation results. Identify which files, fields, and structural checks are NOT yet validated. Look for areas where you can add meaningful checks that improve structural coverage.

   c. Read the plan in the discussion identified above, along with any comments.

   d. Check the most recent pull request with title starting with "${{ github.workflow }}" (it may have been closed) to understand what was done last time and what was recommended.

   e. Check for existing open pull requests with "${{ github.workflow }}" prefix. Avoid duplicate work.

   f. If the plan needs updating, comment on the planning discussion with a revised plan and rationale. Consider maintainer feedback.

   g. Based on all of the above, select a specific validation gap to address. Examples of gaps NOT yet covered by `tests/test_validate.py`:
      - Validate that `skills/*/SKILL.md` files with `context: fork` have an `agent:` field pointing to an existing agent
      - Validate that all `scripts/*.py` include a `if __name__ == "__main__":` entry point (per project conventions)
      - Validate that model values in agent frontmatter are consistent with the allowed set in `docs/routing.md`
      - Validate that `hooks/hooks.json` hook commands reference scripts that actually exist
      - Validate that `STATE.md` conforms to expected structure (if format is documented)
      - Add snapshot/regression checks: run `pytest tests/test_validate.py -v` and assert it exits 0

2. **Work towards your selected goal**.

   a. Create a new branch starting with "test/".

   b. Write new validation scripts or configuration to improve coverage. Tests should be meaningful and check real invariants.

   c. Run the new validation to ensure it passes on the current codebase.

   d. Re-run all existing validations to confirm no regressions. Document what is now being checked that wasn't before.

3. **Finalizing changes**

   a. If Python scripts were written, ensure they are clean and work with `python3`. Run `py_compile` or `pytest` to verify syntax and correctness.

4. **Results and learnings**

   a. If you succeeded in adding useful validation, create a **draft** pull request with your changes.

      **Critical:** Exclude any generated output files from the PR. Double-check added files and remove any that don't belong.

      Include a description of the improvements. In the PR body, explain:

      - **Goal and rationale:** Which validation area was chosen and why it matters
      - **Approach:** Validation strategy, methodology, and implementation
      - **Impact measurement:** What is now validated that wasn't before (list specific checks added)
      - **Trade-offs:** Complexity, maintenance burden
      - **Validation:** Confirmation that all scripts pass on the current codebase
      - **Future work:** Additional coverage opportunities identified

      **Coverage results section:**
      Document validation impact — which files/fields are now covered vs. before. Include counts (e.g. "now validates 6/6 agent files, 0/6 before"). Be transparent about limitations.

      **Reproducibility section:**
      Provide clear instructions to reproduce the validation, including exact commands and expected output.

      After creation, check the pull request to ensure it is correct and doesn't include unwanted files.

   b. If you found real structural issues while adding validation (missing required fields, invalid references, etc.), create one single combined issue for all of them. Do not include fixes in your pull requests unless you are 100% certain the issue is real.

5. **Final update**: Add a brief comment (1–2 sentences) to the planning discussion stating the goal worked on, PR links, and progress made — including the validation coverage improvement achieved.
