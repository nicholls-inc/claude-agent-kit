# Oracle Quality Evaluation Rubric

Evaluate the quality of architecture advice produced by the oracle agent.

## Recommendation Quality (1-5)

- 1: Generic advice that doesn't account for the codebase or project context
- 2: Somewhat relevant but misses key architectural patterns in the codebase
- 3: Relevant recommendations but doesn't leverage existing patterns optimally
- 4: Good recommendations that leverage existing patterns
- 5: Pragmatic, well-reasoned recommendations that leverage existing patterns and anticipate trade-offs

## Verbosity Compliance (BOOLEAN)

- TRUE: Bottom line is <= 3 sentences, plan/steps are <= 7 items
- FALSE: Bottom line exceeds 3 sentences or plan exceeds 7 steps

## Effort Tag Present (BOOLEAN)

- TRUE: Response includes an effort tag (Quick/Short/Medium/Large)
- FALSE: No effort tag present
