# PLAN-22: Complete the runtime-state path migration repo-wide

> ✅ **Staged 2026-09-28 under the standing operator directive ("issues about current problems are to be fixed,
> not relayed to PM-MCP").** Emittable; NOT subject to the PM-MCP parking of 2026-09-26.

epic: process-compliance
workstream: WS-03

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-22-runtime-state-path-migration.md` and is queued in the epic's `queue/`
> row files. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.

## Objective

Finish the pre-ADR-002 runtime-state path migration across the whole repository, then make it
self-enforcing. PLAN-13 (PR #1651) swept about 40 files, but only those its self-review loop
reached. That partial migration is exactly what kept the self-review from converging (PLAN-13 report
items 14 and 19): every fix moved the contradiction one contract hop outward. This plan scopes the
migration as full-repo from the start, so no later finalize discovers it piecemeal.

## Deliverables

1. **Derive the population, then correct it.** Enumerate every reference to the three stale forms
   across the whole tree (code, docs, tests, `.claude/**`):
   - `.plan/logs/` — logs now resolve to `get_base_dir() / DIR_LOGS` = `.plan/local/logs`
   - `status.toon` — the live status file is `status.json`
   - `.plan/plans/` without `local/`
   - `.plan/lessons-learned` without `local/` — a fourth form found at cleanup 2026-09-28, in
     `manage-lessons/SKILL.md` and `manage-lessons/standards/file-format.md`

   Triage each hit as intentional or drift. The plugin-doctor detector `_analyze_plan_path_in_scripts.py`
   and its rule-catalog, rule-provenance and tests name the legacy path by design, and migration tests
   may assert it. Correct every drift hit. The count published in the PR states the population it was
   derived from. The tracked inventory at `c56710b` is the baseline (see Claim Labels):
   - `.plan/logs/`: 7 files / 12 matches
   - `status.toon`: 2 files / 2 matches
   - `.plan/plans/`: 10 files / 32 matches, after excluding the 5 plugin-doctor detector files

   ⚠ The inventory does not walk `.claude/**` or `.github/**` (57 tracked files). Sweep those with
   Grep. `.claude/skills/audit-archived-plan-retrospectives/checks/merge-window-accounting.md` is a
   likely `.plan/logs/` hit. Git-ignored trees (`.claude/worktrees/`, `__pycache__`, stale ignored
   skill dirs) are out of scope. They are what inflated a raw `grep -r` to 84 / 23 / 201.
2. **Named leftovers from PLAN-13's self-review, re-checked by hand:**
   - `manage-run-config/scripts/_cmd_cleanup.py:46-48`: the comment still says "per-project global
     plan-marshall directory" beside `PLAN_BASE_DIR = get_base_dir()`.
   - `plan-retrospective/references/artifact-consistency.md` (a path fragment): none of the stale
     literals appears there at `c56710b`. Identify the fragment or close the item with that finding.
   - Dropped at cleanup 2026-09-28, with a positive account:
     - `ci_complete_precondition.py:496` is a docstring describing the already-fixed ghost-dir defect.
       The code uses `file_ops.get_plan_dir`, so the hit is intentional, not drift.
     - `emit-landing.md` L45/64/338 are a different defect class (the "never blocks archive" versus
       loop_back-stops-archive wording), not runtime-state paths. That belongs to PLAN-21 or PLAN-20
       territory, and is not re-staged here.
3. **Doc-vs-resolver parity for every runtime-state path.** Extend PLAN-13's
   `test/plan-marshall/manage-status/test_archive_path_doc_resolver_parity.py` pattern, which covers
   the archive path, to three more paths: the live-plan path (`get_base_dir()`), the log directory
   (`DIR_LOGS`) and the status filename. Run it over the full inventory, with an explicit allowlist
   that names the plugin-doctor detector and the migration tests. A new stale reference must turn the
   suite red.

## Claim Labels

- OBSERVED: residue after #1651 — cited at `inbox/archive/plan-13-finalize-mechanism-defects/plan-13-finalize-mechanism-defects-008.md` § Residue (a sweep over 3523 inventoried files: `.plan/logs/` 13 hits in 7 files, `status.toon` 2 files, `.plan/plans/` 30 hits in 15 files); spot-checked at HEAD by the orchestrator: `manage-logging.py` lines 22, 35 and 192 name `.plan/logs/`, and `collect-plan-artifacts.py:48` names `status.toon`
  - verdict: corroborated | checked_at: c56710b36f01f05be781ff9fb73dbf91b93f5706 | by: process-compliance/cleanup | rescoped: n/a | evidence: manage-logging.py L22, L35, L192 name .plan/logs/; collect-plan-artifacts.py L48 'status.toon'
- HYPOTHESIS (count): the populations are larger than that message states. An orchestrator `grep -rlE` over `marketplace/ test/ doc/ .claude/` counts 84 files for `.plan/logs/`, 23 for `status.toon` and 201 for `.plan/plans/`. The gap is either intentional hits, fixtures, or trees outside the sender's inventory. Confirm or refute by the deliverable-1 derivation itself (verify-at-outline); neither figure is authoritative. **Re-scoped at cleanup 2026-09-28:** refuted. The larger counts came from git-ignored trees. The tracked inventory matches the sender (7 / 2 / 15 files; 10 after excluding the detector). Deliverable 1 now states the inventory baseline plus the `.claude/**` / `.github/**` gap.
  - verdict: contradicted | checked_at: c56710b36f01f05be781ff9fb73dbf91b93f5706 | by: process-compliance/cleanup | rescoped: yes | evidence: inventory sweep 7/2/15 files matches the sender; 84/23/201 came from git-ignored trees (.claude/worktrees, __pycache__, stale ignored dirs); spec re-scoped in place with the inventory baseline + .claude/.github gap
- OBSERVED: a partial path migration cannot converge inside pre-submission-self-review — cited at `plan-13-…-004.md` §§ 14 and 19 and `landings/PLAN-13.md` § Metrics and Anomalies
  - verdict: unverifiable | checked_at: c56710b36f01f05be781ff9fb73dbf91b93f5706 | by: process-compliance/cleanup | rescoped: n/a | evidence: 'cannot converge' is a run-time causal claim; the residue it depends on is present (claim 0)
- OBSERVED: the archive-path parity test exists — `test/plan-marshall/manage-status/test_archive_path_doc_resolver_parity.py`, added by #1651
  - verdict: corroborated | checked_at: c56710b36f01f05be781ff9fb73dbf91b93f5706 | by: process-compliance/cleanup | rescoped: n/a | evidence: test/plan-marshall/manage-status/test_archive_path_doc_resolver_parity.py exists, last touched by c56710b36 (#1651)

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-logging/scripts/manage-logging.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-locks/scripts/_locks_core.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/collect-plan-artifacts.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-retrospective/references/artifact-consistency.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-build.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/marshall-steward/references/wizard-flow.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-run-config/scripts/_cmd_cleanup.py`
- OBSERVED: `doc/user/efforts.adoc`
- OBSERVED: `test/plan-marshall/manage-status/` — parity test
- OBSERVED: `test/plan-marshall/manage-logging/`
- OBSERVED: `test/plan-marshall/plan-retrospective/`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-lessons/` — `.plan/lessons-learned` form (added cleanup 2026-09-28)
- OBSERVED: `test/plan-marshall/audit-archived-plan-retrospectives/`, `test/plan-marshall/manage-files/`, `test/plan-marshall/manage-ci-artifacts/`, `test/plan-marshall/manage-findings/`, `test/plan-marshall/manage-metrics/`, `test/plan-marshall/manage-references/`, `test/plan-marshall/tools-file-ops/` — test files with inventory hits (added cleanup 2026-09-28)
- OBSERVED: `.claude/skills/` — not in the inventory, sweep required (added cleanup 2026-09-28)
- HYPOTHESIS: more files join once deliverable 1 derives the full population. Whatever the plan adds must be declared back through its own footprint (verify-at-outline).

## Dependencies and Sequencing

- Depends on: none
- ⛔ Surface is repo-wide by nature and grows at outline, so the declared list is a floor. Run this plan
  ALONE: emit it only when no other process-compliance plan is running. It overlaps PLAN-20 / PLAN-21
  (`phase-6-finalize/`) and PLAN-19 (tests) by declaration, and almost certainly many more.
- Scope-bloat guard: 3 deliverables. The population, not the deliverable count, drives the size.

## Folded inbox material (same act)

- `plan-13-finalize-mechanism-defects-008.md` (finding; supersedes `-004` item 12): deliverables 1–3
- `plan-13-finalize-mechanism-defects-004.md` item 12 (previously discarded as shipped, a verdict this message refutes): deliverable 1

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/process-compliance/plans/PLAN-22-runtime-state-path-migration.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message.
