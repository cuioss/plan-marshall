envelope_version=1
sender_type=plan
sender_id=output-volume-standard
epic=operator-ux
kind=candidate-lesson
created=2026-09-03T16:08:54Z

component=plan-marshall:plan-marshall
category=bug

# phase_handshake reported invariant drift because the captured count outlived its findings

## Observation

At the 3-outline phase transition, `plan-marshall:plan-marshall:phase_handshake` exited 1 with `failure_kind=script_internal_failure`:

```
status: drift
plan_id: output-volume-standard
phase: 3-outline
override: false
drift_count: 1
diffs[1]{invariant,captured,observed}:
  pending_findings_blocking_count,"1","0"
```

The captured value was `1` and the observed value `0` — the outline Q-Gate finding `1e3eeb` was pending when the invariant was captured, and the operator resolved it (`accepted`, at the `outline_prompt` `d3_scope` gate) between capture and the handshake. The drift is therefore a legitimate resolution landing inside the capture window, not a corrupted state.

## Recommended rule

`pending_findings_blocking_count` decreasing between capture and handshake is the EXPECTED direction of travel for a phase that resolves its own gate findings. Treat a monotonic decrease of that invariant as satisfied, and reserve the drift fault for an INCREASE (a new blocking finding appeared) or for a non-monotonic change. As it stands the handshake faults on the phase doing exactly what it is supposed to do, which trains the operator to reach for `--override`.

If the strict-equality check must stay, re-capture the invariant after the phase's own gate-resolution step rather than before it, so the captured value names the state the handshake will actually see.

## Evidence

- Plan: `output-volume-standard` (epic `operator-ux`)
- Work log 2026-09-03T08:11:15Z: `[ERROR] (plan-marshall:execute-script:1) script_failure notation=plan-marshall:plan-marshall:phase_handshake exit_code=1 failure_kind=script_internal_failure`
- The resolving event is Q-Gate finding `1e3eeb` (3-outline), resolved `accepted` at 2026-09-03T07:47:15Z
- The plan proceeded to 4-plan normally; no state was lost
