# Landing Analysis: PLAN-114 — Orchestrated-plan detection fails silently

epic: truthful-signals
workstream: WS-01
pr: [#1057](https://github.com/cuioss/plan-marshall/pull/1057) — merged as `eab1b2e88`

> Every claim below was corroborated against ground truth before recording. The plan's
> landing message and the operator paste were treated as leads.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — accept the three settled id forms + distinguishable detection outcome | shipped-as-specified | `_orchestrator_inbox.py:105-128` defines `DETECTION_TOKENS` as a closed four-token vocabulary and `SourceIdClassification.detection`; `classify_source_id` returns the discriminated verdicts at `:420` (`unsafe_slug`), `:423` (`unrecognised_id`), `:424` (`not_orchestrator_pointer`) |
| D2 — dispatcher reports an unrecognised pointer instead of proceeding silently | shipped-as-specified | `phase-6-finalize/SKILL.md` +12 lines in the merged diff (Step 3 item 4b.a0 WARNING emission) |
| D3 — update the `inbox detect` describe-side contract | shipped-as-specified | `marshall-orchestrator/SKILL.md` +23 lines; `:793-807` exposes `detection` through the single detection seam |

**Diff corroborated**: `git show --stat eab1b2e88` = 5 files, +281/−40 — matching the message's claim
exactly. Test deltas confirmed: `test_inbox_envelope.py` +128, `test_finalize_orchestration_routing.py` +50.

⭐ **Self-verifying landing.** The `inbox detect` call this plan's own finalize made returned
`detection: orchestrated` from the newly-shipped detector — the fix exercised itself, and the 15
inbox messages it wrote are the observable proof the previously-silent path now works.

⭐ **Scope grew on evidence, not on assumption.** The single-detection-seam claim was a HYPOTHESIS in
the spec and was **confirmed by deriving the consumer set** (one runtime call site; two downstream
bodies are forwarded the verdict and contractually barred from re-issuing) rather than asserted. A
finding the request never carried — 14 assertions pinning the old 3-tuple arity across two modules —
was **migrated rather than deferred**. `unsafe_slug` was gained for free: it already existed as a
distinct branch being collapsed into the same silent negative.

⭐ **The over-acceptance guard is the right shape.** The grammar is an explicit three-way alternation,
not an optional group — an optional group would also admit `01-foo.md`, which is none of the three
settled forms. Pinned by test.

## Metrics and Anomalies

- Tokens: 2.2M across 6/6 phases
- Duration: 1h42m worked
- Finalize: 22/22 steps done

**Anomalies — three, all infrastructure, none caused by this change:**

1. **`status.json` internally inconsistent** — `current_phase: 6-finalize` while `phases[].2-refine`
   stayed `in_progress`. The light lane collapsed the refine envelope and never closed the row.
2. **`worktree-remove` timed out twice** at a hardcoded 60s inner `git` ceiling, leaving a
   half-deleted tree; completed via the doc's own sanctioned `--force` at 600s.
3. **The pre-merge review barrier would have falsely blocked the merge.** `fetch_findings` deduped
   pr-agent's already-stored comment, emptying `participated_bots`, and `branch-cleanup.md` says to
   feed exactly that set to the predicate → `pr-agent: absent`. Re-derived from the store
   (`pr-agent:issue_comment`, reviewed sha == HEAD) → `complete`. ⭐ **Recorded in the decision log
   rather than laundered** — the correct handling of a signal the operator's own machinery got wrong.

## Routing and Merge Behavior

- **Review: THIN, and verified so post-merge.** `ci pr comments --pr-number 1057` returns 4 comments:
  - `sourcery-ai` — **hard weekly quota** ("reached your weekly rate limit of 500000 diff characters")
  - `coderabbitai` — **rate limited, review never started** ("you've reached your PR review limit, so
    we couldn't start this review")
  - `cuioss-review-bot` (pr-agent) — informational Guide only: *PR contains tests / No security
    concerns / No major issues detected*. Zero actionable content.
  - `cuioss-oliver` — triage disposition recording exactly that.

  ⛔ **Only one bot participated, informationally. This green finalize is NOT a reviewed diff.**
  Both refusals are *stated in the bots' own comment bodies* — the check states would not have shown it.

  ⭐ **CodeRabbit's refusal says "Next review available in: 2 minutes"** (posted `15:14:56Z`). That
  window is long past, so a re-review IS obtainable now via `@coderabbitai review` — this is a
  recoverable coverage gap, not a permanent one.

  ⭐ CodeRabbit's refusal body still enumerates the 5 files it *would* have reviewed, and names
  `test/plan-marshall/phase-6-finalize/test_finalize_orchestration_routing.py` — independently
  corroborating the retrospective's phantom-path finding below.

- **CI/merge**: 12/12 checks green; merged via queue as `eab1b2e88`; branch and worktree removed;
  working tree clean. No rebase conflicts, no surface collision with the four concurrently-launched
  plans — the disjointness pairing held.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-114 --status shipped`
- [x] row `pr` stamped — `1057`
- [x] row `landing` stamped — `landings/PLAN-114.md`
- [x] row `plan_marshall_plan_id` stamped — `orchestrated-plan-detection-fails-silently`
- [x] epic.md queue reconciled from status.json
- [x] START-HERE block regenerated
- [x] resume_anchor updated
- [x] 15 inbox messages drained

## Follow-Ups

1. ⛔ **Post-merge revisit owed on #1057** — and CodeRabbit is re-triggerable now. Standing rule,
   recurrence n=5.
2. **The `change_type` mis-scoped read is broader than PLAN-112's fix** — `phase-4-plan` takes
   `change_type` from the **first deliverable**, so a plan opening with a read-only discovery
   deliverable reports `verification` however much its later deliverables mutate. Recorded as an
   Open Defect.
3. **Outline declared a path that has never existed** —
   `test/plan-marshall/marshall-orchestrator/test_finalize_orchestration_routing.py`; the real file
   is under `phase-6-finalize/`. It propagated unchecked into the scope estimate and the manifest.
   **Nothing stat'd it.** Recorded as an Open Defect — a phantom path that survives into a manifest
   is the same family as this session's phantom-plan-ID citations.
4. **Five process defects** filed as candidate-lessons (light-lane `pr_title` producerless consumer,
   light-lane `references.json` missing `track`/`affected_files`, vacuous `--help` freshness
   evidence, `enabled_bots` doc drift, wrong compose-time `execution_tier: per_task` stamp).
5. **`worktree-remove` 60s hardcoded inner ceiling** — recorded as an Open Defect.
