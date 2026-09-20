# PLAN-02: The epic ledger is per-concern files, and the row vocabulary matches reality

epic: orchestrator-refactor
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-02-ledger-decomposition-and-row-vocabulary.md` and is queued in the
> epic `status.json` `plans[]` field. The orchestrator EMITS the command below; it never
> launches the plan inline. This spec is SELF-SUFFICIENT: the emitted command is a one-line
> pointer and carries no brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

Decompose the two monolithic ledger documents (`status.json`, `epic.md`) into self-contained,
per-concern files so two sessions on two machines mutate disjoint paths, and settle the
plan-row status vocabulary in the same change — because both are the `kind=orchestrator`
schema and splitting them across two plans would mean two schema migrations of one document.
Today `status.json` is the single file every queue mutation, every `resume_anchor` write and
every metadata write re-serialises, and `epic.md` is the single file `compact` and
`resume-summary` rewrite blocks inside. The measured worst case is a 63,698-byte / 2,045-line
`status.json` holding 221 plan rows and a 1,887-character anchor string, beside a
367,233-byte / 3,916-line `epic.md`.

## Deliverables

1. **D0 — GATE: derive the collision surface before designing the split.** For each of the 9
   top-level `status.json` fields and each `epic.md` section, state which verbs write it and
   at what frequency. The split follows the write pattern; it is not chosen from the field
   list.
2. **D1 — the per-concern layout**, with the decision recorded per file: what is one file,
   what stays aggregated, and why.
3. **D2 — the row-status vocabulary**, derived from the four observed extra values, with each
   admitted value's meaning stated once and `--transition` accepting the settled set.
4. **D3 — readers and writers**, updated so no consumer re-serialises a whole document to
   change one row. The bulk `update-field --field plans` form is reduced to the seed case or
   removed.
5. **D4 — the layout contract, the schema doc and the template** tell the truth about the new
   shape.
6. **D5 — a concurrency test** that exercises two sessions staging two different plans and
   asserts both survive. This is the deliverable the whole plan exists for; it must fail
   against today's layout before the fix and pass after.

## Non-Goals

- No address change — PLAN-01 owns that; this plan assumes it has already landed.
- No identifier rename (WS-03's job).
- No `orchestrator.py` module split (PLAN-07's job, sequenced last).

## Claim Labels

- OBSERVED — measured on disk: `truthful-signals/status.json` 63,698 B / 2,045 lines / 221
  `plans[]` rows / `resume_anchor` 1,887 chars; `code-intelligence-substrate/status.json`
  116,933 B; `truthful-signals/epic.md` 367,233 B / 3,916 lines;
  `code-intelligence-substrate/epic.md` 274,819 B; `review-apparatus/epic.md` 277,257 B.
- OBSERVED — the schema is 9 top-level fields and a 7-field plan row
  (`status-lifecycle.md:174-196`).
- OBSERVED — `_status_core.py:478-506`: `workstreams` and `plans` are
  `ORCHESTRATOR_LIST_FIELDS`, so `update-field` on either is a whole-array rewrite (inside
  `rmw_json`, but still a full re-serialisation).
- OBSERVED — the queue-write boundary reserves the bulk rewrite to the `decompose`
  seed-from-nothing case (`orchestration-model.md:102-117`).
- OBSERVED — `orchestrator.py:190` declares
  `VALID_STATUS_VOCABULARY = {'staged','launched','running','parked','shipped','landed'}`.
- OBSERVED (derived, population = all 12 ledgers present on this machine, 500 plan rows): 95
  rows (19%) carry a status the vocabulary cannot express — `superseded` 54, `retired` 31,
  `transferred` 5, `resolved` 5 — in 6 of 12 epics. `--transition` argparse-refuses every one;
  only the bulk rewrite can write them.
- OBSERVED — `review-apparatus/epic.md:2533-2542` records this independently and filed it out
  to `truthful-signals` as `review-apparatus-036.md`, explicitly as "not this epic's to fix" —
  this plan is the owner it was missing.
- OBSERVED — `.plan/project-architecture/` is an existing git-tracked, one-file-per-concern
  directory under `.plan/` (13 files, 62,748 B), so the split shape has a working precedent.
- HYPOTHESIS — per-plan-row files remove the staging collision entirely, while per-workstream
  files only narrow it; confirm/refute by constructing the two concurrent-staging scenarios
  against `orchestrator.py` § `_append_plan_row` and the shared `rmw_json` critical section
  (verify-at-outline).
- HYPOTHESIS — `resume_anchor` belongs in its own file: it is written on almost every verb and
  is the field a fresh session reads first; confirm/refute at `orchestrator.py` §
  `cmd_resume_summary` and `_status_core.py` § `cmd_orchestrator_update_field`
  (verify-at-outline).
- HYPOTHESIS — the four unexpressible statuses are four distinct concepts and must not be
  collapsed into one (`superseded` = replaced by a successor spec; `retired` = withdrawn;
  `transferred` = moved to another epic; `resolved` = closed without a plan). Confirm/refute by
  reading one instance of each from its own ledger before fixing the set (verify-at-outline).
- Verify-first clause: the 500-row / 12-ledger figure is derived from the ledgers present on
  this machine at research time. Re-derive at outline and state which population any count is
  drawn from.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-status/standards/status-lifecycle.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_status_core.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-status/SKILL.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/SKILL.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/templates/epic.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/persona-plan-orchestrator/standards/orchestration-model.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/workflow/decompose.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/workflow/cleanup.md`
- OBSERVED: `test/plan-marshall/manage-status/test_orchestrator_store.py`
- OBSERVED: `test/plan-marshall/manage-status/test_orchestrator_store_orchestrator.py`
- OBSERVED: `test/plan-marshall/plan-orchestrator/test_orchestrator_status_regression.py`
- OBSERVED: `test/plan-marshall/plan-orchestrator/test_orchestrator_queue_add_row_concurrency.py`
- OBSERVED: `test/plan-marshall/plan-orchestrator/test_orchestrator_compact.py`

## Dependencies and Sequencing

- Depends on: PLAN-01 (this plan's Non-Goals assume the tracked address has already landed).
- Overlaps with: PLAN-05 (`orchestrator.py`, `plan-orchestrator/SKILL.md`, `manage-status/**`
  — the sharpest collision in the epic's corpus: PLAN-02 changes the schema shape, PLAN-05
  may rename its `slug` field. Land this plan first.); PLAN-06 (the row-status-vocabulary item
  is also a PLAN-06 intake candidate — assigned here, PLAN-06 records the assignment rather
  than duplicating it); PLAN-07 (`orchestrator.py`, sequence PLAN-07 last).
- Adjacent to: `truthful-signals` PLAN-TRUTH-151 (staged, sibling epic, declares
  `orchestration-model.md`) — a cross-ledger overlap the disjointness gate cannot see; check
  its status before staging this plan's command.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/orchestrator-refactor/plans/PLAN-02-ledger-decomposition-and-row-vocabulary.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source, tests, and the
orchestrator's own templates/standards. It creates and edits NO file under
`.plan/local/orchestrator/` (or the migrated tracked address, once PLAN-01 lands) other than
its own `inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and
reports its outcome through its PR and its inbox message. The inbox exception's qualifiers and
the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
