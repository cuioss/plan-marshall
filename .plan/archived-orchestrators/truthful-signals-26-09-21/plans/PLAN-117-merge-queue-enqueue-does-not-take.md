# PLAN-117: The merge-queue enqueue does not take, and a failed enqueue can reach the forbidden immediate-merge path

epic: truthful-signals
workstream: WS-01

## Objective

On a repo whose base branch **requires** a merge queue, and whose config says so correctly at every
layer, a plan's finalize still arrived at `pr safe-merge` — which refused (correctly). Establish why
the enqueue is not taking, and close the path by which a failed enqueue can reach an immediate merge
that `branch-cleanup.md` explicitly forbids.

## ⛔ Read this before scoping: the obvious premise is REFUTED

The originating operator hypothesis was *"make `safe-merge` config-aware about merge queues."*
**That is already implemented and a plan scoped to it would land a no-op.** Verified at HEAD
2026-07-29:

| Layer | Value | Evidence |
|---|---|---|
| Platform | `eligible_configured`, `merge_method: SQUASH`, `externally_managed: true` | `ci repo merge-queue probe` on `main` |
| Project config | `use_merge_queue: true` | `marshal.json` → `plan.phase-6-finalize.steps.default:branch-cleanup` |
| Plan-local snapshot | `use_merge_queue: true` | `manage-execution-manifest step-params get` on a live plan |
| `safe-merge` behaviour | **already refuses** on `eligible_configured` | `tools-integration-ci/standards/pr-operations.md:196` |

A second hypothesis was also **refuted**: that `branch-cleanup.md`'s unprefixed
`--step-id branch-cleanup` would miss the `default:branch-cleanup` key. `cmd_step_params_get` is
explicitly **prefix-agnostic** via `canonicalize_step_key`
(`manage-execution-manifest/scripts/_manifest_validation.py:64-77`), so both forms resolve.

⛔ **Do not re-derive either of these. Do not "fix" `safe-merge`'s probe.** The refusal is the #866
guard working as designed.

## The real question

With `use_merge_queue: true`, `branch-cleanup.md:746-751` routes the merge to `ci pr merge-queue`
and **never to `safe-merge`**. `safe-merge` being reached at all means one of:

- **(i)** the enqueue failed and control **fell through** to the immediate-merge path — which
  `branch-cleanup.md:777` explicitly forbids: *"do NOT silently fall back to an immediate merge,
  since the operator opted into queue serialization for a reason"*; or
- **(ii)** the routing branch was not taken despite the param resolving `true`.

**Both are defects. D1 decides which — do not assume.**

## Deliverables

1. **D1 — GATE (mutates nothing): establish the actual path taken, and DERIVE the routing
   population.** Determine whether (i) or (ii) occurred, from the decision/work log of a plan that
   exhibited it. ⛔ **`use_merge_queue` is consumed at FOUR separate decision points** in
   `branch-cleanup.md` — the CI-wait strategy (`:359-394`), the consent-prompt wording (`:530-573`),
   the merge routing (`:746-751`), and the post-merge cleanup. **A mis-route at each produces a
   DIFFERENT wrong outcome.** Enumerate all four and classify each as correct/incorrect at HEAD.
   Treat the merge-routing site as a **sample**, not the finding.
2. **D2 — establish why the enqueue does not take.** The probe reports `externally_managed: true` and
   `merge_method: SQUASH`; `pr_merge_strategy` is `squash`. Determine whether the enqueue is
   rejected, silently no-op'ing, or never issued. ⚠ **A `status: success` with `enqueued: true` that
   does not actually place the PR on the queue is the false-green form of this defect — check the
   platform state, not just the return value.**
   - ⭐ **STRONG LEAD (orchestrator-verified 2026-07-29): a config-vs-platform contradiction on
     exactly this axis.** `marshal.json` → `project.merge_queue_managed_externally` is **`false`**,
     while `ci repo merge-queue probe` returns **`externally_managed: true`**. The project config and
     the live platform disagree about who manages the queue — and *who manages it* plausibly decides
     whether our enqueue is permitted, a no-op, or overridden.
   - ⛔ **Check this FIRST, and do NOT assume it is the cause.** It is a contradiction of the same
     shape as the archetype this epic tracks (a hand-maintained mirror of a probeable fact), which
     makes it *attractive* — and this plan already exists because an attractive hypothesis was wrong.
     **Establish the causal link or discard it explicitly.**
   - If it IS causal, the fix direction follows the epic's standing rule: **derive the value from the
     probe, do not mirror it in config** — or, if the knob must stay, reconcile it at set time the
     way `use_merge_queue` already is.
3. **D3 — make the forbidden fallback structurally impossible.** If D1 finds (i), the no-fallback
   rule is prose that did not hold. Enforce it in the mechanism rather than the doc: after a failed
   enqueue the immediate-merge path must be **unreachable**, not merely discouraged.
4. **D4 — a failed enqueue is actionable, not a dead end.** `branch-cleanup.md:777-781` already
   requires the abort message to name BOTH remedies. Verify that message actually fires and reaches
   the operator, and that the mutex is released on that path.
5. **D5 — tests, each verified to FAIL pre-fix.** (a) A failed enqueue does NOT reach `safe-merge`.
   (b) With `use_merge_queue: true`, all four consumption sites take the queue branch. (c) An enqueue
   that returns success but does not place the PR is detected rather than reported as merged.

## Claim Labels

- OBSERVED (orchestrator-verified at HEAD 2026-07-29): all four rows of the refutation table above;
  the `pr-operations.md:196` refusal contract; the prefix-agnostic `step-params` lookup.
- OBSERVED (operator paste): `safe-merge` refused with the required-queue reason on a live plan, and
  the enqueue "isn't taking".
- HYPOTHESIS: the fallback (i) rather than the mis-route (ii) is what occurred — **confirm/refute at
  D1** against the plan's decision log. **Confirm/refute artifact**: the `branch-cleanup` work-log
  lines for the affected plan.
- HYPOTHESIS: `externally_managed: true` is material to the enqueue failure (verify-at-outline).
- ⚠ Line numbers are OBSERVED at 2026-07-29 HEAD; `branch-cleanup.md` is a hot surface.
  **Re-ground by SYMBOL and section heading, not by line.**

## Expected Surface

- OBSERVED: `phase-6-finalize/standards/branch-cleanup.md` (the four `use_merge_queue` sites)
- OBSERVED: `tools-integration-ci/scripts/ci_base.py` (`pr merge-queue`, `pr safe-merge`)
- HYPOTHESIS: the GitHub provider's enqueue implementation (verify-at-outline)
- OBSERVED: `test/plan-marshall/tools-integration-ci/**`

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: ⛔ **PLAN-115** (`tools-integration-ci` pr verbs, **LAUNCHED**) — same verb group.
  **Sequence, never pair.** ⛔ **PLAN-112** (**LAUNCHED**) is finalize gating. ⚠ **PLAN-119** (barrier
  deadlock) also edits `branch-cleanup.md` — **sequence against it**; they are adjacent and both
  reach the merge path.
- Adjacent to: PLAN-116 (participation detectors) — different observable, verify before pairing.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-117-merge-queue-enqueue-does-not-take.md"
```

## Write-Boundary

This plan MUST NOT create or edit any file under `.plan/local/orchestrator/`. Its only channels back
to the epic are its PR and its `inbox/` OUTBOX.
