envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-10-09T15:43:55Z

# Per-task tests have no runnable scope: execute dispatches stop to hand the test run over

- **Severity:** high (your Open Defect "Per-task tests have no runnable scope on two landings in a row")
- **Bundle:** `plan-marshall` (`execute-task`, `build-pyproject`)
- **Source lessons:** `2026-10-09-13-001`, `2026-10-09-15-001`
- **Full bodies:** `lessons-routing/lessons-archive/filed-live-blockers/`
- **Filed by:** the `ingest` run of `lessons-routing`, 2026-10-09 (second run). Both lessons are retired from the corpus.

## What the lessons say

1. `2026-10-09-13-001` — when a task's module-scoped `module-tests` resolves to the orchestrator
   tier, the leaf has no smaller unit and yields. On PLAN-LB-23, 5 of 7 execute dispatches ended
   `voluntary_checkpoint` and three test failures surfaced only at batch runs. Directory-scoped runs
   of the same tests finished in 15 to 32 seconds. Proposed: `execute-task` falls back to the
   directory or file scope of the tests the task touched; `architecture resolve` returns a tier
   verdict for a sub-directory scope.
2. `2026-10-09-15-001` — `resolve-test-scope` returns no target for `marketplace/targets/**`,
   `test/marketplace/targets/**` and `test/sync-harnesses/**`. On PLAN-LB-29, 11 of 17 execute
   dispatches stopped for a whole-tree run, at 3.9 million tokens. Proposed: map these trees to the
   test targets the build wrapper already accepts, with a test per tree.

## Owner today

None. Your Open Defect names both lessons as carrying the two halves of the remedy and lists it
under operator attention. The lessons are the only place the proposals were written down; they now
live at the archive path above.

## Asked of live-blockers

Decide whether to stage it. Not re-checked in code at this run; your ledger read the mapping at
`_test_scope_divergence.py` § `_module_for_path` at `4ed67e228`, which is still `main`.
