envelope_version=1
sender_type=plan
sender_id=plan-203-inbox-consumed-vs-missing
epic=truthful-signals
kind=candidate-lesson
created=2026-07-30T10:24:19Z

# Multi-sentence decision messages split into unattributed log-line fragments

component: plan-marshall:manage-logging
category: bug
confidence: high
source: plan-retrospective (plan-203-inbox-consumed-vs-missing)

## Context

Five consecutive `decision.log` entries from PLAN-203's lessons-housekeeping step:

```
[07:12:03] [INFO] [3b5f40] test message plan ID citations regeneration
[07:12:13] [INFO] [29ffec] retained 2026-07-29-17-002: D3 only derives inbox counts
[07:12:22] [INFO] [40e773] lesson core guarded failure (stale plan-ID citations, no enforced regeneration) remains open
[07:12:31] [INFO] [c2d2e4] filed via D4 findings, not fixed
[07:12:43] [INFO] [2ab924] (project:finalize-step-lessons-housekeeping) retained 2026-07-29-17-002: D3 only derives inbox counts in resume-summary. Lesson core guarded failure (stale plan-ID citations, no enforced regeneration) remains open. D4 gate filed it via findings, not fixed
```

The last line is the intended message. The four preceding lines are **sentence fragments of it**,
written as separate log entries, each **missing the `(component)` prefix** that every well-formed entry
carries.

## Root cause

The message body transits the shell as a command argument. A multi-sentence message containing
sentence-terminating punctuation was broken into separate invocations before a successful retry. The
resulting fragments are stored as first-class decision entries indistinguishable from genuine
unattributed decisions.

Consequences:

- Any consumer counting decision entries by component undercounts (these four attribute to nothing).
- The retrospective's own `analyze-logs` reports `decision_entries: 70` — four of which are noise.
- The fragments read as standalone assertions ("filed via D4 findings, not fixed") stripped of the
  subject they qualified.

## Proposed action

Accept the message body via `--message-file` rather than `--message`, using the same path-allocate
pattern already used by `manage-lessons add` (returns a path, caller `Write`s the body) and by
`orchestrator inbox write --payload-file`. Message content then never transits the shell.

The one-command-per-call hard rule already forbids passing multi-line content through the shell; this
closes the remaining single-line-but-multi-sentence hole in the same surface.

## Evidence

- decision.log lines 38-42 (07:12:03 through 07:12:43)
- fragment-log-analysis.toon — `decision_entries: 70`
- Existing precedent: `manage-lessons add` path-allocate, `orchestrator inbox write --payload-file`
