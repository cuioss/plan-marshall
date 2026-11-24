envelope_version=1
sender_type=orchestrator
sender_id=libraries-initial-implementation
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:07:43Z

component=plan-marshall:phase-6-finalize
category=improvement
title=phase-6-finalize: re-sync with the base before the head-bound review steps run, not at branch-cleanup
source_lesson=2026-11-24-07-008
source_repo=git-document-repository (epic libraries-initial-implementation)
source_created=2026-11-24

# phase-6-finalize: re-sync with the base before the head-bound review steps run, not at branch-cleanup

Source: orchestrator-observed fact, confirmed by the plan's work and decision logs.

Evidence:
- 2026-11-24T06:27:06Z decision: the pre-merge conflict gate found overlap_no_content_conflict against threshold no_overlap_only; the operator chose "Rebase and force-push onto the base", which overrode use_merge_queue=true with queue_wait=forbidden.
- 06:39:16Z work: branch-cleanup completed with outcome=loop_back.
- 06:39:32Z work: "Loop-back iteration 1/3 for branch-cleanup (target=6-finalize): re-firing finalize-step-simplify, ci-verify, automatic-review, sonar-roundtrip at rebased head 5baca51".
- The second pass ran 06:39 to 06:50 (simplify about 74k tokens, automatic-review about 237k tokens and 314 s, sonar about 83k tokens), then branch-cleanup merged via the queue at 06:57 (f7eda4e).

Observation: main had moved on (b30ec14 and the ledger landing) while the PR waited out the review-bot windows. The late rebase was content-clean, but every verdict bound to the old head had to be produced again.

Candidate rule (for the orchestrator to judge): when a PR waits long on review-bot windows, re-sync with the base before the head-bound review steps run, not at branch-cleanup, so one pass of simplify, ci-verify, automatic-review and sonar covers the head that lands.

Context: plan plan-20-leftover-fixes-2, PR 69.


Source: inbox plan-20-leftover-fixes-2-013. Related: 2026-11-18-07-007 (loop-backs re-fire every step).
