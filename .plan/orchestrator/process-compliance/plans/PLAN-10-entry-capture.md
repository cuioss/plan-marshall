# PLAN-10: Dispatch-entry capture gaps

epic: process-compliance
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-10-entry-capture.md` and is queued in the epic `status.json` `plans[]`
> field. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.

## Objective

Close the light-lane entry gaps that force exempt-and-continue overrides at plan start:
the 2-refine capture demanding a `pr_title` the collapsed envelope never produced, the
mailbox probe reporting `not_orchestrated` for valid staged-spec pointers, the
recipe-match/aspect-classify lane lacking file input for verbatim narrative, the
`phase_steps_complete` parser reading non-step bullets, and the missing phase-handshake
captures. Every gap below was absorbed as an explicit operator-approved exemption; this
plan makes the entry lane decidable so the exemption stops recurring.

## Deliverables

1. Capture-source matrix + fix: `pr_title` capture source for the light-lane collapsed
   envelope (refine-artifact vs required flag), so post-exempt capture stops refusing
   with `pr_title_missing`.
2. Mailbox-probe fix: valid staged-spec pointers resolve instead of reporting
   `not_orchestrated`.
3. Recipe-match/aspect-classify file input parity (`--content-file` or equivalent) for
   verbatim narrative ingestion.
4. `phase_steps_complete` parser fix: reads step bullets only; post-archive state handled.
5. Phase-handshake capture backfill: the zero-capture runs across two completed phases
   get a contract (capture or recorded reason), not silence.

## Claim Labels

- OBSERVED: post-exempt 2-refine capture refuses `pr_title_missing` because the collapsed envelope never ran Step 13 — read at `.plan/orchestrator/process-compliance/inbox/ledger-joins-002.md` § body (filed, then `--override` under prior approval)
  - verdict: unverifiable | checked_at: 93bda90 | by: process-compliance/cleanup | rescoped: n/a | evidence: ledger cite (ledger-joins-002 inbox); run-behavior premise needs outline
- OBSERVED: mailbox probe reports `not_orchestrated` for a valid spec pointer — cited at `.plan/orchestrator/process-compliance/inbox/plan-09-outline-sweep-002.md` § body (dispatched leaf gist; body auditable in archive after drain)
  - verdict: unverifiable | checked_at: 93bda90 | by: process-compliance/cleanup | rescoped: n/a | evidence: dispatched leaf gist (plan-09-outline-sweep-002); body in archive, not opened this pass
- OBSERVED: recipe-match/aspect-classify lack file input for verbatim narrative — cited at `.plan/orchestrator/process-compliance/inbox/plan-09-outline-sweep-001.md` § body (dispatched leaf gist)
  - verdict: unverifiable | checked_at: 93bda90 | by: process-compliance/cleanup | rescoped: n/a | evidence: dispatched leaf gist (plan-09-outline-sweep-001); CLI-flag check deferred to outline
- OBSERVED: main-dirt assertion fires on pre-existing dirt; light-lane entry demands refine-artifact `pr_title`; steps parser reads non-step bullets — cited at `plan-09-outline-sweep-003.md`, `plan-09-outline-sweep-004.md`, `plan-09-outline-sweep-005.md` § bodies (dispatched leaf gists)
  - verdict: unverifiable | checked_at: 93bda90 | by: process-compliance/cleanup | rescoped: n/a | evidence: dispatched leaf gists (sweep-003/004/005); run-behavior premises need outline
- HYPOTHESIS: zero phase-handshake captures across two completed phases is a contract gap, not operator choice — confirm/refute at `marketplace/bundles/plan-marshall/skills/plan-marshall/` § handshake capture seam (verify-at-outline; folded lead from `test-fidelity-rules-follow-up-003.md`)
  - verdict: corroborated | checked_at: 93bda90 | by: process-compliance/cleanup | rescoped: n/a | evidence: phase-handshake.md capture/verify registry and SKILL.md capture at :273
- HYPOTHESIS: light-lane routing on an 8-deliverable scope without a solution outline is undocumented entry, not sanctioned entry — confirm/refute at `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/planning.md` § light-lane entry (verify-at-outline; folded lead from `test-fidelity-rules-follow-up-004.md`)
  - verdict: corroborated | checked_at: 93bda90 | by: process-compliance/cleanup | rescoped: n/a | evidence: planning.md light-lane branch at :222-273
- Verify-first clause: the consuming phase settles both HYPOTHESIS clauses against the implementing source before scoping — refutation loops back to re-scope

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/planning.md` — light-lane entry + capture pairing live here
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py` — mailbox probe seam lives here
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/` — entry-lane scripts and workflow docs
- OBSERVED: `test/plan-marshall/plan-orchestrator/` — probe regression tests live here
- OBSERVED: `test/plan-marshall/plan-marshall/` — entry-lane regression tests live here

## Dependencies and Sequencing

- Depends on: none
- Overlaps with: PLAN-01 surfaces (shipped, no live collision); PLAN-08 (shared orchestator surface area — sequence, do not parallelize)
- Adjacent to: condensed-inline lane question (recorded defect; stays untouched — this plan fixes the documented lane, not the undocumented one)

## Folded inbox material (same act)

- `ledger-joins-002.md` (finding): pr_title capture gap — head of this spec
- `plan-09-outline-sweep-001.md` (finding): file-input parity — staged into this spec
- `plan-09-outline-sweep-002.md` (finding): mailbox probe — staged into this spec
- `plan-09-outline-sweep-003.md` (finding): dirt assertion — staged into this spec
- `plan-09-outline-sweep-005.md` (finding): steps parser — staged into this spec
- `plan-09-outline-sweep-004.md` (finding): pr_title capture recurrence — folded; expected surface unchanged by this fold (recurrence note, adds no file surface — recorded explicitly)
- `test-fidelity-rules-follow-up-003.md` (finding): handshake captures — staged into this spec
- `test-fidelity-rules-follow-up-004.md` (finding): light-lane routing — staged into this spec

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/process-compliance/plans/PLAN-10-entry-capture.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message.
