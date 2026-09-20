envelope_version=1
sender_type=plan
sender_id=plan-cis-027-graph-merge-drops-every-resolver-edge
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-02T15:05:18Z

component=plan-marshall:build-pyproject
category=bug
created=2026-08-02
bundle=plan-marshall

# Resolved bash_timeout_seconds disagreed with the wrapper internal ceiling and killed a run

Two independent timeout authorities disagreed by 30 seconds, and the shorter one silently killed a
passing test suite while the outer status reported `duration_seconds=0`.

## Context

TASK-001's verification ran `module-tests plan-marshall` against an architecture-resolved envelope
that claimed `execution_tier=per_task` with a **441s** budget. The wrapper's own internal ceiling
was **411s**, and the run was killed there:

```
[VERIFY] module-tests plan-marshall hit the wrapper internal timeout at 411s
  (resolved envelope claimed per_task/441s) — the outer routed status reported
  duration_seconds=0, the job log carries the real 411s timeout
```

TASK-002 recovered by passing an explicit override, and the same suite then completed comfortably:

```
module-tests plan-marshall PASS (330s, explicit --timeout 570 override —
  the learned 411s value was short and had killed the earlier run)
```

The suite needed 330s. The learned ceiling was 411s. The resolved envelope promised 441s. The
suite would have passed under either published number — it was killed by a third value the caller
could not see.

## Two distinct faults

**1. Two timeout authorities, no reconciliation.** The architecture-resolved envelope's
`bash_timeout_seconds` and the wrapper's internally-learned ceiling are computed independently. The
caller reads and trusts the resolved envelope; the wrapper enforces its own. Nothing asserts they
agree, so the effective timeout is the minimum of two numbers only one of which is published.

**2. A timeout kill reported `duration_seconds=0`.** This is the more dangerous half. A kill after
411 seconds of work surfaced on the outer routed status as a zero-duration return — the signature
of an *instant* return, not a *timed-out* one. The real 411s figure existed only in the job log. A
caller reading only the outer status cannot distinguish "killed at the ceiling" from "returned
immediately", and an implausible `duration_seconds=0` is exactly the shape that gets mentally
normalised as a glitch.

## What went right (and why it is not a substitute for the fix)

The handling was exemplary and should be preserved as the reference behaviour: the run was **not
blind-retried**. The provenance was established first — decision `e54dfc` classified the suite as
"orchestrator-tier in practice, as deliverable 1's own verification note anticipated," explicitly
noted "Not a task failure and not blind-retried," and reasoned that the module-tests signal was
only meaningful after TASK-002 landed anyway. The recovery then used a *deliberate* override, not a
larger version of the same call.

That is the discipline working. But it cost an LLM a full provenance analysis to recover from a
number mismatch that should never have reached the caller.

## Proposed action

1. **One authority.** Derive the wrapper's internal ceiling **from** the resolved
   `bash_timeout_seconds` rather than from an independently-learned value. If the learned value is
   to remain an input, it must feed the resolver, not shadow it at enforcement time.
2. **Never report `duration_seconds=0` on a kill.** Surface the actual elapsed time and a distinct
   `timeout` status on the outer routed result, so a timeout is distinguishable from an instant
   return without opening the job log.

Fix 2 is independently valuable even if fix 1 is deferred: it converts a silent, misleading signal
into a legible one.

## Cross-reference

This is a fresh instance of the standing "never trust a routed build's outer status — an
implausible duration is a failure signal" rule. Here the implausible duration was `0` against 411
seconds of real work. The rule currently asks the reader to notice the implausibility; this lesson
asks the producer to stop emitting it.

## Evidence

- work.log `2026-08-02T10:18:09Z` `[VERIFY]` — the 411s-vs-441s mismatch and the `duration_seconds=0` outer status, verbatim
- decision.log `e54dfc` — provenance analysis; "Not a task failure and not blind-retried"
- decision.log `2ef3fb` — "module-tests plan-marshall PASS (330s, explicit `--timeout 570` override — the learned 411s value was short and had killed the earlier run)"
- aspect `log_analysis` — `slowest_scripts` shows `pyproject_build` at 690,960 ms and 688,600 ms, well past both published ceilings, confirming this suite genuinely lives near the orchestrator tier
