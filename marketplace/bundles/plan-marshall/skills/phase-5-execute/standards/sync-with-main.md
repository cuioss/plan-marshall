---
description: Authoritative reference for phase-5-execute Step 3 baseline fast-path check
---

# Sync Worktree With Main — Fast-Path Verification

Authoritative reference for the `phase-5-execute` Step 3 "Baseline Fast-Path Check" action. The SKILL.md inlines the step flow; this document explains the fast-path semantics, the drift error contract, the main-checkout fallback, and the rationale for the phase-2-refine ↔ phase-5-execute split.

**Scope note**: This step is a worktree-hygiene action that always runs (no opt-out). It is NOT part of the manifest-driven verification-step selection in `phase_5.verification_steps` from `manage-execution-manifest`.

## Authoritative Reconciliation Lives in phase-2-refine

Substantive baseline reconciliation — pulling upstream commits, surfacing overlapping diffs against the request narrative, and absorbing baseline shifts via the iterate-to-confidence loop — happens at refine time. See [`phase-2-refine/standards/refine-workflow-detail.md` § Step 3d](../../phase-2-refine/standards/refine-workflow-detail.md#step-3d-baseline-reconciliation) for the canonical procedure.

Phase-5-execute Step 3 does NOT perform substantive reconciliation:

- No `git merge`.
- No `git rebase`.
- No conflict-resolution prompts.
- No worktree mutation beyond `git fetch`.

It is strictly a "still clean?" verification gate. The split is structural: refine-time reconciliation is cheap (the request can be re-authored on the new baseline), execute-time reconciliation is expensive (outline + plan + tasks have already locked intent).

Step 3 does, however, **self-absorb the zero-overlap case** — when upstream commits have landed but `baseline-reconcile` reports `conflict_count == 0`, phase-5-execute updates the persisted baseline metadata in place and continues the task loop without dispatching back to refine. The Self-absorption contract below documents the exact mechanics; the contract is bounded so that non-zero overlap still flows through the standard refine re-cycle.

## Purpose

Catch the recurring failure mode where a long-running execute phase is interrupted by upstream merges that landed AFTER the refine baseline-reconciliation pass completed. Without this gate, execute could run against a stale base and surface conflicts at finalize-time (after the entire execute loop has already burned tokens). With this gate, execute aborts immediately and redirects the user back to phase-2-refine, where the iterate-to-confidence loop is the documented absorption path.

## Inputs

| Source | Field | Purpose |
|--------|-------|---------|
| `references.json` (via `manage-files read`) | `base_branch` | The branch to fetch and compare against. Set at `phase-1-init` Step 6. |
| `references.json` (via `manage-files read`) | `worktree_path` | Target of every `git -C` invocation. Absent when the plan runs against the main checkout. |

## Procedure

1. **Resolve base branch and worktree path** from `references.json`. Substitute `.` for `{worktree_path}` when the field is absent (main-checkout fallback — see § Main-Checkout Fallback below).

2. **Fetch base** (read-only network round-trip):

   ```
   git -C {worktree_path} fetch origin {base_branch}
   ```

3. **Fast-path check** — verify the current branch tip already contains `origin/{base_branch}`:

   ```
   git -C {worktree_path} merge-base --is-ancestor origin/{base_branch} HEAD
   ```

   Exit code `0`: up to date. Log `[STATUS] Baseline fast-path: worktree already up to date with origin/{base_branch}` at INFO and continue to Step 4.

4. **Drift detected** — exit code non-zero means upstream has new commits the worktree does not contain. Capture divergent commits via `git -C {worktree_path} log --oneline HEAD..origin/{base_branch}`, then invoke `baseline-reconcile` with `--no-emit` to obtain a deterministic overlap predicate:

   ```
   python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow \
     baseline-reconcile --plan-id {plan_id} --no-emit
   ```

   Parse `conflict_count`, `upstream_commit_count`, and `upstream_commits` from the returned TOON.

5. **Self-absorb (`conflict_count == 0`)** — the upstream commits touch a disjoint set of files from the worktree's in-flight changes. Phase-5-execute absorbs the new baseline metadata in place and continues the task loop (see § Self-absorption contract below). No abort, no return to orchestrator, no refine re-dispatch.

6. **Drift abort (`conflict_count > 0`)** — the upstream commits touch files that overlap with the worktree's in-flight changes. Phase-5-execute returns the structured drift TOON for the orchestrator to act on:

   ```toon
   status: error
   error_type: baseline_drift
   divergent_commits: {divergent_commits}
   upstream_commit_count: {upstream_commit_count}
   conflict_count: {conflict_count}
   display_detail: "baseline drift: {upstream_commit_count} upstream commits"
   ```

   The orchestrator's drift-recovery branch (`plan-marshall/workflow/execution.md` § "Baseline drift recovery (non-zero overlap)") re-dispatches phase-2-refine via the standard envelope, where the iterate-to-confidence loop absorbs the overlap. ABORT the phase. Do NOT enter the task loop. Do NOT auto-merge. Do NOT auto-rebase.

The structured drift TOON is load-bearing — it is the orchestrator's signal to invoke the drift-recovery branch. Returning a generic `status: error` without the `error_type: baseline_drift` discriminator causes the orchestrator to treat the failure as a generic agent error instead of a recoverable baseline drift.

## Self-absorption contract

When `baseline-reconcile` returns `conflict_count == 0`, phase-5-execute performs a metadata-only absorption of the upstream commits and continues its task loop. The contract is:

**Metadata writes** — one fused `manage-status metadata --set` call writes both keys at once:

- `worktree_sha` — the current `HEAD` sha of the worktree (the in-flight feature branch tip). Captured via `git -C {worktree_path} rev-parse HEAD`.
- `main_sha` — the resolved `origin/{base_branch}` sha (the upstream tip that is being absorbed). Captured via `git -C {worktree_path} rev-parse origin/{base_branch}`.

**Decision-log entry** — exactly one `decision` log line, naming the absorbed commits:

```
(plan-marshall:phase-5-execute:self-absorb) Absorbed {upstream_commit_count} upstream commits with zero overlap: {divergent_commits}
```

**Work-log status line** — one `[STATUS]` work-log line for grep-ability:

```
[STATUS] (plan-marshall:phase-5-execute) Self-absorbed zero-overlap drift: {upstream_commit_count} commits, new main_sha={main_sha}
```

**Steps explicitly skipped** — self-absorption is metadata-only. None of the following fire:

- No `git merge`, `git rebase`, `git pull`, or any other working-tree mutation.
- No dispatch back to the orchestrator. The phase-5-execute envelope continues uninterrupted.
- No re-entry into phase-2-refine. The request narrative, solution outline, task list, and confidence score remain valid because zero-overlap upstream commits, by definition, touch no files the plan reasons about.
- No architecture reload — the codebase inventory for the plan's surface is unchanged.
- No source-premise verification — the premises that drove the original refine cycle still hold.
- No Q-Gate re-execution — Q-Gate findings are tied to the refine baseline, not the upstream tip.

**Rationale**: zero-overlap upstream commits, by construction, modify files disjoint from the worktree's in-flight changes. The plan's outline + tasks reasoned about a specific surface; commits outside that surface cannot invalidate any reasoning. The only loose end is the persisted baseline metadata, which the metadata writes above repair. Re-running refine would burn ~135k tokens to reach the same conclusion the deterministic `conflict_count == 0` predicate already established.

**Boundary** — self-absorption applies ONLY when `conflict_count == 0`. Any non-zero conflict count means at least one file is touched by both the upstream and the worktree, and the only safe absorption path is refine's iterate-to-confidence loop. Phase-5-execute MUST NOT attempt to "partially absorb" non-zero overlap — the boundary is sharp on purpose.

## Drift Semantics

| Scenario | Detection | Action |
|----------|-----------|--------|
| Worktree HEAD already contains `origin/{base_branch}` (refine reconciled, no upstream movement since) | `merge-base --is-ancestor` exit `0` | Fast-path: log INFO, continue to Step 4 |
| Drift detected, `baseline-reconcile` reports `conflict_count == 0` (zero-overlap upstream commits) | `merge-base --is-ancestor` exit non-zero AND `conflict_count == 0` | Self-absorb: write `worktree_sha`/`main_sha`, emit decision-log entry, continue task loop |
| Drift detected, `baseline-reconcile` reports `conflict_count > 0` (non-zero-overlap upstream commits) | `merge-base --is-ancestor` exit non-zero AND `conflict_count > 0` | Drift abort: return structured drift TOON; orchestrator re-dispatches phase-2-refine |
| Worktree HEAD is AHEAD of `origin/{base_branch}` AND contains the upstream tip | `merge-base --is-ancestor` exit `0` | Fast-path: log INFO, continue to Step 4 |
| Worktree HEAD is AHEAD of `origin/{base_branch}` BUT does NOT contain the upstream tip (parallel divergence) | `merge-base --is-ancestor` exit non-zero | Branch on `conflict_count` per the two drift rows above |
| `git fetch` fails (network, auth) | Non-zero exit | Log WARNING, continue to Step 4 — do not block on transient infrastructure issues |

## Main-Checkout Fallback

When `metadata.use_worktree == false` and `references.json` has no `worktree_path`, the plan runs against the main checkout. The fast-path check still runs (substituting `.` for `{worktree_path}`), but git fetch on the user's working directory is invasive — log INFO and skip the drift-error abort path. The user is responsible for keeping the main checkout up to date; the gate's role in main-checkout flow is informational only.

## Rationale (Why the Split)

Before this split, phase-5-execute Step 3 attempted substantive reconciliation: `git merge --no-edit origin/{base_branch}` or `git rebase origin/{base_branch}` based on `rebase_strategy` config. The flow worked when the upstream changes were unrelated to the plan's surface. It failed badly when upstream changes overlapped:

- Merge conflicts at the start of execute → user resolves manually → resolution diverges from what the plan would have authored against the new baseline.
- Outline/tasks were authored against a stale snapshot → execute now runs against a different baseline than the one the planner reasoned about.
- The loop is in the wrong phase: re-authoring at execute-time is much more expensive than re-authoring at refine-time.

The split moves substantive reconciliation back to where the loop already exists. Refine's Step 8-12 iterate-to-confidence loop absorbs baseline shifts cheaply. Phase-5-execute Step 3 becomes a fast-path complement that ensures execute starts only against an already-reconciled baseline.

## Anti-Patterns (Prohibited)

- **Do NOT add merge/rebase logic back to phase-5-execute Step 3.** The split is structural; reverting it re-creates the original failure mode. Self-absorption is metadata-only — there is no working-tree mutation, ever.
- **Do NOT self-absorb when `conflict_count > 0`.** The structured drift TOON is the only safe path for non-zero overlap. Self-absorbing non-zero-overlap drift would silently keep the worktree on a stale baseline while the upstream commits touch files the plan reasons about.
- **Do NOT auto-resolve conflicts in phase-5-execute.** The drift contract is fail-loud by design for non-zero overlap — silent reconciliation hides what should be an explicit refine-time decision.
- **Do NOT skip the `baseline-reconcile --no-emit` invocation on drift detection.** `merge-base --is-ancestor` alone tells you that drift exists but not whether it overlaps with the worktree's surface. The deterministic `conflict_count` predicate is what makes the self-absorb branch safe.

## Cross-References

- [`phase-2-refine/standards/refine-workflow-detail.md` § Step 3d](../../phase-2-refine/standards/refine-workflow-detail.md#step-3d-baseline-reconciliation) — authoritative substantive reconciliation procedure
- [`phase-6-finalize/standards/branch-cleanup.md` § Rebase Branch onto Base](../../phase-6-finalize/standards/branch-cleanup.md#rebase-branch-onto-base) — unconditional pre-merge rebase onto `origin/{base_branch}`; the authoritative actor for the rebase that this fast-path gate refuses to perform
- Driving lesson: aggregate `2026-05-04-20-002` Sub-task I (move pre-execute baseline reconciliation into phase-2-refine)
