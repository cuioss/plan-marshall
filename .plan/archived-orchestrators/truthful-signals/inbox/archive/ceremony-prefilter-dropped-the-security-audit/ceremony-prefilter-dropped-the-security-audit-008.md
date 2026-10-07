envelope_version=1
sender_type=plan
sender_id=ceremony-prefilter-dropped-the-security-audit
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T16:53:29Z

component=plan-marshall:plan-marshall
category=anti-pattern
created=2026-07-29

# A single negative read of async remote state is provisional, exactly as a positive one is

At branch-cleanup I read `autoMergeRequest: null` once, shortly after issuing the auto-merge call,
and concluded the PR was blocked from entering the merge queue. On that single observation I filed
**two** findings (`be4ed7`, `f32f39`), recorded a "merge path deviation, operator-authorized"
decision, and fell back from the configured merge queue to `ci pr safe-merge`.

The PR then merged on its own, through the required platform merge queue, exactly as configured.
`f32f39` is now **rejected as contradicted**; `be4ed7` survives only as a narrowed, unresolved
question about propagation delay.

This epic's theme is *a confident positive that hides a caveat*. This is the same defect with the
sign flipped: a confident **negative** read of an eventually-consistent remote field, treated as
definitive, that manufactured two findings and one unnecessary process deviation out of nothing.
The asymmetry is worth naming — an agent that has learned to distrust a green signal will still
happily trust a red one, because red *feels* like the safe direction to be wrong in. It is not:
here it cost a deviation from a configured, working merge path.

## Solution

- **Treat `autoMergeRequest`, merge-queue membership, and check-run conclusions as eventually
  consistent.** A single read of any of them is provisional regardless of its polarity.
- **Require a second, time-separated observation before filing a finding whose premise is
  "the remote state is X".** One read establishes a hypothesis, not a fact.
- **Prefer the terminal-state read.** `merged`/`closed` is durable; `autoMergeRequest` is transient
  scaffolding that disappears the moment the queue consumes it — reading `null` is as consistent
  with "already consumed" as with "never enqueued".
- **When a deviation is taken on a provisional read, record the provisionality in the decision
  entry**, so the correction has somewhere to attach. (This run did do that, which is why the
  correction at 16:38:01Z is legible at all.)

## Impact

Applies to every `branch-cleanup` run on a merge-queue repository, and generally to any gate that
branches on a remote async field. Generalizes beyond merges: **an absent value in an
eventually-consistent store is not evidence of absence — it is evidence of nothing, wearing the
shape of a negative.**
