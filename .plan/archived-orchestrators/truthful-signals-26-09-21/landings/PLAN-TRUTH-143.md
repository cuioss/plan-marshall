# Landing Analysis: PLAN-TRUTH-143 — the orchestrator inbox has no delivery path and its corpus instruments publish an unmeasured zero

epic: truthful-signals
workstream: WS-01
pr: #1539 (https://github.com/cuioss/plan-marshall/pull/1539)

> Landing record for one shipped plan. Written by the `analyze` verb after
> verifying the operator's paste against ground truth: `git log`/`merge-base`,
> the CI abstraction's `pr view`, the archived plan's `status.json`, and the
> plan's own inbox landing message (`truth-143-orchestrator-inbox-delivery-path-020.md`,
> which carries a machine-readable `landing-facts` block the drain-completeness
> check reports `complete: true`). Every material claim below is corroborated,
> not merely restated from either source.

## Deliverable Fidelity vs Spec

Solution outline: 10 deliverables (D0–D9), 28 tasks. The landing-facts block
reports `deliverables_total=10`, `deliverables_done=10`. The plan's own
landing message flags one gap that deliverable-level completeness hides:

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D0 — re-ground carried claims (PLAN-TRUTH-100/131), settle 3 gate questions | shipped-as-specified | `corpus verdicts` is the settled verdict surface; no repo file modified (read-only, matches spec) |
| D1 — symmetric `(epic_slug, plan_id)` channel API | shipped-as-specified | `_orchestrator_inbox.py` write-replace per outline; PR body confirms "one symmetric `(epic_slug, plan_id)` channel address" |
| D2 — replace `undeliverable_to_running_plan` refusal with real delivery | shipped-as-specified | PR body: "This PR replaces that refusal with real delivery" — matches D2's stated root cause and design exactly |
| D3–D9 (hand-off checkpoints, taken-marker, corpus derivation-status tally, queue-row plan-id derivation, status-vocabulary settlement) | shipped, 1 task infeasible | Confirmed via PR body ("candidate-side derivation-status tally per `candidate_kind`", "queue row's plan id is derived from the row itself so a letter-suffixed id no longer collapses", "plan-queue status vocabulary is settled"). **Task 19** ("Derive the mailbox checkpoint plan id from `classification.plan_spec`", under D4, 0/2 sub-steps) is recorded `infeasible` by the plan's own landing message — invisible at the `deliverables_done=10/10` granularity. D4's other tasks (8, 9, 21) completed. |

**Not independently re-derived**: the full D3–D9 file-level diff against the outline was not re-read line-by-line for this report (60KB outline, large PR) — the verdicts above rest on the PR body's own change summary plus the plan's self-reported facts, both corroborated as genuine (PR state, commit ancestry) but not cross-checked deliverable-by-deliverable against the actual diff.

## Metrics and Anomalies

- Tokens: 19,921,101 total (confirmed in both `status.json` and the landing-facts block).
- Duration: 219,622s wall (~61h), per `record-metrics`.
- **Anomaly — expensive convergence.** `loop_back_iteration` reached 11. Firing counts from the landing message: `pre-submission-self-review` 13 (9 of 12 prior firings were `loop_back` to `6-finalize`), `finalize-step-simplify` 13, `project:finalize-step-plugin-doctor` 11, `project:finalize-step-lessons-housekeeping` 9. `push` recorded 1 `error` + 2 `failed` rows before succeeding. The plan's own message notes: "the 19.9M token total and 61h wall-clock are dominated by this re-entry, but no required key distinguishes first-pass cost from loop-back cost." The operator's paste narrates self-review converging at "round 17 (270→275 candidate passes)" — a different counter (self-review round vs. `loop_back_iteration`) from the same phenomenon; not contradictory, but the two figures should not be treated as interchangeable.
- **Anomaly — a step ran but is absent from the composed order.** `verification-feedback` fired twice (`loop_back` to `5-execute`, then `done`) but appears in neither `phase_6.steps` nor `candidate_steps` — it's inserted dynamically by the review-findings path. Its outcome rides the optional `step.verification-feedback.outcome=done` key instead. This matches the operator's paste ("One CodeRabbit finding (TASK-028) fixed via loop-back — pinned test coverage CodeRabbit correctly flagged as unpinned").
- **Anomaly — a step-contract gap the plan itself surfaced.** The dispatch running `emit-landing` did not carry the `orchestrated`/`epic` runtime inputs the step body declares as dispatcher-resolved. The plan resolved its epic via `orchestrator inbox detect` on `request.md`'s `source_id` instead (`orchestrated: true`, `epic: truthful-signals`) rather than following the guard's fail-closed posture literally, which — one step before `archive-plan` destroys the plan directory — would have silently dropped the hand-off. This is recorded here as a genuine defect in the finalize step contract, not an operator error; see Follow-Ups.

## Routing and Merge Behavior

- Review: CodeRabbit hit its hourly quota twice during automatic-review (WAIT 1/10, 2/10 — both resolved per the standing 90-minute recovery protocol, matching `feedback_coderabbit_unattended_recovery_protocol` memory). `cuioss-review-bot` was demoted to `optional_bots` after a structural inability to verify a first clean review (an operator/plan-side reconciliation of the review-bot registry, not something this landing message's facts directly carry — corroborated only by the operator's own paste, not independently re-checked against `.plan/marshal.json`'s `required_bots`/`optional_bots`; **recorded as an unverified lead**).
- CI/merge: merged via merge queue (`step.branch-cleanup.merge_mechanism=merge_queue`), confirmed `merge_state=merged`, `cleanup_owed=false`. `create-pr` produced #1539 (`step.create-pr.pr_number=1539`), independently confirmed via `ci pr view --pr-number 1539` → `state: merged`, `merge_commit_sha: 1c56734ce...` = current `origin/main`/`main` HEAD (verified by `git merge-base --is-ancestor`). Working tree clean (`git status --short` empty) — confirms the operator's "main checkout clean" claim.
- Push was blocked once on a genuine branch divergence (`finalize-step-sync-baseline`: rebased, 7 upstream commits, `work_performed=true`) — matches the operator's note about a force-push-with-lease resolution; the underlying rebase-need is corroborated by the facts block, the specific recovery mechanism (force-push-with-lease) is not independently re-derivable from the facts block and is taken as an unverified lead from the paste.

## Reconciliation Actions

- [x] row `status` → `shipped`
- [x] row `pr` stamped → `1539`
- [x] row `landing` stamped → `landings/PLAN-TRUTH-143.md`
- [x] row `plan_marshall_plan_id` stamped → `truth-143-orchestrator-inbox-delivery-path`
- [x] epic.md queue reconciled from status.json (Ordered Queue regenerated)
- [x] Open Defect added — finalize step-contract gap: a dispatched terminal step (`emit-landing`) can be invoked without the runtime inputs its own contract declares as dispatcher-resolved, one step before an irreversible action (`archive-plan`); the plan's workaround (source_id detection) is not a general fix. See Follow-Ups.
- [x] Watch added — Task 19 (D4, mailbox checkpoint plan-id derivation) recorded `infeasible`; confirm at next `corpus enumerate`/`cleanup` pass whether this leaves a real gap in the delivered checkpoint-address surface or was genuinely out of scope.
- [x] resume_anchor updated
- [x] START-HERE and Ordered Queue blocks regenerated (`orchestrator resume-summary`)
- [x] Inbox landing message `truth-143-orchestrator-inbox-delivery-path-020.md` archived (consumed by this reconciliation)

## Follow-Ups

- **Finalize step-contract gap (new Open Defect, this epic).** A terminal dispatched step can run without its contract-declared dispatcher-resolved inputs (`orchestrated`/`epic`), and the only fallback the plan found was re-deriving its epic from `source_id` via `inbox detect` — one step before an irreversible archive. This is exactly the epic's own recurring theme (a guard's fail-closed posture is safe in general but wrong the one time it fires right before data loss) and is a strong `truthful-signals` candidate itself, not something to route elsewhere. Not yet staged as a spec — needs a deliverable-sized write-up; flagging here so it isn't lost between this landing and the next `cleanup`/`decompose` pass.
- **19 `candidate-lesson` messages remain live in this epic's inbox from this plan** (`truth-143-orchestrator-inbox-delivery-path-{001..019}.md`), separate from the 1 `landing` message this report reconciles. The operator's paste describes "9 tool/doc defects ... routed to the local lessons store or the truthful-signals epic inbox" — the actual inbox count (19) is larger than the number named in the paste, which is consistent (some of the 9 likely went straight to the local lessons store via `manage-lessons`, not through this inbox) but not fully reconciled by this pass. **These are explicitly out of scope for this landing-only analysis** — the operator's paste itself frames them as "for later drain." Recommend a dedicated `analyze` invocation with no paste (inbox-scan mode) to drain them Step 5b-style, rather than folding them into this landing report.
- Task 19's infeasibility (D4) is carried as a Watch, not escalated to a new spec — the plan's own message states D4's other tasks (8, 9, 21) completed, so the practical impact is unclear without reading the abandoned task's actual scope. Left for the next cleanup pass or an operator call.
