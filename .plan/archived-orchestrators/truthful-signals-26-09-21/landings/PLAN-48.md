# Landing Analysis: PLAN-48 — orchestrator emit autonomy (`orchestrator.auto_emit`)

epic: truthful-signals
workstream: WS-01
pr: #996 (https://github.com/cuioss/plan-marshall/pull/996) — squash-merged, 1fad08686

> Landing record for one shipped plan. Reconciled during a `resume` (the ship happened
> while no orchestrator session was watching). Corroborated against the merged diff at
> 1fad08686 — file set, `_config_defaults.DEFAULT_ORCHESTRATOR`, and the
> `orchestrate.md` / `analyze.md` emit-seam diff — not against the PR narrative alone.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 gate — pin what `auto_emit` does / does NOT automate | shipped-as-specified | `orchestrate.md` Step 5 gate text: candidate selection unchanged under either branch; only whether the emitted block's `launched` transition is auto-recorded changes |
| D2 — add `orchestrator.auto_emit` + wire the landing flow | shipped-as-specified | `_config_defaults.py` `DEFAULT_ORCHESTRATOR = {'auto_emit': False}` (+25), `_config_core.py` canonical key order (+1), `_cmd_system_plan.py` `cmd_orchestrator` get/set noun (+60), `manage-config.py` (+20); `orchestrate.md` (+28) / `analyze.md` (±4) read the knob at the post-landing emit seam |
| D3 — invariant guard enforced and tested | shipped-with-caveat | The emit≠running invariant is enforced as a **doc contract** ("neither branch ever records started/`running`", plus the anchor-wording rule) — correct, because the emit seam is a workflow doc with no code path to assert against. The shipped tests (`test_config_defaults.py` +84, 6 cases) pin default-off seeding, the block's presence in the default config and key order, the get/set roundtrip, and unknown-field rejection — config surface, **not** an emit-cadence regression test. No executable test asserts "auto_emit=true fills with `launched` only" or the shortfall-logs-nothing path. |
| D4 — steward seeding + doc | shipped-as-specified | Seeded through `get_default_config()`'s `'orchestrator': deepcopy(DEFAULT_ORCHESTRATOR)` (steward `sync-defaults` deep-merges it); documented in `data-model.md` (+27), `api-reference.md` (+38), and `orchestration-model.md` (+8) beside the plan-tier autonomy knobs |

Diff: 10 files, 289 insertions / 6 deletions.

**Deliverable-count reconciliation.** The finalize summary reports **3/3** deliverables; this spec
staged **four** (D1–D4). The mapping: D1 was an investigation gate consumed at outline (it mutates
nothing, so it never became an executed deliverable); D2's config half and D4's seeding/test half
merged into executed deliverable 1; D2's wiring became executed deliverable 2; D4's docs became
executed deliverable 3. **D3 has no executed deliverable of its own** — its test obligation was
absorbed into deliverable 1's config-layer test set. That absorption IS the caveat recorded in the
table above, and the finalize summary independently corroborates it: no deliverable line claims an
emit-cadence assertion.

## Metrics and Anomalies

- Duration 1h14m / 1.6M tokens. Finalize: 21/21 steps, CI green across 11 checks, squash-merged via
  the merge queue. `automatic-review` 0 actionable comments; `review-retrospective` 0 findings;
  `lessons-capture` 0 new lessons (the doc-drift recurrence was covered by an existing lesson);
  `preference-emitter` promoted nothing; `finalize-step-simplify` 0 edits. Archived to
  `2026-07-25-orchestrator-emit-autonomy` — **relocated 2026-07-26 by the archived-plan audit's dormation sweep; the artifacts now live at `.plan/temp/dormated-plans/2026-07-25-orchestrator-emit-autonomy`** (a move, not a delete; `.plan/local/archived-plans/` is now empty).

- **Block-definition order inverted vs plan.** The spec said "whichever lands first defines
  the block" — PLAN-48 landed first, so **PLAN-48 DEFINED** the top-level `orchestrator`
  block (with `auto_emit` only). PLAN-47 (still in flight, PR #997) must now **EXTEND** the
  existing block, not define it. `sync-defaults` deep-merge converges under either order, so
  this is a sequencing note, not a defect.
- **Self-review caught a doc-contract gap**: `api-reference.md`'s "Complete noun-verb API"
  omitted the new `orchestrator` noun — fixed in-plan. Recurrence of the under-scoped
  doc-surface archetype (lesson 2026-06-25-10-001), an in-plan catch, not an escaped defect.

## Routing and Merge Behavior

- CI/merge: green, squash-merged. Surface (manage-config scripts/standards + orchestrator
  workflow docs) overlaps PLAN-47 **only** on the shared `orchestrator` config block, exactly
  as the spec's disjointness note predicted; the coordination held — no collision, PLAN-47
  remains open and rebasable.

## Reconciliation Actions

- [x] status.json `plans[]` entry updated → shipped, pr 996, landing landings/PLAN-48.md
- [x] epic.md queue reconciled from status.json
- [x] Watch — emit-not-running discipline: knob is default-off and the invariant is
      doc-enforced in both branches; watch stays OPEN (now with an autonomy path that could
      violate it if a future author automates the start transition)
- [x] resume_anchor updated
- [x] START-HERE block regenerated

## Follow-Ups

- ⚠ **PLAN-47 must EXTEND, not define, the `orchestrator` block** — carry into its outline/
  review. PR #997 is open on `feature/orchestrator-effort-config-block`.
- **Residual (D3 caveat)**: no executable regression pins the auto-emit cadence itself
  (`launched`-only fill, shortfall-emits-nothing). If the emit seam ever gains a code path,
  that assertion is owed. Recorded as a watch, not a new plan — the doc contract is the
  correct enforcement surface for a workflow-doc seam today.
- PLAN-49 drain-gate: 41/42/43/44/45/46/48 shipped = 7/8; **gated on PLAN-47 only**.
- **Title-repaint watch may now be dischargeable.** This finalize ran `sync-plugin-cache` (10 bundles
  synced, executor regenerated), so the running cache should now carry the #994 orchestrator-title
  fix that earlier sessions predated. Not asserted — this session's repaint still returned
  `no_controlling_tty`, which is the *expected* answer for a session with no controlling terminal and
  therefore does not distinguish the two causes. Re-check at the next session started from a real
  terminal: a `feature_inactive`/success answer discharges the watch; a repeat `no_controlling_tty`
  there would mean the cache is still stale.
