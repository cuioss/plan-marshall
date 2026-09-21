# Landing: PLAN-93 — inbox sequence reuse collides with the archive

plan: PLAN-93 · plan_id: `inbox-sequence-reuse-collides-with-the-archive` · PR **#1034**
merged: `89fd4d1f6` · 2/2 deliverables · 22/22 finalize steps

## Deliverable fidelity

Both shipped as specified.

1. **Archive-aware `next_sequence` + sender-constrained `--as-name` recovery.** Allocation now takes
   the max across `inbox/` **and** `inbox/archive/`; the `O_EXCL` claim stays scoped to `inbox/` — only
   the starting number moved. The stricter `--as-name` decision landed as a distinct
   `as_name_sender_mismatch` refusal with both accepted and refused arms tested.
2. **Drain archive-failure branch + accounting invariant made real.** D2's verify-at-outline question
   resolved: the drain does **not** infinite-loop within a run, but it **did** silently re-process
   across runs — `analyze.md` item 4 had no error branch, and its `## Output` block asserted an
   accounting invariant nothing computed. `messages_archive_failed` now exists.

**The spec's central instruction was honoured:** the `archive_conflict` refusal, `os.link` semantics,
and `samefile` inode discrimination are byte-for-byte unchanged and pinned by two separate regression
assertions. The guard was correct; the bug was upstream in allocation, and that is where it was fixed.

## Orchestrator corroboration (first-party)

- ✅ `origin/main` at `89fd4d1f6` — *"fix(inbox): archive-aware sequence allocation (#1034)"*.
- ✅ **Dogfooded live:** this plan wrote nine inbox messages (001–009) with no collision, against an
  archive already holding a same-named twin family. The fix is exercised by its own landing.
- ✅ The defect it fixes had **fired live in this epic hours earlier** — a `truthful-signals-001.md`
  collision that required hand repair. That instance is now closed by construction.

## ⛔ Review reality — verified via `ci pr comments`, not from the report

Four comments. The plan's self-report was accurate, and ground truth adds a sharper finding:

| Reviewer | Ground truth |
|---|---|
| **sourcery-ai** | `review_body` — **refusal**: *"you have reached your weekly rate limit of 500000 diff characters"*. **Did not review.** |
| **coderabbitai** | Real review — 8 files, run id recorded, base `d5b53d04d`→`e52e9df94`. No actionable comments. |
| **cuioss-review-bot** (pr-agent) | PR Reviewer Guide — participation, no findings. |
| **cuioss-oliver** | Our own triage reply. |

⭐ **THE FINDING THAT MATTERS — Sourcery has (at least) TWO refusal phrasings, and #1021 covers only
one.** PLAN-80 / #1021 shipped its recognizer against the stable substring
*"your pull request is larger than the review limit of"*. **This refusal is a different mode
entirely** — a **weekly diff-character quota**, phrased *"you have reached your weekly rate limit of
500000 diff characters"*. So the detector's coverage is narrower than believed, and
`automatic-review` folded a **detected** refusal into `completeness: complete: true` via
`no_check_name`.

**This CONFIRMS, with evidence, the doubt the epic recorded as owed to PLAN-92 D1** — that #1021's
credit is overstated. It is no longer a hypothesis. Third consecutive PR (#1024, #1032, #1034) where
a Sourcery refusal was not recognized as one.

⚠ Note also: our own `cuioss-oliver` triage reply is returned as a stored comment — the same shape as
**PLAN-92 defect 6** (author filter not filtering), which under `pre_merge_comment_barrier`
`fail_into_loopback` is an infinite loop.

## Cost

2.7M tokens, 3h01m wall — **over the error anchor for `single_module` + `bug_fix` on both axes.**
Outline + plan cost **4×** the implementation. Routed to the cost/measurement plans rather than
absorbed here.

## Operational notes

- `git worktree remove` timed out at 60s mid-removal, leaving 4 tracked files deleted, then refused
  with *"contains modified or untracked files"*. Restored via `git checkout --` and removed cleanly —
  **no `--force`**. This is the third sighting of the timeout-mid-removal shape and matches the open
  operator question about which recovery the standard should mandate. **This landing supplies the
  answer that worked without `--force`.**
- `finalize-step-simplify` returned `blocked / leaf_cannot_dispatch` — a two-level-dispatch contract
  violation; the inner review was run from main context instead.

## Reconciliation

- Queue row → `shipped`, `pr=1034`, `landing=landings/PLAN-93.md`,
  `plan_marshall_plan_id=inbox-sequence-reuse-collides-with-the-archive`.
- The inbox-collision watch is **closed** — the hand-repair procedure it required is now obsolete.
- Nine inbox messages drained; dispositions recorded in the epic decision log.
