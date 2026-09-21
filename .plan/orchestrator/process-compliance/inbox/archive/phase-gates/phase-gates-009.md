envelope_version=1
sender_type=plan
sender_id=phase-gates
epic=process-compliance
kind=candidate-lesson
created=2026-09-19T14:25:04Z

component=plan-marshall:phase-6-finalize
category=improvement
created=2026-09-19
bundle=plan-marshall

# Barrier-ask-override precedent for spend-capped stale review bot

The automatic-review barrier force-doned with cuioss-review-bot stale (backend spend-capped, re-review triggers silent) while CodeRabbit fully reviewed with both findings closed and CI green. The operator selected merge-anyway, recorded as a HEAD-bound gap-class `barrier-ask-override` authorization in status metadata, and the merge-queue squash landing succeeded.

## Solution

When a required bot is provably incapacitated (stale participation + failure notice) and every other signal is green, escalate to the operator and persist the override as a merge-authorization record bound to HEAD and gap class — never as an undocumented skip.

## Impact

Future plans hitting a spend-capped or otherwise silent required reviewer have a recorded precedent: escalate, bind the authorization, land, and keep the gap auditable.

## Evidence

- status.metadata.merge_authorizations barrier-ask-override @ b72e26f4c, gap_class review-barrier-gap
- plan phase-gates, PR #1540 merged as 433d0a6, epic process-compliance
