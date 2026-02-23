# Momus Quality Evaluation Rubric

Evaluate the quality of plan reviews produced by the momus agent.

## Verdict Accuracy (BOOLEAN)

- TRUE: OKAY verdict for executable, well-formed plans; REJECT only for genuine blockers (missing files, impossible constraints, broken dependencies)
- FALSE: REJECT for minor style issues, or OKAY for plans with genuine blockers

## Issue Specificity (1-5)

- 1: Vague concerns with no references ("this might not work")
- 2: Some specificity but mostly general observations
- 3: References general areas but not exact tasks or files
- 4: References specific tasks and files with minor gaps
- 5: Issues reference exact files, task numbers, and specific problems with suggested fixes
