# PLAN-53: Orchestrator queue row-field setter

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-53-orchestrator-queue-row-field-setter.md` and is queued in the epic
> `status.json` `plans[]` field. The orchestrator EMITS the command below; it never launches
> the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-marshall-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

The orchestrator's `plans[]` rows carry three per-plan result fields — `plan_marshall_plan_id`,
`pr`, and `landing` — that the render path reads back but no verb can set individually. `queue`
accepts only `--transition/--status`, so the only sanctioned way to stamp a landing result is
`manage-status update-field --field plans` with the **entire** array re-serialized as one JSON
payload. That is a read-modify-write of the whole queue to change one cell: verbose, easy to get
wrong, and lossy under concurrent epics. In practice orchestrators have skipped it, leaving
`plan_marshall_plan_id` empty on 22 of 39 rows in the archived `plan-optimization` epic while the
id survives only as prose in `resume_anchor` — and at least two epics' ledgers now instruct a
**direct `status.json` edit**, which the script-mediation rule prohibits outright.

This plan adds a per-row setter to the `queue` verb so stamping a landing is a single targeted
call, and retires the direct-edit instruction wherever it appears in orchestrator guidance.

## Deliverables

1. **D1 (design gate)** — Settle the setter's shape against the existing `queue` surface: whether
   the row fields are set by extending `--transition` (a status change and a stamp in one call) or
   by a separate `--set-field/--value` pair usable without a status change, plus whether an unknown
   plan id or an unknown field name is an error (fail-closed) or a no-op. Settle concurrency: the
   whole-array rewrite is read-modify-write, so the setter must not reintroduce a lost-update race
   between two orchestrator sessions. Record the choice as an ADR-grade rationale in the PR body.
2. **D2** — Implement the per-row setter in `orchestrator.py`'s `queue` command, writing through
   the same `manage-status`-mediated path the transition already uses. No new direct-write path.
3. **D3** — Make the incomplete row observable rather than silent: `resume-summary` currently
   renders `plan={id}` only when the field is truthy (`orchestrator.py:205-206`), so an unstamped
   shipped row is indistinguishable from a correctly-stamped one. A `shipped` row missing `pr` or
   `landing` must surface as a visible gap in the generated block.
4. **D4** — Retire the prohibited workaround from guidance: remove/replace any "stamp via DIRECT
   Edit of status.json" instruction in orchestrator workflow docs and templates, pointing at the
   new setter instead.
5. **D5** — Tests: per-row set lands in the named row and leaves siblings byte-identical; a
   `shipped` row with an empty `pr`/`landing` renders the D3 gap signal; unknown plan id and
   unknown field behave per the D1 verdict; a whole-array `update-field` write still works
   (no regression to `decompose`'s Step-5 bulk seed).

Five deliverables — under the six-deliverable split guard; D1 is a gate rather than a shipped
artifact, so the implementation surface is effectively four. No split.

## Claim Labels

- OBSERVED: `plan_marshall_plan_id` is declared in the schema — read at
  `manage-status/standards/status-lifecycle.md`:115 and `manage-status/scripts/_status_core.py`:120
  (TOON row comment).
- OBSERVED: the field is seeded as `""` at stage time and never subsequently written — read at
  `marshall-orchestrator/workflow/decompose.md`:49 (the `plans[]` entry shape).
- OBSERVED: the field is read back at render time — read at
  `marshall-orchestrator/scripts/orchestrator.py`:205-206 (`parts.append(f'plan={...}')`), guarded
  by a truthiness check so an empty value renders as nothing at all.
- OBSERVED: `queue` exposes only `--transition` and `--status`, which must be supplied together —
  read at `marshall-orchestrator/scripts/orchestrator.py`:156-160 and the argparse block at
  :361-375.
- OBSERVED: a sanctioned whole-array write path DOES exist — `manage-status update-field
  --field plans --value {json_array}` — read at `marshall-orchestrator/workflow/decompose.md`:49-61.
  This plan is therefore an **ergonomics and safety** fix, NOT the creation of a missing capability.
- OBSERVED (derived count, verified this session): in
  `.plan/local/archived-orchestrators/plan-optimization/status.json`, 17 of 39 rows carry a
  non-empty `plan_marshall_plan_id` and 22 are empty, interleaved across the id range
  (PLAN-01–06 empty, 07–19 populated, 20–31 empty, 32–34 and 36–39 populated, 35 and 40 empty).
- OBSERVED (fresh corroboration, 2026-07-25 session): the whole-array rewrite was performed **twice
  in one session** on this epic, each time re-serializing all 27 `plans[]` rows to stamp two cells
  (PLAN-48 `pr`+`landing`, then PLAN-47 `pr`+`landing`). Both writes were correct, but each carried
  the full lost-update surface D1 must address. This is direct evidence that the ergonomics gap is
  live and recurring, not historical.
- OBSERVED: direct mutation of `status.json` is prohibited — read at
  `persona-marshall-orchestrator/standards/orchestration-model.md` § Carve-Outs, "Status
  transitions" bullet ("never by direct file writes").
- HYPOTHESIS: the interleaved emptiness is per-session orchestrator diligence variance rather than
  a withdrawn capability — confirm/refute at `marshall-orchestrator/scripts/orchestrator.py`
  § `_cmd_queue` git history, checking whether any prior revision exposed a row-field setter
  (verify-at-outline). A withdrawn writer would predict a clean chronological cutoff, which the
  observed interleaving contradicts.
- Verify-first clause: before scoping D2, confirm against the implementing source that
  `manage-status update-field` genuinely rejects a dotted/indexed path into `plans[]` (i.e. that
  it is top-level-only in fact and not merely by convention). If it already supports a nested
  path, D2 collapses to documenting that path and D1's shape question is moot — loop back and
  re-scope rather than building a redundant setter.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/marshall-orchestrator/scripts/orchestrator.py`
  :145-210 — `_cmd_queue` and the resume-summary row renderer.
- OBSERVED: `.../skills/marshall-orchestrator/scripts/orchestrator.py`:361-375 — the `queue`
  argparse block.
- HYPOTHESIS: `.../skills/manage-status/scripts/_status_core.py` — `update-field` path handling,
  touched only if the verify-first clause shows nested-path support is the better seam
  (verify-at-outline).
- OBSERVED: `.../skills/marshall-orchestrator/SKILL.md` — the "Canonical invocations" § `queue`
  block, which plugin-doctor reads as source-of-truth and which must gain the new arguments.
- OBSERVED: `.../skills/marshall-orchestrator/workflow/analyze.md` — the landing-reconciliation
  step that stamps `pr`/`landing`.
- HYPOTHESIS: `.../skills/marshall-orchestrator/templates/plan-spec.md` and `epic.md` — only if a
  direct-edit instruction is present (verify-at-outline; D4 is a sweep, so enumerate against the
  whole `marshall-orchestrator` tree, not against the diff).
- OBSERVED: `test/plan-marshall/marshall-orchestrator/` — the queue-verb test module.

Re-verify this surface against HEAD at outline before scoping: PLAN-49 renames
`marshall-orchestrator` → `plan-orchestrator` wholesale, and PLAN-41 edits `orchestrate.md`.

## Dependencies and Sequencing

- Depends on: none. Emittable as soon as a slot frees.
- Overlaps with: **PLAN-49** (drain-gated last) renames this plan's entire directory and both
  orchestrator skills — PLAN-53 MUST land before PLAN-49, which is already the epic's terminal
  plan, so no additional gate is needed beyond keeping PLAN-49 last. **PLAN-41** edits
  `orchestrate.md`; PLAN-53 does not, but both sit in the `marshall-orchestrator` tree — sequence
  PLAN-53 after PLAN-41 (the operator's chosen order) rather than concurrently.
- Adjacent to: **PLAN-47/PLAN-48** touch orchestrator-tier *config* (`marshal.json` schema,
  `manage-config`), a different seam from this plan's *status writer* — they stay untouched here.
  **PLAN-46** touches `manage-status/_status_core.py` for title repaint; if PLAN-53's verify-first
  clause pulls `_status_core.py` into scope, re-check disjointness against PLAN-46 before running
  the two concurrently.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-53-orchestrator-queue-row-field-setter.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/local/orchestrator/` — the orchestrator owns every ledger write —
and reports its outcome through its PR alone. See
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
