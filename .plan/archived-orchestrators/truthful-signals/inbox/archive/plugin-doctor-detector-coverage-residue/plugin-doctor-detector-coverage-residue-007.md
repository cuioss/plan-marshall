envelope_version=1
sender_type=plan
sender_id=plugin-doctor-detector-coverage-residue
epic=truthful-signals
kind=candidate-lesson
created=2026-08-25T07:38:13Z

component=plan-marshall:automatic-review
category=bug
created=2026-08-25

# A re-fired automatic-review leaves its second round's comments un-ingested

## Context

`automatic-review` fired twice on this plan: round 1 at HEAD `981a3bc9` (15 `pr-comment` findings
ingested, all carrying `reviewed_commit_sha` `981a3bc9`), and round 2 at the merged HEAD `98f8bc27` (12
new comments, confirmed live by `wait-for-comments` new_count 12, baseline 12 -> final 24). Only round
1's comments are in the finding store.

## Root cause

Comment ingestion is internal to `automatic-review`'s workflow body and there is no standalone verb
that fetches PR comments into the store after the fact (`manage-findings ingest` is finding-to-lesson
promotion, schema `finding`, not comment ingestion -- it returned `skipped` for all 20 qgate findings
when tried). `finalize-step-review-retrospective` deliberately runs late (order 990) specifically so
the store is complete by the time it compares reviewers, but a re-fire defeats that ordering guard
silently: it runs late as designed, over a store still missing the later round. Here the loss was not
marginal -- round 2 is the round CodeRabbit found the merge-blocking correctness defect (see the sibling
lesson on 5bdbb9), so a reviewer comparison over round 1 alone would have understated the
best-performing reviewer precisely where it performed best.

## Proposed action

Either re-ingest comments on every `automatic-review` firing, or have `finalize-step-review-retrospective`
assert that `max(reviewed_commit_sha)` in the store equals the merged HEAD and refuse (or publish the
gap) when it does not -- the population-vs-claim shape this plan's epic exists to close.

## Evidence

- Finding a02741 in this plan's qgate store, measured live at this plan's own finalize
- aspect: execution_context_dispatch_audit -- dispatch_coverage classified `automatic-review` as
  `dispatched` on both firings with clean channel confidence (nominal), so the gap is in the ingestion
  path, not in dispatch discipline
