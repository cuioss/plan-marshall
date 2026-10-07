# PLAN-183: Carried Defects and Watches Closure

epic: test-quality
workstream: WS-03

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-183-carried-defects-and-watches-closure.md` and is queued in the epic
> `status.json` `plans[]` field. The orchestrator EMITS the command below; it never
> launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
>
> ⛔ **Scope is exactly the carried defect + watch backlog below (D1–D8).**
> The defect inventory and watch dispositions were verified at file:line during
> staging; every population figure is a LEAD (rule populations move every
> window) and is re-derived before sizing. Deliberately excluded: the B0/B1–B4
> module-budget campaign (PLAN-182 RUNNING owns it), any new carve or slice
> work, and all `.plan/orchestrator/` ledger writes — the 7 settled.md dangling
> `landings/` refs are orchestrator-owned ledger work, fixed in the staging
> pass directly, never a plan deliverable.

## Execution Contract

The executing plan complies strictly with the plan-marshall process and rules: it
runs the phased lifecycle through its managing skills, treats this spec as the binding
brief, verifies every HYPOTHESIS and verify-first clause against the implementing
source before scoping on it, honors the Write-Boundary below, and reports back through
its PR and its inbox message. Standing operator instruction for this epic (opencode): process compliance is mandatory, not advisory.

## Objective

Close every carried defect and retire every open watch in the epic's backlog so
the ledger carries zero unowned findings when the module-budget campaign lands:
re-derive the test-conventions gate and clear its residual false positives,
resolve the 2 open CodeRabbit nits, close the lsp-surfacer blind spots, sync
`uv.lock`, fold the 4th builder, re-derive the rule-catalog rows, decide the
conformance-drift flip, and enforce `ruff format`. Done when each D-row's Done
criterion reads clean at the merge HEAD and no watch in the epic's Watches
section still names one of these items as open.

## Deliverables

1. **D1 — Re-derive the test-conventions gate at dispatch.** ⛔ **Gating.** The
   nomination cites whole-tree `total_issues 467, error_count 2,
   warning_count 465` with `test-module-line-budget` 429 and climbing — all LEADS.
   Re-run the doctor's own sweep at dispatch HEAD before sizing; do not adopt the
   nomination figures. Within the re-derive, clear the 5 residual
   `subprocess-pythonpath` error-severity false positives (the 5 shapes PLAN-177
   taught: 462a76/c0f4ef/02c9ea/79bf95/24970a — plus `_run_python` isolation
   discrimination) and fix the `_has_pythonpath_env_kwarg` name-only shortcut
   (`_analyze_test_conventions.py` L555, used L299) so the kwarg test proves the
   PYTHONPATH behavior, not just the parameter name.
   *Done when:* the gate figures are re-derived at dispatch with the producing
   commands recorded, the 5 false-positive shapes read clean, and the kwarg
   shortcut is replaced by a behavior-proving test.
2. **D2 — Resolve CodeRabbit nit (1): platform-runtime router.** The hardcoded
   operation table at `test_platform_runtime_router.py:304-316` — expose an
   operation registry on `_dispatch` in
   `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/platform_runtime.py`
   and drive the router tests from it.
   *Done when:* no hardcoded op table remains in the router test scope and the
   suite is green both orders.
3. **D3 — Resolve CodeRabbit nit (2): tools-permission-fix parser.** The inline
   parser rebuild at `test_permission_fix.py:1093-1113` — parser-construction
   refactor exposing a builder, tests driven from the builder.
   *Done when:* the inline rebuild is gone, the builder is the single
   construction site, and the suite is green both orders.
4. **D4 — Close the lsp-surfacer blind spots.** Two recorded lessons, both in
   `ext-self-review-plan-marshall` (`_self_review_patterns.py:490`,
   `_self_review_detectors.py:193`): `user_facing_strings` structural
   unreachability for module/async docstrings (lesson `2026-09-02-14-003`) and
   the hand-mirrored-table enumerated-but-unmatched class — 194 candidates
   matched none of c6d03d/525092/5f3517 (lesson `2026-09-09-01-001`; context in
   `2026-09-08-21-001`). Fix the surfacer so both classes are detected or the
   gap is closed by construction with a negative control each.
   *Done when:* both blind-spot classes carry a failing-before/passing-after
   control and the surfacer suite is green.
5. **D5 — Sync `uv.lock` + fold the 4th builder.** `uv.lock` (99660 B, last
   touched #1536 at ruff ≥0.16.7; sync state HYPOTHESIS — verify, never assume)
   is re-synced against `pyproject` at dispatch; the `create_nested_marshal_json`
   4th builder at `test/plan-marshall/manage-config/_manage_config_fixtures.py:43`
   (PLAN-020 § D2 leftover; siblings `create_minimal_marshal_json` at
   `test_detection.py:133` plus the `_marshal_with_*` helpers) is folded into
   the surviving builder shape.
   *Done when:* `uv.lock` verifies in-sync at the merge HEAD and exactly one
   marshal-json builder construction site remains.
6. **D6 — Re-derive the rule-catalog rows.** ⚠️ The epic's "no rows" defect is
   STALE: the 3 `test-conventions` rules DO have `rule-catalog.md` rows
   (L686–688, added 3cb595f76/#1250). Re-derive what is actually missing —
   currently only `test-docstring-historical-prose` carries a per-rule `###`
   section (L703) — and complete the catalog to the rule set at dispatch.
   *Done when:* every shipped rule has its catalog row and per-rule section, or
   the delta is recorded with cause.
7. **D7 — Decide the conformance-drift flip (WS-03 named owner).** The
   conformance-drift watch (four firings plus a refuted-stability instance)
   carries the standing flip question: `severity: warning` → `error`,
   per-rule, conditioned on a zero violation count. Make the flip decision —
   flip with the zero-count evidence, or record the deferral with its named
   re-check — so the watch retires either way.
   *Done when:* the flip decision is recorded with its evidence and the watch
   no longer names an open decision.
8. **D8 — Enforce `ruff format` (watch closure).** The ruff-format
   unenforcement watch (new from PLAN-181, GH006, WS-03 candidate): make format
   enforcement real so `ruff format` findings cannot silently vanish from
   merged PRs. Per-PR review logging throughout: Tier M `skip-bot-review`
   label; log label y/n, CodeRabbit skipped y/n, Sourcery present y/n +
   dispositions; every arrived Sourcery comment triaged/handled before merge.
   *Done when:* the enforcement mechanism is in place with a control proving a
   format finding blocks, and the D8 log lines are in the landing message.

## Expected Surface

- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_test_conventions.py` — D1 kwarg-shortcut fix (WS-03 production scope)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/platform_runtime.py` + `test/plan-marshall/platform-runtime/test_platform_runtime_router.py` — D2 op-registry (production + its test)
- OBSERVED: `test/plan-marshall/tools-permission-fix/test_permission_fix.py` — D3 builder refactor (test scope; production sibling untouched)
- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/` — D4 surfacer blind spots (WS-03 production scope)
- OBSERVED: `uv.lock` + `test/plan-marshall/manage-config/_manage_config_fixtures.py` — D5 sync + builder fold (root lockfile + test scope, named in-scope exceptions)
- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/references/rule-catalog.md` + `standards/doctor-test-conventions.md` — D6 catalog re-derive (docs scope)
- OBSERVED: rule severity config + repo format enforcement config — D7/D8 flips (config scope, named in-scope)

## Dependencies and Sequencing

- Depends on: PLAN-177 instruments (landed — the 5 taught shapes); PLAN-181
  landing (landed #1582 — the nit-bearing surfaces); the lessons-archive trio
  (`2026-09-08-21-001`, `2026-09-09-01-001`, `2026-09-02-14-003`).
- Overlaps with: PLAN-182 (RUNNING) owns the module-budget campaign — **this
  row sequences behind the running plan** (N=1 default); the surfaces are
  disjoint by charter (WS-03 production/harness + named config/test scopes vs
  WS-04 budget carves), so concurrent emission is available on operator word
  only. Emit into a free slot or on operator order.
- Pairs with: none — terminal backlog closure; when D1–D8 read clean, the
  epic's unowned-finding count is zero.
- Settled.md 7 dangling refs: NOT staged here — orchestrator-owned ledger
  work, fixed in the staging pass directly per the Write-Boundary.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/test-quality/plans/PLAN-183-carried-defects-and-watches-closure.md"
```

## Write-Boundary

The plan implementing this spec touches only the scoped sources above. Only
WS-03-chartered production edits under `marketplace/bundles/**` plus the
explicitly named in-scope exceptions (`uv.lock`, the two router/parser test
scopes, the builder fixture, the rule-catalog docs, rule-severity and format
configs) are admitted — anything outside the Expected Surface is a scope
escalation requiring a spec amendment first. It creates and edits NO file under
`.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through
its PR and its inbox message. The report carries a complete `landing-facts`
block; narrative-only landings cost a hand-recovery drain every time. The inbox
exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
