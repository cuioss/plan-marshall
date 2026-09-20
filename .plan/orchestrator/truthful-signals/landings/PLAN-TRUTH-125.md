# Landing analysis — PLAN-TRUTH-125

**Plan:** `one-format-several-implementations-that-disagree`
**PR:** #1427 · **Merge commit:** `39ec2a0ad` · **Workstream:** WS-01

## Merge corroboration

`git log main` → `39ec2a0ad fix(toon): unify TOON read/write on the canonical serializer (#1427)`;
`ci pr view --pr-number 1427` → `state: merged`, `merge_commit_sha: 39ec2a0ad9c522aa5730fc6a966359f107c4561b`;
absent from `manage-status list`; archived. **`landing-check: complete: true`, zero missing keys** —
recovered from `-099`'s regression.

## ⭐⭐⭐ The shipped test is the exemplar this epic has been asking for

TOON has one canonical implementation every marketplace emitter routes through, **plus a test that
proves its population TWO INDEPENDENT WAYS — by function name AND by behaviour — cross-checked.**

⇒ **Completeness is DERIVED, not asserted.** ⭐ That is the corpus's own most-repeated rule
(`derive completeness, never assert it`) implemented as a control rather than restated as prose.
**Cite `39ec2a0ad` as the reference implementation** — folded to `PLAN-TRUTH-116` on exactly that basis.

## ⭐⭐ It closed a defect reported against it, in the same commit

`arm-the-refusal-recovery-that-has-never-run-002` reported that **no plan could pass a local whole-tree
`verify` on macOS**: the always-on skip gate refused the `/proc`-dependent nodeid, which was absent from
`_SKIP_EXCEPTIONS`. CI is Linux, so the breakage was invisible there.

⛔ **Verified first-party — and it is already CLOSED.** `_SKIP_EXCEPTIONS` now carries 12 entries
including `::test_read_process_argv_reads_this_process_from_proc`, and
`git log -S` names the adding commit: **`39ec2a0ad` — PR #1427, this very landing.**

⇒ **Discarded with a positive account rather than staged.** The reporter observed it on `05ca6fe7b`,
one commit before the fix; the report and the remedy crossed in flight.

## ⛔ The 90-minute floor cost ~5 hours against a 21-minute window

Rounds 5, 6 and 7 were ~1h45m apart and all three refused. **Round 7's notice stated its own reset —
*"Next included review available in 21 minutes"* — and a retry timed to that succeeded immediately.**
The tooling reported `refusal_eta: ""` throughout, because **none of the three registered extraction
regexes matches that phrasing.**

⇒ **THIRD report of the same gap** (`truthful-signals-049.md`, then `-051.md`), and **the first with a
price**: the earlier two established the ETA is unreadable; this one measures what unreadability costs.
Forwarded as `truthful-signals-052.md`.

⚠ **The run deviated from the operator's floor on that evidence and asked whether the floor is
absolute.** ⭐ Relayed, not adjudicated — but the halves are separable: **a floor is a safe default
precisely BECAUSE the ETA is unreadable**, so fixing the regex is what makes the floor unnecessary.

## ⛔ Two cleanup defects found by DOING, not by inspection

- **`prune-local-and-remote-ref` is not idempotent against its own sibling.** `worktree-remove` deletes
  the local branch; the prune then hard-errors on the missing branch, **aborts, and never reaches the
  remote-tracking ref** — precisely the stale ref it exists to remove. Verified against the remote
  (`git ls-remote` empty, `show-ref` still resolving) and removed by hand.
  ⇒ **Two independent problems, either benign alone**: not idempotent, and fails fast across
  independent operations.
- **`check-artifact-consistency`'s failing 57% recall has a CONTAMINATED DENOMINATOR** — six of its ten
  "missing files" are `lessons-consult` prose bullets. **Real recall ≈ 71%.** Folded to
  `PLAN-TRUTH-104`: the metric is wrong in the direction that MANUFACTURES a failure, and both numbers
  are plausible, so only enumerating the ten reveals four are not files.

## ⛔⛔ Dispatch was blocked mid-finalize and the topology changed silently

**Agent dispatch and `SendMessage` were blocked by the session's permission classifier, so
`branch-cleanup`, the retrospective and everything after ran INLINE rather than under their dispatch
envelopes.**

⇒ ⛔ **The steps completed and the `[OK]` rows are indistinguishable from enveloped runs.** Every
per-dispatch measurement for those steps is absent rather than zero, and the run's own cost figures for
the tail are not comparable with earlier landings'. ⚠ **Recorded as an Open Defect**: a topology change
that alters what is measurable should not be invisible in the step record.

## Reconciliation actions

- Queue: `PLAN-TRUTH-125` → `shipped`; `pr` = `1427`; `landing` = `landings/PLAN-TRUTH-125.md`.
- Inbox: 11 messages drained.
- Capacity: **R 1 → 0 of N=3. THREE slots free, and `PLAN-TRUTH-139` is UNBLOCKED** — `-125` was its
  only collision (`tools-file-ops/scripts/file_ops.py`), sequenced for two consecutive rounds.

## Metrics

**51h26m wall / 5h18m worked / 6.2M tokens / 184.4M billing-weighted** — `6-finalize` alone **47h5m of
the wall and 141.5M of the billing.**

⛔ **91.5% of the wall clock and 76.7% of the billing weight in one phase**, on a plan whose review
ultimately returned zero findings. ⚠ **~5 of those hours are the ETA gap above** — which makes this the
first landing where a named, fixable defect accounts for a measurable slice of the finalize share this
epic has been tracking at 70-77% across six runs.
