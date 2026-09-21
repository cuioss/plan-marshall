envelope_version=1
sender_type=plan
sender_id=plan-145-publish-the-missing-parser-seams
epic=test-quality
kind=candidate-lesson
created=2026-09-04T14:48:57Z

# Script-failure cluster: phase_handshake verify exits 1 on a drift that is the gate working correctly

**Signal**: script-failure cluster (1 of 9 distinct failing notations on this plan)
**Notation**: `plan-marshall:plan-marshall:phase_handshake`
**Plan**: `plan-145-publish-the-missing-parser-seams` (PR #1395, merged `8d8c17bd`)

## Evidence

```text
[2026-09-03T16:03:52Z] [ERROR] plan-marshall:plan-marshall:phase_handshake verify (5.64s)
  exit_code: 1
  args: verify --plan-id plan-145-publish-the-missing-parser-seams --phase 3-outline --strict
  stdout: status: drift
          drift_count: 2
          diffs[2]{invariant,captured,observed}:
            qgate_open_count,"2","0"
            pending_findings_blocking_count,"2","0"
          informational_diffs[1]: main_sha, b510ef29 -> 902c23c5
```

Both drifted invariants moved in the **benign** direction: 2 open Q-Gate findings at capture, 0 observed — i.e. the two `3-outline` findings (`98e7f3`, `21aba3`) were resolved between capture and verify, which is exactly what the phase is supposed to do. `main_sha` also moved (an upstream landing), reported informationally.

## Why it is candidate-lesson material

A blocking-finding count that legitimately **decreased** inside the capture window is reported as `status: drift` with a non-zero exit. The caller cannot distinguish "the invariant broke" from "the invariant was satisfied while I was holding a stale snapshot of it", so the only safe reading is to treat a successful phase as a failure and re-capture. On this run that cost a re-capture and a re-verify; over a plan with a moving `main_sha` it is a repeated tax.

This is a **known** shape — global lesson `2026-09-03-16-005` states it verbatim ("phase_handshake faults on a blocking-finding count that legitimately decreased inside the capture window") — so this run is a recurrence, not a discovery. Sibling `2026-09-03-19-006` records the related diagnosability gap: `verify` can exit non-zero with empty stderr, so the failure is classifiable but not triageable.

## Proposed rule (for orchestrator judgement)

Make the drift verdict **directional** for monotone-improving invariants: a blocking-finding count that decreased is a `resolved` outcome, not `drift`. Report the movement, do not fault on it. Where the value genuinely regressed, keep the current behaviour.

## Related already-active lessons

- `2026-09-03-16-005` — phase_handshake faults on a blocking-finding count that legitimately decreased inside the capture window
- `2026-09-03-19-006` — phase_handshake verify exits non-zero with empty stderr
