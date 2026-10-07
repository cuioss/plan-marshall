envelope_version=1
sender_type=plan
sender_id=inbox-sequence-reuse-collides-with-the-archive
epic=truthful-signals
kind=candidate-lesson
created=2026-07-28T15:12:47Z

component=project:finalize-step-plugin-doctor
category=anti-pattern
bundle=plan-marshall

# Logging-escape probes were written into the plan's permanent work log

The plan's `logs/work.log` carries two throwaway probe messages emitted by the
plugin-doctor finalize step:

```
[2026-07-28T13:51:39Z] [WARNING] [6d817c] test message no special chars
[2026-07-28T13:51:43Z] [WARNING] [a4c23f] [STATUS] (project:finalize-step-plugin-doctor) test with parens and PR #915 class.
```

The step was evidently probing how `manage-logging` handles parentheses and `#`
in a message body — a known-live concern (a literal `;` in a log message trips
the one-command-per-Bash hook). The probing was reasonable; the venue was not.
Both lines are now permanent, immutable content of a landed plan's audit trail.

## Why this is more than untidiness

1. **They are indistinguishable from real output.** The second probe carries a
   well-formed `[STATUS] (project:finalize-step-plugin-doctor)` prefix. Any log
   consumer — `analyze-logs`, the retrospective, a future auditor, the cross-plan
   `global-log-analysis` check — reads it as a genuine status emission from that
   step.
2. **They are WARNING-severity.** They inflate the plan's warning count and will
   surface in any warning-triggered review path.
3. **They defeat their own purpose.** A probe that lands in production output has
   not validated the escaping in a controlled place; it has demonstrated it in an
   uncontrolled one.

## Corrective action

Escaping behaviour of `manage-logging` belongs in a pytest against the logging
script with a temp plan store — the test infrastructure already provides
`PlanContext` + `PLAN_BASE_DIR` for exactly this. No workflow step should ever
write a message to a live plan log whose content is not a truthful record of what
the step did. If a step genuinely needs to verify escaping at runtime, it must
probe against a scratch plan id under `.plan/temp/`, never the plan it is
finalizing.

## Evidence

- aspect: logging_gap_analysis — gap category STATUS,
  `project:finalize-step-plugin-doctor`
- `logs/work.log` lines 164-165 of the landed plan directory
- the same step's third message at 13:51:58 is a genuine, useful warning about
  scoped plugin-doctor coverage — so the probes sit directly adjacent to real
  output a reader must not confuse them with
