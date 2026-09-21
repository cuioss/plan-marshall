# Landing Analysis: PLAN-44 — preference-emitter Writes a Tracked File After the Merge Gate

epic: truthful-signals
workstream: WS-01
pr: 990

> Landing record. Narrative UPGRADED from provisional to full on 2026-07-23 from the operator's
> finalize paste (#990, 4/4 deliverables, 22/22 steps). Deliverable fidelity corroborated against
> merged commit `b8581d952` on `origin/main`.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — GATE: confirm order values, classify the sink | shipped-as-specified | Commit body confirms the sink (`enriched.json`) was classified as legitimately tracked source; the fix moved the step rather than declaring the sink non-source. The D1 fork resolved to the "source → move before merge gate" branch. |
| D2 — apply the chosen fix | shipped-as-specified | `finalize-step-preference-emitter` re-ordered `order: 80` → `61` (memory) into the post-wait settle band (`order < 70` branch-cleanup), so its write rides the plan PR. |
| D3 — finalize contract detects the class, not just the instance | shipped-as-specified + widened | Closed a **second, independent** root cause the spec did not name: the step declared no `mutates_source` key, so the dispatcher's commit instrumentation never fired. Closed the vacuous `if step.mutates_source is None: continue` hole in plugin-doctor's `mutates-source-step-post-merge-order` gate; added finding type `mutates_source_declaration_missing`; back-filled `mutates_source: false` on 7 post-merge omitters. This is a genuine flagship archetype instance (vacuous guard: a gate the omission-of-a-key silently bypassed). |
| D4 — regression test | shipped-as-specified | Commit body + memory confirm tests pinning both the order invariant and the mutates_source-declaration gate. |

## Metrics and Anomalies

- Tokens: 2.7M. Duration: 3h21m wall, 6 phases recorded. Merged Thu 2026-07-23 00:03 UTC.
- Lane: light lane **escalated to deep** on `cross_cutting` — correct, the fix spans a step
  definition, the compose-time gate, and 7 back-filled omitters.
- Q-Gate earned its keep: **2 blocking scope gaps caught at outline + 2 more at plan time**, all
  folded in before execute. The plan's spec (D1–D4) held; the gaps were within-plan completeness,
  not spec defects.
- The plan found a **second root cause** (the mutates_source omission hole) beyond the spec's single
  order-violation framing, and widened scope to close it — a symptom fix turned into an archetype fix.
- Nice confirmation: preference-emitter's own finalize run was a **clean no-op** (no patterns
  promoted) — the fix did not reproduce the symptom it repairs.

## Routing and Merge Behavior

- Merged as #990 at `b8581d952`, rebased onto #989; one commit ahead on origin/main.
- Review: automatic-review 0 actionable comments. CI green.
- Merge path: merge-queue squash-merge; worktree removed, working tree clean. deploy-target v0.1.1200.
- Collisions: PLAN-44 (finalize-step surface) ran concurrent with PLAN-43 (manage-architecture),
  PLAN-41 (phase-1-init), PLAN-42 (CI-await). No conflict observed — disjointness held.

## Reconciliation Actions

- [x] status.json `plans[]` entry updated — PLAN-44 → shipped, pr=990, landing=landings/PLAN-44.md
- [x] epic.md queue reconciled from status.json
- [x] Watch "PLAN-44 source-edit-pushability checks nothing post-merge" retired (the compose-time gate now fires)
- [x] resume_anchor updated
- [x] START-HERE block regenerated

## Follow-Ups

- Lesson `2026-07-23-01-002` (vacuous-guard archetype: a gate bypassed by omitting the key it keys
  on) captures the reusable residue.
- **New watch surfaced** — the `mutates_source_declaration_missing` fix is a fresh, strong data point
  for candidate (a) VACUOUS-GUARDS SWEEP: "a guard whose predicate is skipped when a declaration is
  absent" is now a named, shipped pattern. Fold into candidate (a)'s pattern list.
- No new plan staged; the archetype instance was fully closed within #990.
