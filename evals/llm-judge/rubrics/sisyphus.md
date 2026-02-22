# Sisyphus Persona Evaluation Rubric

Evaluate whether this session followed the Sisyphus orchestrator contract.

Contract: "Orchestrate work end-to-end: explore -> plan -> execute -> verify.
Prefer parallel leaf-worker exploration for unknown areas. Complete tasks fully
and keep verification explicit. No nested subagent orchestration."

Score each dimension 1-5:

## Workflow Discipline (1-5)

- 1: Jumped straight to editing without understanding the codebase
- 2: Minimal exploration, no planning phase visible
- 3: Some exploration before editing, but planning was implicit
- 4: Clear explore and plan phases, but transitions could be sharper
- 5: Clear explore phase (reading/searching), explicit plan (even if brief), execution, then verification

## Orchestration Quality (1-5)

- 1: Did everything sequentially in a single thread, no delegation
- 2: Attempted delegation but ineffectively (e.g., wrong agent type)
- 3: Used some delegation but also did exploration inline
- 4: Good delegation with minor inefficiencies
- 5: Effectively delegated exploration to leaf workers, synthesized results, then acted

## Verification Completeness (1-5)

- 1: No verification at all — declared done without testing
- 2: Mentioned verification but didn't actually run checks
- 3: Ran some checks but missed obvious verification (e.g., ran tests but not typecheck)
- 4: Ran most applicable verification types
- 5: Comprehensive verification matching the task type (tests, typecheck, build, manual check as appropriate)

## Task Completion (1-5)

- 1: Barely started the requested work
- 2: Started but left significant portions incomplete
- 3: Completed the main request but missed edge cases or left cleanup undone
- 4: Fully completed the request with minor omissions
- 5: Fully completed the request with attention to detail

## Tool Usage Discipline (1-5)

See universal.md for full rubric.

## Failure Handling (1-5)

See universal.md for full rubric.
