# PLAN-TRUTH-099: The epic ledger has no safe single-row append, so staging a plan means rewriting 145 rows

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Staged by `analyze` on 2026-08-22, from a gap hit while staging PLAN-TRUTH-098.
> ⛔ **This spec is itself unqueued** — it cannot be added to `plans[]` without performing the
> very operation it exists to make safe. That is not an oversight; it is the defect, observable.

## Objective

Give the orchestrator a verb that appends ONE row to an epic's `plans[]`. Today the only add-path
is `manage-status update-field --field plans` carrying the entire array as a single `--value`, so
staging one plan into this epic's 145-row ledger means re-serializing 145 unrelated rows — a
read-modify-write over the whole machine authority, on a shell argument, with no rollback. The
`--set-row` verb already solved exactly this problem for *mutating* a row; the *append* half was
never built.

## Problem

**The gap is closed on three sides and open on the fourth.** `orchestrator queue` offers:

| Operation | Mechanism | Safe? |
|---|---|---|
| Read the queue | `queue --slug` | yes |
| Transition one row's status | `queue --transition PLAN-NN --status S` | yes — locates one row, mutates in a shared read-modify-write critical section |
| Set one row's result field | `queue --set-row PLAN-NN --field F --value V` | yes — same critical section, `--field` whitelisted |
| **Append a new row** | **none** | — |

`update-field`'s own help states the intent plainly: *"the list fields workstreams / plans
(JSON-array `--value`)"*. It is the bulk seed `decompose` uses to write a queue from nothing.
`analyze.md` Step 5b's **Stage** disposition points at *"the `decompose.md` Step 5 queue-write
shape"* for adding one row — which was reasonable when a queue held a handful of rows and is not
reasonable at 145.

⭐ **The lost-update reasoning that motivated `--set-row` applies to append verbatim.** The
`queue --set-row` canonical block already says it: *"re-serializing every row to change one cell is
the lost-update path `--set-row` exists to remove."* Appending re-serializes every row to ADD one
cell. Same path, same risk, no verb.

**Observed consequence, this drain (2026-08-22).** `analyze` staged PLAN-TRUTH-098 from two drained
inbox messages, authored the spec file, and then could not queue it. The operator was consulted and
chose to leave it unqueued rather than accept a 146-row hand-serialization against the ledger that
107 shipped plans depend on. `corpus enumerate` now reports `specs_without_row_count: 2` — this spec
and PLAN-TRUTH-098 — so **the gap is visible rather than silent**, which is the only reason the
state is acceptable at all. Neither plan is emittable until a row exists.

## Deliverables

### D1 — `queue --add-row`: append exactly one row

Add an append form to `orchestrator queue`, in the SAME shared read-modify-write critical section
the existing two write forms use, mutually exclusive with both (supplying more than one write form
returns `wrong_parameters`, matching the existing `--transition` / `--set-row` contract).

Minimum argument surface — the fields `decompose` seeds per row:
`--add-row PLAN-NN --slug-value {plan_slug} --workstream WS-NN [--status staged]`.
The three result fields (`plan_marshall_plan_id`, `pr`, `landing`) initialise empty and are set
afterwards through the existing `--set-row`, so this verb gains no second stamping path.

⛔ **Refuse a duplicate id** (`duplicate_plan_id`, naming the existing row) rather than appending a
second row with the same `PLAN-NN`. A duplicate id silently breaks every `--transition` and
`--set-row` call thereafter, since both locate by id.

⛔ **Refuse an id whose spec file is absent** — or return it as a named warning field, not silently.
The bidirectional invariant `corpus enumerate` checks (`rows_without_spec` / `specs_without_row`) is
the thing this verb must not be able to violate from the row side.

### D2 — repoint the Stage disposition at the new verb

`analyze.md` Step 5b's **Stage** row and `decompose.md` Step 5 currently both point at the bulk
array write. Repoint Stage at `queue --add-row`; leave `decompose` on the bulk form, which is the
correct mechanism for seeding a queue from nothing. State the boundary explicitly in
`orchestration-model.md` alongside the existing `--set-row` boundary sentence, so the three write
forms read as one contract: **bulk seed at decompose, single append at stage, single mutate at
reconcile.**

### D3 — a matched control proving the critical section holds

Per the epic's standing rule, prove the append participates in the same concurrency guarantee as
the existing forms: a positive control where two writers append concurrently and both rows survive,
and a negative control where the bulk `update-field` path is used concurrently and the lost update
is observable. The negative control is what makes the fix's value measurable rather than asserted.

### D4 — retire the two unqueued specs' backlog

After D1 lands, append the rows for **PLAN-TRUTH-098** and **PLAN-TRUTH-099** (this spec) using the
new verb, and confirm `corpus enumerate` returns `specs_without_row_count: 0`. ⭐ This is the fix
verifying itself against the exact state that motivated it — the two rows it must be able to add
are already on disk waiting.

## Claim Labels

- **OBSERVED (this orchestrator, 2026-08-22, at HEAD `31211a99b`)**: that `orchestrator queue
  --help` declares exactly `--transition/--status` and `--set-row/--field/--value` and no append
  form; that `manage-status update-field --help` declares `--value` as a JSON array with no file
  input; that `corpus enumerate` reports `rows_total: 145` against `specs_total: 146` with
  `specs_without_row_count: 1` at the moment PLAN-TRUTH-098 was authored.
  - verdict: corroborated | checked_at: 31bed3e76 | by: truthful-signals/cleanup | rescoped: n/a | evidence: Confirmed at this HEAD, not merely at the cited 31211a99b: orchestrator queue --help declares only --transition/--status and --set-row/--field/--value, with no append form. This drain then had to USE the whole-array update-field path twice (to add the -112 and -113 rows), which is first-party confirmation of the gap this plan exists to close
- **OBSERVED**: that `analyze.md` Step 5b's Stage disposition points at `decompose.md` Step 5's
  queue-write shape — read from the workflow doc.
  - verdict: corroborated | checked_at: 31bed3e76 | by: truthful-signals/cleanup | rescoped: n/a | evidence: analyze.md Step 5b's Stage disposition reads 'Stage a NEW spec plus its queue entry, via the decompose.md Step 5 queue-write shape' - the pointer is present in the workflow doc as claimed
- **HYPOTHESIS**: that the existing read-modify-write critical section in `orchestrator.py`'s queue
  group can host an append with no structural change. Confirm/refute against `orchestrator.py`, the
  `queue` command's critical-section helper — **verify-at-outline**.
  - verdict: unverifiable | checked_at: 31bed3e76 | by: truthful-signals/cleanup | rescoped: n/a | evidence: Whether the existing read-modify-write critical section can host an append with no structural change is a design-feasibility question settled by attempting it at outline, not by reading the current code. The section exists; whether it SUFFICES is not observable before the change
- **HYPOTHESIS**: that `decompose` is the ONLY caller that legitimately needs the bulk array write,
  so D2's repointing strands no other consumer. Confirm/refute by deriving the caller set from the
  population rather than from a reading — ⚠ this epic's standing correction: *a reviewer's list of
  call sites is a SAMPLE, not an enumeration.*
  - verdict: unverifiable | checked_at: 31bed3e76 | by: truthful-signals/cleanup | rescoped: n/a | evidence: The claim itself requires deriving the caller set from the population rather than from a reading, and that derivation is D2's own work. Answering it here by reading would commit the exact error the claim warns against

## Expected Surface

- `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py` — the `queue`
  command group and its shared critical section
- `marketplace/bundles/plan-marshall/skills/plan-orchestrator/SKILL.md` — the `queue` canonical
  invocation block
- `marketplace/bundles/plan-marshall/skills/plan-orchestrator/workflow/analyze.md` — Step 5b Stage row
- `marketplace/bundles/plan-marshall/skills/plan-orchestrator/workflow/decompose.md` — Step 5 boundary note
- `marketplace/bundles/plan-marshall/skills/persona-plan-orchestrator/standards/orchestration-model.md`
  — the three-write-form boundary statement
- `test/plan-marshall/plan-orchestrator/test_orchestrator.py` — append form, duplicate-id refusal,
  and the D3 matched controls

## Dependencies and Sequencing

- **Depends on**: none.
- **Overlaps with**: **PLAN-TRUTH-096** (orchestrator inbox and landing residue) — both edit
  `plan-orchestrator/SKILL.md` and `workflow/analyze.md`. ⛔ **Sequence these, do not parallelize.**
- **Adjacent to**: PLAN-TRUTH-098, which this plan unblocks at D4 but does not otherwise touch.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-099-the-ledger-has-no-safe-single-row-append.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and
edits NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message —
the orchestrator owns every other ledger write — and reports its outcome through its PR and its
inbox message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated
in `persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
