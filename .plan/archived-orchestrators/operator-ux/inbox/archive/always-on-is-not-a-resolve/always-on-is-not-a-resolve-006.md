envelope_version=1
sender_type=plan
sender_id=always-on-is-not-a-resolve
epic=operator-ux
kind=candidate-lesson
created=2026-09-03T19:22:20Z

component=plan-marshall:plan-marshall
category=bug
bundle=plan-marshall
confidence=medium

# Emit diagnostics when phase_handshake verify exits non-zero

## Context

`plan-marshall:plan-marshall:phase_handshake verify` exited 1 twice at
2026-09-03T07:41:32Z, during the 4-plan boundary. The plan's
`script-execution.log` records the non-zero exit; the captured stderr is empty.

`script-failure-analysis` classifies the pair as
`bug / script_internal_error` — a non-argparse exit-1, i.e. the script body ran
and failed rather than rejecting its arguments.

## Root cause

The verify path returns a non-zero exit without writing anything to stderr, so
the only artifact of the failure is the exit code. Nothing in the plan's
recorded state says which handshake invariant failed or against which phase, and
the retrospective can classify the failure but cannot triage it.

## Proposed action

On any non-zero exit from `phase_handshake verify`, write the failing invariant
name and its observed-versus-expected values to stderr before returning. The
verify path already computes both sides to make the comparison; the cost is one
formatted line.

## Evidence

- aspect: script_failure_analysis — `bug / script_internal_error`, component `plan-marshall:plan-marshall:phase_handshake`, subcommand `verify`, exit_code 1, `stderr_excerpt` empty, occurrence_count 2
- The plan otherwise completed both handshakes cleanly, so the failure was transient or recovered — which is precisely the class that goes uninvestigated when it logs nothing
