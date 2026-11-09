# PLAN-LB-131: The foreign-PR gate never takes a repository's default branch as the change's branch, and a merged branch whose refs are gone still reads merged

epic: live-blockers
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-131-foreign-gate-default-branch.md` and is queued as one row file, `queue/PLAN-LB-131.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged on the operator's word of 2026-11-09 as the fix plan for the PLAN-LB-126 major (#1942, `landings/PLAN-LB-126.md` L3-1), with
> its fold candidates L1-1, L2-2 and L3-6. Designed by a read-only leaf against `main` at `9cd644892`. Ruling check: D1 is a false
> block of the archive gate in the state the spec and the CLI test call typical (blocking, narrow: ruling 20, option d, foreign
> deliverables only). **Each deliverable is its own outline deliverable, and each Done-when is its own success criterion. Do not merge
> them.** Every Done-when below fails at `9cd644892` unless it says "holds at". No Sonar. No token or measurement work.

## Objective

After cleanup a foreign repository's tree sits on its default branch. The gate takes the branch the checkout is on, `landing-state`
answers `pushed_no_pr` for `main` (no PR has the tip of `main` as its head), and the gate blocks a change that merged with the text
"open a PR". Declaring the change branch does not help, because a checkout on `main` then reads as a `branch_disagreement`; and a
declared branch whose local ref is gone cannot be tip-resolved. This plan makes the default branch never a change's branch, lets a
declaration win over a checkout on it, and lets a merged branch be read after its refs are deleted.

## Deliverables

1. **The default branch is never a change's branch, and a declaration wins over a checkout on it.**
   - `foreign_pr_gate.py` gains a seam `default_branch_resolver(repo_root) -> str | None` on `check()` (the seam list at L413-416),
     reading `git -C {repo_root} symbolic-ref --short refs/remotes/origin/HEAD` (with `origin/` stripped) and, when that is absent,
     `git -C {repo_root} ls-remote --symref origin HEAD`. Decide at outline whether the CI abstraction already has a default-branch
     verb (`ci.py` was not read) and use it if so.
   - `_branch_for_repo` (L223-263): undeclared and checkout == default gives `None` with reason `branch_is_default: the foreign
     checkout at {root} is on its default branch {main!r}, which is never a change's branch; declare foreign_branch: <change branch>
     in the deliverable's **Metadata:** block`. Declared X and checkout == default returns X (a checkout on the default branch says
     nothing about the change). `branch_disagreement` stays only for a checkout on a non-default branch other than X. Default
     unreadable and undeclared is an unresolved row `default_branch_unreadable` (fail closed); default unreadable and declared keeps
     today's disagreement test.
   - No landing read is made for a repository with an unresolved branch.

   *Done when:* each of these fails at `9cd644892`, in `test/plan-marshall/phase-6-finalize/test_foreign_pr_gate_gate.py` (the `_run`
   helper L54-101 gains a `default_branches` seam, default `'main'` per root; `test_foreign_pr_gate_cli.py` `_run` L49-89 gains the same
   seam so every existing fixture with checkout `fix/foreign-branch` is unaffected):
   - undeclared, checkout `main`, default `main`, `landings={'main': 'pushed_no_pr', 'feature/p': 'pushed_no_pr'}` gives `status == 'error'`, `unresolved[0].reason` starting `branch_is_default` and `landing_branches == {}` (it is `blocked` at `9cd644892`);
   - declared `docs/x`, checkout `main`, default `main`, `{'docs/x': 'merged'}` gives `clear` with branch `docs/x` (it is `branch_disagreement` at `9cd644892`);
   - default unreadable and undeclared gives `default_branch_unreadable`.

   `test_the_plan_id_branch_is_never_the_fallback` (L486-504) answers `main: merged`, which the real verb cannot give; it is replaced by
   the first case, and the no-fallback guarantee stays pinned by `test_the_checkout_branch_is_used_when_nothing_is_declared`
   (L469-483). `test_a_declared_branch_that_disagrees_with_the_checkout_is_unresolved` (L415-429) uses checkout `fix/other`, since
   with `main` it becomes a clear under the new rule. These hold at `9cd644892` and must keep holding: `docs/workflow-dsl` merged is
   `clear`; the same change pushed with no PR is `blocked`; an unreadable checkout branch with no declaration is `branch_unreadable`.

2. **A declared branch whose local ref is gone is resolved from the remote and, failing that, from its merged PR.**
   - `landing-state --branch X` accepts the argument (`_github_pr.py` `_resolve_landing_branch` L1521-1542), but `_branch_tip_sha`
     (L1545-1560) runs `git rev-parse X`, which does not try `refs/remotes/origin/X`; with the local ref deleted the gate gets an
     unresolved "Could not resolve the tip SHA" row. The tip is resolved in order: `refs/heads/X`, `refs/remotes/origin/X`,
     `git ls-remote --heads origin X`; when the branch is absent everywhere, nothing unlanded exists under that name, and the state
     is classified from the full `gh pr list --head X` listing: any MERGED gives `merged`; any OPEN is an error (an open PR implies
     the ref exists, so the read is inconsistent); none is an error `branch_absent`.
   - The remote name `origin` is an assumption; the GitLab handler (`workflow-integration-gitlab`, not read by the design leaf) is read at
     outline and given the same rule or recorded as unchanged with the reason.
   - The `derive_landing_state` docstring (`ci_base.py` L947-951) claims `merged` survives deletion of the head branch; it states the
     condition (the tip is resolvable).

   *Done when:* each of these fails at `9cd644892`, in `test/plan-marshall/workflow-integration-github/test_pr_landing_state_states.py`
   and `test_pr_landing_state_errors.py`: local ref missing and `origin/X` present matches the tip and reads `merged` for a merged PR;
   both refs missing, `ls-remote` empty and a PR list `[{'state': 'MERGED', …}]` reads `merged`; both missing and an empty list is an
   error `branch_absent`. And these hold at `9cd644892` and must keep holding: a stale merged PR on a reused branch name whose head is
   not the current tip does not read `merged` for new commits (the tip-matching rule); a truncated listing at the ceiling is an error.

3. **The documents state the branch rule once and in the present tense.**
   - `phase-6-finalize/standards/archive-plan.md` L37 replaces "The reason the ambient HEAD alone is not the answer still holds —
     after branch cleanup …" with the rule: the default branch is never a change's branch; an undeclared repository whose checkout is
     on it is an unresolved `branch_is_default` row; a declaration wins over a checkout on the default branch.
   - The `foreign_pr_gate.py` module docstring (L67-86) states the same and drops "a plain `main`" (L80).
   - `manage-status/scripts/_cmd_lifecycle.py` L876-879 ("The payload has always carried … left the operator repairing one commit")
     becomes present tense: "The payload carries the whole set in `unrecorded_commits`, and the message names every SHA with its own
     invocation so one pass repairs them all."
   - Two test docstrings that carry history wording ("At HEAD", "used to refuse", "assumed at HEAD" in
     `test_source_commit_gate_commit_path.py` and `test_foreign_pr_gate_gate.py`) are made present tense.

   *Done when:* each of these fails at `9cd644892`: a doc test asserts `archive-plan.md` states the default-branch rule once and carries no "still holds" wording; the module docstring names no plain `main` as a change branch.

Split guard: three deliverables. D2 is independent of D1 and splits off first (it is a verb in another skill); D3 follows D1.

## Standing Constraints

- Settle each HYPOTHESIS first. A refuted claim is dropped from its deliverable and the PR says so.
- The foreign gate fails closed: an unread branch, default branch or landing state is never `clear`; there is no fallback to `feature/{plan_id}`.
- Out of scope, by ruling 20: a plan-owned worktree for a sibling path, push and PR for it, a cross-repo footprint bucket, a module name for a sibling path.
- Documentation states the current behaviour; no comment or document describes a change or the old behaviour.
- Tests state their purpose, use the `PLAN_MARSHALL_HOME` fixture, are shown red where a Done-when says so, and a fixture answer is one the real verb can give.
- Executor regeneration only if a verb or a flag is added.
- No token or measurement work. No Sonar.

## Claim Labels

- OBSERVED: `_branch_for_repo` (`marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/foreign_pr_gate.py` L223-263) returns the checkout's branch when nothing is declared (L258-263) and `branch_disagreement` for a declaration beside a different readable checkout branch (L252-256); `_current_branch` L184-201; `check` L410-571; the docstring L67-86 names "a plain `main`" at L80
- OBSERVED: `cmd_pr_landing_state` (`workflow-integration-github/scripts/_github_pr.py` L1583-1693) keeps only PRs whose head is the branch tip (L1665) and `derive_landing_state` (`tools-integration-ci/scripts/ci_base.py` L926-958) returns `pushed_no_pr` for a pushed branch with no tip-matching PR, so `main` reads `pushed_no_pr`
- OBSERVED: `_branch_tip_sha` runs `git rev-parse {branch}` (L1545-1560), which does not try `refs/remotes/origin/{branch}`; `_branch_pushed_state` L1563-1580
- OBSERVED: `test_foreign_pr_gate_cli.py` L416-419 records that after cleanup the foreign checkout typically sits on `main`, "which would read `pushed_no_pr` for a change that already merged"
- OBSERVED: `test_the_plan_id_branch_is_never_the_fallback` (`test_foreign_pr_gate_gate.py` L486-504) pins `clear` with the answer `main: merged`, which the real verb does not give
- HYPOTHESIS: the CI abstraction has a verb that returns a repository's default branch — confirm at `tools-integration-ci/scripts/ci.py` (not read by the design leaf; verify-at-outline, D1)
- HYPOTHESIS: the GitLab landing-state handler resolves the tip the same way and has the same gap — confirm at `workflow-integration-gitlab` (verify-at-outline, D2)
- HYPOTHESIS: `git ls-remote --symref origin HEAD` is available without credentials for the foreign tree — confirm (verify-at-outline, D1)
- Verify-first clause (D1): reproduce the undeclared-`main` block as a fixture at `9cd644892` before editing.
- Verify-first clause (D2): decide whether the full PR-list classification is safe against a reused branch name (the tip-matching rule); record why.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/foreign_pr_gate.py` — `_branch_for_repo`, `check`, the module docstring (D1, D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py` — `_branch_tip_sha`, `cmd_pr_landing_state` (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/tools-integration-ci/scripts/ci_base.py` — the `derive_landing_state` docstring (D2)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/workflow-integration-gitlab/scripts/` — the GitLab landing-state handler (verify-at-outline) (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/archive-plan.md` — L37 (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_lifecycle.py` — the comment at L876-879 (D3)
- OBSERVED: `test/plan-marshall/phase-6-finalize/test_foreign_pr_gate_gate.py` and `test/plan-marshall/phase-6-finalize/test_foreign_pr_gate_cli.py` (D1, D3)
- OBSERVED: `test/plan-marshall/workflow-integration-github/test_pr_landing_state_states.py` and `test/plan-marshall/workflow-integration-github/test_pr_landing_state_errors.py` (D2)
- OBSERVED: `test/plan-marshall/workflow-integration-git/test_source_commit_gate_commit_path.py` — docstring wording (D3)

## Dependencies and Sequencing

- Depends on: PLAN-LB-126 (shipped, #1942, `f1945737a`).
- Overlaps with: PLAN-LB-133 on `manage-status/scripts/_cmd_lifecycle.py` (a different region) and PLAN-LB-139 on the `phase-6-finalize` test directory; the gate decides. PLAN-LB-132 shares `_github_pr.py`'s neighbourhood (`github_pr.py`, not `_github_pr.py`).
- Adjacent to: the Open Defect "A deliverable in a sibling repository has no lifecycle", which stays open for everything ruling 20 excluded.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-131-foreign-gate-default-branch.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
