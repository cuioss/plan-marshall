# PLAN-PR-009: The merge-queue enqueue does not take, and a failed enqueue can reach the forbidden immediate-merge path

epic: review-apparatus
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-marshall-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Provenance — re-issued from `truthful-signals` PLAN-117

Released to this epic on 2026-07-30 (row `transferred` there, verified against its live queue). Under
this epic's `PLAN-PR-NNN` rule **no id travels**: this is a re-issue, not a rename. Carried whole.

## Objective

On a repo whose base branch **requires** a merge queue, and whose config says so correctly at every
layer, a plan's finalize still arrived at `pr safe-merge` — which refused (correctly). Establish why the
enqueue is not taking, and close the path by which a failed enqueue can reach an immediate merge that
`branch-cleanup.md` explicitly forbids.

## ⛔ Read this before scoping: the obvious premise is REFUTED

The originating operator hypothesis was *"make `safe-merge` config-aware about merge queues."*
**That is already implemented and a plan scoped to it would land a no-op.** Verified at HEAD 2026-07-29:

| Layer | Value | Evidence |
|---|---|---|
| Platform | `eligible_configured`, `merge_method: SQUASH`, `externally_managed: true` | `ci repo merge-queue probe` on `main` |
| Project config | `use_merge_queue: true` | `marshal.json` → `plan.phase-6-finalize.steps.default:branch-cleanup` |
| Plan-local snapshot | `use_merge_queue: true` | `manage-execution-manifest step-params get` on a live plan |
| `safe-merge` behaviour | **already refuses** on `eligible_configured` | `tools-integration-ci/standards/pr-operations.md:196` |

A second hypothesis was also **refuted**: that `branch-cleanup.md`'s unprefixed `--step-id branch-cleanup`
would miss the `default:branch-cleanup` key. `cmd_step_params_get` is explicitly **prefix-agnostic** via
`canonicalize_step_key` (`manage-execution-manifest/scripts/_manifest_validation.py:64-77`), so both
forms resolve.

⛔ **Do not re-derive either of these. Do not "fix" `safe-merge`'s probe.** The refusal is the `#866`
guard working as designed.

## The real question

With `use_merge_queue: true`, `branch-cleanup.md:746-751` routes the merge to `ci pr merge-queue` and
**never to `safe-merge`**. `safe-merge` being reached at all means one of:

- **(i)** the enqueue failed and control **fell through** to the immediate-merge path — which
  `branch-cleanup.md:777` explicitly forbids: *"do NOT silently fall back to an immediate merge, since
  the operator opted into queue serialization for a reason"*; or
- **(ii)** the routing branch was not taken despite the param resolving `true`.

**Both are defects. D1 decides which — do not assume.**

## ⛔⛔ ABSORBED 2026-08-03 — the false-green merge is SOURCE-CONFIRMED, and it is now this plan's PRIMARY subject

Two independent first-party reports (`fail-closed-signal-integrity-001` from the plan; `truthful-signals-016`
§1 from that orchestrator, who read `gh pr view --json` from its own checkout) plus **an orchestrator source
read of the implementation**. The filers' hypothesis was marked *"do not action unverified"*. **It is now
confirmed, and the mechanism is worse than either of them stated.**

### OBSERVED — the event

| PR | State | Merged | Head branch |
|---|---|---|---|
| **#1081** | **CLOSED** 2026-08-02T21:15:40Z | **`mergedAt: null`** | `feature/fail-closed-signal-integrity` |
| **#1082** | MERGED 21:47:23Z `b713fe4b9` | yes | **the same branch**, re-pushed |

`ci pr merge --pr-number 1081 --strategy squash --delete-branch` returned `merged: true`,
`branch_deleted: feature/fail-closed-signal-integrity`, `already_gone: false`. The plan verified the
non-merge three ways after three separate fetches (`merge-base --is-ancestor` exit 1; no matching commit
in `origin/main`; tip unmoved at `5c41364a5`). Orchestrator re-verified #1082's state independently.

### ⛔ SOURCE-CONFIRMED — `_github_pr.py` § `cmd_pr_merge` (~:875-920)

```python
gh_args = ['pr', 'merge', identifier, f'--{args.strategy}']       # NOTE: no --delete-branch
returncode, stdout, stderr = github_ops.run_gh(gh_args)
if returncode != 0:
    return make_error(...)
...
if args.delete_branch:
    result['merged'] = True                                        # from the EXIT CODE alone
    ...
    delete_result = cmd_branch_delete(delete_args)                 # separate REST delete
```

**Three distinct defects on these forty lines:**

1. ⛔⛔ **`merged: true` is derived solely from `gh pr merge` exiting 0.** Under a required merge queue
   `gh pr merge --squash` **enqueues** and exits 0. ⇒ **The filers' hypothesis is confirmed at the
   source**: the enqueue acknowledgement is mapped onto `merged: true`. This is systematic under
   `use_merge_queue: true`, not a one-off. ⭐ It also explains the contrast `truthful-signals-016`
   flagged as a narrowing lead — `pr merge-queue` honestly returns `enqueued: true` because it is a
   **different function**. Per-verb mapping, exactly as they guessed.
2. ⭐⭐ **`merged` is set ONLY inside `if args.delete_branch:`** — the success field's very *presence* is
   coupled to an unrelated option. A caller that merges without `--delete-branch` gets **no `merged`
   field at all**, so `result.get('merged')` is `None` on a genuinely successful merge. ⛔ **Second
   defect, opposite polarity** (false negative), found only by reading the source — **neither filer saw
   it, because both observed the `--delete-branch` path.**
3. ⭐ **The assertion precedes the destructive action.** `merged = True` is set, and *then* the branch is
   deleted. The comment above it — *"The merge has already succeeded; we never retry the merge on
   branch-delete failure"* — **asserts the very thing that is not established.** Defending-documentation
   archetype, at the exact site.

⛔ **`cmd_pr_safe_merge` (~:1176-1195) carries the IDENTICAL shape** — `result['merged'] = True` inside
`if args.delete_branch:` after an `--admin` merge. **So this is at least TWO sites, and the standing rule
applies: this list is a SAMPLE. Derive the population** (`workflow-integration-gitlab/scripts/gitlab_ops.py`
also emits `branch_deleted` and is unread).

### ⭐ The leading causal hypothesis — the verb may have MANUFACTURED the failure it misreported

`--delete-branch` is **not** passed to `gh`; the delete is a separate REST call. Deleting a PR's head
branch **closes the PR and removes it from the merge queue**. ⇒ The sequence may be: enqueue succeeds →
code asserts merged → REST-delete removes the head branch → **the queue drops the PR and it closes with
`mergedAt: null`**.

⛔ **If this holds, the verb does not merely misreport a failure — it CAUSES it**, and the report is what
hides the cause. ⚠ **Not confirmed.** The competing sub-hypothesis is that `gh` exited 0 without
enqueuing at all. **Discriminator**: the plan found no `gh-readonly-queue/*` branch — but checked only
*after* the fact, which cannot separate never-enqueued from enqueued-then-dequeued. **Settle at D1 by
issuing an enqueue and observing queue state BEFORE any delete**, not by re-reading #1081.

### ⇒ What this does to the plan

⭐ **The original objective (why the enqueue "isn't taking") and this finding are plausibly ONE defect
seen from two ends** — if the delete dequeues, then "the enqueue does not take" is the *symptom* and this
is the *cause*. **D1 must test that identity explicitly rather than treating them as two workstreams.**

⛔ **Severity is now data-loss, not observability.** The work survived only because the author re-derived
`origin/main` instead of trusting the return value; recovery cost a re-push and a new PR number. A caller
that trusts `merged: true` marks the step done, removes the worktree, and archives the plan as shipped —
**with its work present nowhere on the remote, the branch having just been deleted by the same call.**

⛔ **Downstream contamination, already live**: the originating plan's `kind: landing` message names
**#1081** as where it shipped. Any artifact keyed off that message carries the wrong PR id.
**Stamp PR ids from PR state, never from a landing message.**

## Deliverables

0. ⛔⛔ **PRIMARY — the merge verb's success assertion must be CORROBORATED, not reported.** After the
   provider call: fetch, then assert the head is an ancestor of the base before returning `merged: true`.
   Distinguish **`enqueued`** from **`merged`** in the return vocabulary so a queued merge is not
   indistinguishable from a landed one. ⛔ **Do not delete the branch until the merge is corroborated** —
   and settle first whether the delete is what dequeues it. Decouple `merged` from `--delete-branch`
   (defect 2). Population **derived** across every merge-shaped verb, including `safe_merge` and the
   GitLab provider.

1. **D1 — GATE (mutates nothing): establish the actual path taken, and DERIVE the routing population.**
   Determine whether (i) or (ii) occurred, from the decision/work log of a plan that exhibited it.
   ⛔ **`use_merge_queue` is consumed at FOUR separate decision points** in `branch-cleanup.md` — the
   CI-wait strategy (`:359-394`), the consent-prompt wording (`:530-573`), the merge routing
   (`:746-751`), and the post-merge cleanup. **A mis-route at each produces a DIFFERENT wrong outcome.**
   Enumerate all four and classify each as correct/incorrect at HEAD. Treat the merge-routing site as a
   **sample**, not the finding.
2. **D2 — establish why the enqueue does not take.** The probe reports `externally_managed: true` and
   `merge_method: SQUASH`; `pr_merge_strategy` is `squash`. Determine whether the enqueue is rejected,
   silently no-op'ing, or never issued. ⚠ **A `status: success` with `enqueued: true` that does not
   actually place the PR on the queue is the false-green form of this defect — check the platform state,
   not just the return value.**
   - ⭐ **STRONG LEAD (orchestrator-verified 2026-07-29): a config-vs-platform contradiction on exactly
     this axis.** `marshal.json` → `project.merge_queue_managed_externally` is **`false`**, while
     `ci repo merge-queue probe` returns **`externally_managed: true`**. The project config and the live
     platform disagree about who manages the queue — and *who manages it* plausibly decides whether our
     enqueue is permitted, a no-op, or overridden.
   - ⛔ **Check this FIRST, and do NOT assume it is the cause.** It is a contradiction of the same shape
     as the archetype this project tracks (a hand-maintained mirror of a probeable fact), which makes it
     *attractive* — and **this plan already exists because an attractive hypothesis was wrong.**
     Establish the causal link or discard it explicitly.
   - If it IS causal, the fix direction follows the standing rule: **derive the value from the probe, do
     not mirror it in config** — or, if the knob must stay, reconcile it at set time the way
     `use_merge_queue` already is.
3. **D3 — make the forbidden fallback structurally impossible.** If D1 finds (i), the no-fallback rule is
   prose that did not hold. Enforce it in the mechanism rather than the doc: after a failed enqueue the
   immediate-merge path must be **unreachable**, not merely discouraged.
4. **D4 — a failed enqueue is actionable, not a dead end.** `branch-cleanup.md:777-781` already requires
   the abort message to name BOTH remedies. Verify that message actually fires and reaches the operator,
   and that the mutex is released on that path.
5. **D5 — tests, each verified to FAIL pre-fix.** (a) A failed enqueue does NOT reach `safe-merge`.
   (b) With `use_merge_queue: true`, all four consumption sites take the queue branch. (c) An enqueue
   that returns success but does not place the PR is detected rather than reported as merged.

## Claim Labels

- OBSERVED (orchestrator-verified at HEAD 2026-07-29): all four rows of the refutation table above; the
  `pr-operations.md:196` refusal contract; the prefix-agnostic `step-params` lookup.
- OBSERVED (operator paste): `safe-merge` refused with the required-queue reason on a live plan, and the
  enqueue "isn't taking".
- HYPOTHESIS: the fallback (i) rather than the mis-route (ii) is what occurred — confirm/refute at D1
  against the plan's decision log. **Confirm/refute artifact**: the `branch-cleanup` work-log lines for
  the affected plan.
- HYPOTHESIS: `externally_managed: true` is material to the enqueue failure (verify-at-outline).
- ⚠ Line numbers are OBSERVED at 2026-07-29 HEAD; `branch-cleanup.md` is a hot surface. **Re-ground by
  SYMBOL and section heading, not by line.**

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md`
  (the four `use_merge_queue` sites)
- OBSERVED: `.../tools-integration-ci/scripts/ci_base.py` (`pr merge-queue`, `pr safe-merge`)
- HYPOTHESIS: the GitHub provider's enqueue implementation (verify-at-outline)
- OBSERVED: `test/plan-marshall/tools-integration-ci/**`

## Dependencies and Sequencing

- Depends on: **`truthful-signals` PLAN-115** (`plan-less-pr-can-be-opened-but-never-corrected`,
  **launched** and retained there) — same `tools-integration-ci` pr verb group. ⛔ **Sequence, never
  pair.** That epic will report PLAN-115's landing here; **name that PR when retiring this deferral**
  (see the epic's named-PR deferral convention) rather than relying on memory.
- Overlaps with: ⛔ **PLAN-PR-008** (barrier deadlock) also edits `branch-cleanup.md` and reaches the
  merge path. **Sequence, never pair.**
- Adjacent to: PLAN-PR-005 / PLAN-PR-006 (participation detectors) — a different observable entirely.
  Verify before pairing.
- ⛔ **THE PR NUMBER IS `#1065`, AND IT IS OPEN — DO NOT SEQUENCE OFF A MERGE.** Delivered by
  `truthful-signals-005` (2026-07-30) under the named-PR convention: `feat(ci): add plan-less path to
  pr/issue correction verbs`, branch `feature/plan-less-pr-can-be-opened-but-never-corrected`,
  `state: open`, `mergeable`, `merge_state: unstable`, `review_decision: none`.
  ⚠ **Their plan emitted a `kind: landing` message claiming "PR: #1065" under a "What landed" heading
  while the PR is open** — they caught it by corroborating against `origin/main` and did NOT transition
  the plan to shipped. **Re-derive `#1065`'s state against `origin/main` at your outline**, exactly as
  they did; the note makes the deferral expirable, the re-derivation is what expires it.
- ⛔ **RE-DERIVE THIS PLAN'S COLLISION SURFACE — the ground moved.** Their D1 population derivation found
  the `--plan-id` binding was **not** a `ci`-local asymmetry: ~18 *incidental* consumers across 11 skills
  each re-derived a working tree from a plan id they did not need. What `#1065` ships is therefore much
  wider than the two verbs its request named — a single `resolve_plan_context` resolver plus a `NO_PLAN`
  sentinel in `tools-file-ops`, ~18 migrated consumers plus test mirrors, the pre-existing
  `ci pr create --body-file` outlier absorbed, and a population-derived plugin-doctor check
  (`_analyze_plan_path_in_scripts.py`, including a Form C resolver-bypass detector).
  ⚠ **If this plan touches the `pr` verb group's argument handling, re-derive against what `#1065`
  actually shipped, NOT against its request's framing.**
- ⚠ **`PLAN-115` KEEPS its id** (it is launched, so it was not renamed in the sibling's 2026-07-30
  `PLAN-TRUTH-{NNN}` re-issue) — this plan's deferral may keep naming it, and that epic will send its
  **PR number** when it opens, not merely word that it landed. ⛔ Still re-derive it against their live
  queue at drain time: the note makes the deferral expirable, the re-derivation is what expires it.
- Adjacent to: `truthful-signals` **PLAN-TRUTH-006** (ex-`PLAN-52`,
  `baseline-reconcile-persists-merge-commit`, retained there as
  a git-mutation-contract defect, not a review defect) — same finalize bundle, different file.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/review-apparatus/plans/PLAN-PR-009-merge-queue-enqueue-does-not-take.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/local/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
