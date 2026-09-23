# PLAN-10: `land` and `land-all` — monitored, never-remove ledger landing

epic: orchestrator-refactor
workstream: WS-05

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-10-orchestrator-land-verbs.md` and is queued in the epic
> `status.json` `plans[]` field. The orchestrator EMITS the command below; it never launches
> the plan inline. This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer
> and carries no brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

PLAN-09 gives each epic a fixed-name, long-lived worktree; this plan gives the orchestrator
the two verbs to LAND that worktree's changes onto `main` in a controlled, monitored way —
replacing today's ad hoc `git commit`/`git push` with an explicit `land` (this epic's own
pending `.plan/orchestrator/{slug}/**` changes) and `land-all` (every active epic's pending
changes, one sweep). Both create-or-reuse a branch, open-or-update a PR, wait for CI via the
existing bounded `ci checks wait` primitive, merge, and pull the result into BOTH `main` and
the worktree — never deleting the worktree, the one constraint stated twice by the operator
who proposed this mechanism.

## Deliverables

1. **D1 — `land`: stage, commit, push.** Within the epic's worktree (from PLAN-09), stage
   and commit only the epic's OWN dirty paths (`.plan/orchestrator/{slug}/**` — scoped even
   though a per-epic worktree makes cross-epic leakage structurally impossible, so the
   discipline survives if the worktree model changes later), push the worktree's branch.
2. **D2 — `land`: PR create-or-update.** Call the `ci` abstraction's PR primitives DIRECTLY
   with `--project-dir {worktree_path}` (confirmed generic, not plan-bound —
   `tools-integration-ci:ci pr create/view/prepare-body` all support this addressing) rather
   than reusing `phase-6-finalize`'s `create-pr` workflow doc (confirmed plan-bound: it reads
   PR title/body from plan-only sources — `manage-status metadata --plan-id`,
   `manage-plan-documents request read --plan-id` — that an orchestrator epic does not have).
   Reuse an existing open PR for the same branch rather than opening a duplicate on a second
   `land` call before the first merges.
3. **D3 — the monitor.** Wait for CI via `ci checks wait --pr-number N --project-dir
   {worktree_path}` — already a bounded, self-timing-out primitive (`ci_complete_precondition.py`'s
   pattern: a `--timeout` ceiling, `status: timeout` on expiry meaning "re-poll on
   re-entry", never a foreground busy-loop). On green, merge — reusing `ci pr merge`/
   `merge-queue` — and stamp the landed PR number from the PR's OWN state after merge,
   never from the landing call's own return message (this epic's own memory already records
   an incident, `project_ci_pr_merge_false_green.md`, where a merge call returned
   `merged: true` and deleted the branch without actually merging — `land` must not repeat
   it).
4. **D4 — pull main AND resync the worktree, without removing it.** On confirmed merge:
   fast-forward the PRIMARY checkout's `main` (so a session working there sees the landed
   state), and separately reset/resync the WORKTREE's own branch onto the new `main` so it
   is ready for the next round of writes — both steps leave the worktree directory in place;
   decide at outline whether the worktree's branch is reset-in-place (`git reset --hard
   origin/main` after a fresh fetch) or deleted-and-recreated fresh each cycle while only
   the DIRECTORY persists — either satisfies "the worktree is never removed", but they are
   different mechanisms with different failure modes, so pick one deliberately rather than
   by accident.
5. **D5 — `land-all`.** Enumerate active epics via `orchestrator corpus epics` (no `--slug`,
   partitions `active[]`/`archived[]` across both store roots — confirmed the correct,
   already-proven substrate). For each active epic whose worktree carries dirty or
   unpushed-but-committed `.plan/orchestrator/{slug}/**` state, run D1-D4's sequence.
   Decide at outline whether epics land sequentially or bounded-parallel — concurrent PRs
   landing through the SAME merge queue against the SAME `main` is a real collision surface
   this decision must account for, not wave past.
6. **D6 — failure/timeout leaves the worktree recoverable, never silently discarded.** A CI
   failure, a merge-queue ejection, or a `ci checks wait` timeout is reported (returned
   error / Open Defect on the calling epic) and the LAND ATTEMPT stops there — the
   worktree's own uncommitted or unpushed-but-committed state is left exactly as it was,
   never force-reset or discarded, so a retry (an operator re-invoking `land`) picks up
   where the failed attempt left off.

## Non-Goals

- No change to review-bot participation policy — `.plan/**` is already excluded from
  CodeRabbit/PR-Agent review org-wide (`project_plan_excluded_from_bot_review`, shipped),
  and the whole-tree build's `skip-on-docs-only` footprint gate already fast-paths a
  non-buildable ledger-only diff. `land` relies on both; changes neither.
- No worktree teardown/removal — PLAN-09's D3 already places that out of scope; this plan
  inherits the same boundary and does not add a removal path either.
- No change to the PLAN lifecycle's own `phase-6-finalize` create-pr/branch-cleanup
  workflow docs — this plan calls the underlying `ci` primitives directly instead of
  reusing those plan-bound docs, per D2's finding; the docs themselves are untouched.

## Claim Labels

- OBSERVED: `phase-6-finalize/workflow/create-pr.md` reads PR title from `manage-status
  metadata --plan-id --get --field pr_title` and PR body from `manage-plan-documents
  request read --plan-id --section clarified_request`, and gates completion via
  `manage-status mark-step-done --plan-id --phase 6-finalize --step create-pr` — all three
  plan-only surfaces an orchestrator epic does not have (no `request.md`, no execution
  manifest). This workflow doc is confirmed NOT reusable as-is from an orchestrator
  context.
- OBSERVED: `tools-integration-ci:ci`'s PR primitives (`pr create/view/prepare-body`)
  support `--project-dir {path}` as an alternative to `--plan-id` throughout
  (`create-pr.md:33,65,115,283` cites the pattern even though that doc itself is
  plan-bound) — the PRIMITIVE layer is provider-agnostic and not plan-coupled, confirming
  D2's approach of calling it directly.
- OBSERVED: `tools-integration-ci:ci checks wait` is a bounded, self-timing-out primitive —
  `standards/blocking-wait-pattern.md` and `ci_complete_precondition.py:152-239` show a
  `--timeout` ceiling with harness-bash-ceiling-aware clamping and a `status: timeout`
  return meaning "re-poll on re-entry", matching this project's "never foreground-poll,
  always arm a waiter" convention (`feedback_no_shell_polling_loops`). `ci pr` additionally
  carries `merge-queue`/`merge`/`auto-merge`/`safe-merge`/`update-branch` sub-verbs.
- OBSERVED: `orchestrator corpus epics` (no `--slug`) enumerates every epic slug across
  BOTH `.plan/orchestrator/` and `.plan/archived-orchestrators/`, partitioned
  `active[]`/`archived[]`, with per-root `exists`/`listed`/`entries_scanned`/`error`
  accounting — the correct, already-used-this-session substrate for D5's sweep.
- OBSERVED: this epic's own memory records an incident (`project_ci_pr_merge_false_green`)
  where `ci pr merge` returned `merged: true` and deleted the branch WITHOUT actually
  merging — D3's "stamp from PR state, never from the landing call's own message" rule is
  a direct, first-party-verified response to a real recurring failure mode, not
  precautionary boilerplate.
- HYPOTHESIS: `ci pr merge`'s existing merge-queue sub-verbs are sufficient for D3's
  "merge, then verify from PR state" sequence without additional orchestrator-side
  polling beyond `ci checks wait`; confirm/refute at `ci`'s merge-queue verb behavior
  (does it block until settled, or return immediately with the queue entry still
  pending?) before designing D3's exact call sequence (verify-at-outline).
- Verify-first clause: PLAN-09 may change `git-workflow.py`'s addressing surface (its own
  HYPOTHESIS, D2) before this plan is picked up — re-derive this plan's exact worktree-path
  resolution call against WHATEVER PLAN-09 actually shipped, not against PLAN-09's own
  staged design, at this plan's own outline.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/SKILL.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/tools-integration-ci/**`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/git-workflow.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-locks/**`
- OBSERVED: `test/plan-marshall/plan-orchestrator/**`
- OBSERVED: `test/plan-marshall/tools-integration-ci/**`

## Dependencies and Sequencing

- Depends on: PLAN-09 (strict — the worktree and its resolver routing must exist first).
- Overlaps with: PLAN-07 (`orchestrator.py`'s whole-file structural split, sequenced last in
  the epic — this plan adds real new verbs to the same file, so PLAN-07's line-attribution
  research must be re-derived AFTER this plan lands, exactly as PLAN-07 already states for
  every other plan touching the same file).
- Adjacent to: `manage-locks`' existing merge mutex / FIFO admission queue — D5's
  sequential-vs-parallel decision for `land-all` may end up reusing it rather than building
  a second coordination primitive; not committed to here, flagged for outline.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/orchestrator-refactor/plans/PLAN-10-orchestrator-land-verbs.md"
```

## Write-Boundary

The plan implementing this spec touches only repository source, standards and tests. It
creates and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and
reports its outcome through its PR and its inbox message. The inbox exception's qualifiers
and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
