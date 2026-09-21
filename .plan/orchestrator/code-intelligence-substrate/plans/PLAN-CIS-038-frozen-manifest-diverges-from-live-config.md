# PLAN-CIS-038: The Frozen Manifest Diverges From Live Config, and Finalize Prompt/Log Residue

epic: code-intelligence-substrate
workstream: WS-04

> Staged 2026-08-08 by SPLITTING `PLAN-CIS-011` (eleven deliverables). This spec takes the
> **frozen-vs-live manifest** arm plus the small finalize prompt/log residue (CIS-011's former D3 and
> D4). CIS-011 keeps the step/dispatch **emission** arm; `PLAN-CIS-037` takes the **boundary-ledger
> arithmetic** arm.
>
> ⚠ **This is the arm with the weakest internal cohesion of the three**, and that is stated rather than
> hidden: D2/D3 are one story (a plan's frozen view of the world going stale mid-run), while D4/D5 are
> genuinely miscellaneous residue that had accumulated in CIS-011's catch-all D4. **If the outline finds
> D4/D5 do not belong beside D2/D3, drop them to their own trivial plan rather than carrying them** —
> they were grouped by *who filed them*, not by surface.

## Objective

A plan's `execution.toon` is **composed at outline and frozen**, then consumed at finalize against a
`marshal.json` that may have changed — including by the plan's own edits. A self-modifying plan's frozen
manifest references steps that no longer exist, or misses steps that now do; and after a non-noop rebase
the per-tree executor is not regenerated, so a clean-env dispatch cannot resolve notations. Make the
frozen view reconcile against the live one instead of silently diverging.

## Why this is ours

The manifest is the substrate's own record of what a run will do; a frozen record diverging from live
config is a code-intelligence staleness defect. Routing test 2 — no PR/review surface.

## Deliverables

### D1 — GATE: establish what diverges and how it is currently handled (mutates nothing)

Read the finalize-entry path and answer: is the frozen `execution.toon` compared against the live
candidate set at all, and what happens on divergence today — a hard `validate-loadable` failure, a
silent pass, or nothing? ⛔ **Settle the fail-direction before writing the fix**: a hard fail on a
self-modifying plan blocks legitimate work, which is why the original lesson asked for **diff/backfill,
not a hard fail**.

### D2 — reconcile frozen `execution.toon` against live `marshal.json` at finalize entry

From lesson `2026-06-21-01-001`. A self-modifying plan's frozen toon references a deleted or added
step. **Diff and backfill** rather than failing loudly — per D1's settled fail-direction.

⭐ **Note the self-exercisability trap, which this plan inherits and must state**: a plan that changes
finalize-entry behaviour runs its **own** finalize under the manifest frozen at **its** outline, i.e.
under the OLD behaviour. ⛔ **Its own green finalize is NOT evidence the fix works** (lesson
`2026-08-03-06-004`). Name the observation point — the next plan composed after this one merges.

### D3 — regenerate the per-tree executor after a non-noop rebase

From lesson `2026-07-10-23-002`. `finalize-step-sync-baseline` must regenerate the phase-5-generated
per-tree executor when a rebase changed the script set; otherwise a clean-env dispatch fails notation
resolution. ⚠ **Same family as the recurring plugin-cache/executor/registry drift the epic tracks in
§ Open Defects** — coordinate the read, but ⛔ **do not absorb the registry-pin work**: that is
`truthful-signals`' `PLAN-TRUTH-059` and this epic has a standing do-not-duplicate on it.

### D4 — finalize prompt and log residue

- `2026-06-25-08-003`: the `finalize-step-simplify` dispatched prompt gains a **line-level** *"pre-existing
  lines OUT OF SCOPE"* clause under changeset scope — today the boundary is file-level only, so a
  dispatched simplifier is invited to rewrite lines the changeset never touched.
- `2026-07-22-12-001`: suppress the repeated `[MANAGE-STATUS] Title token` INFO line when the token
  value is unchanged.
- Promote `2026-06-28-13-001`'s residue: a bypass/guard branch must be placed **before** the dispatch it
  guards (landed #786; promote the rule).

### D5 — tests, each verified to FAIL pre-fix

(a) A frozen manifest referencing a deleted step reconciles per D1's fail-direction rather than
failing hard or passing silently. (b) A rebase that changes the script set leaves a regenerated
executor. (c) An unchanged title token emits no repeated INFO line.

Five deliverables — under the split guard.

## Claim Labels

- **OBSERVED**: the lesson ids, their components, and their OPEN status as carried by `PLAN-CIS-011`
  before the split.
- **HYPOTHESIS (verify-at-outline)**: that each of the four defects is still live at HEAD. ⛔ **This
  plan carries the OLDEST claims in the queue — `2026-06-21`, `2026-06-25`, `2026-06-28`, `2026-07-10`
  — and the 2026-08-08 reconciliation retired `PLAN-CIS-008` in full and re-scoped `PLAN-CIS-020` by
  half for exactly this reason.** ⇒ **D1 MUST re-ground all four against the implementing source before
  scoping any of them**, and should expect at least one to have been closed by unrelated work.
  Confirm/refute artifacts: the finalize-entry manifest comparison site; `finalize-step-sync-baseline`'s
  post-rebase path; the `finalize-step-simplify` prompt body; the `manage-status` title-token log site.

## Expected Surface

- **HYPOTHESIS**: `manage-execution-manifest` — the frozen-vs-live reconciliation (verify-at-outline).
- **HYPOTHESIS**: `phase-6-finalize` — `sync-baseline` executor regeneration and the simplify prompt
  (verify-at-outline).
- **HYPOTHESIS**: `manage-status` — the title-token INFO emission (verify-at-outline).
- **OBSERVED**: tests under `test/plan-marshall/**`.

**Disjointness:** ⛔ **WS-04 serialization class — never pair with `PLAN-CIS-011`, `PLAN-CIS-037`,
`PLAN-CIS-034`, or `PLAN-CIS-020`.** This plan shares `phase-6-finalize` with CIS-011 and CIS-037 and
was one plan with them until 2026-08-08.

## Dependencies and Sequencing

- No hard dependency. ⚠ **Lowest priority of the three CIS-011 arms**: it carries the oldest and least
  corroborated claims, and none of it blocks another plan — unlike `PLAN-CIS-037`, which blocks
  `PLAN-CIS-035`. **Sequence it last of the three.**

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/code-intelligence-substrate/plans/PLAN-CIS-038-frozen-manifest-diverges-from-live-config.md"
```

## Write-Boundary

Repository source + tests only; NO `.plan/local/orchestrator/` writes other than this plan's own
`inbox/{sender}-{seq}` message. See
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
