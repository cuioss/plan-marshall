envelope_version=1
sender_type=plan
sender_id=remediate-user-facing-sites
epic=operator-ux
kind=candidate-lesson
created=2026-09-08T12:42:18Z

component=plan-marshall:automatic-review
category=improvement
confidence=medium
source_plan=remediate-user-facing-sites

# Persist the quota-wait deadline so a killed sleep resumes without re-derivation

## Context

The plan served one CodeRabbit quota wait — the mandated 90-minute window that the operator's
recorded stall-recovery policy commits to waiting up to ten times. During that single window, three
background sleeps were killed by host memory pressure. Each kill cost turns: the wait had to be
noticed as dead, its remaining interval recomputed, and a fresh sleep started.

No wall-clock time was lost, because the remainder was recomputed from wall clock each time rather
than restarted from 90 minutes. That is the correct recovery and it happened three times in a row.
But it happened because the agent re-derived it by hand on each kill, not because anything persisted
the deadline. A recovery that depends on the agent remembering when the window opened is a recovery
that degrades quietly under context pressure — which is exactly the condition a long wait produces.

The waits are also long enough that the failure compounds: at ten permitted waits of 90 minutes, a
policy that silently restarts the clock on a kill turns a 90-minute wait into an unbounded one.

## Root cause

The wait is expressed as a duration to sleep rather than as a deadline to reach. A duration has no
memory: once the process holding it dies, the only surviving record of when the window opened is in
the agent's context.

## Proposed action

Persist the wait deadline once, when the quota window is first observed, and expose a wait-until
verb that recomputes the remaining interval from wall clock on every call. A killed sleep then
resumes by calling the same verb again, with no re-derivation and no dependence on remembered state.
This also makes the wait resumable across a session restart, which the current shape is not.

## Evidence

- aspect: llm_to_script_opportunities — logged as candidate 3, complexity low, repetition 3.
- aspect: chat_history_analysis — the single free-form operator turn in the whole session is
  "why did you stop?", consistent with a wait whose liveness is not externally visible.
- `status.metadata.coderabbit_quota_wait_count: 1` — one window, three kills inside it.
