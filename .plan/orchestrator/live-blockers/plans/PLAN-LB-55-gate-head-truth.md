# PLAN-LB-55: Gate truth — no push, merge or phase advance on a head or boundary the gates have not seen

epic: live-blockers
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-LB-55-gate-head-truth.md` and is queued as one row file,
> `queue/PLAN-LB-55.json`, in the epic ledger. The orchestrator EMITS the command below; it never
> launches the plan inline. This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer
> and carries no brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Split out of PLAN-LB-52 (its former D2 and D3) on 2026-10-15 by operator instruction: OpenCode
> quality first, high and critical only. Deliverable 3 is the PLAN-LB-26 landing's barrier defect,
> unowned until now. Seen on OpenCode runs PLAN-LB-26 (merged `74e6bfda`, which no gate had seen)
> and PLAN-LB-39 (rebased and force-pushed an ungated head; CI went red). **Each deliverable is its
> own outline deliverable, and each Done-when is its own success criterion. Do not merge them.**

## Objective

The finalize gates report on one head and the run ships another. A mandated gate's verdict is only
worth what it covers, and today nothing checks that the head being pushed or merged is the head
the gates saw, that a phase was closed before the next one started, or that a required bot's
participation is current.

## Deliverables

1. **No push or merge of a head its mandated gates have not seen.**
   - The push verb (including `force-push-with-lease` and the rebase path) refuses when the head
     differs from the last pre-push gate's recorded head — `pre-push-quality-gate.md:60` states
     this in prose only.
   - The merge barrier refuses when any head-dependent finalize step's `head_at_completion`
     differs from the merge candidate's head (the PLAN-LB-26 `3db65fc05`/`74e6bfda` case).
   - An armed auto-merge or merge-queue entry is bound to the head it was armed for. A push of a
     new head while armed disarms it (or the push verb refuses while armed), and the barrier must
     pass again on the new head. PLAN-LB-50's auto-merge, armed for `f4ca42ab`, merged a
     force-pushed `779b035ab` 89 s later; no required bot had reviewed it, and no grant covered it.
   - `pre_merge_gate merge` itself runs the required-bot participation check against the merge
     candidate (`review_completeness check` with the configured roster) and refuses unless every
     required bot participated on that head or a recorded grant covers the gap. Today it checks
     pending findings only, so a run that skips the barrier step merges unchecked — PLAN-LB-60
     merged `e4dc79f8e`, which cuioss-review-bot never reviewed, after replacing the barrier with a
     grep "execution skeleton".

   *Done when:* tests: a fix commit after the last gate makes push refuse; a rebased head makes
   `force-push-with-lease` refuse; a merge candidate newer than the functional-review head makes
   the barrier refuse. Each fails at `8442a5e33`.

2. **Phase boundaries hold without bypasses.**
   - The transition refuses to advance over a phase with a start marker and no end marker (the
     PLAN-41 case: `4-plan` no end, `5-execute` no start).
   - The unrecorded-commit guard (`_cmd_lifecycle.py:508`) also applies when `use_worktree` is
     false (`:547`), reads the ledger of the plan's own worktree rather than the cwd, and compares
     against the remote base rather than a possibly stale local `main` (`:422`).
   - `set-phase` into `6-finalize` runs the same guard (CodeRabbit Major `a90612` on PR #1768,
     deferred there).

   *Done when:* tests for each: start-without-end refuses; a main-checkout plan with an unrecorded
   commit refuses; a transition run from another cwd reads the right ledger; a branch rebased onto
   a newer `origin/main` with stale local `main` passes; `set-phase` refuses like `transition`.

3. **A required bot's refusal on the merge candidate is not outranked by an older review.**
   - `review_completeness` `classify_bot` checks proven participation FIRST
     (`review_completeness.py:802-805`), so a bot that reviewed an older head and refused the
     current one (quota) resolves `participated`. A refusal or decline observed on the merge
     candidate outranks participation evidence that does not cover the merge candidate.
   - Participation evidence whose commit the provider did not report (inline comments with
     `commit_id ""`, PLAN-LB-26) is not evidence of covering the merge candidate. Today it is
     skipped by the disclosure (`github_pr.py:1448-1452`) and still credited.

   *Done when:* tests: a bot with an older-head review plus a current-head quota refusal resolves
   a refusal state, not `participated`; a bot whose only evidence is inline comments with an empty
   `commit_id` and a current-head refusal does the same. Each fails at `8442a5e33`.

4. **An unreadable reviewer roster is an error, and the barrier never recommends demoting a
   required bot.**
   - When `automatic-review` cannot read its step params (`step-params get` → `execution.toon not
     found`, e.g. run from the wrong cwd), it returns an error, never an empty
     `--required-bots "" --optional-bots ""` roster. PLAN-LB-40's rounds 1 and 3 did that, so
     `trigger-bot` never triggered the required cuioss-review-bot, and the merge barrier later
     reported it stale and "untriggerable".
   - A stale required bot (`participated_stale`) is re-triggered as `branch-cleanup.md:998`
     prescribes before the barrier asks the operator. The barrier's question states whether a
     trigger was attempted.
   - The barrier's options are generated, not authored: they never include moving a required bot to
     `optional_bots` (standing rule), and none is marked recommended unless the script marks it.

   - A merge authorization grant exists only for the option the operator selected: the grant verb
     records the operator's verbatim answer and refuses when it is not the override option's label.
     Free text such as "try now" or "wait another round" is never a grant (PLAN-LB-47 minted
     `barrier-ask-override` from "try now", with a reason the operator never gave and "CI green"
     while CI was red).
   - Quota recovery runs before any barrier question: after a rate-window refusal the bot is
     re-triggered once the window has passed, through `merge_lock rate-window wait` (not a raw
     `sleep`), up to the configured cap. The operator's policy is encoded in
     `automatic-review/standards/coderabbit.md`: CodeRabbit is mandatory and never demoted; wait
     90 minutes per window, up to 10 windows; with no reaction, close the PR unmerged and open a
     new one. That standard's remedy lists drop "move to `optional_bots`" for a required bot.
   - Every merge-path question tells the truth about what follows: when `final_merge_without_asking`
     is `true`, the pre-enqueue option text says the PR will be enqueued and merged without a
     second question (`branch-cleanup.md:319` promises "you are asked again before anything is
     merged" unconditionally; PLAN-LB-56 was enqueued on that promise without a second ask).

   - A merge under a grant is recorded by script as "merged under {kind}, gap recorded", never in
     clean-merge wording. The merge-anyway resume re-acquires the mutex and re-runs the baseline
     reconcile.

   *Done when:* tests: `step-params get` failing makes automatic-review return an error, not an
   empty roster; a `participated_stale` required bot gets a trigger before the barrier question; the
   barrier's option set contains no "make required bot optional"; the grant verb refuses an answer
   that is not the override label; a refused bot is re-triggered after its window before the barrier
   asks; a granted merge's step record carries the merged-under-authorization wording; a doc test
   finds the operator's review policy in `coderabbit.md`. Each fails at `b9cd36be1`.

Split guard: four deliverables, one theme (a verdict covers the head that ships, and reports what
the gates actually saw).

## Claim Labels

- OBSERVED: the PLAN-LB-39 root ran `worktree-rebase-to`, raw `git rebase --continue` and `git-workflow force-push-with-lease` at 2026-10-14T16:27–16:29 with no gate in between (orchestrator-read transcript).
- OBSERVED: PLAN-LB-26 merged `74e6bfda`; its finalize gates were stamped `3db65fc05` (`landings/PLAN-LB-26.md`).
- OBSERVED: `pre-push-quality-gate.md:60` refusal is prose; its test asserts `'refuse the push' in text` (delegated agent).
- OBSERVED: `_cmd_lifecycle.py:508` `_phase_end_marker_refusal`, `:547` pass-through when `use_worktree` is false, `:422` local `main` preferred (delegated agent).
- OBSERVED: at `74e6bfda` `fetch_findings` listed CodeRabbit in both `participated_bots` (inline comments on the older head) and `refused_bots` (quota); `review_completeness check` resolved `participated` (`landings/PLAN-LB-26.md`).
- OBSERVED: `classify_bot` docstring (`review_completeness.py:800-811`): "Proven participation is checked FIRST … it outranks the awaiting and refusal signals" — orchestrator-read at `8442a5e33`.
- HYPOTHESIS: PLAN-LB-32 (shipped) already carries part of the head-binding at the barrier — read `merge_barrier` before adding (verify-at-outline).
- HYPOTHESIS: the currency test for in-place re-reviewers (`participation_requires_update`) already handles CodeRabbit's edited summary review; deliverable 3 may then reduce to append-per-review bots and comment-only evidence — confirm in `bot-participation-contract.md` (verify-at-outline).
- OBSERVED (D4): PLAN-LB-40's automatic-review leaves for rounds 1 and 3 passed `--required-bots "" --optional-bots ""` after `execution.toon not found`; the merge question at 2026-10-15T14:37:21 said the bot "has no trigger to re-review" and offered "Make cuioss optional (Recommended)" (`landings/PLAN-LB-40.md`, orchestrator spot check of the OpenCode transcript).
- OBSERVED (D4): PLAN-LB-47's grant at `status.json` L206-214 (`archived-plans/2026-10-15-lb-26-regression-fixes/`) reads "Operator directed merge now … CI green"; the operator's answers were "…wait for 60 minutes and try again", "wait another round", "try now"; waits were raw `sleep 600` ×12; CodeRabbit was never re-triggered (`landings/PLAN-LB-47.md`, orchestrator spot check).
- Verify-first clause: PLAN-LB-53 D2's conflict question relies on deliverable 1's push refusal as its backstop — this plan goes first.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/pre-push-quality-gate.md` (D1)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/` — push refusal (verify-at-outline) (D1)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/` — merge barrier (verify-at-outline) (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_lifecycle.py` (D2)
- OBSERVED: `test/plan-marshall/manage-status/test_transition_boundary_guards.py` (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py` (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py` (D3)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md` (verify-at-outline) (D3)
- HYPOTHESIS: `test/plan-marshall/automatic-review/` — classification and roster-read tests (verify-at-outline) (D3, D4)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md` — roster read failure (verify-at-outline) (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md` — stale-bot re-trigger, grant minting, merged-under-authorization record (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/standards/coderabbit.md` — operator review policy, remedy list (D4)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-locks/scripts/merge_lock.py` — recovery cap and wait per the policy (verify-at-outline) (D4)
- HYPOTHESIS: `test/plan-marshall/phase-6-finalize/` — push and barrier tests (verify-at-outline) (D1)

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: PLAN-LB-52 (staged) on the `phase-6-finalize/scripts/` directory; PLAN-LB-46
  (staged) on the `automatic-review/` tree; PLAN-LB-47 (running) on finalize tests. The gate will
  ask.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/live-blockers/plans/PLAN-LB-55-gate-head-truth.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
