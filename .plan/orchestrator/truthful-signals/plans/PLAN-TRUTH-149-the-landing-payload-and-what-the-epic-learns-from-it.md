# PLAN-TRUTH-149: The landing payload, and what the epic learns from it

## Objective

One payload, two renderings, and a curation step in between that decides — unaudited — what the epic gets to
learn. The operator report and the landing message are authored separately from the same run, so they drift;
and the plan, not the epic, decides which of its findings are transported, with nothing reconciling filed
against transported afterwards. Merged because the fix is one payload with the report as a VIEW of it, and
that same payload is the transport the findings ledger needs.

## Deliverables

10 deliverables, within the epic's operator-set ceiling of 12 (recorded 2026-09-12: the orchestration-model scope-bloat guard presumptively splits at ~6 and permits proceeding unsplit with a recorded rationale; that decision is the rationale). **D0 is a gate: nothing downstream starts until every carried claim is re-grounded at HEAD.** Each deliverable names the superseded spec it came from, so the audit trail back to the source is a pointer, not a restatement.

1. **D0 — GATE: derive the report↔landing delta from the ARTIFACTS, and the findings population WITH its type taxonomy.** ⛔ Derive the delta from the artifacts themselves, never from a spec's own table — a table restating the delta is the restatement this epic exists to remove. (PLAN-TRUTH-106 D0 + PLAN-TRUTH-110 D0.)
2. **D1 — `emit-landing` verifies its own emission and reports the verdict.** (PLAN-TRUTH-106 D1.)
3. **D2 — The landing carries the COMPLETE per-step record, not one prose line per step.** (PLAN-TRUTH-106 D2.)
4. **D3 — The landing carries the run's NARRATIVE, and the narrative gets a producer.** (PLAN-TRUTH-106 D3.)
5. **D4 — The operator report becomes a VIEW of the landing payload.** One producer, two renderings — the drift is structurally removed rather than policed. (PLAN-TRUTH-106 D4.)
6. **D5 — The report states the landing reached the epic inbox, WITH its completeness verdict.** (PLAN-TRUTH-106 D5.)
7. **D6 — Retire the narrative-only transport carve-out, and state the boundary that replaces it.** (PLAN-TRUTH-106 D6.)
8. **D7 — The findings ledger is transported, not curated away.** (PLAN-TRUTH-110 D1.)
9. **D8 — The orchestrator can see a live plan's findings.** (PLAN-TRUTH-110 D2.)
10. **D9 — The audit: reconcile filed against transported, after the fact — with the control that would have caught the retracted error.** (PLAN-TRUTH-110 D3 + D4.)

## Claim Labels

⛔ Every claim below is a POINTER at the superseded source spec that authored it. The sources are on disk and are the audit record; re-derive each claim **from the source spec's own section at HEAD**, never from this restatement. D0 owns that re-grounding.

- HYPOTHESIS: every scoping premise carried from PLAN-TRUTH-106 still holds at HEAD — confirm/refute at `.plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-106-the-terminal-emission-and-the-operator-report-do-not-check-themselves.md` § `## Claim Labels` (verify-at-outline)
  - verdict: unverifiable | checked_at: 74153664d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Pointer at PLAN-TRUTH-106 Claim Labels: 9 verdicts, 4 corroborated + 5 unverifiable.
- HYPOTHESIS: every scoping premise carried from PLAN-TRUTH-110 still holds at HEAD — confirm/refute at `.plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-110-a-plan-decides-what-the-epic-learns-and-nothing-audits-that-decision.md` § `## Claim Labels` (verify-at-outline)
  - verdict: unverifiable | checked_at: 74153664d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Pointer at PLAN-TRUTH-110 Claim Labels: 8 verdicts, 3 corroborated + 5 unverifiable.

## Expected Surface

Machine-derived: the union of the `## Expected Surface` sections of every superseded source, resolved through `plan-marshall:script-shared`'s `epic_spec_parser` — the single reader the disjointness gate uses. Not retyped.

- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/emit-landing.md` — carried from PLAN-TRUTH-106
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/output-template.md` — carried from PLAN-TRUTH-106
- `marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/landing-payload-spec.md` — carried from PLAN-TRUTH-106
- `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/_orchestrator_inbox.py` — carried from PLAN-TRUTH-106
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md` — carried from PLAN-TRUTH-106
- `test/plan-marshall/phase-6-finalize/` — carried from PLAN-TRUTH-106
- `test/plan-marshall/plan-orchestrator/test_landing_completeness.py` — carried from PLAN-TRUTH-106
- `marketplace/bundles/plan-marshall/skills/manage-findings/**` — carried from PLAN-TRUTH-110
- `marketplace/bundles/plan-marshall/skills/plan-retrospective/**` — carried from PLAN-TRUTH-110
- `.claude/skills/audit-archived-plan-retrospectives/**` — carried from PLAN-TRUTH-110
- `test/plan-marshall/**` — carried from PLAN-TRUTH-110
- `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/**` — carried from PLAN-TRUTH-110

## Dependencies and Sequencing

D0 gates everything downstream. Surface overlaps with other merged plans in this epic are expected; the disjointness gate reports them and sequences accordingly. PLAN-TRUTH-139, -127 and -103 were running when this plan was staged and were NOT re-scoped.

## Supersession Record

This plan SUPERSEDES the following specs, which stay on disk as the audit record of why they were retired (⛔ a superseded spec is never deleted):

- `PLAN-TRUTH-106-the-terminal-emission-and-the-operator-report-do-not-check-themselves.md` (PLAN-TRUTH-106)
- `PLAN-TRUTH-110-a-plan-decides-what-the-epic-learns-and-nothing-audits-that-decision.md` (PLAN-TRUTH-110)

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-149-the-landing-payload-and-what-the-epic-learns-from-it.md"
```

## ⭐ FOLDED 2026-09-15 — DISPATCH-TRAIL AND TOKEN-RECORD GAPS, FROM BOTH SAME-DAY LANDINGS

Forwarded from `plan-truth-148-005.md`, `plan-truth-148-006.md`, `plan-truth-157-004.md`, and
`plan-truth-157-007.md`. Expected Surface unchanged.

**Per-step token record gap** (`148-005`, `157-004`): the dispatch audit classifies terminal finalize
steps by token evidence, and 13 of 16 (148) / 9 of 16 (157) come back `no_evidence` — which conflates two
different facts: a step that never dispatches by design, and a step that dispatched but whose record was
lost. `157-004` sharpens the fix: separate the two by declaring which finalize steps are by-design-inline
before scoring the population, rather than treating every `no_evidence` step as an instrumentation gap.
Do not paper over with a default — emit an explicit `unmeasured` token record per terminal step so the
population shrinks to genuinely unmeasurable steps, and keep the three-state classification (collapsing
`no_evidence` into `ran_inline` would convert a not-measured majority into a false claim about execution
mode).

**Dispatcher composes `plan-marshall:plan-retrospective`'s prompt body incorrectly** (`148-006`): no
`iteration` field (risking the wrong mode-detection heuristic firing and skipping the `mark-step-done`
handshake) and an empty `WORKTREE` (not a member of the documented value set, which requires `.` for a
non-worktree plan). Recovered only by reading manifest membership by hand. Proposed: forward `iteration`
as the step's own input contract declares, resolve `WORKTREE` to `.` when `use_worktree` is false, and
consider mode resolution consulting manifest membership rather than flag presence.

**A bare `effort resolve-target` query leaves its dispatch unattributable** (`157-007`): the resolve seam
only emits its `[DISPATCH]` work-log line and paired decision-log record when `--workflow` is supplied —
a bare-level query (`role=None` in this run's own decision log) carries no dispatch context and emits
nothing, so a resolve that DID back a real dispatch can be indistinguishable from one that was a level
query only. 1 violation of 32 in this run's own dispatch-audit population.

## ⭐ FOLDED 2026-09-15 (c) — THE `orchestrated` VERDICT HAS NO PERSISTED CARRIER: D1 MAKES A LOST LANDING VISIBLE, NOT REACHABLE

Forwarded from `api-sheriff-deployment-configurability-010.md` — six observations in the API-Sheriff epic
(3 delivered / 5 skipped-at-runtime / 1 absent-from-manifest), `inbox detect` returning
`orchestrated: true` on every affected plan. Expected Surface unchanged — `phase-6-finalize/standards/emit-landing.md`,
`phase-6-finalize/SKILL.md` and `manage-execution-manifest/**` are already declared.

⛔ **This names a CAUSE D1 does not reach.** D1 ("`emit-landing` verifies its own emission") would make the
failure visible; a step reporting "I emitted nothing because `epic` was empty" is still a lost landing.
Re-grounded at `7a028157e`:

- **Runtime skip on an EMPTY INPUT, not a negative detection.** `emit-landing.md` Step 0 (line 120) skips
  with `"not orchestrated, no landing emitted"` when the `epic` input is empty. The only resolution lives in
  `phase-6-finalize/SKILL.md` § 4b "Lessons-capture Signal Gate" (line 764) — a DIFFERENT step's gate — and
  line 883 has `emit-landing` "carry the same two values into it directly" across ~9 intervening steps,
  forbidding re-resolution. If `lessons-capture` is not composed/dispatched or the value is not carried,
  a genuinely orchestrated plan is skipped by the defensive guard.
- **Compose-time drop fails toward silence on an unobservable detector.** `manage-execution-manifest.py`
  (lines 971–972) drops `emit-landing` with `"orchestration detector unavailable; dropping terminal emission
  (fails toward non-orchestrated)"`, logged to the decision log only — the absent-from-manifest mode.

**Remedy direction to add to this spec's scope:** persist the `orchestrated` verdict once (at compose time)
or let `emit-landing` re-resolve from the plan's own `source_id`, which `inbox detect` answers correctly;
and have the compose gate distinguish *detector unavailable* from *not orchestrated* instead of dropping on
both. Adjacent active lesson `2026-09-09-06-001` names neither cause.

## Write-Boundary

The executing plan MUST NOT create or edit any file under `.plan/local/orchestrator/truthful-signals/` except its own `inbox/{sender}-{seq}.md` messages, written through `plan-marshall:plan-orchestrator:orchestrator inbox write`. The orchestrator owns every other ledger write.
