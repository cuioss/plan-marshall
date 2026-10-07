envelope_version=1
sender_type=plan
sender_id=audit-report-path-ignores-plan-dir
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-07-30T09:32:08Z

component=plan-marshall:automatic-review
category=bug
title=A crashed review_completeness must block mark-step-done — check conclusions cannot express non-participation

# A crashed participation gate is worse than no gate

## Observation

On PR #1063, round 2 (HEAD `2475cd179`, the loop-back commit that actually shipped):

- `review_completeness check` was **argparse-rejected** at 07:48:27 (`exit_code=2`, `failure_kind=argparse_rejection`). This is the one component in the system that models review participation properly — it takes `--participated-bots` as *evidence-typed* `bot_kind:evidence_kind` pairs, splits refusals into `refused_awaitable` / `refused_hard`, and gates the quorum on required bots only.
- The `automatic-review` step nonetheless recorded `outcome: done` at 07:49:50.
- The persisted CI manifest for that run (`artifacts/ci-runs/30522438711/manifest.toon`, `head_sha: 2475cd179`) records:

  ```
  Sourcery review, SUCCESS
  CodeRabbit,      SUCCESS
  final_status:    success
  ```

- The plan's own review-retrospective states the truth plainly: *"the final commit that actually shipped (`2475cd179`) was reviewed by nobody."* Sourcery hard-quota-refused both rounds and produced no artifact of any kind; CodeRabbit explicitly declined to re-review an already-reviewed commit; pr-agent — the **required** bot — was never re-triggered and never saw the commit.

## Mechanism

Two failures compose:

1. **The gate crashed and the pipeline continued.** An `exit_code=2` from the completeness checker is indistinguishable, to the step, from not having run it. The rejection is reproducible: passing an empty-valued list flag (e.g. `--participated-bots` with no value — the natural shape when *nobody participated*) yields exactly the logged signature `review_completeness.py check: error: a…`. The gate is therefore most likely to crash precisely in the scenario it exists to detect.
2. **The surviving evidence cannot represent the negative case.** A bot's *check conclusion* is `SUCCESS` whether it reviewed and approved, refused on quota, or declined as redundant. There is no conclusion value meaning "did not review". So a green check set is not weak evidence of review — it is **no evidence at all**, and it looks identical to strong evidence.

## Rule

- A non-zero exit from `review_completeness` MUST block `mark-step-done` for `automatic-review`. A crashed gate is an *unknown* verdict, never a pass.
- Never substitute check conclusions for a participation record. The only admissible evidence is an evidence-typed participation pair; `ci pr comments` presence is necessary but not sufficient (a comment *from* a bot is not a review *by* it), and a check conclusion is not even necessary.
- The completeness checker must accept the zero-participation case without argparse error — that input is not malformed, it is the finding.

## Relation to the corpus

Directly reinforces the standing "review bots — check states lie in both directions" body of evidence, and adds a new, sharper instance: previously a *detected* refusal was reported as a clean review (#1026); here the detector itself crashed, and the fallback signal was structurally incapable of dissent. Companion to the same plan's `review-bot participation is per-commit, not per-PR` lesson — that one explains *why* the final commit was unreviewed; this one explains why nothing stopped it.
