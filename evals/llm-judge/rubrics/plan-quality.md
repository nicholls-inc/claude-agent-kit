# Plan Quality Evaluation Rubric

Evaluate the quality of a plan produced by prometheus or metis agents.

## Structure (1-5)

- 1: No discernible structure, stream-of-consciousness
- 2: Basic bullet points without sections
- 3: Has some sections but missing key ones (Context, Tasks, or Verification)
- 4: Has Context/Tasks/Verification sections with minor structural issues
- 5: Clear Context/Tasks/Verification sections, checklist format with `- [ ]` items

## Task Granularity (1-5)

- 1: Single monolithic task or >15 tasks (too coarse or too fine)
- 2: 1-2 overly broad tasks or >12 overly detailed tasks
- 3: 3-10 tasks but some are too broad or too narrow
- 4: 3-10 well-scoped tasks with minor granularity issues
- 5: 3-10 well-scoped, independently executable tasks with clear boundaries

## Verifiability (1-5)

- 1: No verification commands or criteria
- 2: Vague verification ("test it")
- 3: Some verification commands but not for all tasks
- 4: Concrete verification for most tasks
- 5: Concrete, runnable verification commands for every task (e.g., specific test commands, type check, build)

## Actionability (1-5)

- 1: Abstract descriptions with no file or code references
- 2: Some references but mostly abstract
- 3: References specific files but lacks implementation detail
- 4: References specific files and patterns, mostly actionable
- 5: References specific files, patterns, and existing code; each task can be picked up and executed immediately

## Scope Discipline (1-5)

- 1: Massive scope creep, covers far more than requested
- 2: Notable scope creep
- 3: Mostly on-scope with some extras
- 4: Tightly scoped with explicit boundaries
- 5: Tightly scoped to the request, no creep, explicit about what's excluded
