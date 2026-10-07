envelope_version=1
sender_type=plan
sender_id=executor-rejects-invalid-invocations-before-spawn
epic=code-intelligence-substrate
kind=landing
created=2026-08-09T14:49:53Z

# PLAN-CIS-032 executor-rejects-invalid-invocations-before-spawn SHIPPED as PR #1127

plan_spec: PLAN-CIS-032
workstream: WS-01
plan_marshall_plan_id: executor-rejects-invalid-invocations-before-spawn
pr: 1127
merge_sha: 415dcf1397fb6b2eca06e0654801b66d8eaaedbf
merge_mechanism: merge_queue (squash)

## Corroboration

Per the epic's standing rule (corroborate against origin/main AND PR state before any shipped
transition), both were checked first-party from the main checkout after the merge:

- `ci pr view --pr-number 1127` → `state: merged`, base `main`, head
  `feature/executor-rejects-invalid-invocations-before-spawn`.
- `git log 415dcf139` → `feat(tools-script-executor): validate invocations before spawn (#1127)`.
- `git branch -a --contains 415dcf139` → present on `main` and `remotes/origin/main`.

This is a real landing, not a message-derived claim. The queue row for PLAN-CIS-032 is still
`running` and needs transitioning to `shipped` with `pr=1127`.

## What shipped

26 files, +7789 / -1070, 19 commits.

- **Pre-spawn invocation validation in the generated executor.** `execute-script.py.template`
  now resolves a call against a derived argparse surface and refuses an invalid invocation
  before spawning the child, returning a `status: error` TOON with a corrective (nearest-verb
  and nearest-flag suggestions, or the declared/required set) instead of letting argparse
  reject it after the spawn.
- **A new shared derivation module**, `script-shared/scripts/argparse_surface.py` (1357 lines,
  new), which derives each script's parser tree by probing `--help` per parser node, under a
  per-probe timeout, a per-script node cap and a shared total wall-clock deadline, cached by a
  content digest covering the script, its sibling `.py` files, the injected shared-module dirs
  and the derivation's own `CACHE_VERSION`.
- **plugin-doctor migrated onto that same accept-set.** `_analyze_manage_invocation.py` shrank
  by ~700 lines and `_analyze_argument_naming.py` was rewritten; both now bind to the shared
  `UNIVERSAL_FLAG_ARITY` / derived surface rather than carrying their own `add_parser` AST
  walk, so the edit-time rule and the dispatch-time rejection read one definition and cannot
  disagree about what a script accepts. `script-call-drift` deliberately keeps its own
  independent probe, and `rule-catalog.md` now says so.
- The executor's build-ledger stamp, `generate_executor` guard ordering, and
  `script-failure-analysis.py` were corrected as in-radius consequences.

## Verification state

- `pre-push-quality-gate`: quality-gate, test-compile and module-tests green at the final
  settled HEAD.
- `project:finalize-step-plugin-doctor`: clean, whole-tree, 31 rules.
- `ci-verify`: all checks green.
- Q-Gate 6-finalize: 13 findings, **all resolved `fixed`, 0 pending**.
- Full verify observed at 18081 passed during the finalize fix rounds.

## Deviations and caveats the orchestrator should carry

1. **`pre-submission-self-review` closed on a recorded WARNING deviation, not a clean pass.**
   Six rounds, 1,008,012 tokens (~60% of all 6-finalize spend), closed without a final clean
   full-scope pass. The behavioural half DID converge (rounds 4-5 found real shipped-code
   defects, round 6 found none); the doc-claim half self-seeded, because each correction
   authored new prose for the next round to audit. Detail in candidate 003.
2. **The on-main executor regeneration reported success while producing a surfaces-less
   executor.** The shipped guard was NOT live on main until the generator was re-run directly
   from merged source (`--marketplace --marketplace-root . --force`, 106 surfaces over 148
   scripts). The only observable distinguishing the two outcomes is the *absence* of a
   surface-stats line, and nothing consumes absence. Recovered by hand; `sync-plugin-cache`
   then reported 10 bundles synced and the regeneration at 106 surfaces. Detail in candidate
   001 — this is directly relevant to the epic's standing pin-check rule, because it is a
   second, independent way the on-main executor can silently disagree with merged source.
3. **`project:finalize-step-deploy-target` emitted 1132 files at version 0.1.1333.** The pin /
   marker survey was not re-run after that regeneration by this plan.
4. **Review composition carried no information from the required bot.** pr-agent, the sole
   REQUIRED bot, resolved `participated_but_empty` on all three passes. coderabbit (optional)
   produced every actionable finding — the review-retrospective measured 1 reviewer, 14
   actionable comments, 2 unmeasurable. sourcery resolved `hard_quota` on all three passes
   (diff over its 150,000-character limit), which is deterministic by diff size and will recur
   on every comparable PR. Detail in candidate 005.
5. **The retrospective's footprint checks were structurally unable to run.** Both
   `affected_files` checks returned `inconclusive` post-merge because `branch-cleanup` removes
   the worktree before `plan-retrospective` runs. Computed by hand from the merge SHA: declared
   17, realized 26, recall 58%, precision 88%. Two of the 11 undeclared files were the subject
   of three review findings. Detail in candidate 004.

## Result that bears on the epic's method, not just this plan

The plan predicted its own guard would be inert until a post-merge regeneration and therefore
not self-exercisable. **That premise was partly refuted in flight** (decision.log `e4341f`):
phase-5 generates a *worktree-bound* executor, so regenerating it inside the run exercised the
guard end-to-end against 148 real notations. The non-exercisability boundary is
main-checkout-and-cache-scoped, not absolute.

This mattered concretely. Four false-rejection / false-corrective defects in the shipped guard
were found **only** by probing it live, and none by the test suite — the suite's fixtures were
all populated surfaces, so a whole defect class ("the derivation strips attribute X") could not
manifest. That is the epic's own standing "PROBE THE OBJECTIVE LIVE" rule paying out, and it is
filed as candidate 007 with the recommendation that the fixture corpus be population-derived
from the real surface index.

## Residue routed to this inbox

Seven `candidate-lesson` messages from this plan, `-001` through `-007`. Messages 001-006 were
written by `plan-marshall:plan-retrospective`; `-007` was written by `lessons-capture` and is
the only one not already covered by the retrospective. Zero global-store lesson writes and zero
`architecture enrich` calls were made (Branch B4).

| Msg | Component | Subject |
|-----|-----------|---------|
| 001 | `plan-marshall:tools-script-executor` | Fail a regeneration that derives zero surfaces where the previous had surfaces |
| 002 | `plan-marshall:phase-6-finalize` | Emit `[DISPATCH]` on loop-back re-fires (4 of 13 dispatches unlogged, 31%) |
| 003 | `plan-marshall:phase-6-finalize` | Cap self-review on convergence, not budget exhaustion |
| 004 | `plan-marshall:plan-retrospective` | Recover the plan footprint from the merge SHA when the worktree is gone |
| 005 | `plan-marshall:phase-6-finalize` | A required bot resolving `participated_but_empty` should not alone satisfy the gate |
| 006 | `plan-marshall:plan-retrospective` | Name the canonical aspect key in each Step 3 table row |
| 007 | `plan-marshall:tools-script-executor` | Hand-built surface fixtures cannot see a strip-the-attribute defect |

## Queue implication

With PLAN-CIS-032 shipped, the running count drops to 0 against N=2, so **two slots are open**.
The current resume anchor names PLAN-CIS-041 (WS-03, operator-directed) as the next emit
alongside a running CIS-032, and notes CIS-039 should follow CIS-041 rather than pair with it.
The anchor still describes CIS-032 as "RUNNING (probed live, at 5-execute)" and needs updating.
