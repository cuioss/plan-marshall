<!-- ⛔ RETIRED 2026-09-12 — ABSORBED INTO `PLAN-CIS-052`, NOT ABANDONED.

This spec is no longer emittable and its queue row is off the staged list. All four deliverables
survive inside
`plans/PLAN-CIS-052-finalize-dispatch-and-blocking-boundary-observability.md`:

  D1 (standing completion instruction)  -> PLAN-CIS-052 D7
  D2 (raise the voluntary_checkpoint bar) -> PLAN-CIS-052 D8, RE-SCOPED from the PREDICATE to the
                                             THRESHOLD, because claim 3 below is REFUTED: the emit
                                             site already consults tasks_remaining
  D3 (publish the stall rate)           -> PLAN-CIS-052 D9
  D4 (test pinning the classification)  -> PLAN-CIS-052 D10

Reason for the merge (operator direction, 2026-09-12): larger plans, ceiling twelve deliverables,
grouped by shared target. PLAN-CIS-052 owns what the finalize dispatch RECORDS; this spec owns what
it does when it STOPS. One dispatch loop, one boundary ledger, one termination vocabulary.

⚠ Why NOT into PLAN-CIS-050, which this spec overlaps more heavily (manage-metrics.py,
data-format.md, analyze-logs.py): PLAN-CIS-050 absorbed PLAN-CIS-057 in the same re-cut and stands
at ELEVEN deliverables, so taking these four would have breached the twelve ceiling. The four-file
contention with PLAN-CIS-050 therefore SURVIVES and is recorded in PLAN-CIS-052's Expected Surface
as a sequencing constraint. This is the one contention the re-cut did not dissolve.

The claim verdicts below are left verbatim as the record. Do not re-stamp them, and do not
resurrect this file.
-->

# PLAN-CIS-061: `voluntary_checkpoint` is the modal dispatch termination, and it is a stall

epic: code-intelligence-substrate
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and hand-off contract.

Staged 2026-08-31 by the `analyze` drain of the PLAN-CIS-051 landing (PR #1370), from
candidate-lesson `detector-and-auditor-integrity-011.md`. Staged rather than folded because no
existing spec in the corpus covers dispatch-termination policy: `PLAN-CIS-050` owns measurement
integrity and `PLAN-CIS-052` owns finalize dispatch RECORDING, while this is about what a dispatch
does when it stops.

## Objective

A dispatch that stops with work still in its queue and no blocking condition is a **stall**, not a
checkpoint, and today it is the modal outcome. On PLAN-CIS-051 the phase-5 boundary ledger recorded
14 terminations — `voluntary_checkpoint` 10, `budget_yield` 3, `clean_exit_queue_empty` 1 — while the
session transcript reduces to 9 operator turns of which **six exist only to restart a halted run**.
This plan makes a standing run-to-completion instruction survive a dispatch boundary, and raises the
bar `voluntary_checkpoint` clears so that a stall is recorded and treated as one.

The epic's interest is direct and measurable: two thirds of all operator attention on a 9.4M-token
plan went to re-issuing an instruction given in the operator's FIRST message, and the wall-clock cost
is visible beside it — 3h0m idle against 10h44m worked, with phase 3-outline alone carrying 1h9m idle
against 35m1s worked.

## Deliverables

1. **Persist the standing completion instruction into plan state that each dispatch reads.** The
   operator's opening instruction on PLAN-CIS-051 was *"continue as defined to the end of finalize.
   DO only stop on issue."* It did not survive a dispatch boundary. Establish where such an
   instruction can live (plan `status.json` metadata is the candidate) and make the dispatch prompt
   carry it.
2. **Raise the bar `voluntary_checkpoint` clears.** A termination with `tasks_remaining > 0` and no
   `blocked_*` cause is a stall. Either classify it as one at the boundary, or auto-resume rather
   than returning to the operator. The ledger already distinguishes it from `budget_yield` and
   `blocked_*`, so the discriminator exists and is unread.
3. **Publish the stall rate as a first-class figure.** `analyze-logs` already partitions terminations
   by cause; surface `voluntary_checkpoint` with `tasks_remaining > 0` as its own count so the rate is
   trackable across plans instead of being re-derived by hand from one run's transcript.
4. **A test that pins the stall classification.** A termination fixture with a non-empty queue and no
   blocking cause must not classify as a clean checkpoint. Per the epic's standing rule the guard must
   be population-derived and publish the population it scored.

## Claim Labels

- OBSERVED: phase-5 terminations on PLAN-CIS-051 were `voluntary_checkpoint` 10, `budget_yield` 3,
  `clean_exit_queue_empty` 1 — read at that plan's dispatch-boundary ledger (14 rows), reported in
  `.plan/local/orchestrator/code-intelligence-substrate/inbox/archive/detector-and-auditor-integrity/detector-and-auditor-integrity-011.md`
  - verdict: corroborated | checked_at: 28b578f1ed435973e53c510f0c8225446cc024aa | by: code-intelligence-substrate/cleanup | rescoped: n/a | evidence: Re-derived at HEAD: the 14-row boundary ledger split (voluntary_checkpoint 10 / budget_yield 3 / clean_exit_queue_empty 1) on PLAN-CIS-051 appears verbatim in inbox/archive/detector-and-auditor-integrity/detector-and-auditor-integrity-011.md lines 18-24.
- OBSERVED: six of nine operator turns on that run exist only to restart a halted dispatch — quoted
  verbatim in the same message ("why did you stop?" ×2, "do continue", "why do you allways stop???
  run to the end as instructed multiple times", "why did you stop? continue with finalize to the
  end", "proceed with finalize without further stopping")
  - verdict: corroborated | checked_at: 28b578f1ed435973e53c510f0c8225446cc024aa | by: code-intelligence-substrate/cleanup | rescoped: n/a | evidence: Re-derived at HEAD: the 6-of-9 operator-turn restart count is quoted verbatim at detector-and-auditor-integrity-011.md lines 28-38 together with the operator's first-message instruction.
- OBSERVED: the two observations corroborate each other from INDEPENDENT sources — the boundary
  ledger and the session transcript — which is why this is a measurable defect and not a mood
  - verdict: corroborated | checked_at: 28b578f1ed435973e53c510f0c8225446cc024aa | by: code-intelligence-substrate/cleanup | rescoped: n/a | evidence: Re-derived at HEAD: both sub-facts were verified independently at claims 0 and 1 from two different sources (the boundary ledger and the session transcript), so the independent-corroboration argument holds.
- HYPOTHESIS: `voluntary_checkpoint` is emitted at a site that does not consult `tasks_remaining` —
  confirm/refute at `marketplace/bundles/plan-marshall/skills/phase-5-execute/SKILL.md` and
  `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/execution.md` (verify-at-outline)
  - verdict: contradicted | checked_at: 28b578f1ed435973e53c510f0c8225446cc024aa | by: code-intelligence-substrate/cleanup | rescoped: no | evidence: REFUTED at HEAD. The emit site DOES consult tasks_remaining: execution.md:199 defines voluntary_checkpoint as firing when a non-error payload returns while pending tasks remain in the queue. execution.md:221-243 and phase-5-execute/SKILL.md:1173-1181 (B7) already reclassify a no-progress subclass to error using in_progress_count and completed_tasks_delta. git log -S dates that machinery to #349/#714/#730/#842 - all older than PR #1370 - so it predates PLAN-CIS-051 and is not a post-hoc fix. The defect as stated is not the predicate; if anything remains it is the classification threshold. Spec needs re-scoping before launch.
- HYPOTHESIS: no plan-state field today carries a standing completion instruction across a dispatch —
  confirm/refute at `marketplace/bundles/plan-marshall/skills/manage-status/SKILL.md` § metadata
  (verify-at-outline)
  - verdict: corroborated | checked_at: 28b578f1ed435973e53c510f0c8225446cc024aa | by: code-intelligence-substrate/cleanup | rescoped: n/a | evidence: Re-derived at HEAD over a stated population: architecture search --content for standing_instruction|run_to_completion|completion_instruction returned count 0 over 5357 files scanned with 0 unreadable and no truncation; manage-status/SKILL.md:73 lists only change_type/confidence/domain/use_worktree/worktree_path/worktree_branch/session_ids.
- Verify-first clause: the termination-cause vocabulary and its emit sites must be re-read at HEAD
  before scoping. If `tasks_remaining` is already consulted at the emit site, deliverable 2 re-scopes
  to the classification rather than the predicate, and this spec is amended rather than proceeding on
  the stale reading.
  - verdict: corroborated | checked_at: 28b578f1ed435973e53c510f0c8225446cc024aa | by: code-intelligence-substrate/cleanup | rescoped: n/a | evidence: The verify-first clause fired as written: re-reading the termination-cause vocabulary and emit sites at HEAD is exactly what refuted claim 3, so the clause discharged correctly and D2 must re-scope to the classification threshold rather than the predicate.

## Expected Surface

Paths are as of staging and were swept against HEAD `7845a4b9a` before this spec was staged; the
sweep is the `grep -rln voluntary_checkpoint` over `marketplace/bundles/` and `.claude/` that
produced the eleven files below, of which these are the ones this plan expects to CHANGE.

- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-5-execute/SKILL.md` — D1, D2: the
  dispatch loop and its termination contract
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/execution.md` — D1, D2
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/standards/execution-recovery.md`
  — D2: the resume path a stall would take
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-metrics/scripts/manage-metrics.py` — D3:
  `record-dispatch-boundary` and the termination-cause vocabulary
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-metrics/standards/data-format.md` — D3
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/analyze-logs.py` —
  D3: the cause-class partition that already computes the counts
- OBSERVED: `test/plan-marshall/manage-metrics/` and `test/plan-marshall/plan-retrospective/` — D4
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-status/SKILL.md` — D1, only if the
  standing instruction lands in plan metadata (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: `PLAN-CIS-050` on `manage-metrics.py`, `data-format.md` and `analyze-logs.py`, and
  on `phase-5-execute/SKILL.md` which CIS-050 gained in the same 2026-08-31 drain. ⛔ **Do not run
  concurrently with `PLAN-CIS-050`.** `PLAN-CIS-052` also declares `analyze-logs.py` (read-only), so
  the three-way contention on that file is recorded here for the disjointness gate.
- Adjacent to: `phase-6-finalize/SKILL.md` and `lessons-capture.md`, which mention
  `voluntary_checkpoint` but are `PLAN-CIS-052`'s surface — untouched here.

## Notes

**The merge-mutex override belongs to the same class and is NOT in this plan's scope.** The same run
recorded the operator intervening on the merge mutex, and that override's cost materialised: the
first enqueue was ejected when four upstream PRs landed during the queue wait, forcing a rebase, a
re-derived constant, a full re-verify, a force-push and a re-review. It is recorded in
`landings/PLAN-CIS-051.md` as residue. It is the same shape — an operator instruction overriding a
guard, at cost — but it is a merge-queue concern and staging it here would widen this plan past its
subject.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/code-intelligence-substrate/plans/PLAN-CIS-061-voluntary-checkpoint-is-a-stall.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and
edits NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message —
the orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message.
