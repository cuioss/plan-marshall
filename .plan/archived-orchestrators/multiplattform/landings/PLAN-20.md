# Landing Analysis: PLAN-20 — sync-opencode prune boundary

epic: multiplattform
workstream: WS-04
pr: #1418 (https://github.com/cuioss/plan-marshall/pull/1418)

> Landing record for one shipped plan. Lives at `landings/PLAN-20.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

Drained from `inbox/sync-opencode-prune-boundary-001.md`. **This landing closes WS-04** and
retires a standing Open Defect.

## Deliverable Fidelity vs Spec

| Deliverable | Verdict | Evidence |
|-------------|---------|----------|
| **D1** — `_derive_synced_bundles` resolves exactly one bundle per entry | **shipped-as-specified, and it is EXACTLY the recorded fix direction** | Read from the merged diff: the old `for kb in known_bundles: if name == kb or name.startswith(f'{kb}-'): matched.add(kb)` — which added **every** match — became a `matches = [...]` comprehension followed by `matched.add(max(matches, key=len))`. The Open Defect recorded the fix direction as "take the LONGEST matching bundle per entry, not every match". The landing implements precisely that. |
| **D2** — adversarial prefix-ambiguous test cases | **shipped-as-specified** | Two tests added: `test_sync_opencode_prefix_ambiguous_shorter_bundle_preserved` and `test_sync_opencode_prefix_ambiguous_both_bundles_managed` (+102 test lines). ⭐ **These are BEHAVIOURAL, not structural** — the first builds a real source/dest tree in `tmp_path`, discovers a real prefix-ambiguous pair from `marketplace/bundles/`, drives the actual script through `_run`, and asserts the shorter bundle's stale destination entry survives. Red-first was demonstrated for that case. |

## ⭐ This is the strongest test work in the epic so far

Worth stating explicitly because it contrasts with the landing immediately before it. PLAN-14's
D1 pin was an `inspect.getsource` substring assertion that never drove the code. PLAN-20's D2
tests drive the real script against a real filesystem and assert on the observable outcome —
the exact instrument PLAN-14's done-condition asked for and did not get. **The lane can produce
that quality of pin**; PLAN-14's shortfall was a plan-level choice, not a lane limitation.

⚠️ One small caveat, recorded and not overstated: both tests `pytest.skip` when no
prefix-ambiguous pair exists in `marketplace/bundles/`. The guard is **honest** — a skip is
visible in pytest output, unlike a silent pass — and both real pairs (`pm-dev-java` /
`pm-dev-java-cui`, `pm-dev-frontend` / `pm-dev-frontend-cui`) exist today. But the coverage is
contingent on the bundle set, so a future consolidation could retire the pairs and quietly
retire the regression guard with them. Not a defect; a thing to know.

## Metrics and Anomalies

- **Tokens: not reported.** `total_tokens=unknown`; `landing-check` → `complete: false,
  missing_keys: [total_tokens]`. **Fourth consecutive landing** with this key missing. The
  run recorded it as expected incompleteness in its own report — correct handling, and the
  pattern is now established rather than incidental.
- **Gates:** `verify` green at 24,347 tests, `total_issues: 0`; generator gate green across
  3 targets.
- ⚠️ **A worktree self-hosting gap was exposed and worked around, not fixed.** The daemon
  re-enters the executor from inside `--project-dir`, so the worktree needed its **own**
  `.plan/local/` plus a generated executor before the gate would run. This is the **third**
  observation in one family — alongside the executor self-heal walking the wrong plugin-cache
  depth (PLAN-09) — where executor/worktree path resolution fails in a way the run has to work
  around by hand. Recorded as an Open Defect; it belongs with the tooling cluster, not here.

## Routing and Merge Behavior

- **Review:** CodeRabbit reviewed with **no actionable comments**; cuioss-review-bot reviewed;
  Sourcery rate-limited and **disclosed as optional rather than reported clean** — the third
  consecutive landing to handle the rate-limit honestly.
- **CI/merge:** merged as `565d4ade7`, corroborated via the CI abstraction and confirmed an
  **ancestor of `origin/main`** by `git merge-base --is-ancestor`.
- ℹ️ **The run reported "main is clean and current" at `565d4ade7`, and that has since moved.**
  `origin/main` is now `d03ca621c` — PR #1399 (`fix(planning-lane)`) landed after this merge,
  and the local `main` checkout is one commit behind. Not a contradiction of the landing and
  not a defect: the merge is real and its ancestry is verified. Noted only so a later reader
  does not treat `565d4ade7` as the current head.
- **No collision materialized.** Ran solo at `parallelization_scope: 1`. Its single
  `corpus_spec` overlap was with PLAN-04 on `sync_opencode.py` — already dead, PLAN-04 having
  landed.
- **Surface fidelity: exact.** Both touched paths declared; nothing else touched; no
  under-declaration. The spec's known false-positive `/sync-opencode` unresolved span played
  no part.

## Reconciliation Actions

- [x] row `status` → `landed`; `pr` → `#1418`; `landing` → `landings/PLAN-20.md`;
      `plan_marshall_plan_id` → `n/a`
- [x] **Open Defect RETIRED on re-derivation** — the `sync_opencode.py` prefix-ambiguous
      over-prune. The defect named the exact failing mechanism (every prefix match entering the
      managed set) and the exact remedy (longest match). Both were re-derived from the merged
      diff and the remedy is in place, with behavioural regression tests. Closed.
- [x] **New Open Defect opened** — the worktree self-hosting gap (above), folded into the
      existing orchestrator/executor tooling cluster entry rather than filed separately.
- [x] WS-04 recorded complete in the workstream charter
- [x] START-HERE and Ordered Queue blocks regenerated; `resume_anchor` updated
- [x] Message archived to `inbox/archive/sync-opencode-prune-boundary/`

## Follow-Ups

- **The tooling cluster is now FOUR defects, all failing quietly**: `queue --transition`
  accepts any status token; `corpus set-verdict` has a claim-index off-by-one; the executor
  self-heal walks the wrong plugin-cache depth; and the worktree needs hand-built
  `.plan/local/` + executor state for the daemon to re-enter. ⛔ They are not four unrelated
  bugs — three of the four are **path/state resolution across the executor's own boundaries**.
  This is the strongest candidate for the next non-epic plan.
- **`total_tokens=unknown` is now a standing lane property, not a per-run gap.** Four for four.
  Whoever fixes the RUNBOOK Step 10 obligation should decide whether the lane should stop
  claiming a required key it structurally cannot supply, rather than each run re-disclosing it.
