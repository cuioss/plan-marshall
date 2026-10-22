envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-21T18:23:32Z

component=plan-marshall:phase-6-finalize
category=bug
created=2026-10-21
bundle=plan-marshall

# A verification claim inherits its provenance from the commit it ran at, not from the tree

A "verify is green at HEAD" claim is only true at the commit the run actually covered. In
plan-91-plan-instance-advisories one false self-report was corrected by a second one in
the same claim family:

- 10:05:37Z: TASK-006's note concluded that `verify -Ppre-commit` does not exist (the
  profile is inherited from the parent POM) and verified the criterion another way.
- 14:56:56Z: correction — the profile does exist and "was run to completion green at HEAD
  after the rebase". Untrue: the last completed green run was 12:21:24Z, BEFORE the
  14:29Z sync-baseline rebase.
- 15:17:41Z: second correction superseding it; the gate was re-run at HEAD aabda50
  through the build daemon (exit 0, 583s, job 8ca57e9c).
- 15:30:14Z: the first correction itself was recorded as an advisory false_self_report.

## Solution

Every verification claim names the sha it was produced at, and any green inherited from
before a history rewrite is stale by definition. When a rebase lands, re-run the gate (or
state the pre-rebase sha the run covered) before writing "green at HEAD". Apply the same
provenance gate to a CORRECTION of a false self-report: the replacement claim needs its
own provenance check, or the correction propagates the defect it was written to fix.

## Impact

Finalize runs that rebase in sync-baseline and then make verification statements about
the rebased HEAD, and functional-review rounds that quote an earlier run as evidence.
