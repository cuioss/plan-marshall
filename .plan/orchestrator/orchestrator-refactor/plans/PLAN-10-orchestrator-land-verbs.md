# PLAN-10: `land` and `land-all` — monitored, never-remove ledger landing

> ✅ **RE-STAGED 2026-09-26 by explicit operator decision** — exempted from the PM-MCP supersession that parked
> the rest of this epic's queue the same day. **RE-SCOPED the same day, operator direction: ONE fixed worktree
> for ALL epic changes**, replacing the earlier one-worktree-per-epic design. Objective, Deliverables and
> Non-Goals below are rewritten for that; Claim Labels are unchanged research (their per-epic phrasing is
> historical). Implementation-independent content is also carried in
> `plan-marshall-mcp/doc/known-defects/orchestrator-refactor-carry-over.md`.

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

PLAN-09 gives ALL epics one shared, long-lived worktree on a fixed branch; this plan gives the orchestrator the
verb to LAND that worktree's pending ledger changes onto `main` in a controlled, monitored way — replacing
today's ad hoc `git commit`/`git push`. Because every epic writes into the same worktree, one `land` lands
everything pending there in ONE PR: create-or-reuse the PR, wait for CI via the bounded `ci checks wait`
primitive, merge through the queue, confirm the merge from the PR's own state, and resync both `main` and the
worktree — never deleting the worktree (the constraint the operator stated twice). The earlier per-epic
`land-all` sweep and its concurrent-PRs-into-one-merge-queue collision disappear with the shared worktree.

## Deliverables

1. **D1 — `land`: snapshot, commit, push, serialized.** In the shared worktree, stage and commit ONLY
   orchestrator ledger paths (`.plan/orchestrator/**`, `.plan/archived-orchestrators/**`, minus the git-ignored
   `logs/`) — never anything else a stray process left there — and push the fixed branch. Several epic sessions
   can call `land` concurrently and all touch one git index, so `land` holds a repository-wide lock for its git
   steps (reuse `manage-locks` rather than a second primitive; decide the exact lock at outline). A second
   caller either waits or finds the open PR and returns it — never commits over a land in progress.
2. **D2 — PR create-or-update with an epic-native title/body.** Call the `ci` PR primitives directly with
   `--project-dir {worktree_path}` (not `phase-6-finalize`'s plan-bound `create-pr` doc). **Re-scoped at cleanup
   2026-09-29:** `--project-dir` is a ROUTER flag and replaces only the router-level `--plan-id`; the body-consumer
   verbs `pr prepare-body` / `pr create` each REQUIRE their own `--plan-id` bound to the body file — pass the
   `NO_PLAN` sentinel (accepted by the provider) and `--head` naming the fixed ledger branch. Reuse the open PR for
   the branch on a repeat `land` rather than opening a duplicate. Title/body are composed from the landed diff
   itself: which epics changed, and per epic which ledger files (rows, specs, anchor, landings, inbox) — no
   plan-only source (`pr_title`, `request.md`) exists for a ledger landing.
3. **D3 — monitor WITH an explicit post-enqueue settle loop.** Wait for CI via `ci checks wait --pr-number N
   --project-dir {worktree_path}` (bounded; `status: timeout` means re-poll on re-entry, never a foreground busy
   loop). On green, `ci pr merge-queue` enqueues and returns after a single membership read
   (`workflow-integration-github/scripts/_github_pr.py` `cmd_pr_merge_queue`, :2469 at cleanup 2026-09-29) — it
   never settles, and `enqueued` is THREE-valued: `true`, or `indeterminate` with a reason (e.g.
   `auto_merge_armed_awaiting_checks`); both mean "not merged yet". Poll `ci pr view --pr-number N` until a terminal
   state — NOT `ci pr landing-state`, which is keyed on the branch tip, and the queue deletes the head branch — and
   stamp the landed PR only from the PR's own state then, never from the merge call's return
   (incident `project_ci_pr_merge_false_green`: `merged: true` with the branch deleted and nothing merged).
4. **D4 — resync main and the worktree without losing post-snapshot writes.** On confirmed merge, fast-forward
   the primary checkout's `main`, and bring the worktree's branch onto the new `main`. Other epic sessions may
   have written into the worktree AFTER D1's snapshot, so the resync MUST NOT discard them — a blind `reset
   --hard origin/main` is forbidden; choose a mechanism that carries uncommitted and not-yet-landed committed
   changes across (e.g. stash-and-reapply, or rebase that drops the squash-merged commits) and decide it at
   outline, stating its failure mode. The worktree directory persists either way. The merge queue DELETES the
   remote head branch on merge, so the fixed long-lived ledger branch must be re-created on the remote (or pushed
   fresh) on the next `land`, never assumed to still exist.
5. **D5 — failure/timeout leaves the worktree recoverable.** CI failure, merge-queue ejection or a wait timeout
   is reported and the land attempt stops there; the worktree's uncommitted or committed-but-unlanded state is
   left exactly as it was, and the lock released, so a re-invoked `land` resumes.

6. **D6 — harden the PLAN-09 worktree `land` relies on (folded from the PLAN-09 landing, #1652).** Two residues
   of PLAN-09 sit directly on `land`'s path: (a) an already-registered `_orchestrator` worktree is reused without
   verifying it is checked out on the ledger branch (CodeRabbit, filtered as noise at #1652) — `land` must refuse
   to commit from a worktree on any other branch, naming what it found; (b) `worktree-remove --plan-id
   _orchestrator` is refused only incidentally by the move-back guard (`plan_dir_not_moved_back`) — add the same
   dedicated reserved-key refusal the `worktree-create` guard already has, so "never removed by normal operation"
   is enforced rather than accidental.

## Non-Goals

- No change to review-bot participation — `.plan/**` is already excluded from CodeRabbit/PR-Agent review
  org-wide, and `skip-on-docs-only` fast-paths a non-buildable ledger-only diff. `land` relies on both and must
  NOT route through the plan pre-merge barrier (it requires bot participation a ledger PR never gets).
- No worktree teardown/removal (PLAN-09 D3).
- No change to `phase-6-finalize`'s create-pr / branch-cleanup docs.
- No per-epic `land-all` sweep — superseded by the one-shared-worktree direction (2026-09-26).

## Claim Labels

- OBSERVED: `phase-6-finalize/workflow/create-pr.md` reads PR title from `manage-status
  metadata --plan-id --get --field pr_title` and PR body from `manage-plan-documents
  request read --plan-id --section clarified_request`, and gates completion via
  `manage-status mark-step-done --plan-id --phase 6-finalize --step create-pr` — all three
  plan-only surfaces an orchestrator epic does not have (no `request.md`, no execution
  manifest). This workflow doc is confirmed NOT reusable as-is from an orchestrator
  context.
  - verdict: corroborated | checked_at: fa7b517742567f1d271e3f3562a61e6daa40f3f0 | by: orchestrator-refactor/cleanup | rescoped: n/a | evidence: Re-grounded at fa7b51774: create-pr.md still plan-bound (clarified_request :82-83, pr_title metadata :259-260, mark-step-done :383/:392).
- OBSERVED: `tools-integration-ci:ci`'s PR primitives (`pr create/view/prepare-body`)
  support `--project-dir {path}` as an alternative to `--plan-id` throughout
  (`create-pr.md:33,65,115,283` cites the pattern even though that doc itself is
  plan-bound) — the PRIMITIVE layer is provider-agnostic and not plan-coupled, confirming
  D2's approach of calling it directly.
  - verdict: contradicted | checked_at: fa7b517742567f1d271e3f3562a61e6daa40f3f0 | by: orchestrator-refactor/cleanup | rescoped: yes | evidence: At fa7b51774: --project-dir is a ROUTER flag replacing only the router --plan-id (ci_base.py:670-706); body-consumer verbs pr create / pr prepare-body carry their own REQUIRED --plan-id bound to the body file (BODY_CONSUMER_VERBS ci_base.py:378-380). D2 re-scoped: pass --plan-id NO_PLAN (accepted, _github_pr.py:849) and --head on the ledger branch.
- OBSERVED: `tools-integration-ci:ci checks wait` is a bounded, self-timing-out primitive —
  `standards/blocking-wait-pattern.md` and `ci_complete_precondition.py:152-239` show a
  `--timeout` ceiling with harness-bash-ceiling-aware clamping and a `status: timeout`
  return meaning "re-poll on re-entry", matching this project's "never foreground-poll,
  always arm a waiter" convention (`feedback_no_shell_polling_loops`). `ci pr` additionally
  carries `merge-queue`/`merge`/`auto-merge`/`safe-merge`/`update-branch` sub-verbs.
  - verdict: corroborated | checked_at: fa7b517742567f1d271e3f3562a61e6daa40f3f0 | by: orchestrator-refactor/cleanup | rescoped: n/a | evidence: At fa7b51774: ci checks wait bounded (--timeout default 600, --interval 30). The harness-ceiling clamp (ci_complete_precondition.py:159-275) belongs to phase-6's resolver only; a direct call from land gets just its own --timeout.
- OBSERVED: `orchestrator corpus epics` (no `--slug`) enumerates every epic slug across
  BOTH `.plan/orchestrator/` and `.plan/archived-orchestrators/`, partitioned
  `active[]`/`archived[]`, with per-root `exists`/`listed`/`entries_scanned`/`error`
  accounting — the correct, already-used-this-session substrate for D5's sweep.
  - verdict: corroborated | checked_at: fa7b517742567f1d271e3f3562a61e6daa40f3f0 | by: orchestrator-refactor/cleanup | rescoped: n/a | evidence: At fa7b51774: cmd_corpus_epics (orchestrator.py:3748-3797) returns active/archived with per-root accounting. Inert since the re-scope dropped land-all (D5 is now failure recovery); no body change.
- OBSERVED: this epic's own memory records an incident (`project_ci_pr_merge_false_green`)
  where `ci pr merge` returned `merged: true` and deleted the branch WITHOUT actually
  merging — D3's "stamp from PR state, never from the landing call's own message" rule is
  a direct, first-party-verified response to a real recurring failure mode, not
  precautionary boilerplate.
  - verdict: corroborated | checked_at: fa7b517742567f1d271e3f3562a61e6daa40f3f0 | by: orchestrator-refactor/cleanup | rescoped: n/a | evidence: Incident real (#1081 merged:true, never merged) but its root cause (off-routing dispatch) was fixed in #1087 (ca7cf9bd4); 'recurring' overstated. The stamp-from-PR-state rule still holds; ci pr view --pr-number now exists for it.
- HYPOTHESIS: `ci pr merge`'s existing merge-queue sub-verbs are sufficient for D3's
  "merge, then verify from PR state" sequence without additional orchestrator-side
  polling beyond `ci checks wait`; confirm/refute at `ci`'s merge-queue verb behavior
  (does it block until settled, or return immediately with the queue entry still
  pending?) before designing D3's exact call sequence (verify-at-outline).
  - verdict: contradicted | checked_at: fa7b517742567f1d271e3f3562a61e6daa40f3f0 | by: orchestrator-refactor/cleanup | rescoped: yes | evidence: At fa7b51774: cmd_pr_merge_queue now _github_pr.py:2469-2573, returns after one membership read, never settles; enqueued is three-valued (true / indeterminate with reason e.g. auto_merge_armed_awaiting_checks). pr landing-state is branch-keyed and the queue deletes the head branch, so the settle poll must use ci pr view --pr-number. D3/D4 re-scoped.
- Verify-first clause: PLAN-09 may change `git-workflow.py`'s addressing surface (its own
  HYPOTHESIS, D2) before this plan is picked up — re-derive this plan's exact worktree-path
  resolution call against WHATEVER PLAN-09 actually shipped, not against PLAN-09's own
  staged design, at this plan's own outline.
  - verdict: corroborated | checked_at: fa7b517742567f1d271e3f3562a61e6daa40f3f0 | by: orchestrator-refactor/cleanup | rescoped: n/a | evidence: PLAN-09 shipped 438a0a71f. Addressing via orchestrator_worktree_path()/ensure_orchestrator_worktree() and orchestrator resolve-path (store_checkout). D6 premises hold: reuse without branch check (orchestrator_worktree.py:324-325); cmd_worktree_remove (:2000) lacks a reserved-key check. LEDGER_PATHSPECS (:54) reusable for D1.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/SKILL.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/tools-integration-ci/**` (now a thin
  provider router — the PR merge-queue implementation itself lives at
  `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py`,
  re-verified at cleanup 2026-09-24 after an intervening provider-split refactor relocated it)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/git-workflow.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-locks/**`
- OBSERVED: `test/plan-marshall/plan-orchestrator/**`
- OBSERVED: `test/plan-marshall/tools-integration-ci/**`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/tools-file-ops/scripts/orchestrator_worktree.py` — D6(a), added by the PLAN-09 landing fold
- OBSERVED: `test/plan-marshall/workflow-integration-git/**` — D6(b)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py` — D3 (the merge-queue return this plan reads; added at cleanup 2026-09-29)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/workflow/**` — the new `land` verb's workflow doc
- OBSERVED: `marketplace/bundles/plan-marshall/skills/persona-plan-orchestrator/standards/orchestration-model.md` — the ledger landing model `land` changes
- OBSERVED: `test/plan-marshall/tools-file-ops/**` — D6(a)'s `orchestrator_worktree.py` tests
- HYPOTHESIS: `test/plan-marshall/manage-locks/**` — only if D1 extends `manage-locks` rather than consuming it (decided at outline)

## Dependencies and Sequencing

- Depends on: PLAN-09 (strict — the worktree and its resolver routing must exist first).
- Overlaps with: PLAN-07 (`orchestrator.py`'s whole-file structural split, sequenced last in
  the epic — this plan adds real new verbs to the same file, so PLAN-07's line-attribution
  research must be re-derived AFTER this plan lands, exactly as PLAN-07 already states for
  every other plan touching the same file).
- Adjacent to: `manage-locks` — D1's repository-wide land lock reuses it rather than building a second
  coordination primitive; the exact lock is decided at outline.
- Overlaps with: PLAN-11 (`orchestrator.py`, `test/plan-marshall/plan-orchestrator/**`) — sequence.

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
