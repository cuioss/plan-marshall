envelope_version=1
sender_type=plan
sender_id=runtime-edge-paths-crash-or-silently-lose-data
epic=truthful-signals
kind=candidate-lesson
created=2026-08-09T20:26:38Z

component=plan-marshall:phase-6-finalize
category=improvement
confidence=high
source_plan=runtime-edge-paths-crash-or-silently-lose-data
source_aspects=chat_history_analysis,log_analysis,plan_efficiency

# Separate a harness-killed background build from a real budget timeout before degrading a gate

## Context

`pre-push-quality-gate` degraded from a whole-tree arm to a scoped fallback, and recorded an
unusually careful WARNING doing so (work.log 17:39:01). Its stated attribution:

> it timed out twice at the daemon learned budget (module-tests 642s, verify 618s) with
> runtimes degrading across the session (215s, 378s, 537s, then two timeouts)

The recorded evidence does not uniquely support "timed out at the learned budget". Both
failures logged:

```
status: error
exit_code: -1
duration_seconds: 0
error: execution_failed
```

`exit_code: -1` with `duration_seconds: 0` is a no-result signature, not a timeout signature.
Both results reached the orchestrator as backgrounded task-notifications — the session
transcript carries `Background command "Whole-tree module tests" failed with exit code 1` and
`Background command "Whole-tree verify on rebased tree" failed with exit code 1` — which is the
known harness-kills-a-backgrounded-job class. A third background job in the same finalize run,
`"Re-validate plan-marshall tests after simplify"`, was reported outright `killed`, and was
silently re-run to success two minutes later.

The WARNING's own corroborating detail points the same way: the run

> reached 99 percent with every reported test PASSED

which fits a job that was cut, not one that hung or overran a budget.

## Root cause

The gate's degradation path treats "the wait returned without a verdict" as evidence about the
*build*. It is equally evidence about the *transport*. Three of five backgrounded long builds
in this plan failed to return a result; the two that did return were the short scoped runs.

## Why the distinction is load-bearing

The two hypotheses have opposite remedies:

- **real budget overrun** → the whole-tree suite is genuinely getting slower; raise the budget,
  or split the suite, and treat the scoped fallback as covering a real risk.
- **harness kill** → the tree was probably green, the result was merely lost, and the correct
  action is to re-run synchronously rather than to degrade the gate and carry an un-gated
  divergence class into the push.

The gate degraded and the push proceeded with the PLAN-08 scoped-green-over-whole-tree-red
class explicitly un-gated for three footprint paths. That may well have been unnecessary.

## Proposed action

Before attributing a gate degradation to a timeout, consult the discriminator that is already
on disk: the daemon job log at `~/.plan-marshall/marshalld/job-logs/{job_id}.log`. A job that
ran to a real budget limit has a log ending mid-suite; a killed job's log ends with the last
completed test and no terminating record. Record which of the two was observed in the WARNING,
and prefer one synchronous re-run over an immediate fallback when the signature is a kill.
Relevant job ids from this run: `3d66725214ac4de29059db452fa39d58` (module-tests) and
`07f944ba3c6f42459b4b74101c25abb4` (verify).

## Evidence

- artifact: `logs/work.log` 16:47:24 and 17:00:37 — both `exit_code: -1`, `duration_seconds: 0`, `error: execution_failed`
- aspect: chat_history_analysis — three of five backgrounded builds returned no result; one explicitly `killed` and silently recovered
- artifact: the 17:39:01 WARNING itself, for both the attribution and the 99-percent corroboration

## What went right

The WARNING is a model of its kind and should not be weakened. It named the un-gated divergence
class by name, listed the exact three footprint paths it applied to, stated the corroborating
evidence it was relying on instead, and identified CI python-verify as the authoritative gate
that still covered the residual. The gap is the attribution beneath it, not the disclosure.
