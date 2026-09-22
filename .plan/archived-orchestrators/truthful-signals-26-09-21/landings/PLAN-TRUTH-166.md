# Landing analysis — PLAN-TRUTH-166

**Plan**: `truth-166-architecture-refresh-migration-churn` · **PR**: #1501 · **Merged**: `e8c3cad5b` (squash via merge queue) · **Analyzed**: 2026-09-17

## Corroboration

Every fact below was checked first-party before any ledger write; the landing message is a lead, not a fact.

| Claim | Verdict | Evidence |
|---|---|---|
| Merged as `e8c3cad5b` | corroborated | `git log origin/main` — `e8c3cad5b fix(architecture-refresh): attribute tool-migration churn correctly (#1501)` |
| PR #1501 merged, base `main` | corroborated | `ci pr view --pr-number 1501` — `state: merged`, `merge_commit_sha: e8c3cad5bf139c5…` |
| Landing facts complete | corroborated | `inbox landing-check` — `complete: true`, `missing_keys[0]`; `footprint_base_stale: false` |
| 5/5 deliverables, 16/16 tasks | corroborated | landing-facts `deliverables_total=5 deliverables_done=5 tasks_total=16 tasks_done=16`; PR body enumerates all five |
| `cleanup_owed: false`, branch/worktree removed | corroborated | landing-facts; operator report; branch absent from `origin` |
| 23/23 finalize steps | corroborated | landing-facts `steps=` — 21 named rows plus the two the plan reports; every row `done` |

⚠ **One figure differs between sources and neither is load-bearing**: the operator report states `verify plan-marshall` green at **22,133** tests, the PR body's test plan at **22,115**. Recorded, not reconciled — the two were taken at different commits of the same branch.

## Deliverable fidelity vs the spec

The spec staged five deliverables; all five landed, and D0's gate question was answered in code rather than deferred.

| Spec | Landed as | Note |
|---|---|---|
| D0 — settle the attribution discriminator | `_descriptor_delta.py` (new) — plan-caused (`module_added`, `module_removed`, `extensions_used_changed`, `index_entry_added`) vs tool-caused (`generation_backfill`, `concept_type_backfill`, `key_packages_rekey`) | The MIXED case and a named cannot-decide outcome are both in the vocabulary, as D0 required |
| D1 — commit only the plan-attributable delta | `--apply plan\|migration\|all` on `discover`; finalize Branches J and K | `all` stays the default, so no existing caller changed |
| D2 — a reconcile path for tool churn | `marshall-steward upgrade` Stage 2 `migrate-architecture-descriptors` | The plan-less path the spec required, so the fix does not strand the migration |
| D3 — the regression check says what it examined | `examined_fields` / `modules_examined` / `modules_unreadable`, and it now reads `enriched.json` | A byte-identical dotted→path re-key reports as migration, not regression |
| D4 — no `rm -rf` baseline cleanup | `--pre-ref` reads the baseline via `git archive` into a self-cleaning temp dir | The step now issues no Bash call a consumer's permission layer can refuse |

⭐ **The fix was exercised on itself.** This plan's own finalize ran the new `discover --force --apply plan`, which classified its descriptor delta as `clean` and committed nothing — the behaviour the plan exists to produce, observed on the plan's own branch. That is the strongest possible control for this defect class, and it is the reason the plan's own PR carries no descriptor churn.

## Metrics and anomalies

- 9,979,683 tokens; 7h25m worked / 36h0m wall; `loop_back_iteration: 6`.
- `pre-submission-self-review`: 4 rounds, 20 findings, all fixed. Self-seeded share **55% overall, 79% after round 1** — measured by the plan itself and filed as message `-006`.
- `automatic-review`: 3 mandatory CodeRabbit rounds, 7 actionable, 0 false positives (TASK-10..16). One quota refusal handled under the operator's standing unattended protocol — **1 wait of 10 spent (~96 min)**, so 9 remain.
- Gates: `verify plan-marshall` green, whole-tree `quality-gate` clean, `plugin-doctor` 37 rules / 0 issues. Target tree regenerated (1206 entries), 10 bundles synced, on-main executor regenerated.

## Routing and merge behaviour

Squash via the merge queue (`step.branch-cleanup.merge_mechanism=merge_queue`, `merged_sha=e8c3cad5b`). Main is clean and even with `origin/main`. No collision with any concurrently-running plan: 166 ran alone, and the three specs the gate had sequenced behind it (`-145`, `-158`, `-167`) were never launched.

## Reconciliation actions

1. Queue row `PLAN-TRUTH-166` → `shipped`; `pr`, `landing` and `plan_marshall_plan_id` stamped.
2. The three specs blocked on 166's surface are unblocked: **`-145`**, **`-158`**, **`-167`**.
3. 13 candidate-lessons drained with the landing (2 relayed from Token-Sheriff, 11 from this plan) — 11 folded, 1 forwarded to `review-apparatus`, 1 promoted to the lessons corpus.
4. Two items outlive the plan and are tracked, not closed by it:
   - **`finalize-step-simplify` edited three files outside the declared footprint** (`effort_pins.py`, `runtime_info.py`, `argparse_surface.py`), because `compute-footprint` resolves `base_ref` against the LOCAL `main`. All three edits were reverted by the plan. This is the same attribution-scope defect one layer up; it is now owned by **`PLAN-TRUTH-167` D3**, corroborated by message `-003` with the exact source lines.
   - **The marshalld daemon reconcile was deferred** (daemon busy), leaving a `reconcile-owed` marker on this developer machine. Machine-local operator action; no plan work owed.

## Parallelization consequence

None observed — no concurrent plan, no rebase conflict, no re-verify signal. The gate's sequencing of `-145`/`-158`/`-167` behind this plan was correct: all three declare `architecture-refresh.md` or a path under `test/plan-marshall/phase-6-finalize/`, which this plan rewrote.
