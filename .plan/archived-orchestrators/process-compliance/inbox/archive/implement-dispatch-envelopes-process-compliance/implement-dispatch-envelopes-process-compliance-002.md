envelope_version=1
sender_type=plan
sender_id=implement-dispatch-envelopes-process-compliance
epic=process-compliance
kind=finding
created=2026-09-22T18:51:36Z

# Run record from plan implement-dispatch-envelopes-process-compliance (PLAN-05 implementation)

Plan: implement-dispatch-envelopes-process-compliance, phase 6-finalize in progress.
PR: #1583 (feature/implement-dispatch-envelopes-process-compliance), CI green on both
heads (bcb392a, c1ec63949). Enqueued to the platform merge queue; landing not yet
observed (Branch F: mutex released, branch intact, tail deferred to re-entry).

## Deliverables (all implemented, verify green)

1. Step-owned dispatch body contract (`requires_prompt_fields`, author/verifier
   choreography, generic-deferral rule) in phase-5 operations.md.
2. Fix-task loop-back dispatch envelope (carried vs omitted fields) + null-envelope
   reassignment rule on the inject_project_dir seam.
3. `loop_back_target` required on every verification-feedback `loop_back` return.
4. Closure tests (test_dispatch_envelope_contracts.py) pinning each contract.
   Whole-tree verify: 27585 tests green. Review triage: 8 findings, all resolved
   (1 fix task TASK-5 executed, 2 taken_into_account).

## Process issues filed

1. Freshness gate `build_scope_narrow` on module-scoped builds: `verify plan-marshall`,
   `module-tests plan-marshall`, `quality-gate` rows were refused as evidence with
   `canonical_performs_too_few_analyses` / `scope_narrower_than_change`; only whole-tree
   `verify` (27585 tests) satisfied the gate. For a change confined to one bundle this
   doubles build cost per push. Suggest documenting which canonical+scope the gate
   demands per footprint class, so the first build is the covering one.
2. Loop-back execute envelope returned `status: blocked` (worktree freshness
   build_scope_narrow) with tasks_completed=5/tasks_remaining=0 and TASK-5 done+committed.
   A blocked label over an empty queue is ambiguous; recorded clean_exit_queue_empty with
   the label preserved in the decision log. Suggest the envelope distinguish
   blocked-with-remaining-work from blocked-with-empty-queue.
3. Triage-created fix task arrived with `envelope_id: null` (known -005 recurrence);
   re-ran `pack-envelopes` at loop-back entry per the new D2 contract, but the packer
   refused on missing `predicted_cost_tokens`, which triage never stamps. Seeded cost
   via `derive-cost-size` signals (S/25000) then packed. Suggest triage stamp cost at
   allocation, or the packer default it.
4. Light-lane pre-dispatch closure needed two exemptions: `transition --completed 2-refine`
   required `--allow-bare-transition` (no refine artifact on the skipped lane) and
   `phase_handshake capture --phase 2-refine` required seeding `metadata.pr_title`
   (Step 13 never ran). Suggest the light-lane branch document both.
5. `request.md` Step 5.2 full-file Write clobbered the allocator stub frontmatter
   (`clarified_request`/`original_input` missing → change_type heuristic unresolved).
   Suggest append-body-only wording.
6. Pre-merge review barrier: cuioss-review-bot (required) showed only stale
   issue-comment evidence; operator granted merge-anyway (CodeRabbit review handled).
   Recorded as HEAD-bound WARNING grant at c1ec63949.
