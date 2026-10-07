# Landing Analysis: PLAN-01 — The orchestrator store resolves to a git-tracked, repo-local address

epic: orchestrator-refactor
workstream: WS-01
pr: #1557, #1558, #1561 (#1555 closed, superseded by the split)

> Landing record for one shipped plan. Lives at `landings/PLAN-01.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

## Deliverable Fidelity vs Spec

Verified against `git log origin/main` (commits `8c8c7bbf`, `6728b738`, `441cc46c`, all
present), `ci pr view` for #1555/#1557/#1558/#1561, and direct read of the landed source.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D0 — reference population | shipped-as-specified (split-adjusted) | Original PR #1555 was closed unmerged after CodeRabbit could not review its 4,028-file diff; the operator-approved remedy split it into a code PR (#1557, ~48 files) and a ledger-relocation PR (#1558, 3,977 files, `skip-bot-review`). |
| D1 — resolver tier | shipped-as-specified | #1557 merged (`8c8c7bbf`): new tier in `marketplace_paths.py`/`file_ops.py`, honouring `PLAN_BASE_DIR`/`set_base_dir()` precedence. |
| D2 — `get_store_dir` routes there | shipped-as-specified | Confirmed live: `orchestrator inbox detect --source-id ".plan/orchestrator/{epic}/plans/{spec}"` now resolves `orchestrated: true` (see Follow-Ups — the OLD-path form no longer does, a real consequence below). |
| D3 — `.gitignore` negation | shipped-as-specified | `!.plan/orchestrator/` and `!.plan/archived-orchestrators/` present; `*/logs/` re-ignored after the negation, as designed (machine-local churn excluded from tracking). |
| D4 — `archive` becomes git-aware | shipped-as-specified | `cmd_archive` in `orchestrator.py` replaces the unconditional `shutil.move` (per #1557's body); not independently re-verified line-by-line here. |
| D5 — layout contract / docstrings tell the truth | shipped-as-specified | `orchestration-model.md` § Directory Layout, `tools-file-ops/SKILL.md`, `tools-script-executor/standards/cwd-policy.md`, `doc/concepts/orchestration.adoc`, `doc/concepts/audit-trail.adoc` updated per #1557's body. |
| D6 — an ADR | shipped-as-specified | `doc/adr/024-The_orchestrator_ledger_moves_from_the_main-anchored_tier_to_the_git-tracked_tier.adoc`, amending ADR-002's bounded exception set. |
| — added-unplanned | #1561 | A follow-up fix for a hardcoded-path finding the split missed (`fix(audit-scripts): derive repo/scratch paths instead of hardcoding a machine and session`) — not in the original spec's deliverable list, filed and landed post-#1558. |

## Metrics and Anomalies

- Duration: 4h43m worked (per the operator's paste — not independently re-verified against
  a metrics artifact here).
- Tokens: 6.9M total.
- Anomalies:
  - **The 4,028-file/427,783-insertion diff overflowed GitHub's per-comment character limit**,
    blocking CodeRabbit review entirely — this is the stuck-mid-finalize state this epic's own
    `cleanup` pass (2026-09-21) recorded as a prominent Open Defect. Resolved by an operator
    decision to split into a ledger PR (`skip-bot-review`) and a ~50-file code PR (full
    review) — executed as #1557 + #1558, with #1555 closed and pointed at the replacements.
  - Findings ledger: 5 PR-comment findings, all resolved (4 fixed, 1 `taken_into_account`).
  - `finalize-step-deploy-target` / `finalize-step-sync-plugin-cache` were **skipped** for this
    plan's own branch — the operator's local `~/.claude/plugins/cache/plan-marshall/` may be
    stale relative to what just landed. Recorded as a Watch below; the orchestrator cannot run
    `/sync-plugin-cache` itself (outside the small-ops carve-out — it is a build/maintenance
    action, not orchestration).

## Routing and Merge Behavior

- Review: findings ledger clean (4 fixed, 1 taken_into_account) across the split PRs.
- CI/merge: #1557 `merged` (verified), #1558 `merged` (verified), #1561 `merged` (verified),
  #1555 `closed` unmerged (verified) — all four states corroborated via
  `ci pr view --pr-number {N}` against live GitHub state, not merely trusted from the paste.
  `git log origin/main` confirms all three landing commits present at HEAD.

## Reconciliation Actions

- [x] row `status` → `shipped`
- [x] row `pr` stamped → `#1557, #1558, #1561`
- [x] row `landing` stamped → `landings/PLAN-01.md`
- [x] row `plan_marshall_plan_id` stamped → `tracked-orchestrator-store-resolver`
- [x] epic.md queue reconciled from status.json
- [x] Open Defect retired: the PR-#1555-stuck-mid-finalize defect this epic's own `cleanup`
      pass recorded is now resolved by the split landing.
- [x] **New critical finding folded into PLAN-03**: `_orchestrator_inbox.py`'s
      `_SOURCE_ID_RE` now hardcodes the `.plan/orchestrator/` prefix (the NEW tracked path)
      with no acceptance of the old `.plan/local/orchestrator/` prefix — so THIS PLAN's own
      `source_id` (correctly written at its own init time, before the migration landed)
      permanently fails `inbox detect` with `unrecognised_id`, reproduced directly. This is
      exactly the migration-shim gap PLAN-03 exists to close, now demonstrated concretely
      rather than only theorised, and it affects every OTHER currently-in-flight plan across
      every epic whose `source_id` was captured before PLAN-01 landed (`truthful-signals`
      PLAN-TRUTH-144 is a confirmed-running example).
- [x] **Two-tree divergence found and reconciled.** `.plan/orchestrator/orchestrator-refactor/`
      (new, git-tracked, seeded by #1558's merge as a one-time snapshot predating this epic's
      own `cleanup` pass) fell out of sync with `.plan/local/orchestrator/orchestrator-refactor/`
      (old, git-ignored) for two compounding reasons: (a) `cleanup` itself ran before PLAN-01
      had landed, so its script calls correctly resolved OLD at the time; (b) after PLAN-01
      merged into local `main`, this orchestrator's own direct `Write`/`Edit` calls kept
      hardcoding the OLD path out of habit for several turns (this very landing analysis, the
      PLAN-03 fold, epic.md's own updates), while its SCRIPT calls (`queue --transition`) had
      already begun resolving NEW — silently splitting `status.json` from everything else.
      Reconciled: `epic.md`, all 7 `plans/PLAN-0{1..7}-*.md`, and this landing record copied
      forward into the tracked tree; `status.json`'s PLAN-06 transition re-applied via script
      once correct resolution was confirmed. `logs/` deliberately stays local-only (by #1557's
      own design). **These are now UNCOMMITTED changes in the tracked repository working
      tree** — this orchestrator does not commit or push without being asked.
- [x] resume_anchor updated
- [x] START-HERE and Ordered Queue blocks regenerated

## Follow-Ups

- **PLAN-03** (this epic, staged) — folded: first-party reproduced evidence that the
  migration/redirect mechanism PLAN-03 is chartered to build is not merely theoretical. The
  detection seam (not only the store resolver) needs to keep accepting the old address form
  for some bounded window, or every plan straddling the cutover silently loses its
  orchestration routing.
- **Global lessons corpus** — candidate for promotion (not yet actioned this pass, flagged for
  the next drain): `finalize-step-deploy-target`/`finalize-step-sync-plugin-cache` skip
  behavior on a plan's own branch leaves the operator's local plugin cache stale with no
  explicit warning at finalize time.
- **Operator action owed, not this orchestrator's to perform**: run `/sync-plugin-cache` to
  refresh the local plugin cache; commit the now-uncommitted tracked-tree reconciliation this
  landing performed, when ready.
