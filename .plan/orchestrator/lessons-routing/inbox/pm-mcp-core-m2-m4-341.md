envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-18T10:23:51Z

component=plan-marshall:execute-task
category=anti-pattern
created=2026-10-18

# A fix that changes a guarantee must update every place that states it

## Context

In plan-20-job-runner, fixes changed what the runner guarantees, and the sentences stating the old guarantee survived in the Javadoc, the ADR and the developer guide. Reviews then found them one by one as false self-reports:

- 1f692c: SubprocessJobRunner class Javadoc still said a start never reports a running job without a PID, after the bounded report wait (TASK-23) made that possible
- af94fc: runtime-job.adoc:163 said the same, while :198 of the same document already said the opposite
- b1893c (CodeRabbit): Javadoc, ADR runtime-job/004 and runtime-job.adoc:197 said a cancel on an unlaunched job always settles it cancelled (row 2), after TASK-25 made the cause decide rows 2, 3 or 4
- 06199d (CodeRabbit): Traceability, the probe-job spec section and ADR 007 described an argument_rejected refusal that cannot fire on the runner path
- c4df5f, 3c3ebc: ADR runtime-job/008 and ProcessGroupSignals Javadoc kept the old metadata-location claim after it was reversed

## Root cause

The fix task edits the code and the sentence next to it. In this repository a guarantee is usually stated in three or four places (class Javadoc, package doc, ADR, developer guide, sometimes specification and Traceability), and the fix task has no step that finds them.

## Proposed action

When a fix task changes a behaviour that the documentation states as a guarantee, add a step: search (architecture search --content) for the key terms of the old guarantee across Javadoc, doc/developer, doc/adr, doc/specification and doc/Traceability.adoc, and update or confirm each hit. Name the hits in the task outcome so the review can check them.

## Evidence

- qgate 6-finalize 1f692c, af94fc (functional-review false_self_report), c4df5f, 3c3ebc
- pr-comment b1893c, 06199d (fixed)
