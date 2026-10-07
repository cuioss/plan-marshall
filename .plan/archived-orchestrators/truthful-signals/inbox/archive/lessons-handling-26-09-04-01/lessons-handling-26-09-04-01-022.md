envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-09-04-01
epic=truthful-signals
kind=candidate-lesson
created=2026-09-08T05:58:28Z

component=plan-marshall:phase-6-finalize
category=bug

Relayed from Token-Sheriff PLAN-11 (PR #718 / `4e1e88db`). ⛔ **Observed consequence, not theory**: two ADR-worthy decisions from that run were identified and never surfaced — the step recorded `outcome: done` while the proposals were dropped. The operator learned of them only from the plan's own closing narrative.

component=plan-marshall:phase-6-finalize
category=bug
proposed_by=carry-refresh-token-through-code-exchange
signal_source=signal_qgate_pending_count

# adr-propose escalations are unreachable: the dispatcher wires escalate_ask for automatic-review only

`adr-propose` runs as a dispatched leaf. A dispatched leaf cannot fire `AskUserQuestion` — that is
the documented leaf contract — so when the step finds a decision that needs operator confirmation it
can only return a prompt-required escalation to the main-context dispatcher and rely on the
dispatcher to raise the prompt.

phase-6-finalize's dispatch loop consumes `escalate_ask` for **`automatic-review` only**. No other
step's escalation is read. The consequence for `adr-propose` is total, not partial:

- the leaf returns its proposals as an escalation,
- the dispatcher never reads that field for this step,
- no prompt is ever surfaced to the operator,
- and the step records a clean `outcome: done` — so nothing downstream shows that anything was lost.

## Observed in this run

`adr-propose` recorded `outcome: done` with
`display_detail: "no ADRs proposed (2 candidates need operator confirmation)"`. Two ADR-worthy
decisions were identified and **neither reached the operator**. The `display_detail` is the only
trace, and it reads as a benign zero unless a reader notices the parenthetical.

## Why this is worse than a missing feature

The failure is silent and it is shaped like success. A step that cannot deliver its output should
fail loudly or refuse to run; instead this one reports completion while discarding the entire work
product. Any audit that counts `done` steps sees a healthy run.

## Corrective rule

`escalate_ask` consumption belongs to the dispatch loop as a **step-agnostic** mechanism, not as a
per-step special case:

1. Every dispatched step's return is checked for a prompt-required envelope, keyed on the envelope's
   presence rather than on the step's name.
2. A step that returns a prompt-required envelope which the dispatcher does not (or cannot) surface
   must NOT be recorded as `done` with an empty result. The unconsumed escalation is itself a
   finding.
3. Where a step declares it can escalate, the declaration and the dispatcher's wiring should be
   checkable against each other, so a step whose escalation nothing reads is detectable structurally
   rather than by noticing a parenthetical in a `display_detail`.

## Provenance

Observed during the `6-finalize` run of plan
`carry-refresh-token-through-code-exchange` (PR #718).
