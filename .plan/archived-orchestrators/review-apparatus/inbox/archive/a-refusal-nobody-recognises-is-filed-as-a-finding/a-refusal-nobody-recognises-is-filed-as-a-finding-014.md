envelope_version=1
sender_type=plan
sender_id=a-refusal-nobody-recognises-is-filed-as-a-finding
epic=review-apparatus
kind=candidate-lesson
created=2026-08-25T09:07:50Z

component=plan-marshall:phase-6-finalize
category=improvement
title=A contract-declared aggregate transmitted as a subtotal, with the scope caveat living in prose

# A contract-declared aggregate transmitted as a subtotal, with the scope caveat living in prose

## Possible duplicate — merge candidate

This is likely a **recurrence** of the dispatch-ledger lesson already in this inbox
(seven firings, six ledgers reporting 2/2/5/5/6/5, none publishing a denominator).
Same shape, different component: a count transmitted without the population it was
computed over. Filed separately only because the component and the seam differ; if
the orchestrator judges them one lesson, this is the second observation and should be
folded in as a `## Recurrence` rather than allocated fresh.

## The observation

`phase-6-finalize/workflow/lessons-capture.md` declares the forwarded signal input as:

> `signal_qgate_pending_count` — integer; sum across `2-refine`, `3-outline`,
> `4-plan`, `5-execute`, `6-finalize`.

On this run the dispatcher forwarded `signal_qgate_pending_count: 15` together with a
free-text scope note stating that 15 was the **6-finalize resolved-in-run subtotal**
and that the other four phases were not separately queried — "treat 15 as a floor, not
a total."

So the transmitted value was a one-phase subtotal occupying a field whose contract
declares a five-phase sum. The discrepancy was recoverable **only** because the
dispatcher volunteered a prose caveat alongside the payload. Nothing in the field
itself distinguishes a complete five-phase sum from a one-phase floor: both arrive as
a bare integer.

## Why it matters here

This is not a claim that the gate mis-fired — the gate is a non-zero test, and 15 and
the true total are both non-zero, so the routing outcome was identical either way. The
defect is in **representability**, which is exactly the failure mode this epic
collects: a confident-looking scalar whose caveat is not carried by the scalar.

The consequence is latent rather than realised on this run. A downstream consumer that
reads the count as a magnitude — "focus recording on whichever signal source
dominated", which this very workflow invites in as many words — would be comparing a
one-phase floor against two counts computed over their full declared populations, and
would rank the dominant signal wrong. The prose caveat does not survive into any
persisted artifact, so a later reader of the run record sees only `15`.

## Corrective rule

A transmitted count must carry its own scope in the **payload**, never in an adjacent
note:

- When a field's contract declares an aggregate over a named population, the payload
  carries either the full aggregate or an explicit incompleteness marker — a `scope`
  / `phases_queried` / `partial: true` companion field. A prose caveat is not a
  representation; it is a hope that the next reader is the same reader.
- A producer that could not compute the declared aggregate reports **which kind of
  number** it is sending. "Looked at one phase" and "summed five phases" must not
  share a representation, for the same reason `inbox list` names which kind of zero a
  `count: 0` is.
- When forwarding a count a consumer is told not to recompute, that prohibition makes
  the scope field mandatory rather than optional: the consumer has been explicitly
  denied the ability to check.

## Standing rule this reinforces

A count is only as trustworthy as the population it publishes. This epic has now seen
the pattern in the dispatch ledger and in the finalize Signal Gate transport; the
general remedy — every set-guarding or population-derived figure publishes its
denominator — is already recorded, and this is one more site to apply it to.
