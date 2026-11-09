# Landing Analysis: PLAN-LB-126 — Finalize commits write their change-ledger row, and the foreign-PR gate reads the foreign branch

epic: live-blockers
workstream: WS-01
pr: #1942 (https://github.com/cuioss/plan-marshall/pull/1942)

> Landing record for one shipped plan. Written by the `analyze` verb after verifying claims against ground truth.
> Merge commit `f1945737a983d06a3ab19992f2ced93d0661eb05`, a merge-queue squash with ONE parent `5eb2f9d9d2c112e34f676260672cc1ee6b9be902`
> (the PLAN-LB-116 squash), read with git before the leaf prompt named it; 18 files, +966/-123. `ci pr view` reports `state: merged`
> with that merge commit. Lane: runbook, harness `opencode`, model `deepseek-v4.1-flash/high`, `total_tokens` unknown. The inbox message is
> `complete: false`, `missing_keys`: `total_tokens` only (out of scope per the focus rule); the four review-and-Sonar numbers are present.
> The lane's review history, CI and merge-queue claims were not re-read; the merge state and merge commit were. CodeRabbit reviewed head
> `8eeec321a` ("No actionable comments were generated"); the merged head was re-triggered and refused on quota (lane's claim, not
> re-read). The lane ran from the main-checkout spec and merged after PLAN-LB-116, PLAN-LB-127 and PLAN-LB-125 (no conflict reported).

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 every finalize commit writes its own `kind=change` row | shipped-as-specified | `cmd_commit` records the row only when the phase is `6-finalize`, through `change_record` / `append_entry` (`git-workflow.py:1150-1160,1210-1215`, re-read); the refusal names every unrecorded SHA on one line (`_cmd_lifecycle.py:876-889`, re-read); the guard predicate and `VERIFY_REFUSAL_ERRORS` are untouched; the loop-back fixture is red against `5eb2f9d9d` by reading |
| D2 the foreign-PR gate reads the foreign branch | shipped-modified | the branch is the declared `foreign_branch` or the checkout's branch, with named `unresolved[]` rows for disagreement and an unreadable branch and no `feature/{plan_id}` fallback (`foreign_pr_gate.py:223-263`, re-read); the checkout arm reads `main` after cleanup and the landing verb answers `pushed_no_pr` for it (L3-1) |
| D3 the documents state the row obligation and the branch rule once | shipped-as-specified | the obligation is stated once at `workflow-integration-git/SKILL.md` § Commit Changes and pointed to from the others; `archive-plan.md:37` carries the branch rule (re-read); two history-wording slips remain (L3-6) |

## Three-Layer Analysis

Read by one read-only leaf (`execution-context-level-5`, the resolved `orchestrator.analyze` level). One leaf per landing, as the dispatch rule requires. The orchestrator re-read the points marked "re-read" below at their `file:line`; points not listed there are unverified leads.

- **Dispatch:** one read-only leaf per landing — reason: reading the commit verb's order of effects, the guard's ledger resolution and the gate's branch logic is the depth the Dispatch Decision Rule exists for, and its reading must not share context with another landing. The leaf reported one `git grep` call against the project rule and no other deviation.
- **Verdict:** layer 1 findings (1 minor); layer 2 findings (1 minor); layer 3 findings (**1 major**, minors). The major falsely blocks the archive gate in the post-cleanup state the spec names as typical.

### Layer 1 — Specified

The spec offers the foreign checkout's current branch as a source while stating (its own D2 text) that after cleanup the foreign tree typically sits on `main`. It never says that a base branch cannot be a change's branch, and its Done-when tests neither the post-cleanup state nor that rule.

| Finding | Claim | Verdict | Polarity | Evidence |
|---------|-------|---------|----------|----------|
| L1-1 | the checkout-branch source answers the reason the gate gives against it (post-cleanup tree on `main`) | checked | refutes | `foreign_pr_gate.py:258-263` (re-read: a readable checkout branch is returned as is, `main` included) |

**Layer 1 verdict:** findings — 1 (minor; the premise gap behind L3-1).

### Layer 2 — Implemented

| Deliverable | Code trace | Test that can fail | Unexplained file / unborne claim | Verdict |
|-------------|------------|--------------------|----------------------------------|---------|
| D1 | `git-workflow.py:1150-1160,1210-1215`, `_cmd_lifecycle.py:876-889` | `test_a_finalize_commit_then_a_loop_back_and_a_step_10a_commit_admit_the_boundary` (red against `5eb2f9d9d` by reading: the verb wrote no row) | none | checked |
| D2 | `foreign_pr_gate.py:223-263` | `test_a_foreign_change_on_a_branch_the_plan_id_does_not_name_is_clear` | red against `5eb2f9d9d` is a signature `TypeError` (`check()` has no `branch_resolver`), not a semantic failure; the branch semantics were shown red only by mutation after the fix (L2-1) | checked |
| D3 | the documents named in the spec | read of each section | `architecture-refresh.md` widened its exit-code convention from `manage-*` to every script call (follows from the verb no longer being `manage-*`) | checked |

- **L2-1 (minor):** the D2 red proof is a signature red. The lane reported the order as `mutation-after` and said so; the test would also fail on the semantics, but that was shown by mutation, not at the base.
- **L2-2 (minor):** the unit test `test_the_plan_id_branch_is_never_the_fallback` (`test_foreign_pr_gate_gate.py:486-504`, re-read) answers `main: merged`, which the real landing verb cannot give for `main` (L3-1). It pins `clear` for the state the major shows reading `blocked`, so it hides the defect.
- **Lane claim 8 (surface drift):** the three files edited beyond the surface are each explained by D1, D2 or D3. `_ledger_core.py`, `manage-change-ledger.py` and `worktree_sha.py` carry docstring and help-text changes only. No unexplained file was found.

**Layer 2 verdict:** findings — 2 (minor).

### Layer 3 — Correct

| Defect | File:line | Triggering input | Effect | Severity |
|--------|-----------|------------------|--------|----------|
| L3-1 | `foreign_pr_gate.py:258-263` (re-read), `ci_base.py:926-958` (re-read), `_github_pr.py:1621-1673` (re-read) | a foreign change that merged, its tree returned to `main` by cleanup (the state `test_foreign_pr_gate_cli.py:416-419` and the spec call typical), no `foreign_branch` declared | `_branch_for_repo` returns `main`; `landing-state` keeps only PRs whose head is the branch tip, the tip of `main` is no PR head, so `derive_landing_state` returns `pushed_no_pr` for a pushed `main`; the gate is `blocked` and tells the operator to open a PR for an already merged change. With a declaration the same state is `branch_disagreement` and `error` (by design), so after cleanup the gate never clears. The lane records the declaration case as residue and not the undeclared case | **major** |
| L3-2 | `git-workflow.py:1150-1160` (re-read) | the commit succeeds but `rev-parse HEAD` fails, or the phase is `unknown` / unset (no `--plan-id` on a main-checkout tree) | the commit has no row, reported only as `ledger_recorded:false` or with no `ledger_*` key; the gap shows at the next 5-execute boundary (fails closed) | minor |
| L3-3 | `git-workflow.py:1056-1076` | `resolve_ledger_path` raising a non-`OSError` after the commit | only `OSError` is caught; whether anything else can escape after the commit is `not shown by reading` | minor |
| L3-4 | `foreign_pr_gate.py:198-201` (re-read) | a declared branch beside a checkout that is unreadable | `_current_branch` returns `None` for a detached HEAD and for any git failure, so the declaration is accepted; the landing read must still succeed, so it does not fail open | minor |
| L3-5 | `git-workflow.py:1162-1198` (re-read) | `--push` refused by the head gate or the armed-merge gate after the row was written | the refusal carries no `ledger_*` field although the row exists; truthful about the commit, silent about the row | minor |
| L3-6 | `archive-plan.md:37`, `_cmd_lifecycle.py:877-879` (both re-read) | the project's current-state-only rule | "The reason the ambient HEAD alone is not the answer still holds"; "The payload has always carried ..."; test docstrings "At HEAD", "used to refuse" | minor |
| L3-7 | `_cmd_lifecycle.py:886-889` (re-read) | a branch with many unrecorded SHAs | the single-line message grows by about 250 characters per SHA with no truncation; fails closed, no corruption | info |

**Layer 3 not shown by reading:** whether the worktree ledger and the main-checkout ledger resolve to the same file for a commit made from a third cwd (the guard reads the cwd ledger and `{worktree}/.plan/work/`); whether `foreign_branch` is discoverable at authoring time beyond the deliverable template (the lane reports the phase-3-outline block and the artifact inventory as residue); whether a repository-wide sweep finds no remaining "only phase 5 writes `kind=change`" statement (no content search was possible); whether the full suite is green.

**Layer 3 verdict:** findings — 1 major, 5 minor, 1 info. The major is recorded as an Open Defect and reported to the operator; it is not staged.

### Conformance to the Project's Own Rules

| Rule source | Rule | Verdict | Evidence |
|-------------|------|---------|----------|
| CLAUDE.md § Documentation Standards | current state only, no history | deviates | L3-6 |
| spec standing constraint | the transition guard stays as strict; `VERIFY_REFUSAL_ERRORS` unchanged | conforms | the `_cmd_lifecycle.py` diff is docstring and message text only |
| spec standing constraint | one write path, `change_record` / `append_entry` | conforms | `git-workflow.py:1061-1073` |
| spec standing constraint | the foreign gate fails closed | conforms | an undeclared `main` reads `blocked`, which is the closed direction; no path clears without a read landing state (`foreign_pr_gate.py:536-541`) |
| spec standing constraint | executor regeneration only if a verb or flag is added | conforms | no parser change in the `git-workflow.py` diff |
| spec D2 Done-when | a foreign change on a branch other than `feature/{plan_id}` with a merged PR is `clear` | deviates | holds only while the checkout stays on the change branch; after cleanup it reads `blocked` or `error` (L3-1) |
| spec D3 Done-when | no document still says only phase 5 writes a `kind=change` row | not shown by reading | no repository-wide sweep |

## Metrics and Anomalies

- Tokens: `unknown` (not measured; out of scope per the focus rule).
- Anomalies: `self-review: budget-exhausted` (three rounds; round 3's two text findings fixed; the operator chose to proceed); two guard refusals (R1 pipe, R7 edit at the main checkout); builds waited on slots up to about 2300 s; one quality-gate run killed at the daemon floor and re-run.

## Routing and Merge Behavior

- Review: CodeRabbit (required) reviewed head `8eeec321a`, no actionable comments; the merged head was refused on quota; Sourcery (optional) refused on quota. The standing review authorization applied (lane's claim, not re-read).
- CI/merge: merge queue; `ci pr view` reports merged with the merge commit above (re-read). `verify` green on the merge head (lane's claim, not re-read).
- Sonar: `n/a` (Sonar is not enabled for this project).
- Collision: the plan ran after PLAN-LB-123 and alongside PLAN-LB-116, 125 and 127 on disjoint surfaces; no conflict or re-verify signal is reported.

## Reconciliation Actions

- [x] row `status` → `shipped`
- [x] row `pr` stamped `1942`
- [x] row `landing` stamped `landings/PLAN-LB-126.md`
- [x] row `plan_marshall_plan_id` stamped `rb-lb-126-finalize-commit-rows-and-foreign-branch`
- [x] epic.md narrative reconciled (landing entry, one Open Defect, one Watch)
- [x] `queue-view.md` regenerated

## Follow-Ups

- **L3-1 (major)** is an Open Defect in epic.md and was reported to the operator in the same turn. A fix plan only on the operator's word. It qualifies under the stop rule when a foreign deliverable's archive gate falsely blocks in normal use; foreign deliverables are rare, so frequency is the operator's call. If staged, L2-2 (the unrealistic fixture), L1-1 and the digit-ending `--step` hazard are fold candidates, and the fix is a rule that the base or default branch is never a change's branch (so an undeclared `main` reads `unresolved` instead of `blocked`), with a fixture for the post-cleanup state.
- The remaining minors and the history wording: one Watch; not staged.
- Owed outside the plan, operator-run: a harness sync. No executor regeneration (no verb or flag was added).
