# Search Quality Evaluation Rubric

Evaluate the quality of search results produced by the explore agent.

## Completeness (1-5)

- 1: Missed most relevant matches, returned only partial results
- 2: Found some matches but missed obvious ones
- 3: Found most relevant matches but missed some edge cases
- 4: Found nearly all relevant matches
- 5: Found all relevant matches, including edge cases and indirect references

## Path Format (BOOLEAN)

- TRUE: All returned paths are absolute paths
- FALSE: Some paths are relative or malformed

## Output Structure (BOOLEAN)

- TRUE: Output has clear results/files/answer/next_steps sections
- FALSE: Unstructured output without clear sections

## Parallel Execution (BOOLEAN)

- TRUE: First action batch contains 3+ tool calls (parallel exploration)
- FALSE: Tools called sequentially one at a time
