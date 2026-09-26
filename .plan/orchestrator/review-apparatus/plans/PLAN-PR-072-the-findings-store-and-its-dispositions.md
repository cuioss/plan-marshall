# PLAN-PR-072: The findings store, and the dispositions it records

> ⛔⛔ **SUPERSEDED BY PM-MCP (2026-09-26, operator decision; row status `superseded`).** `plan-marshall-mcp` replaces both the
> process prose and the Python scripts this plan edits, so implementing it here is legacy work. Its
> implementation-independent content (rules, invariants, classifications, data, fixtures) was extracted to
> [`findings/2026-09-26-pm-mcp-carry-over.md`](../findings/2026-09-26-pm-mcp-carry-over.md) as PM-MCP input.
> Do NOT emit. `superseded` is terminal; re-staging needs an explicit operator decision.

epic: review-apparatus
workstream: WS-03

> **Component-cut spec, authored 2026-09-18.** This plan owns ONE component: `manage-findings` — `_findings_core.py`, `jsonl-format.md`, the resolution vocabulary and the marker lifecycle.
> ⛔ **Every deliverable body below lives in its ORIGINAL source spec and is NOT restated here** — the
> `Carried from` column names the theme spec this deliverable was cut out of, and that spec's own
> pointer names the retired spec holding the body. Follow the chain; do not retype.
>
> The theme specs `PLAN-PR-056` … `PLAN-PR-064` were retired on 2026-09-18 because their surfaces
> overlapped almost totally — `_findings_core.py` was declared by 7 of 9 — so no two could ever run
> concurrently. The cut is by component, so **no file is declared by two live plans**.

## Objective

Make the store persist what the producers already know, keep a marker honest through its whole lifecycle, and let a disposition express an outcome its vocabulary cannot express today.

## Deliverables

| # | Deliverable | Body lives at | Carried from |
|---|---|---|---|
| D1 | Close and document the marker lifecycle in `manage-findings` | `PLAN-PR-029` § D3 | `PLAN-PR-059` D3 |
| D2 | The discrimination already exists; nothing persists it | `PLAN-PR-053` § D1a | `PLAN-PR-058` D2 |
| D3 | Make the bucket/detail contradiction mechanically detectable | `PLAN-PR-037` § D1 | `PLAN-PR-063` D7 |
| D4 | Accept a reviewer's INTENT, verify its DETAIL | `PLAN-PR-037` § D5 | `PLAN-PR-063` D11 |


**D0 — GATE, mutates nothing.** The merged gate. From `PLAN-PR-050` D0: re-ground all three claims at
HEAD and record, per claim, the file and symbol that settles it. From `PLAN-PR-037` D0: establish which
of the two explanations for the bucket/detail contradiction holds, and publish the population. **HALT
and report** if either no longer reproduces.

*(Carried verbatim from `PLAN-PR-063` D0 at the 2026-09-18 component re-cut.)*

5 deliverables — within the guideline (12 nominal, ~14 when the aspects fit together, operator ruling 2026-09-15). ⛔ **Absorb nothing from another component**: the re-cut exists so this plan's surface stays disjoint.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-findings/scripts/_findings_core.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-findings/standards/jsonl-format.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-findings/SKILL.md`
- OBSERVED: `test/plan-marshall/manage-findings/`

## Claim Labels

- OBSERVED (2026-09-18): every deliverable in this plan was carried verbatim from the theme spec named
  in its `Carried from` column, which carries the claim labels for its own deliverables. Confirm/refute
  by reading that spec's `## Claim Labels` section — this plan re-states none of them.
  - verdict: corroborated | checked_at: 7d82d5d90 | by: review-apparatus/cleanup | rescoped: n/a | evidence: Structural carried-verbatim claim, verified by reading this spec at HEAD: four pointer deliverables plus a merged D0, and the post-run-quality-001 drain table records carriers rather than new bodies.
- OBSERVED (2026-09-18, orchestrator `corpus surfaces` + per-deliverable mapping): this plan's declared
  surface is disjoint from every other live plan's in this epic. Confirm/refute with
  `orchestrator corpus cross-check --slug review-apparatus`.
  - verdict: corroborated | checked_at: 7d82d5d90 | by: review-apparatus/cleanup | rescoped: n/a | evidence: DISJOINTNESS HOLDS, derived by membership: _findings_core.py, jsonl-format.md, manage-findings/SKILL.md and test/plan-marshall/manage-findings are declared by no other STAGED spec - a real change from the theme-spec era this file own header records. AND its whole declared surface is UNDISTURBED: zero of the four declared paths appear in git diff --name-only 7a028157e..HEAD. This plan is the cleanest re-grounding in the corpus.


## Inbox drain 2026-09-18 — `post-run-quality-001.md`

`post-run-quality` forwarded four corpus lessons on reviewer-quality metrics, all one shape: **a ratio
published over a denominator whose members were never established.** All four were already absorbed by
this epic on 2026-09-18 and are carried here — no new deliverable, recorded so the cluster is not
re-forwarded:

| Lesson | Carried by |
|---|---|
| `2026-09-05-07-001` administrative vs refuted premise in `rejected` | `PLAN-PR-076` D1 |
| `2026-08-27-18-001` a refuted finding filed `accepted` reads a confident zero | D3 (bucket/detail contradiction at the write seam) + `PLAN-PR-076` D1 |
| `2026-09-03-08-001` claimless status-summary counted actionable → `0.0%` where the honest answer is undefined | `PLAN-PR-070` D2 + `PLAN-PR-076` D2 |
| `2026-09-15-08-039` "3 reviewers compared" over 1 measured participant | `PLAN-PR-070` D0/D2 + `PLAN-PR-071` D1 |

⭐ **The seam the sender names explicitly as ours**: the `review_completeness` → `bot_states` handoff has
no persisted carrier an `order: 990` step can read, so the retrospective's zero-findings grade fails
closed to `indeterminate`. That producer-side fix is **D2** of this plan, consumed by `PLAN-PR-071` D1.

## Dependencies and Sequencing

- ⛔ **Runs FIRST of the pipeline plans.** Its marker lifecycle (D1) and its persisted bot states (D2)
  are read by `PLAN-PR-067` D8 and written through by `PLAN-PR-068` D1; its new disposition member
  (D4) changes what `PLAN-PR-071` D8 counts.
- ⛔ **D4 before `PLAN-PR-071` D8**, or 071 publishes a denominator the next deliverable invalidates.
- ⚠ D0 is a store SWEEP: a zero means "none in the reachable stores", never "none exist" — the
  originating archive of the observed instance is on another machine.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/review-apparatus/plans/PLAN-PR-072-the-findings-store-and-its-dispositions.md"
```

## Write-Boundary

The plan implementing this spec writes to its own repository source only. It creates and edits NO file
under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message.
