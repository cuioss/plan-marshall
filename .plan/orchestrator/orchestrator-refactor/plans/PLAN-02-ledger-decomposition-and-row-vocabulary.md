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

> **Re-grounded 2026-09-21 against HEAD `e8a716501`.** D2 is LARGELY ALREADY DELIVERED —
> `truthful-signals` PLAN-TRUTH-143 (PR #1539, the same landing that unblocked PLAN-06)
> shipped a `VALID_STATUS_VOCABULARY` that is now derived by union of three sets, including
> `CLOSED_UNSHIPPED_PLAN_STATUSES = ('superseded','transferred','retired','resolved')` — the
> exact four values this deliverable's HYPOTHESIS proposed, with the exact four meanings.
> `cmd_queue` validates `--status` against the live set, so `--transition` already accepts
> all four. **D2 shrinks to a documentation/reconciliation task**: `review-apparatus/epic.md`
> (`:48`, `:2533-2542`) and other ledgers still assert the RETIRED vocabulary in narrative —
> reconcile that stale prose, it is not this plan's schema work to redo. D0/D1/D3/D4/D5 are
> untouched and still real; D0's own gate must re-derive the field-write-frequency population
> at THIS plan's own HEAD regardless, since D2's premise moved under it.

## Deliverables

1. **D0 — GATE: derive the collision surface before designing the split.** For each of the 9
   top-level `status.json` fields and each `epic.md` section, state which verbs write it and
   at what frequency. The split follows the write pattern; it is not chosen from the field
   list.
2. **D1 — the per-concern layout**, with the decision recorded per file: what is one file,
   what stays aggregated, and why.
3. **D2 — the row-status vocabulary.** ⚠ ALREADY LANDED at HEAD via PLAN-TRUTH-143 (#1539) —
   `orchestrator.py`'s `VALID_STATUS_VOCABULARY` already admits `superseded`/`transferred`/
   `retired`/`resolved` with the exact meanings this deliverable proposed. What remains:
   reconcile stale ledger prose (`review-apparatus/epic.md`, others) that still asserts the
   old six-value vocabulary, and confirm no OTHER consumer (docs, the schema doc's own
   prose) still states the retired set.
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
- ⚠ SUPERSEDED AT HEAD (was OBSERVED at research time, 2026-09-19; corroborated stale
  2026-09-21) — `orchestrator.py:190` is now a `PLAN_ROW_FIELDS` comment.
  `VALID_STATUS_VOCABULARY` lives at `:243`, derived by union of `LIVE_PLAN_STATUSES` +
  `SHIPPED_PLAN_STATUSES` + `CLOSED_UNSHIPPED_PLAN_STATUSES` (`:220-228`, the last being
  exactly `('superseded','transferred','retired','resolved')`) = 10 members. Landed via
  `1c56734ce` (PR #1539). `cmd_queue` validates `--status` against this set at `:1422` —
  `--transition` already accepts all four.
- ⚠ SUPERSEDED AT HEAD (was OBSERVED, re-derived 2026-09-21 against 13 ledgers — 8 active +
  5 archived, 509 plan rows, 95 rows/19% pre-vocabulary) — `7d82d5d90` (#1578, "restructure
  epics into a fresh live/archived split") moved the population again: `orchestrator corpus
  epics` now reports **25 distinct ledgers (9 active + 16 archived)**, not 13. The 509-row/
  95-row/19% figures are therefore STALE denominators, not a current fact — re-derive
  against 25 rather than trusting either cached figure. This is now historical motivation
  for the fix, not an open gap: the vocabulary itself already landed (see above). D2's
  remaining work is reconciling stale ledger PROSE that still asserts the retired six-value
  set — that work is unaffected by which denominator the historical row-count used.
- OBSERVED — `review-apparatus/epic.md:2533-2542` records this independently and filed it out
  to `truthful-signals` as `review-apparatus-036.md`, explicitly as "not this epic's to fix" —
  this plan is the owner it was missing.
- OBSERVED — `.plan/project-architecture/` is an existing git-tracked, one-file-per-concern
  directory under `.plan/` (13 files, 62,748 B), so the split shape has a working precedent.
- HYPOTHESIS — per-plan-row files remove the staging collision entirely, while per-workstream
  files only narrow it; confirm/refute by constructing the two concurrent-staging scenarios
  against `orchestrator.py` § `_append_plan_row` and the shared `rmw_json` critical section
  (verify-at-outline).
  - verdict: corroborated | checked_at: 9588b30b317d0312ede90f1982122aa3145ea871 | by: orchestrator-refactor/cleanup | rescoped: n/a | evidence: Flips from unverifiable -- the layout now EXISTS and the claim is empirically settled. Per-plan-row files shipped: queue/PLAN-01.json..PLAN-11.json (11 files) beside a header-only status.json, resume_anchor.md, queue-view.md. _status_core.py:340-355 declares the layout and ORCHESTRATOR_LIST_FIELDS at :359 is now frozenset({workstreams}) -- plans is gone from the whole-array rewrite set. Collision-removal proven by matched controls in test_orchestrator_queue_add_row_concurrency.py: test_concurrent_appends_both_survive (:189-222) asserts both writers land and the pre-existing row is byte-identical; negative control test_concurrent_stale_array_commits_lose_one (:224-249) asserts the legacy form silently drops one.
- HYPOTHESIS — `resume_anchor` belongs in its own file: it is written on almost every verb and
  is the field a fresh session reads first; confirm/refute at `orchestrator.py` §
  `cmd_resume_summary` and `_status_core.py` § `cmd_orchestrator_update_field`
  (verify-at-outline).
  - verdict: corroborated | checked_at: 9588b30b317d0312ede90f1982122aa3145ea871 | by: orchestrator-refactor/cleanup | rescoped: n/a | evidence: Flips from unimplemented design proposal -- resume_anchor now has its own file. _status_core.py:341/:349 document resume_anchor.md as a first-class per-concern file; cmd_orchestrator_update_field (:473) branches on field==resume_anchor at :510 to write that file; :353-355 makes a status.json still carrying plans or resume_anchor a refused legacy_layout. The file exists on disk at .plan/orchestrator/orchestrator-refactor/resume_anchor.md.
- HYPOTHESIS — the four unexpressible statuses are four distinct concepts and must not be
  collapsed into one (`superseded` = replaced by a successor spec; `retired` = withdrawn;
  `transferred` = moved to another epic; `resolved` = closed without a plan).
  - verdict: corroborated | checked_at: 9588b30b317d0312ede90f1982122aa3145ea871 | by: orchestrator-refactor/cleanup | rescoped: n/a | evidence: Four distinct concepts, intact, +25 line shift. CLOSED_UNSHIPPED_PLAN_STATUSES=(superseded,transferred,retired,resolved) at orchestrator.py:254; LIVE_PLAN_STATUSES :234, SHIPPED_PLAN_STATUSES :244, TERMINAL_PLAN_STATUSES :260, VALID_STATUS_VOCABULARY derived by union :269; pairwise disjointness enforced by construction-time assert :293-295 over _DECLARED_STATUS_SETS :278-282. cmd_queue validates --status against the live set at :1462.
- Verify-first clause: the 500-row / 12-ledger figure is derived from the ledgers present on
  this machine at research time; re-derive at outline and state which population any count is
  drawn from.
  - verdict: corroborated | checked_at: 9588b30b317d0312ede90f1982122aa3145ea871 | by: orchestrator-refactor/cleanup | rescoped: n/a | evidence: Re-derived at HEAD: orchestrator corpus epics returns distinct_count:25 (active_count:9, archived_count:16, entries_scanned:25, both roots exists/listed true, unreadable_count:0) -- unchanged from the prior pass, matching the rescoped OBSERVED bullet. The methodological instruction to state population remains a live D0 obligation; the prior re-scope has held, no further one owed.

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
/plan-marshall task="implement .plan/orchestrator/orchestrator-refactor/plans/PLAN-02-ledger-decomposition-and-row-vocabulary.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source, tests, and the
orchestrator's own templates/standards. It creates and edits NO file under
`.plan/orchestrator/` other than
its own `inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and
reports its outcome through its PR and its inbox message. The inbox exception's qualifiers and
the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
