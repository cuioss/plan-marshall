# Landing Analysis: PLAN-16 — Bring `marketplace/targets` inside the ruff gate

epic: multiplattform
workstream: WS-02
pr: [#1375](https://github.com/cuioss/plan-marshall/pull/1375) — merged as `5a5703b28457cef4d00b4aa3c1aa83000616a4b2`

> Landing record for one shipped plan. Claims corroborated against the merged diff, PR/CI state and
> the current tree. This landing also **regenerated the executor**, which closed a standing
> orchestration blocker — analyzed below alongside the deliverables.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| **D1** — fix the violations the widened scope exposes | shipped-as-specified | 5 violations (4× I001 import-sorting, 1× UP017) across `marketplace/targets/__init__.py`, `claude/content_drift.py`, `content_drift_cli.py`, `equality_check.py`, `target.py` |
| **D2** — widen the ruff gate to `marketplace/targets/` | shipped-as-specified | Three coordinated edits verified in the diff: `build.py` adds `TARGETS_DIR` to its ruff paths; `pyproject.toml` `lint`/`lint-fix` aliases add `marketplace/targets/`; `[tool.ruff] src` adds `marketplace/targets`. Both docs restated (`doc/developer/build.adoc`, `pre-push-quality-gate.md`) |

**Realized surface: 10 files**, against a declared surface of `pyproject.toml`, `marketplace/targets/generate.py` and the `marketplace/targets/**` glob. The glob covers the five violation sites; `build.py`, the two docs and `_gate_coverage.py` were not declared. This is mild **under-declaration** of the D2 mechanism — widening a lint gate necessarily touches the build script and the docs that describe it — not scope drift.

**The escape pin was the right verification and it was performed** (planted import → red → removed → green). For a plan whose entire subject is *a check that silently passed*, asserting the widened scope without demonstrating it would have reproduced the original defect. Not independently reproducible here after the fact; accepted on the run's record, and the mechanism it proves is corroborated by the config diff above.

## Metrics and Anomalies

- **Tokens: unavailable** — OpenCode lane, no `manage-metrics` record. Not estimated.
- **CI:** 11 checks, `overall_status: success`. `verify / verify` ran in full at **1125 s** (Python changed, so the docs-only skip correctly did *not* apply — the contrast with PLAN-19's skip is the footprint gate working in both directions). `generate-check` passed.
- **Verify gate:** `total_issues: 0`, empty `errors[]`, 23 647 tests passed (run-reported; not re-executed here, as a verify run is plan work).
- **`Sourcery review` SKIPPED** — consistent with the new reviewer policy, and the first landing in this epic where a bot did not participate.
- **Anomalies:** none in the deliverables.

## Routing and Merge Behavior

- **Review:** CodeRabbit passed and raised one finding — the `_gate_coverage.py` ruff-mypy-targets **parity cell** was wrong once ruff's scope widened. Fixed in `b063ac848` and confirmed addressed. A precise catch: the widened gate silently invalidated a coverage table that describes it, which is the same *stale-description* class the plan itself was created to fix.
- **The 14 plugin-doctor findings were stale-cache false positives.** Clearing the cache and regenerating the executor produced `total_issues: 0`, and **no repository change was made** on their account. Correct handling — changing code to satisfy a stale cache would have been the serious error.
- **CI/merge:** merged, fast-forwarded onto local main, all 10 files present.

## Reconciliation Actions

- [x] row `status` → `landed`; `pr` `#1375`; `landing` `landings/PLAN-16.md`; `plan_marshall_plan_id` `n/a` — one call each
- [x] **standing blocker closed** — executor regenerated to `0.1.1573`; `corpus surfaces` available again
- [x] **owed verification discharged** — PLAN-07's fold surface confirmed registered
- [x] **the "lossy extractor" annotation superseded** — all three documented limits re-measured as fixed
- [x] watch opened: the `lint` / `format` scope asymmetry
- [x] follow-up recorded: the reviewer-policy PR is not yet raised
- [x] epic.md reconciled; both generated blocks regenerated; `resume_anchor` updated

## Follow-Ups

- ⚠️ **OUTSTANDING, and it is a contract change, not code: the reviewer-policy PR has not been raised.** Per operator direction the policy — *only CodeRabbit is required; sourcery and pr-agent are optional* — is documented in the RUNBOOK, and per the runbook a contract change ships as its own `chore/` PR, deliberately kept out of #1375. That PR is still owed. ⛔ Until it lands, the policy lives **only** in the git-ignored `.plan/local/opencode/RUNBOOK.md`, so it exists on this machine and nowhere else — and this landing already ran under it (`Sourcery review` SKIPPED). The gap between an enacted policy and a recorded one is exactly what a later reader cannot reconstruct.
- ✅ **The executor regeneration closed the epic's standing orchestration blocker.** `corpus surfaces` had been unavailable since the PLAN-04 landing (executor pinned at cache `0.1.1565`), which made the disjointness half of the emit gate unestablishable and was the stated reason `parallelization_scope` could not safely rise above 1. Re-measured now: **20/20 specs `declarative`, `indeterminate_count: 0`.** Raising the scope is now a live option rather than a blocked one.
- ✅ **The three "lossy extractor" limits recorded in the Queue annotations are obsolete** and have been superseded there with evidence. The upgraded `epic_spec_parser` resolves recursive globs, slash-less repo-root files, and exclusions (partitioned into `excluded[]`). ⛔ The old instruction to keep exclusions *out* of `## Expected Surface` is retracted — it now destroys information the gate can use.
- **Watch — `lint` covers `marketplace/targets/` but `format` does not.** `pyproject.toml:98-101`: the `lint`/`lint-fix` aliases were widened while `fmt`/`format` were deliberately left at their original path set. Self-consistent today (`lint-fix` covers the new tree, so I001 stays fixable), but a developer running `./pw format` will not format `marketplace/targets/`, and the reason for the asymmetry is recorded in neither file. *Re-check trigger: any format-sensitive rule enabled for that tree, or a formatting diff appearing there.*
- **Recurring housekeeping, not a defect:** the local branch `chore/160-lint-scope-marketplace-targets` survives after the remote was deleted — the same residue PLAN-19 left. Two of the last three landings; worth a habit rather than a ledger entry.
