# In-run reviews close over shrunken coverage, and one passed a real lost-data defect

Severity: high. Bundle: **plan-marshall** (`phase-6-finalize` code review, functional review, security audit, triage). Filed under RULING 2026-10-09 (a).

## Sources

- inbox `pm-mcp-core-m2-m4-322`, `-340`, `-342`

## Consolidated statement

Three independent coverage failures, each of which let a real defect through or would have:

1. **A delta round loaded 6 of the 22 rule-source skills** and closed the round; a later full round found a real lost-data defect (a move into a store that already holds an integrity key overwrites or deletes it in the clean-up). The delta narrows the files reviewed, not the rules applied — but nothing enforces that.
2. **The in-run code review passed four defects that CodeRabbit then raised**, two of them quoting rules the repository states in its own review path instructions ("a hardcoded list that must mirror a set defined elsewhere, unless derived from it"; "check a guard's predicate against the scenario the guard exists for"). The code-review leaf loads plan-marshall's rules and the language skills, but not the repository's configured `path_instructions`.
3. **An invariant-scoped fix loop.** A finding names a file and line range; the fix takes that as its scope, so six rounds each closed the cited site and the next round found the same invariant broken on a neighbouring path ("every path that removes a job from the running map settles it"). The operator granted two extra rounds after the budget was spent.

Related, graded medium: a security audit that read 5 of 17 fixtures and recorded `done` with "all examined" (root cause is the search inventory, filed separately).

## What is asked

- Have the code-review workflow verify the loaded rule-source count against the resolved set before it accepts a close verdict (fail closed on under-load), and have the verifier check the author's loaded set.
- Let the code-review step load the repository's configured review `path_instructions` as an extra lens, checking each changed file against the rules matching its path.
- When a finding breaks a stated invariant ("on every path", atomicity), require the fix task to restate the invariant, list every path that removes/settles/answers for the same state, and add one test per path (or name why a path cannot break it); the next verifier checks the list.
- A coverage-class leaf that could not read files of its footprint returns a coverage gap, never `done` with "all examined".

## Evidence

As recorded by the senders. Not re-verified against HEAD in this run.
