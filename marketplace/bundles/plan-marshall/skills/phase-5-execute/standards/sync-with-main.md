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

4. **Drift contract** — exit code non-zero means upstream has new commits the worktree does not contain:

   - Capture divergent commits via `git -C {worktree_path} log --oneline HEAD..origin/{base_branch}`.
   - Log at ERROR with the divergent commits and the documented redirect: re-run `phase-2-refine` to absorb the upstream changes via Step 3d.
   - ABORT the phase. Do NOT enter the task loop. Do NOT auto-merge. Do NOT auto-rebase.

The drift-error message MUST name `phase-2-refine` Step 3d as the redirect — this is load-bearing operational guidance, because users who see "baseline drift" without the redirect default to running ad-hoc git merges that bypass the iterate-to-confidence loop.

## Drift Semantics

| Scenario | Detection | Action |
|----------|-----------|--------|
| Worktree HEAD already contains `origin/{base_branch}` (refine reconciled, no upstream movement since) | `merge-base --is-ancestor` exit `0` | Fast-path: log INFO, continue to Step 4 |
| Worktree HEAD is BEHIND `origin/{base_branch}` (upstream commits landed after refine) | `merge-base --is-ancestor` exit non-zero | Drift: log ERROR with divergent commits + redirect, abort phase |
| Worktree HEAD is AHEAD of `origin/{base_branch}` AND contains the upstream tip | `merge-base --is-ancestor` exit `0` | Fast-path: log INFO, continue to Step 4 |
| Worktree HEAD is AHEAD of `origin/{base_branch}` BUT does NOT contain the upstream tip (parallel divergence) | `merge-base --is-ancestor` exit non-zero | Drift: log ERROR, abort — phase-2-refine reconciliation required |
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

- **Do NOT add merge/rebase logic back to phase-5-execute Step 3.** The split is structural; reverting it re-creates the original failure mode.
- **Do NOT auto-resolve conflicts in phase-5-execute.** The drift contract is fail-loud by design — silent reconciliation hides what should be an explicit refine-time decision.
- **Do NOT remove the redirect to `phase-2-refine` Step 3d from the drift error message.** The redirect is load-bearing; without it, users default to ad-hoc git workflows that bypass the iterate-to-confidence loop.

## Cross-References

- [`phase-2-refine/standards/refine-workflow-detail.md` § Step 3d](../../phase-2-refine/standards/refine-workflow-detail.md#step-3d-baseline-reconciliation) — authoritative substantive reconciliation procedure
- [`phase-6-finalize/standards/pre-push-quality-gate.md`](../../phase-6-finalize/standards/pre-push-quality-gate.md) and finalize's `pr update-branch` — second-line safety net for long-running execute runs
- Driving lesson: aggregate `2026-05-04-20-002` Sub-task I (move pre-execute baseline reconciliation into phase-2-refine)
