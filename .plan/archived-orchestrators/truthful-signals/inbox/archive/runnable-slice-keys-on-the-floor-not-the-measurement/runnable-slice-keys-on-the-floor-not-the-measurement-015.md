envelope_version=1
sender_type=plan
sender_id=runnable-slice-keys-on-the-floor-not-the-measurement
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T06:11:36Z

component=phase-6-finalize
category=bug
created=2026-07-29

# A recorded ci-verify green survives the force-push that invalidates it

`status.json` records the `ci-verify` step as `outcome: done`,
`display_detail: "ci-verify: all checks green"`, `head_at_completion:
63d9a1a63f...`. `work/ci-precondition-cache.toon` likewise holds
`head_sha: 63d9a1a63f...` with `ci_final_status: success`.

But the branch was then rebased and force-pushed (05:23:37Z), and the PR head at
merge was `f02f2645` on parent `8e49ed0`. The green verdict in the plan's own
state was bound to a SHA that no longer existed on the PR. Nothing re-evaluated
it: the two post-force-push `ci_complete_precondition` calls both returned an
instant unusable `timeout`, and the plan proceeded to merge.

The sharpest detail is that the mechanism to catch this was already present and
already populated. `head_at_completion` exists precisely so a recorded step
outcome can be invalidated when HEAD moves. It recorded the correct pre-rebase
SHA. No consumer compared it against current HEAD. A field that records the
staleness condition but is never read is indistinguishable from not having the
field at all — except that its presence makes the state look MORE trustworthy.

The rebased HEAD's green was in fact real, but it was established by an ad-hoc
Monitor (`CI_STATUS: pending -> success`, `CI_TERMINAL: success failing=[]`) that
leaves no plan artifact. No file under the plan directory records that `f02f2645`
passed CI.

## Impact

Any step outcome stamped with `head_at_completion` must be re-validated — or
explicitly invalidated — whenever HEAD moves past that SHA, and force-push is the
canonical mover. Concretely: a force-push should invalidate the `ci-verify` step
outcome and clear `ci-precondition-cache.toon` rather than leaving both bound to
a superseded SHA. Recording a staleness key without a consumer that reads it is a
false assurance, not a partial one.
