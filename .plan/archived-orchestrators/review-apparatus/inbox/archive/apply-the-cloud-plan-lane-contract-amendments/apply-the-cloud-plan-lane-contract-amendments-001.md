envelope_version=1
sender_type=plan
sender_id=apply-the-cloud-plan-lane-contract-amendments
epic=review-apparatus
kind=candidate-lesson
created=2026-09-05T06:17:20Z

component=plan-marshall:phase-6-finalize
category=bug
status=active

# A self-review round can return findings and never persist them, so the qgate store under-counts

## Context

`pre-submission-self-review` fired six times on plan `apply-the-cloud-plan-lane-contract-amendments`. Two of those rounds — round 4 and round 6 — each returned 2 findings that were never written to `artifacts/findings/qgate-6-finalize.jsonl`. The store holds 5 findings, all `resolution=fixed`; the true rounds-1-to-6 defect count is **9**.

Both unpersisted rounds were fixed on the merits (round 4: `SKILL.md:2242` contract_drift and `SKILL.md:1366` stale_count_prose; round 6: `SKILL.md:1376` contract_drift and `SKILL.md:1378` same_document_contradiction). In both cases the fix agent correctly refused to file-then-resolve substitute records rather than inventing `hash_id`s to close — so the loss leaves no trace inside the store.

## Root cause

Two distinct causes, one symptom. Rounds 1-4 ran outside contract because the dispatcher omitted the required `candidates` prompt-body field, and round 4's Step 4 finding-persistence deviated with it — that half has a filed root cause, lesson `2026-09-02-18-001`. Round 6 hit the same non-persistence **after** the dispatch shape had changed, so the persistence gap is separately live and is not closed by fixing the candidates-field omission.

## Proposed action

Make finding persistence a post-condition of the self-review round rather than a step inside it: when a round returns a non-empty findings list, the dispatcher verifies that the qgate store gained a matching record per finding before accepting the round's return, and fails the step otherwise. A round that reports N findings and persists fewer than N is a contract violation the caller can detect without trusting the leaf.

## Evidence

- aspect: logging_gap_analysis — "Self-review rounds 4 and 6 each returned 2 findings that were never persisted; store holds 5, true count is 9"
- decision.log 2026-09-04T15:54:42Z — "Round 4 returned 2 findings ... but did NOT persist them to qgate-6-finalize.jsonl, so no hash_id exists for either ... Root cause: the dispatcher omitted the required 'candidates' prompt-body field in rounds 1-4"
- decision.log 2026-09-05T00:33:17Z — "Round 6 returned 2 findings ... but did NOT persist them to the qgate store - the same non-persistence gap round 4 hit"
- `manage-findings qgate list --plan-id apply-the-cloud-plan-lane-contract-amendments --phase 6-finalize` → `total_count: 5`
- Downstream consequence: the retrospective brief for this very plan arrived stating "5 defects found by pre-submission-self-review across rounds 1-4", a number read off the lossy store.
