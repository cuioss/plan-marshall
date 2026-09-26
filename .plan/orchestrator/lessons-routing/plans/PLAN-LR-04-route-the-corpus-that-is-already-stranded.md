# PLAN-LR-04: Route the corpus that is already stranded

> ⛔⛔ **SUPERSEDED BY PM-MCP (2026-09-26, operator decision; row status `parked`).** `plan-marshall-mcp` replaces both the
> process prose and the Python scripts this plan edits, so implementing it here is legacy work. Its
> implementation-independent content (rules, invariants, classifications, data, fixtures) was extracted to
> `/Users/oliver/git/plan-marshall-mcp/doc/known-defects/lessons-routing-carry-over.md` as PM-MCP input.
> Do NOT emit; un-park only by explicit operator decision.

epic: lessons-routing
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and hand-off contract.

## Objective

Route the findings that are **already** lost. Every other plan in this epic is forward-looking; a new
route does nothing for a finding sitting in a git-ignored directory on one developer's machine.

⛔⛔ **STALE at cleanup 2026-09-23 — the population below moved substantially since staging; re-derive
fresh at outline via D0, do not inherit these counts.** At staging: "at least five such findings...
across two of four known consumer repos." Re-sampled: `cui-jsf-test-basic` unchanged (4 lessons, 3
stranded); `API-Sheriff` now holds **16** live lessons + 32 tombstones, and its two originally-named
lessons (`api-sheriff:maven-build`, `api-sheriff:ci-workflows`) are BOTH retired — D2 as originally
scoped has no live subject; `nifi-extensions` (never sampled at staging) holds 20 lessons including
**2 more** stranded `plan-marshall:*` findings (`plan-marshall:build-maven` `2026-07-16-21-002`,
`plan-marshall:phase-4-plan` `2026-07-17-17-002`) plus several correctly-local
`nifi-extensions:*`-prefixed lessons that may show the SAME mis-classification class D2 targets,
just on different concrete lessons; `TokenSheriff` 0 live, 59 tombstones. This is exactly the D0 delta
this plan's own gate exists to catch — it is not this cleanup note's job to re-scope D0/D1/D2's
deliverable text further, since D0 is specifically the mechanism for absorbing a moved population.

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

**D2 — reclassify every mis-classified local finding.** The class this deliverable targets — a client's
own component mis-classified as foreign by the old predicate — is real; the two SPECIFIC lessons
originally named here (`api-sheriff:maven-build`, `api-sheriff:ci-workflows`) are retired per the
Objective's stale-population note above and are NOT this deliverable's live subject — re-derive which
concrete lessons need reclassification from D0's fresh enumeration. ⛔ **They stay in their own repo** —
this deliverable corrects a classification, it does not move a finding anywhere.

**D3 — leave the migration auditable, and make a second run a no-op.** Record what was routed, where it
went, and what was deliberately not routed. ⛔ **Every finding gets a recorded disposition — routed,
reclassified, or retired — and "retired" requires a stated reason.** A silent drop during a migration
whose whole purpose is to stop silent drops would be this epic's own archetype committed by its final
plan. ⚠ Re-running must not re-file what was already routed; the dedup key from LR-03 D2 is the
mechanism, not a fresh one.

## Expected Surface

- consumer repo checkouts under `~/git/**/.plan/local/lessons-learned/` *(read, and — for D2 only —
  local reclassification within each client's own store)*
- the plan's own `work/` artifacts recording each finding's routed/reclassified/retired disposition —
  NOT a write into `.plan/orchestrator/lessons-routing/`, which the plan may not touch; the orchestrator's
  `analyze` verb folds this into `landings/PLAN-LR-04.md` after landing

⛔ **No plan-marshall source changes.** This plan consumes machinery that LR-02 and LR-03 shipped; if it
finds itself needing a code change, that is a defect in one of those plans and belongs there.

## Dependencies and Sequencing

- ⛔ **Depends on PLAN-LR-01, PLAN-LR-02 and PLAN-LR-03 — all hard.** It is the epic's terminal plan.
- ⚠ **It writes into consumer repositories** (D2's reclassification), which every other plan in this
  epic is forbidden to do. ⛔ **Confirm the write scope with the operator before executing D2** — a
  cross-repo write is not covered by any standing authorization this epic carries.

## Claim Labels

- OBSERVED: `cui-jsf-test-basic` holds 3 stranded `plan-marshall:*` lessons and 1 local one — read at `~/git/cui-jsf-test-basic/.plan/local/lessons-learned/*.md` § `component=` headers.
  - verdict: corroborated | checked_at: 14d8f3ccd | by: lessons-routing/cleanup | rescoped: n/a | evidence: 4 .md files enumerated in cui-jsf-test-basic; component= headers read individually, unchanged since staging
- OBSERVED: `API-Sheriff` holds 2 lessons, both its own, both mis-classified as foreign by the current predicate — read at `~/git/API-Sheriff/.plan/local/lessons-learned/*.md` § `component=` headers.
  - verdict: contradicted | checked_at: 14d8f3ccd | by: lessons-routing/cleanup | rescoped: yes | evidence: MAJOR DRIFT: git -C ~/git/API-Sheriff ls-files --others --ignored --exclude-standard = 16 live .md + 32 tombstones. Neither api-sheriff:maven-build nor api-sheriff:ci-workflows exists live (both tombstoned). Objective section rewritten with the current population and D2 corrected to not name specific retired lessons
- OBSERVED: two of four known consumer repos were sampled, so the denominator is NOT established — this plan's own staging record.
  - verdict: corroborated | checked_at: 14d8f3ccd | by: lessons-routing/cleanup | rescoped: n/a | evidence: true as a statement of the staging record; now obsolete in effect since cleanup enumerated all 4 repos (see Objective note) - the STATEMENT is still accurate history, the underlying denominator gap has since been closed
- HYPOTHESIS: the corpus has not grown since PLAN-LR-01 enumerated it — confirm/refute at each consumer store § file count (verify-at-outline). **D0 re-verifies rather than inheriting; a moved population is itself a finding.**
  - verdict: contradicted | checked_at: 14d8f3ccd | by: lessons-routing/cleanup | rescoped: yes | evidence: Grown substantially: API-Sheriff 2->16 (all filed after staging), nifi-extensions 20 lessons never counted incl. 2 previously-unknown stranded plan-marshall:* findings. D0's own 'report the delta explicitly' obligation is now live, not hypothetical - Objective section rewritten to state this
- Verify-first clause: every finding must carry a recorded disposition (routed / reclassified / retired, the last with a stated reason) before this plan may report done — a silent drop inside a migration against silent drops is the failure mode.
  - verdict: corroborated | checked_at: 14d8f3ccd | by: lessons-routing/cleanup | rescoped: n/a | evidence: still binding, now over a materially larger population (40 live lessons across 3 repos vs the 6 the spec assumed); API-Sheriff's own 32-tombstone set shows retirements already happened without this epic's disposition record - the clause is load-bearing
