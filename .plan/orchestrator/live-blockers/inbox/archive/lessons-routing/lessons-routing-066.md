envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-11-02T10:27:08Z

# CodeRabbit participation is read from the wrong signals: thread replies credit an unreviewed head, and a finished review in the new summary format is never credited

Severity: **high** (graded at the 2026-11-02 sweep). One side lets the gate pass when it should not; on the other, since `merge_participation_unproven` landed (PLAN-LB-100), every clean CodeRabbit review needs an operator override at the barrier.
Bundle: `plan-marshall` (`automatic-review` `standards/coderabbit.md` registry block and participation contract; `phase-6-finalize` pre-merge barrier).

## Sources (API-Sheriff epic api-sheriff-0-2-0)

- `api-sheriff-api-sheriff-0-2-0-055`: plan-v02-23-cookie-forwarding-policy-r2, PR cuioss/API-Sheriff#515 (merge bd730f5a)
- `api-sheriff-api-sheriff-0-2-0-074`: plan-v02-07-threat-classification, PR cuioss/API-Sheriff#537

## Observation

1. #515: after fix pushes, CodeRabbit's replies on existing threads, stamped at the new HEAD, were counted as participation for that HEAD. The barrier reported the review as current while the new commits had not been reviewed. A manual `@coderabbitai review` was refused inside the hourly window while automatic reviews were active.
2. #537: CodeRabbit reviewed two heads with no findings. Its check-run reported `success`, and its summary carries `final_review_risk_coverage` with `coveredCommitId` equal to the head and `kind: reviewed`. The rewritten summary has no `<!-- recent_review_start -->` marker, so the result was `participation_complete: false` and `coderabbit:refused_awaitable`; an older `Review rate limited` reply was still counted. automatic-review needed a forced done twice, and the merge needed `barrier-ask-override`.

## Ground truth (c431a8193)

- `coderabbit.md:48-53`: `participation_evidence` is review_body, inline and issue_comment; only issue_comment requires a marker (`<!-- recent_review_start -->`, `:53`). `inline` (`:50`) requires none, so any per-line reply counts.
- `final_review_risk` / `coveredCommitId` are read only by `runbook-lane`; automatic-review and `bot_registry.py` do not read them.
- PLAN-LB-100 (#1883, b399401ee) made `pre_merge_gate merge` refuse `merge_participation_unproven`, so an uncredited clean review now blocks every merge until an override.
- Nearest earlier filing: `lessons-routing-050` (participation from an edited comment, to parked PLAN-LB-46); it covers neither the new summary format nor credit from thread replies.

## What to consider

- Credit CodeRabbit only from evidence bound to the candidate head: `coveredCommitId == head` with `kind: reviewed`, or the completed `CodeRabbit` check-run on that head. Never credit thread replies or acknowledgements.
- Let a finished review of the current head override an earlier quota refusal.
- Do not post the manual trigger while automatic reviews are active.
- Fixtures: thread replies at HEAD with an older `coveredCommitId` = not reviewed; a new-format summary at HEAD = reviewed. Reuse the runbook lane's reading instead of writing a second parser.
