envelope_version=1
sender_type=plan
sender_id=plan-150-close-the-namespace-conversion
epic=test-quality
kind=landing
created=2026-09-02T22:03:37Z

## What landed

plan-150-close-the-namespace-conversion shipped as #1383 (merged) — the architecture-and-orchestration slice's hand-built namespace conversion is closed.

```landing-facts
schema=landing-facts/1
plan_id=plan-150-close-the-namespace-conversion
epic=test-quality
pr=#1383
merge_state=merged
deliverables_total=8
deliverables_done=8
total_tokens=4376049
total_wall_seconds=26640
steps=finalize-step-sync-baseline:done,project:finalize-step-lessons-housekeeping:done,pre-push-quality-gate:done,project:finalize-step-plugin-doctor:done,pre-submission-self-review:done,finalize-step-simplify:done,architecture-refresh:done,push:done,create-pr:done,project:finalize-step-era-stamp-fill:done,ci-verify:done,automatic-review:done,branch-cleanup:done,project:finalize-step-deploy-target:done,project:finalize-step-sync-plugin-cache:done,project:finalize-step-review-retrospective:done,plan-marshall:plan-retrospective:done,lessons-capture:done,finalize-step-preference-emitter:done,record-metrics:done,finalize-step-print-phase-breakdown:done,emit-landing:done,archive-plan:pending
step.branch-cleanup.merge_commit_sha=80da16e30f6f49c8ff7212a303b2e7f9c867d740
step.finalize-step-sync-baseline.action=noop
step.finalize-step-sync-baseline.upstream_commit_count=0
outcome.hand_built_namespace_before=547
outcome.hand_built_namespace_after=1
outcome.simple_namespace_before=13
outcome.simple_namespace_after=13
outcome.parse_ns_before=1
outcome.parse_ns_after=78
outcome.collected_items_before=3905
outcome.collected_items_after=3909
outcome.blocked_sites=0
outcome.whole_tree_verify_tests=23739
```

## Residue

**The spec's sizing was beaten, and the epic should re-cost the remaining WS-02 work against
that.** PLAN-150's Scope Note expected a second run and treated partial completion as
acceptable ("Convert by directory and commit per directory, so a run that exhausts its budget
lands what it did"). All eight deliverables completed in one run. The cost was real —
4.38M tokens and 7h24m wall — and crossed both `broad + tech_debt` error anchors (≥3.5M
tokens, ≥240 min worked), so the over-delivery was bought, not free.

**The distribution is more concentrated than the spec assumed.** Only 9 of the 29 enumerated
slice entries carried any hand-built site; the other 20 were already clean. `plan-orchestrator/`
alone held 277 of 547 (51%). A future slice plan sized from a directory count rather than a
measured per-directory distribution will over-estimate.

**Two production-relevant defects were exposed by the conversion, which is its whole point.**
`test_phase_1_init.py` drove lesson id `2026-04-15-099`, which `validate_lesson_id` rejects
(the format is `YYYY-MM-DD-HH-NNN`) — a contract test pinning what phase-1-init invokes
through the executor was using an id that path could never deliver. `test_lifecycle_handshake_e2e.py`
carried an unreachable stub branch matching `--task`/`task` where the CLI declares
`--task-number`/`task_number`. Both were invisible to a hand-built namespace and both surfaced
the moment the parser became the source of truth.

**External review contributed zero findings; every defect came from in-house gates.**
pr-agent posted "no major issues", CodeRabbit posted "no actionable comments" with Merge Risk
Minimal, sourcery refused on diff size (cap 150000 diff characters vs 4086 changed lines).
`pre-submission-self-review` found 4 real defects the bots did not, all fixed in `4f8b0733a`.
This is a gate-versus-review parity signal the epic may want to weigh when deciding how much
review-bot latency to buy on future slice plans.

**Two review-verdict defects were filed and are unresolved — they are two halves of one
end-to-end gap and should be scheduled together.** `cc3ce9` (detection): the automatic-review
noise pre-filter consumes CodeRabbit's clean-review publish shape, so a bot that reviewed
cleanly scores `absent`; the loop cannot converge because re-firing re-filters the same
comment identically. `cf3722` (transport): even when participation IS detected, nothing
persists `bot_states` where the order-990 post-merge review-retrospective can read it, so its
grade is structurally always `indeterminate`. This run merged past `cc3ce9` on a HEAD-bound
`barrier-ask-override` grant carrying the evidence, not by forcing the step.

**`198a01` is deferred plan-sized work, not a defect this plan left broken.** The `_variant`
helper is duplicated byte-identically across 38 test modules (~500 lines); `conftest.py`
already owns its sibling `parse_ns` and already imports `copy` and `Any`. Consolidating means
one shared helper plus ~230 call-site renames plus per-file import pruning — a plan, not a
finalize-step edit.

**Four measurement defects in the plan machinery were surfaced by the retrospective and are
not this plan's to fix.** Build-time attribution is entirely lost (27 change-ledger build rows
written `plan_id: NO_PLAN` while 175 `pyproject_build` calls consumed 71.5% of plan script
time); per-dispatch context load is 0 of 13 measured because every `record-dispatch-boundary`
call site omits the four context-load flags; `[VERIFY]` emission ratio is 0.38 (3 lines against
8 verifying deliverables). A fourth — "`manage-metrics enrich` never ran" — is an ORDERING
ARTIFACT, not a real gap: `enrich` is executed by `record-metrics` at order 996, after the
retrospective measures at 995, so it structurally cannot have run at measurement time. It
subsequently ran clean (641 messages, 6 four-field phases attributed).

**Out of scope by the spec, still owed elsewhere:** ~20 rule-invisible docstring B3 citations
(PLAN-130 owns that sweep tree-wide) and 10 `spec_from_file_location` preamble sites
(PLAN-135). Both were reported, neither fixed, exactly as the spec required.
