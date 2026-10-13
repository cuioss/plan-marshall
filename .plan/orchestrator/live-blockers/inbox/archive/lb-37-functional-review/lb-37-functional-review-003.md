envelope_version=1
sender_type=plan
sender_id=lb-37-functional-review
epic=live-blockers
kind=finding
created=2026-10-12T19:04:05Z

# Follow-up: ceremony selection re-adds steps the no-push filter dropped

**From:** lb-37-functional-review (PLAN-LB-37), raised by CodeRabbit on PR #1757 (thread PRRT_kwDOQ3xasM6rlaMn, `_manifest_rules.py`)

## Observation

The run is local-only when `phase-5-execute.commit_and_push` is false. In that case the commit-push filter drops the push-related steps (`_COMMIT_PUSH_DROP_STEPS`). The ceremony gates then map a step's `lane: minimal` to `always`, and `_apply_ceremony_finalize_selection` adds the step back without consulting `commit_and_push`. So a local-only run can still schedule `pre-push-quality-gate`, `functional-review` or `code-review`.

## Status

This was already the case before PLAN-LB-37 and applies to every ceremony gate, including the quality-gate step's own gate. PLAN-LB-37 extended the same gate mechanism to the two review steps. The finding was declined there as outside its scope.

## Decision needed

Decide which rule wins. Either a `minimal` lane overrides "no push" (the step runs in a local-only plan), or "no push" is binding after ceremony selection. A review step plausibly keeps value in a local-only run, while a pre-push gate does not, so the answer may differ per step class. Then apply the rule uniformly in `_apply_ceremony_finalize_selection` and pin it with a test.
