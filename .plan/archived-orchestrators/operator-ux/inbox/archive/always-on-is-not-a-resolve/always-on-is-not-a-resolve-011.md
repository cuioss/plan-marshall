envelope_version=1
sender_type=plan
sender_id=always-on-is-not-a-resolve
epic=operator-ux
kind=candidate-lesson
created=2026-09-03T19:27:21Z

component=plan-marshall:plan-marshall
category=bug
created=2026-09-03

# phase_handshake drifts on `pending_findings_blocking_count` at two phase exits

`plan-marshall:plan-marshall:phase_handshake` exited non-zero twice in plan
`always-on-is-not-a-resolve`, both times with `status: drift` on the same
invariant and both times in the direction of the captured value being stale:

```text
[07:41:32] phase: 2-refine   pending_findings_blocking_count  captured "1"  observed "3"
[08:11:32] phase: 3-outline  pending_findings_blocking_count  captured "1"  observed "0"
```

The two diverge in opposite directions (observed higher at 2-refine, lower at
3-outline), so this is not a one-off miscount — the captured snapshot and the
live count are being read at points that a Q-Gate re-entry moves between them.
The 2-refine drift fired immediately before the outline Q-Gate re-entry
("Starting outline phase (Q-Gate re-entry: 2 pending 3-outline findings)"), and
the 3-outline drift fired after those findings were resolved.

## Solution

Not established by this run. The observation to carry forward is that the
handshake's captured `pending_findings_blocking_count` is taken before a
Q-Gate validation dispatch can add or clear findings, so the invariant compares
a pre-validation capture against a post-validation observation. Either the
capture point moves after the Q-Gate settles, or the invariant tolerates a
Q-Gate-attributable delta.

## Impact

Both drifts were non-blocking (`override: false`, the run continued), so the
signal is easy to normalise as noise. It recurred within one plan at two
consecutive phase boundaries, which is the shape that argues against treating
it as noise.
