# Landing Analysis: PLAN-47 — orchestrator effort + parallelization-scope config block

epic: truthful-signals
workstream: WS-01
pr: #997 (https://github.com/cuioss/plan-marshall/pull/997) — squash-merged via merge queue, ed5366e

> Landing record for one shipped plan. Corroborated three ways: the merged diff at `ed5366e`,
> the operator's finalize narrative, and a **live read of the running config** (the union block
> resolves in this session's regenerated cache/executor). The last check is the load-bearing one —
> the PLAN-47↔48 collision made "does the merged block actually work" the real question.

## Deliverable Fidelity vs Spec

| Deliverable | Verdict | Evidence |
|-------------|---------|----------|
| D1 — `orchestrator` block schema docs | shipped-as-specified | `marshal-json-reference.md` (+38), `effort-roles.md` (+30) |
| D2 — manage-config resolver/writer/scalar verbs | shipped-as-specified | new `_cmd_orchestrator.py` (+164), `_cmd_effort.py` (+195) per-surface resolver + `--scope orchestrator[.surface\|.default\|.max]` writer, `manage-config.py` (+67); `_cmd_system_plan.py` (−60) — #996's handler was **moved**, not duplicated |
| D3 — empty-block seed + `validate_orchestrator_block` + canonical key order | shipped-as-specified | `_config_defaults.py` (+115), `_config_core.py` (+5); tests `test_orchestrator_seed.py` (+209), `test_sync_defaults.py` (+69) |
| D4 — config-resolved uplift ceiling at the 3 dispatch surfaces | shipped-as-specified | `orchestration-model.md`, `analyze.md`, `decompose.md` — the `effort.max` clamp binds the read-only analysis dispatches |
| D5 — `init.md` parallelization-scope pre-fill | shipped-as-specified | `init.md` (+9) |

Diff: 21 files, 1651 insertions / 151 deletions. Test surface is substantial and real —
`test_orchestrator_scope.py` (+527) is a genuine behavioural suite, not a config-shape smoke test.
This is the **contrast case** to PLAN-48's D3 caveat: here the knob has a code path, and it is
asserted.

## Ground-Truth Verification of the Collision Repair

The spec's coordination clause fired **in reverse** — PLAN-48 (#996) landed *during* PLAN-47's
finalize window, so PLAN-47 became the extender mid-flight. The operator reports that git's naive
auto-merge would have produced two semantically-incoherent results. Both verified repaired at
`ed5366e`:

| Near-miss | Verified at ed5366e |
|-----------|---------------------|
| Empty `DEFAULT_ORCHESTRATOR = {}` shadowing #996's `{'auto_emit': False}` → **auto_emit silently lost** | `DEFAULT_ORCHESTRATOR = {'auto_emit': False}` intact; live `orchestrator get --field auto_emit` → `false` |
| Duplicate `orchestrator` subparser → **argparse crash at import** | Exactly one `add_parser('orchestrator')` and one `elif args.noun == 'orchestrator'` dispatch |
| Duplicate canonical key + duplicate seed key; two competing handlers | Handler converged on `_cmd_orchestrator`; `_cmd_system_plan.py` net −60 |

Live reads in this session (regenerated executor + cache): `auto_emit` → `false`,
`parallelization_scope` → `null` (unset), `effort resolve-target --role orchestrator.analyze` →
`level-3` via `source: plan.effort`. One coherent block carrying **effort + parallelization_scope +
auto_emit**, resolving exactly as "unset everywhere = today's behaviour" promised.

**This near-miss is the epic's own theme, one tier up.** A silently-lost `auto_emit` is precisely a
confident-signal-hides-a-caveat instance: the merge would have reported success while deleting a
shipped knob, and only the *absence* of a default would ever have surfaced it. It was caught by a
dispatched reconciliation agent, not by a gate — no machinery would have flagged it. Recorded as a
watch below.

## Metrics and Anomalies

- 2h59m worked / 2.7M tokens across all 6 phases (no gaps). Finalize 21/21; squash-merged via merge
  queue; executor + plugin cache regenerated; plan archived.
- **Lane escalation was correct**: the router chose light/minimal on the 4 named paths; the operator
  escalated to deep/auto for a 4-deliverable schema change with a design gate and live cross-plan
  coordination. The final shape — 21 files, 1651 insertions — vindicates the escalation and is
  another data point for the scale-blind lane-router false negative staged as **PLAN-57**.
- **Under-scoped doc-contract surface recurred, in BOTH plans.** #996 missed one manage-config doc;
  #997's self-review caught **three** (`SKILL.md`, `api-reference.md`, `data-model.md`). Lesson
  `2026-06-25-10-001` now has back-to-back recurrences on the same skill's doc set.
- CodeRabbit found two real defects: `analyze.md` hard-coded reader `--schema ci-finding` for issue
  bodies (now source-selected), and `orchestrator.default` missing from scope help/error text. Both
  fixed pre-merge.

## Reconciliation Actions

- [x] status.json `plans[]` → shipped, pr 997, landing landings/PLAN-47.md
- [x] epic.md Ordered Queue + Watches reconciled
- [x] **launched-count = 0** — the drain-in-flight-first hold is satisfied
- [x] **PLAN-49 drain-gate CLEARED** (8/8: 41/42/43/44/45/46/47/48)
- [x] resume_anchor updated; START-HERE regenerated

## Follow-Ups

- ⚠ **This epic's `parallelization_scope` is not persisted.** The ledger has operated at scope **4**,
  but `orchestrator.parallelization_scope` reads `null` — so the config-resolved value is the
  documented default of **1**. D5 pre-fills the knob at `init`, and this epic predates D5. Until it is
  set, the epic's real concurrency bound lives only in ledger prose and any config-reading surface
  disagrees with it. Operator decision owed: persist `4`, or adopt the config default.
- **New watch — semantically-incoherent auto-merge across coordinated plans.** Two plans sharing one
  config block produced an auto-merge that was textually clean and semantically destructive. Nothing
  in the machinery would have caught it. Relevant to any future pair sharing a surface; the current
  mitigation is entirely "the orchestrator sequenced them and a human/agent checked the merge."
- PLAN-49's rename is now unblocked, but remains **DRAIN-GATED LAST** by its own charter.
