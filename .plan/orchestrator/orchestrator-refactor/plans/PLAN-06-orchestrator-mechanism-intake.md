# PLAN-06: Take ownership of the orchestrator mechanism scattered across sibling epics

epic: orchestrator-refactor
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-06-orchestrator-mechanism-intake.md` and is queued in the epic
> `status.json` `plans[]` field. The orchestrator EMITS the command below; it never launches
> the plan inline. This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer
> and carries no brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

Consolidate under one owner the orchestrator-mechanism items currently carried by epics whose
domain is something else. The mechanism is not the problem; the ownership is. One schema file
(`landing-payload-spec.md`) has three would-be owners in three ledgers that cannot see each
other, and one schema defect (the row-status vocabulary) was routed to the catch-all epic
explicitly because its finder judged it "not this epic's to fix".

## Deliverables

1. **D0 — GATE: re-ground every carried item against HEAD before scoping.** At research time,
   three items below were already believed shipped (PLAN-CIS-051 / PR #1370, PLAN-TRUTH-113 /
   PR #1366). An item that is already closed is dropped from the intake and recorded as
   dropped, not silently carried.
2. **D1 — one owner for `landing-payload-spec.md`.** State the ownership, and state how the
   sibling specs that declare it (see Claim Labels) are sequenced against it.
3. **D2 — the two-parser split**, closed: one reader of `## Expected Surface`, wired to the
   gate that consumes it, with the second deleted rather than corrected.
4. **D3 — the plan-id detection seam**, single, per the seam's own declaration
   (`orchestrator inbox detect`).
5. **D4 — the transfer record.** Each intake item names its source epic, its source location,
   and whether the source row is retired, re-scoped, or left alone. An offer is not a transfer;
   the sibling ledger must be updated by its own orchestrator session, and this plan records
   what it asks for rather than performing it.
6. **D5 (folded 2026-09-20, from `identifier-vocabulary-decision-003`) — reconcile
   orchestration detection between `phase-1-init` and the `phase-6-finalize`
   terminal-emission gate.** The two surfaces currently disagree about whether a launched
   plan is orchestrated: `phase-1-init`'s file-pointer branch does not always record
   `source_id` on `request.md`, so the compose-time `terminal_emission_orchestration_gate`
   drops `emit-landing` (`detection=not_orchestrator_pointer`) even when the plan
   demonstrably belongs to an epic and the finalize dispatcher later hands its retrospective
   `orchestrated: true`. Either write `source_id` when a plan is launched from a staged epic
   plan spec, or make the terminal-emission gate consult the same signal the finalize
   dispatcher uses before dropping `emit-landing` — and fail loudly rather than silently when
   the two disagree. The omission is measurable and permanent for a plan's whole lifecycle
   once it happens (there is no later point to still emit the landing), so this is a
   correctness defect in the delivery path `orchestrator inbox detect` sits on top of, not
   merely an inbox-schema gap.

## Non-Goals

- No `status.json` schema change (PLAN-02's job), except where an intake item IS the schema
  change (the row-status vocabulary) and is explicitly assigned there instead of duplicated
  here.
- No sibling ledger is edited by this plan.

## Claim Labels

- OBSERVED — three-way concurrent ownership of ONE orchestrator schema file,
  `plan-orchestrator/standards/landing-payload-spec.md`, declared as Expected Surface by:
  `post-run-quality` PLAN-PRQ-04 (staged, "the owed-item fact keys", D1/D2);
  `truthful-signals` PLAN-TRUTH-149 (staged), -146 (staged), -144 (staged), -167 (staged,
  HYPOTHESIS); `review-apparatus` PLAN-PR-073 (staged, "⚠ D2 edits the orchestrator inbox"),
  plus parked -055 and -064.
- OBSERVED — `review-apparatus/epic.md:2533-2542`: the queue cannot express `retired`;
  `VALID_STATUS_VOCABULARY` is `{staged, launched, running, parked, shipped, landed}` and
  `--transition` refuses `retired` "while four rows in this very ledger already carry it"; the
  item was "Filed to `truthful-signals` as `review-apparatus-036.md`… it is not this epic's to
  fix". Generalised first-party (see PLAN-02): 95 of 500 rows across 12 ledgers, 6 epics. This
  item is ASSIGNED to PLAN-02 (WS-01) — it is the schema — and this deliverable records that
  assignment rather than re-implementing it.
- OBSERVED — `review-apparatus/epic.md:2008-2013` records that specs declare
  `../cloud-runs/*` as Expected Surface while their own Write-Boundary forbids editing anything
  under `.plan/local/orchestrator/` and that tree is git-ignored, "so such an edit can never
  appear in a PR". This is this epic's own aspect-1 thesis (PLAN-01/PLAN-02), found
  independently from another ledger — cite it there, do not re-derive it here.
- OBSERVED — `truthful-signals/epic.md:2146-2158`: two parsers read one `## Expected Surface`
  and disagree — `orchestrator.py`'s queue renderer returns "(no expected surface)" and governs
  the disjointness gate, while `epic-surface-partition classify` returns "declarative, 6
  resolved paths" and governs only the report. `:2168-2174` records this as a live ADR-019
  violation inside our own machinery.
- OBSERVED — `truthful-signals/epic.md:2160-2166`: `epic-surface-partition classify` carries a
  THIRD plan-id detector that does not recognise `PLAN-{CODE}-{NNN}`, so attribution "cannot
  group by plan for this epic at all"; `orchestrator inbox detect` already declares itself the
  single detection seam.
- OBSERVED — `epic-surface-partition.py:132` calls `get_store_dir('orchestrator', epic,
  allow_archived=True)`: the orchestrator mechanism has a second implementation home in the
  `pm-plugin-development` bundle.
- OBSERVED — `code-intelligence-substrate` PLAN-CIS-052 (staged) declares `inbox-envelope.md`
  (D6d) and `_orchestrator_inbox.py` (D6e), with a recorded cross-epic ordering constraint
  against the now-superseded `truthful-signals` PLAN-TRUTH-100 (successor PLAN-TRUTH-143,
  running).
- HYPOTHESIS — the two-parser disagreement and the third plan-id detector were closed by
  `truthful-signals` PLAN-TRUTH-113 (shipped, PR #1366); confirm/refute at `orchestrator.py`
  § the queue renderer and the partition script's `classify` path before staging any remedy
  (verify-at-outline).
- HYPOTHESIS — the claim-parsing gates recorded at
  `code-intelligence-substrate/epic.md:1267-1292` (`orchestrator.py:389`
  `CLAIM_LABELS_HEADING_RE` case-exact, and `_parse_claims` accepting only top-level bullets,
  jointly producing a vacuous prep-ready admission) were closed by PLAN-CIS-051 (shipped, PR
  #1370); confirm/refute at those two symbols (verify-at-outline).
- Verify-first clause: `truthful-signals` PLAN-TRUTH-143 is RUNNING and declares the widest
  orchestrator surface of any live spec (`orchestrator.py`, `_orchestrator_inbox.py`,
  `SKILL.md`, `inbox-envelope.md`, `orchestration-model.md`, `workflow/analyze.md`,
  `workflow/orchestrate.md`). Do NOT re-scope it — the running-row exclusion in
  `orchestration-model.md` § Cleanup Contract forbids changing the brief under a running plan.
  This plan's command is BLOCKED until PLAN-TRUTH-143 lands and this spec is re-grounded
  against the new HEAD.
- ⛔ CLOSED, do not re-stage: `code-intelligence-substrate/epic.md:1348-1362` ("the orchestrator
  has NO add-a-row verb") — `queue --add-row` shipped via `truthful-signals` PLAN-TRUTH-099
  (PR #1434) and is live at `orchestrator.py:896-992` and `:1090-1192`.
- ⛔ `lessons-handling-26-08-26-01` PLAN-LH2-14 "orchestrator-stops-short" is NOT an item for
  this plan. Its two clustered lessons concern the plan-LIFECYCLE orchestrator yielding to the
  operator (`*_without_asking` knobs), not the epic-tier orchestrator this epic owns. Two
  different entities share the word "orchestrator" in this codebase — see PLAN-04.
- OBSERVED (D5, from `identifier-vocabulary-decision-003`, filed against PLAN-04's own
  landing) — compose-time decision log entry `7f9799`:
  `terminal_emission_orchestration_gate — dropped emit-landing from phase_6.steps: plan is
  not orchestrated (detection=not_orchestrator_pointer); no epic inbox to write a landing
  to`, on a plan whose `request.md` carried `source: description` with no `source_id`
  section (`request read --section source_id` → `section_not_found`), while the SAME plan's
  finalize retrospective was dispatched with `orchestrated: true, epic: orchestrator-refactor`.
  Measured consequence, independently confirmed by this epic's own `analyze`:
  `orchestrator inbox list --slug orchestrator-refactor` reported
  `queue_reconciliation.queue_count: 7`, `landing_count: 0`, `queue_without_landing_count: 7`
  before PLAN-04's landing was manually reconciled.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/landing-payload-spec.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/inbox-envelope.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/_orchestrator_inbox.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py`
- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/tools-epic-surface-partition/scripts/_epic_partition.py`
- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/tools-epic-surface-partition/scripts/epic-surface-partition.py`
- OBSERVED (added by the D5 fold, 2026-09-20): `marketplace/bundles/plan-marshall/skills/phase-1-init/**`
- OBSERVED (added by the D5 fold, 2026-09-20): `marketplace/bundles/plan-marshall/skills/phase-6-finalize/**`
- OBSERVED: `test/plan-marshall/plan-orchestrator/**`
- OBSERVED: `test/pm-plugin-development/tools-epic-surface-partition/**`
- OBSERVED (added by the D5 fold, 2026-09-20): `test/plan-marshall/phase-1-init/**`
- OBSERVED (added by the D5 fold, 2026-09-20): `test/plan-marshall/phase-6-finalize/**`

## Dependencies and Sequencing

- Depends on: `truthful-signals` PLAN-TRUTH-143 (running, sibling epic) landing first — a
  cross-epic BLOCK, not a same-epic sequencing note. Re-ground this spec against HEAD once it
  lands before staging the command.
- Overlaps with: PLAN-05 (`_orchestrator_inbox.py`, `tools-epic-surface-partition/**`); PLAN-07
  (`orchestrator.py`, `_orchestrator_inbox.py`).
- Adjacent to: `truthful-signals` PLAN-TRUTH-149/-146/-144/-167, `review-apparatus`
  PLAN-PR-073/-055/-064, `post-run-quality` PLAN-PRQ-04, `code-intelligence-substrate`
  PLAN-CIS-052 — all declare `landing-payload-spec.md` and/or `_orchestrator_inbox.py`. None of
  these overlaps are visible to the automated disjointness gate (it does not cross sibling
  ledgers); this plan's D4 records the transfer request into each rather than editing them.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/orchestrator-refactor/plans/PLAN-06-orchestrator-mechanism-intake.md"
```

## Write-Boundary

The plan implementing this spec touches only repository source, standards and tests across two
bundles. It creates and edits NO file under ANY orchestrator store — including sibling
epics' — other than its own `inbox/{sender}-{seq}` message in this epic's own tree. The
orchestrator owns every other ledger write, and reports its outcome through its PR and its
inbox message. The inbox exception's qualifiers and the sole sanctioned write mechanism are
stated in `persona-plan-orchestrator/standards/orchestration-model.md` § Ledger
Write-Boundary.
