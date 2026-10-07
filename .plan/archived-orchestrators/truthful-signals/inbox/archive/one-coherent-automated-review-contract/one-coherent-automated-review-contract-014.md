envelope_version=1
sender_type=plan
sender_id=one-coherent-automated-review-contract
epic=truthful-signals
kind=finding
created=2026-07-29T05:22:09Z

## The pre-merge comment barrier blocks on its own echo (non-terminating loop, LIVE in merged main)

**Observed during the PLAN-92 / PR #1041 finalize run, at `branch-cleanup` order 70.**

### What happened

The fail-closed Pre-Merge Comment-Completeness Barrier re-fetched bot comments
against the current HEAD and filed ONE new pending `pr-comment` finding
(`hash_id a389a9`), blocking the merge.

That "new bot comment" was **plan-marshall's own triage-disposition reply**.

The chain:

1. The wait-region unified triage (`producer=finalize-feedback`) resolved
   pr-agent's finding `1a69d5` and ran the RESPOND half.
2. `github_pr post_responses` transmitted the disposition as a
   `transmit_mode: batched_issue_comment` — an issue comment on the PR,
   authored by the **repo-owner account** (`cuioss-oliver`), because that is
   the identity the CLI is authenticated as.
3. `branch-cleanup`'s barrier called `github_pr fetch_findings` again.
4. `fetch_findings` has a duplicate filter, a noise filter, and a refusal
   filter — but **no self-authored-response filter**. The disposition comment
   is none of those things, so it was ingested as a fresh pending
   `pr-comment` finding.

Body of the ingested "finding", verbatim:

```
## Triage dispositions

### In reply to comment_id: `IC_kwDOQ3xasM8AAAABMIID_g`

Added expires_at/seconds_remaining/expired to the record-is-None branch of
_run_rate_window_check. Regression asserts field-set parity with the claimed
branch. Commit b9692bebe.
```

### Why this is not merely cosmetic

The default is `pre_merge_comment_barrier: fail_into_loopback`. Follow the
documented control flow with this input:

- barrier finds N>0 pending → record `branch-cleanup` as `loop_back` to
  `6-finalize` → re-enter finalize
- re-entry re-fires the wait-region producers and the unified triage → triage
  resolves the echo → RESPOND transmits **another** disposition comment
- barrier re-fetches → ingests the new disposition comment → N>0 again

**The loop has no fixed point.** Each iteration's RESPOND manufactures the
input that blocks the next iteration. It terminates only by exhausting
`max_iterations` (default 3) and halting the plan short of merge — i.e. the
observable symptom is "finalize cannot merge", with the cause hidden behind a
barrier that looks like it is working correctly.

This run did not hit the loop only because the barrier was reached on a
manual finalize drive: the echo was inspected, identified as self-authored,
and resolved `taken_into_account` to proceed. An unattended run
(`loop_back_without_asking: true`, which this plan has) would have spun.

### Theme fit

This is a **confident-signal-hides-a-caveat** instance of a specific shape not
yet in the epic's set: the signal is not merely over-confident, it is
**self-generated**. A fail-closed gate that reads a channel its own
remediation writes to will always eventually block on itself. The gate
reported "1 unhandled bot comment" — truthfully, by its own definition of the
term — while the true count of unhandled *bot* comments was zero.

### Fix owed (tool layer, we own it)

`github_pr fetch_findings` must exclude comments matching the
`post_responses` transmission shape. The strongest available discriminator is
the transmission's own structure, not the author login:

- The batched issue comment has a stable, machine-authored prefix
  (`## Triage dispositions` + `### In reply to comment_id:` lines) emitted by
  `post_responses` itself — a producer-owned marker both sides can key on.
- Author-login matching is the WEAKER option and should not be the primary
  discriminator: the transmitting identity is whatever the CLI is
  authenticated as, so it collides with the human maintainer's own comments.
  Filtering by author would silently drop real human review feedback — a
  strictly worse failure than the one being fixed.

Recommend the producer stamp an explicit marker (e.g. an HTML comment
sentinel, mirroring how the bots mark their own auto-generated comments) and
the consumer filter on that sentinel. That keeps the two ends coupled through
one declared token instead of a scraped heading.

### Adjacent observation

The same asymmetry likely affects `review_completeness`/participation
accounting: a self-authored disposition comment is a comment on the PR from a
non-bot login, so any participation logic that partitions by
"bot vs not-bot" will classify it, harmlessly today, but it is the same
unfiltered input.
