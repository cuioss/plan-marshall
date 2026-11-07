# PLAN-LB-126: Finalize commits write their change-ledger row, and the foreign-PR gate reads the foreign branch

epic: live-blockers
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-126-finalize-commit-rows-and-foreign-branch.md` and is queued as one row file, `queue/PLAN-LB-126.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged on the operator's rulings of 2026-11-07: decision 11 (the inline-commit candidate of inbox `quality-report-001`, theme 4 and
> addendum PLAN-08-010, is reproducible and blocking) and ruling 20 (the narrow sibling-repository fix, option d, rides with it). It
> builds on PLAN-LB-91 (#1847, `5a6058a6e`), which gave the 5-execute boundary its `history_rewritten` / `bookkeeping_gap` signatures
> and the `remap` verb. Points the drafting leaf re-read at HEAD `5cd8ccd92` are OBSERVED; reach and design choices are HYPOTHESIS
> and are settled first. It RUNS AFTER the running PLAN-LB-123.
>
> Ruling check. D1 is a false block of a normal finalize loop-back (blocking); D2 is a false block and a missed block at the archive
> gate (blocking, ruling 20). D3 is the text. No token or measurement work. No Sonar.

## Objective

The 5-execute to 6-finalize transition refuses unless every commit in `merge-base(HEAD, base)..HEAD` has a `kind=change` ledger row,
whichever phase made it, and only phase-5 Step 10a writes one. A finalize commit followed by a loop-back to `5-execute` is therefore
refused at the next transition, and the refusal names one SHA and a remedy written for a deliverable commit. The pre-archive
foreign-PR gate classifies every foreign repository on `feature/{plan_id}`, so a foreign change on any other branch is misread.

After this plan every finalize commit leaves its own row through one deterministic owner, the refusal names every unrecorded SHA with
a remedy that fits it, and the foreign gate reads the branch the foreign change is on or stops with a named reason.

## Deliverables

1. **Every finalize commit writes its own `kind=change` row.** *(decision 11; blocking)*
   - The writers that make no row: the dispatcher's commit of a mutating step's edits (`phase-6-finalize/SKILL.md` item 5f(b),
     L1352-1364, through `workflow-integration-git` with `step: {step_id}`), the triage inline-fix commit `fix(review): apply inline
     review dispositions` (item 7c(4a), L1946, no `step` named) and the architecture-refresh commits, which are raw
     `git -C {worktree_path} commit` calls (`architecture-refresh.md` L265-266 Tier 0, L401-402 Tier 1).
   - One owner, decided at outline and recorded once: the `git-workflow commit` verb (preferred: it already holds the staged paths,
     the new commit SHA and the plan's phase, `git-workflow.py` L1029-1073) or each caller. If the verb: it appends only when the
     plan's `current_phase` is `6-finalize`, so phase-5 Step 10a keeps its own row and no commit gets two; `changed_paths` are taken
     from the commit with `git diff-tree` per the ledger contract; the `deliverable_id` for a finalize commit (the step id, the triage
     source `wait-region-unified-triage`, or a fixed prefix) is chosen so no reader mistakes it for an outline deliverable. Every
     reader of `kind=change` `deliverable_id` is enumerated first, the dirty-tree attribution map at `execution.md` L479-486 included.
   - The architecture-refresh commits go through the same owner.
   - The refusal names every unrecorded SHA in `message`, not only `append_invocations[0]` (`_cmd_lifecycle.py` L897, L909, L923),
     and its remedy is not "run the phase-5-execute Step 10a settlement bookkeeping" (L877, L921) for a commit phase 5 did not make.
     The payload keeps its field set: `unrecorded_commits`, `unrecorded_count`, `branch_commit_count`, `recorded_count`,
     `signature`, `append_invocations`, `append_invocation`, `remap_invocation` (L911-953).

   *Done when:* a fixture with a 5f(b) finalize commit, then a loop-back to `5-execute` and a Step 10a fix commit, transitions to
   `6-finalize` (red at HEAD); a commit with no row is still refused, with every unrecorded SHA in the message (control, two SHAs);
   the triage inline-fix path and the architecture-refresh path each leave a row; a phase-5 Step 10a commit leaves exactly one row.

2. **The foreign-PR gate reads the foreign branch.** *(ruling 20, option d, narrow; blocking)*
   - `plan_branch_for` returns `feature/{plan_id}` (`foreign_pr_gate.py` L169-171) and every foreign repo is classified on it
     (L332-333, L174-211). Decide at outline where the branch comes from: a value declared on the deliverable, or the foreign
     repo's current branch at `repo_root`. The second must answer the reason the gate gives against it: after cleanup the foreign
     tree typically sits on `main` (L178-184; `archive-plan.md` L37). When the two sources disagree, or the branch cannot be read,
     the repo is an `unresolved[]` row with a named reason and the gate is `error`; it never falls back to `feature/{plan_id}`.
   - Out of scope, by ruling 20: a plan-owned worktree for a sibling path, push and PR for it, a cross-repo footprint bucket, a module
     name for a sibling path. The Open Defect "A deliverable in a sibling repository has no lifecycle" stays open for those.

   *Done when:* a fixture whose foreign change is on a branch not named `feature/{plan_id}` with a merged PR is `clear` (red at
   HEAD); the same change pushed with no PR is `blocked` (control); an unreadable or disagreeing branch is a named `unresolved` row
   and `status: error`.

3. **The documents state the row obligation and the branch rule once.**
   - The finalize commit instrumentation (item 5f, item 7c(4a)), `architecture-refresh.md` § 3d and the Tier-1 branch,
     `workflow-integration-git/SKILL.md` Commit Changes, and `manage-change-ledger/SKILL.md` (§ Entry Shapes L141-144, which says only
     phase 5 writes `kind=change`; Integration L388-390) state who writes the row; the others point there.
   - `archive-plan.md` L37 and the gate docstring (L34, L178-184) state the branch rule.

   *Done when:* a read of each cited section shows the one statement and the pointers; no document still says only phase 5 writes a
   `kind=change` row.

Split guard: three deliverables. D2 is independent of D1 and splits off first; D3 follows whichever it documents.

## Standing Constraints

- **Settle each HYPOTHESIS first.** A refuted claim is dropped from its deliverable, not worked around, and the PR says so.
- **The transition guard stays as strict.** The fix is at the writers; no SHA is exempted, no phase filter is added to
  `_phase_end_marker_refusal`, `VERIFY_REFUSAL_ERRORS` is unchanged.
- **One write path.** Rows go through `_ledger_core` `change_record` / `append_entry`; no re-implemented JSONL write.
- **The foreign gate fails closed.** An unread branch or landing state is never a `clear`.
- **Executor regeneration only if a verb or flag is added.** If `git-workflow commit` gains a flag, an executor regeneration is owed
  and the landing says so.
- **Documentation states the current behaviour.** No comment or doc describes a change or the old behaviour.
- **Tests state their purpose**, use the `PLAN_MARSHALL_HOME` fixture, are shown red where a Done-when says so; counts come from an
  enumeration, not a hand list.
- **No token or measurement work.** **No Sonar.**

## Claim Labels

- OBSERVED: the guard runs only on `--completed 5-execute` into a blocking boundary (`_cmd_lifecycle.py` L1771, L1818-1821),
  enumerates `merge-base..HEAD` remote-first (L431-470), matches by full or prefix SHA (L473-499), reads the cwd and the plan-checkout
  ledgers (L683-714), computes the unrecorded set at L869 and refuses `execute_commits_unrecorded`, `bookkeeping_gap` at L917-929.
- OBSERVED: every message embeds only `append_invocations[0]` (L897, L909, L923) with the `DELIVERABLE_ID` / `CHANGED_PATHS`
  placeholders (L536-575); the payload carries all SHAs in `unrecorded_commits` (L947).
- OBSERVED: `execution.md` L454 halts for the operator on every refusal but the two tree-state codes.
- OBSERVED: `cmd_commit` reads the phase (L1029) and staged paths (L1030), commits (L1068) and resolves the SHA (L1072-1073), and
  writes no ledger row — `workflow-integration-git/scripts/git-workflow.py` L1007-1120.
- OBSERVED: `change_record` requires `deliverable_id`, `commit_sha`, `changed_paths` (`_ledger_core.py` L231-255); the `append`
  verb accepts `--deliverable-id` or `--task-id` (`manage-change-ledger.py` L163-182).
- OBSERVED: `architecture-refresh.md` declares no `mutates_source` (L1-11), so item 5f does not commit for it; it commits itself with
  raw `git commit` (L265-266, L401-402).
- OBSERVED: `_branch_tip_sha` runs `git rev-parse {branch}` and returns `status: error` when the branch does not resolve —
  `workflow-integration-github/scripts/_github_pr.py` § `_branch_tip_sha`; `foreign_pr_gate.py` turns that into an `unresolved` row
  (L403-417), so a merged change on another branch reads `error` today.
- OBSERVED: only `pushed_no_pr` blocks (`foreign_pr_gate.py` L99); `LANDING_STATES` (`ci_base.py` L923).
- HYPOTHESIS: the three writers above are the whole population of finalize commits — confirm by a content search for `commit` across
  `phase-6-finalize/standards/` and `workflow/` (verify-at-outline).
- HYPOTHESIS: the triage inline commit (L1946) passes no `step` and is sanctioned by a finding record — confirm at
  `git-workflow.py` § `evaluate_source_commit_gate` (verify-at-outline). It decides whether a `--step`-keyed owner covers it.
- HYPOTHESIS: the raw architecture-refresh commit is refused by the enforcement guard in `6-finalize` (`git-workflow.py` L1013-1014,
  `SKILL.md` L1363-1364 say so) — confirm on the active harness (verify-at-outline).
- HYPOTHESIS: the ledger the verb's process resolves is one the guard reads (cwd ledger or `{worktree}/.plan/work/`) — confirm at
  `_ledger_core.resolve_ledger_path` from a worktree cwd (verify-at-outline).
- HYPOTHESIS: no outline field carries a foreign branch — confirm at `manage-solution-outline/scripts/_plan_parsing.py` §
  `DECLARATION_FIELDS` (verify-at-outline). It decides D2's first option.
- HYPOTHESIS: a foreign branch deleted locally after its merge cannot be tip-resolved, so even a correct branch name reads `error`
  — confirm at `_github_pr.py` § `_branch_tip_sha` and the GitLab provider (verify-at-outline); record it as residue if so.
- Verify-first clause (D1): reproduce the refused loop-back as a fixture at HEAD before editing.
- Verify-first clause (D2): the `landing_resolver(repo_root)` seam hides the branch; the red fixture models the answer per branch.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/git-workflow.py` — `cmd_commit`, if the verb owns the row (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_lifecycle.py` — the refusal message, the guard docstring (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md` — item 5f(b), item 7c(4a) (D1, D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/architecture-refresh.md` — § 3d, Tier-1 commit (D1, D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/foreign_pr_gate.py` — `plan_branch_for`, `check` (D2, D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/archive-plan.md` — L37 (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-change-ledger/SKILL.md` — Entry Shapes, Integration (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-git/SKILL.md` — Commit Changes (D3)
- OBSERVED: `test/plan-marshall/manage-status/test_manage_status_transition_5_execute_and_finalize.py` — the end-marker fixtures (D1)
- OBSERVED: `test/plan-marshall/workflow-integration-git/test_source_commit_gate_commit_path.py` — the commit-verb fixtures (D1)
- OBSERVED: `test/plan-marshall/phase-6-finalize/test_foreign_pr_gate_gate.py` — the gate fixtures (D2)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-change-ledger/scripts/_ledger_core.py` — `change_record` docstring L241-246 (D3; verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/_plan_parsing.py` — only if D2 declares the branch on the deliverable (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py` — read; edited only if the tip read must accept a remote ref (D2; verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/execution.md` — L454 or L479-486, only if the halt or attribution text must name finalize rows (D1, D3; verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/phase-6-finalize/test_foreign_pr_gate_cli.py` — the `plan_branch` output (D2; verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/phase-6-finalize/test_architecture_refresh_files.py` — if it pins the raw commit text (D1; verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/phase-6-finalize/test_unified_triage_commit_precedes_gate.py` — the 7c(4a) text (D1; verify-at-outline)

## Dependencies and Sequencing

- **Depends on:** PLAN-LB-91 (`5a6058a6e`, on the base branch). **Runs after the running PLAN-LB-123 merges:** both edit
  `phase-6-finalize/SKILL.md` (LB-123 D5 at L929; this plan items 5f and 7c) and LB-123 edits `plan-marshall/workflow/execution.md`
  (L239-254, L242), which this plan may touch at L454 / L479-486. Re-read every cited line after that merge.
- **Overlap risk with PLAN-LB-124** (push-gate rows and the Maven guard): its surface includes `pre_merge_gate.py` and `manage-tasks`.
  This plan plans no edit to `pre_merge_gate.py`, but item 5f(d)'s freshness record and the phase-6-finalize documents sit beside the
  push gate. The disjointness gate decides at emit; sequence if any phase-6-finalize document is shared.
- **Overlaps with parked PLAN-LB-87** (`phase-6-finalize/SKILL.md` L1196-1198, `execution.md` L220-222, L265-267): re-ground it
  against this plan's line moves before it is un-parked.
- **Adjacent to** (left untouched): the transition guard's predicate, `remap`, the source-commit gate's sanctions, phase-5 Step 10a
  (`phase-5-execute/SKILL.md` L818-824), the structural sibling-repository lifecycle, and the gate's non-blocking `unpushed` state
  (`foreign_pr_gate.py` L99), which is a separate lead.
- **Owed outside this plan, operator-run:** a harness sync after merge; an executor regeneration only if a verb or flag is added.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-126-finalize-commit-rows-and-foreign-branch.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
