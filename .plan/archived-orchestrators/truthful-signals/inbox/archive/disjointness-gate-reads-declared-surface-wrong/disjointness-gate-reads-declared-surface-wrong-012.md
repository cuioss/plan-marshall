envelope_version=1
sender_type=plan
sender_id=disjointness-gate-reads-declared-surface-wrong
epic=truthful-signals
kind=candidate-lesson
created=2026-08-30T10:44:49Z

component=plan-marshall:phase-6-finalize
category=anti-pattern
source_plan=disjointness-gate-reads-declared-surface-wrong
source_pr=1366

# Re-running a subset of a verification gate is not re-running the gate — the arm that was skipped is the one that catches what the new code introduced

## What happened

CI went red once on PR #1366, on the first PR HEAD `e7299d8e6`. `decision.log`
`70f088` (2026-08-29T21:52:54Z) records the mechanism exactly:

> `verify/verify` failed on a single mypy `no-any-return` in
> `test_orchestrator_corpus.py:3235` (`_own_unreadable_tally`). Root cause:
> `pre-push-quality-gate`'s three arms ran green BEFORE the six self-review rounds
> added that helper; every post-round re-verification re-ran quality-gate +
> module-tests but never test-compile, and only test-compile reads `test/` with mypy.

So the gate passed **completely** at a point when the offending code did not exist,
and thereafter was re-run **partially** — two arms of three — across six rounds that
each added code. The one arm never re-run is the only arm that type-checks `test/`,
and every one of the six rounds was adding test code.

Fixed and pushed as `ba5bd9f27`.

## Why it matters

The failure is structural, not an oversight of attention. Each partial re-run was
individually reasonable: the rounds were editing docs and scripts, and quality-gate
plus module-tests are the fast, obviously-relevant arms. But "obviously relevant" was
judged against *what the round intended to change*, while the escape came from
*what the round incidentally added* — a test helper.

The general shape: a multi-arm gate's arms partition the surface. Re-running a subset
re-verifies a subset, but the pass is reported against the **gate's** name, so the
record reads as a full verification. Nothing in the run's structured state
distinguishes "the gate passed" from "two of its three arms passed". The evidence for
this defect existed only as one WARNING line of `decision.log` prose (see sibling
candidate message 005 for why: the red run was never archived, so no structured
consumer can see it — that message files the *archival* defect for
`manage-ci-artifacts`; the process defect below has no owner and is filed here).

## Rule

**A gate is re-run whole or it is not re-run.** After any change to the tree —
including a change made in response to a review round — re-run the *complete* gate
before treating its verdict as current. Do not select arms by relevance to the
intended change; the class that escapes is by definition the one you did not
anticipate.

Where a full re-run is genuinely too expensive to repeat per round, the record must
say which arms ran, so a later reader sees a partial verification as partial rather
than as the gate's own green.

## Adjacent observation from the same entry

`70f088` also records: a whole-tree `verify` exceeds the marshalld 740s budget and
returns `job_status timeout`, so the arms must be run individually or the budget
raised. That constraint is very likely *why* the arms were split in the first place —
which makes the remedy a budget/scheduling question, not merely a discipline
question. A rule that says "always re-run everything" against a gate that cannot
complete within budget will be silently violated again.

## Remedy shape

Two halves, both needed:

1. Have `pre-push-quality-gate` record **which arms ran** on each firing, and treat a
   firing that did not run every arm as a partial verification in `status.json` —
   not as a `done` firing.
2. Resolve the budget constraint that forces arm-splitting (raise the marshalld
   budget for whole-tree `verify`, or make the arm-split explicit and complete rather
   than ad-hoc), so the complete re-run is actually reachable.
