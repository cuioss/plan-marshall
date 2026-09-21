# PLAN-LR-04: Route the corpus that is already stranded

epic: lessons-routing
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and hand-off contract.

## Objective

Route the findings that are **already** lost. Every other plan in this epic is forward-looking; a new
route does nothing for a finding sitting in a git-ignored directory on one developer's machine, and at
least five such findings were observed first-party across two of four known consumer repos.

⛔ **This plan runs LAST in the epic** — deliberately. Migrating a stranded finding before a
destination exists moves it from one dead end to another and destroys the evidence of where it was.

## Deliverables

Four deliverables.

**D0 — GATE: consume PLAN-LR-01 D1's enumeration; do NOT re-derive it.** ⚠ Re-verify only that the
corpus has not changed since LR-01 ran — consumer repos are live checkouts and a developer may have
filed more. ⛔ If it HAS changed, report the delta explicitly rather than silently adopting the new
figure: a population that moved between derivation and migration is itself a finding about how fast
this corpus accumulates.

**D1 — route every upstream finding through PLAN-LR-03's channel.** ⛔ **Do not hand-copy content
between repositories.** Using the shipped route is what proves the route works on the corpus it was
built for; a hand-migration would leave the mechanism unexercised and the migration unrepeatable.

**D2 — reclassify every mis-classified local finding.** `API-Sheriff`'s two lessons
(`api-sheriff:maven-build`, `api-sheriff:ci-workflows`) are the client's own and were only ever
"foreign" because the old predicate asked the wrong question. ⛔ **They stay in their own repo** — this
deliverable corrects a classification, it does not move a finding anywhere.

**D3 — leave the migration auditable, and make a second run a no-op.** Record what was routed, where it
went, and what was deliberately not routed. ⛔ **Every finding gets a recorded disposition — routed,
reclassified, or retired — and "retired" requires a stated reason.** A silent drop during a migration
whose whole purpose is to stop silent drops would be this epic's own archetype committed by its final
plan. ⚠ Re-running must not re-file what was already routed; the dedup key from LR-03 D2 is the
mechanism, not a fresh one.

## Expected Surface

- consumer repo checkouts under `~/git/**/.plan/local/lessons-learned/` *(read, and — for D2 only —
  local reclassification within each client's own store)*
- an audit artifact in this epic's tree

⛔ **No plan-marshall source changes.** This plan consumes machinery that LR-02 and LR-03 shipped; if it
finds itself needing a code change, that is a defect in one of those plans and belongs there.

## Dependencies and Sequencing

- ⛔ **Depends on PLAN-LR-01, PLAN-LR-02 and PLAN-LR-03 — all hard.** It is the epic's terminal plan.
- ⚠ **It writes into consumer repositories** (D2's reclassification), which every other plan in this
  epic is forbidden to do. ⛔ **Confirm the write scope with the operator before executing D2** — a
  cross-repo write is not covered by any standing authorization this epic carries.

## Claim Labels

- OBSERVED: `cui-jsf-test-basic` holds 3 stranded `plan-marshall:*` lessons and 1 local one — read at `~/git/cui-jsf-test-basic/.plan/local/lessons-learned/*.md` § `component=` headers.
- OBSERVED: `API-Sheriff` holds 2 lessons, both its own, both mis-classified as foreign by the current predicate — read at `~/git/API-Sheriff/.plan/local/lessons-learned/*.md` § `component=` headers.
- OBSERVED: two of four known consumer repos were sampled, so the denominator is NOT established — this plan's own staging record.
- HYPOTHESIS: the corpus has not grown since PLAN-LR-01 enumerated it — confirm/refute at each consumer store § file count (verify-at-outline). **D0 re-verifies rather than inheriting; a moved population is itself a finding.**
- Verify-first clause: every finding must carry a recorded disposition (routed / reclassified / retired, the last with a stated reason) before this plan may report done — a silent drop inside a migration against silent drops is the failure mode.
