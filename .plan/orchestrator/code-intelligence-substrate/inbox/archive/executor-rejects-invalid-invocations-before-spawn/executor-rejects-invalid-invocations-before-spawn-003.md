envelope_version=1
sender_type=plan
sender_id=executor-rejects-invalid-invocations-before-spawn
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-09T14:43:07Z

# Cap pre-submission self-review on convergence, not on budget exhaustion

component: plan-marshall:phase-6-finalize
category: improvement
confidence: high
source_plan: executor-rejects-invalid-invocations-before-spawn
source_pr: 1127

## Context

`pre-submission-self-review` ran **six rounds** (2 full pre-loop-back, 1 delta, 3 full
post-loop-back), produced **13 qgate findings**, and consumed **1,008,012 tokens** — 60%
of all recorded 6-finalize spend and roughly 22% of the whole plan's reconstructed token
floor. It was closed with a **recorded WARNING deviation** rather than a clean verdict:

> "the step is being closed done WITHOUT a final clean full-scope pass... the observed
> pattern is that each doc correction seeds a new claim for the next round to audit, so
> the sweep was not converging to a clean verdict on its own, while each round costs
> roughly 280k tokens."

Critically, the two halves behaved differently. The **behavioural** findings converged:
rounds 4 and 5 found real defects in shipped code (`cdbb40`, `96076c`, `4f7052`) and
round 6 found none. The **doc-claim** findings did not converge, because each correction
authored new prose for the next round to audit.

## Root cause

The stopping rule is cost, not convergence. The step has one iteration budget spanning
two finding populations with different convergence behaviour, so it cannot stop the
converged half while continuing the divergent one — or, as happened here, stop both on
budget and record an undifferentiated residual.

A round-6 result of "only prose findings, all self-authored in rounds 3-5" is a
convergence signal on the behavioural axis that the step had no way to act on.

## Proposed action

Track the finding population by axis (behavioural vs doc-claim) and let the stopping rule
read the axis:

- Stop the behavioural sweep when a full round produces zero behavioural findings — that
  is a converged verdict and further rounds are pure cost.
- For the doc-claim axis, recognise the self-seeding pattern explicitly: when round N's
  findings are all scoped to prose that rounds N-2..N-1 authored, that is the fixpoint,
  and the residual should be reported as "doc-claim precision" rather than as an
  unconverged sweep.

Closing on a recorded deviation should remain available, but it should not be the routine
exit for a step whose behavioural half already converged two rounds earlier.

## Evidence

- decision.log `[2026-08-09T10:50:15Z] [WARNING] [ec2ee0] (plan-marshall:phase-6-finalize:self-review)` — the full deviation record, verbatim source of the quotes above.
- decision.log `[2026-08-09T04:19:33Z] [c5fbeb]` — `record-step pre-submission-self-review ... total_tokens=1008012, tool_uses=270, duration_ms=4228183`.
- qgate-6-finalize findings store — 13 findings, all resolution `fixed`; findings `237f1c`, `900043`, `f2d054`, `27509a`, `d051f8`, `0d5103` are the doc-claim cluster; `dc73da`, `6d981f`, `cdbb40`, `96076c`, `4f7052` are the behavioural cluster.
- status.json `phase_steps["6-finalize"]["pre-submission-self-review"]` — `display_detail: "6 rounds, 13 findings all fixed, 0 pending"`, which does not carry the deviation.
