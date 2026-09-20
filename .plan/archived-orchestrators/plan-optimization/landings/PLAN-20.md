# Landing: PLAN-20 execution-accounting-integrity

- **PR:** #961 (`5d552d04a fix(execution): run in-scope pytest at leaf and fix step-record key`) — squash-merged to main via merge queue (merge commit `5d552d0`)
- **Workstream:** WS-10 pipeline-integrity-hardening
- **Granularity:** full ship
- **Verified:** commit on main + `git show --stat` (23 files, +1266/-152, 10 test files) corroborates every deliverable; enriched with the operator finalize narrative.

## Deliverable fidelity vs spec

| Deliverable | Shipped | Verdict |
|-------------|---------|---------|
| D1 — leaf per-task verification runs the tests it can break | task-scoped pytest at the per-task leaf gate via `resolve-test-scope --changed-paths` (`build-pyproject/pyproject_build.py`, `execute-task`); docs-only / no-python-footprint → no pytest | ✅ reused the PLAN-14 #942 seam as specified (no parallel one) |
| D2 — finalize step-record key matches manifest `step_id` | canonical resolver `_step_key_canonical.canonicalize_step_key` (new, `script-shared`) unified across mark/assert/record; both prior duplicate resolutions removed; provenance-bearing migration test | ✅ prefixed-step residual closed (not a redo of #885) |
| D3 — structural guard so neither regresses | compose-time `non_canonical_step` assertion in `manage-execution-manifest` (`_manifest_validation.py` + `test_canonical_step_key_gate.py`) — **a compose-time assertion, NOT a plugin-doctor rule** | ✅ one guard covers the key case |

Self-demonstrating: D3's new guard **caught a real non-canonical-step inconsistency in-footprint and fixed it** — the plan's honest-accounting theme proven on itself.

## Routing / review

- Planning auto-escalated light→deep (cross-cutting). D2's scope refined across three operator gate decisions — the exhaustive `_strip_default_prefix` consumer migration, with the **extension-api copy deliberately excluded as a distinct semantic**.
- **Review caught 4 genuine bugs, 2 in D2's own new code:** `canonicalize_step_key` non-idempotence on doubly-prefixed input (gemini); a **critical stale-key-shadowing bug** in `_cmd_assert_step_recorded` and a **conflict-bypass** in `_cmd_mark_step` (CodeRabbit); a doc-placeholder-quoting issue. All 4 fixed in a loop-back (TASK-007–010) with regression tests, re-verified, re-reviewed clean.
- Merge queue re-tested green (squash). All gates green; 22/22 finalize steps done.
- Metrics: 3.7M tokens; 3h28m worked / 14h30m wall. Version bumped to 0.1.1172; on-main executor regenerated.

## Reconciliation actions

- Queue: PLAN-20 → shipped, pr=961.
- **Watch retired:** `2026-07-18-22-001` (leaf skips pytest, n=3) — absorbed by D1, enforced-in-code.
- **Watch retired:** `step_record_mismatched_key` (n=5) — absorbed by D2's canonical resolver + D3 guard.
- **Adjacency watch CLEARED:** PLAN-28↔PLAN-20 potential plugin-doctor-rule collision — does NOT materialize; PLAN-20 D3 is a compose-time assertion in `manage-execution-manifest`, touches no plugin-doctor file. PLAN-28 is free to add a plugin-doctor rule without conflict.

## New leads (recorded)

- 2 new lessons captured (the `_strip_default_prefix` migration blind-spot root cause; the doc placeholder-quoting issue).
- Operational: version 0.1.1172, session restart advisable before the next plan (agent set is session-pinned at startup) — reinforces the standing `/marshall-steward` advisory.
