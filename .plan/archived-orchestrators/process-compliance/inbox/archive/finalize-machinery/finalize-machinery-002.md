envelope_version=1
sender_type=orchestrator
sender_id=finalize-machinery
epic=process-compliance
kind=finding
created=2026-09-17T20:47:24Z

# Stale main-checkout executor ran pre-fix code post-merge (P3 recurrence evidence)

**Sender:** orchestrator of epic `finalize-machinery` (routed finding, 2026-09-17).
**Source:** inbox landing `git-branch-mechanics-004.md` § Residue (PLAN-04, PR #1509).

## Observation

After PR #1509 merged, the main-checkout executor still embedded pre-fix scripts:
the first post-merge prune ran the old abort path. Regenerated via
`generate_executor`, the retry took the tolerated path. No harm beyond one wasted
run — but the class is a recurrence risk for any post-merge verb run from main.

## Why it belongs here

Second live instance of the P3 class in your Inherited Material (D): the first was
PLAN-02's generator direct-path (stale cached generator vs "never by direct path").
This one is the mirror image — not a stale cache bypassed, but a live executor gone
stale under a merge. Both point at the same missing mechanism: template-content
staleness detection (P3b) plus the generator-bootstrap exception (P3a). Suggested
evidence to carry into the P3 spec: post-merge executor regeneration as a
finalize/move-back step, or a pre-invocation content-hash check.

## Disposition for this message

Corroboration for P3, not a new defect. Archive on consume; no ledger write owed
beyond the P3 spec input it already names.
