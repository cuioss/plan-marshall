envelope_version=1
sender_type=plan
sender_id=architecture-store-query-truthfulness
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-09-15T07:56:22Z

component=plan-marshall:manage-architecture
category=improvement

# Two hardcoded mirrors of one command set that had never been compared to each other

Source: PR #1489 CodeRabbit inline finding 1b9139 (resolution=fixed as a SPLIT
disposition; TASK-041 plus lesson 2026-09-14-04-001).

client-api.md's summary table had already drifted from the handler population, omitting
derive-verification, profiles and siblings. _cmd_client_handlers.py lines 6-12 hardcode
a count and roster of all 20 CLI handlers. A separate decision on the same PR
cross-checked client-api.md's 17 verb sections against that same document's 17-row
table. Those are two hardcoded mirrors of one underlying set that had never been
compared against each other.

## Solution

The disposition is the transferable part. The comment carried TWO separable asks and
they were answered differently:

- "derive or validate the table from the command registry" was SUPPRESSED as out of
  scope — no such registry exists to derive from, and building one is a scope expansion
  beyond a bug-fix plan. Carried forward as a lesson with two sibling registry-requiring
  findings from the same review.
- The handler-side half was ACCEPTED, because it needs no new registry.

Explicitly excluded: simply correcting the two numbers to agree. A corrected restatement
drifts again on the next verb added, so the fix must derive one from the other or add a
population-publishing cross-validation test.

## Impact

Establishes the boundary between "this needs a registry we do not have" (defer with a
recorded reason) and "the authoritative source is already in hand here" (fix now).
