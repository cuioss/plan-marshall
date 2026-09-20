envelope_version=1
sender_type=plan
sender_id=plan-203-inbox-consumed-vs-missing
epic=truthful-signals
kind=candidate-lesson
created=2026-07-30T09:34:24Z

component=plan-marshall:marshall-orchestrator
category=improvement
title=The operator-confirmed running state has no machine field, so the anchor prose is its sole carrier

# The operator-confirmed running state has no machine field, so the anchor prose is its sole carrier

STAGED by PLAN-203's D4 gate, not fixed. Surface:
`marketplace/bundles/plan-marshall/skills/marshall-orchestrator/workflow/orchestrate.md` Step 6.

## Observation

`orchestrate.md` Step 6 instructs the `resume_anchor` wording to distinguish the auto-emitted
**launched** block from the operator-confirmed **started/running** state. `launched` IS derivable
(`status.json` `plans[].status`). **`running` is not a `status.json` `plans[]` status value anywhere in
the corpus** — the emit-≠-running invariant is enforced **only by prose**.

Consequence: a reader **cannot derive** whether a launched plan was actually started, and a stale
anchor asserting `running` is **unfalsifiable against the machine authority**.

## Classification

Currently NARRATIVE **with no machine source** — but unlike Vision or Notes, this one *should* be
derivable. It is the one enumerated item where the fix is to **add** a machine field rather than to
render an existing one.

## Rule

An invariant the project restates in prose because the operator corrected it repeatedly (emit ≠
running) is a candidate for a machine field, not for another sentence. Give `running` a status value
so the anchor can be checked against it.

Claim label: OBSERVED (first-party enumeration, D4 gate — the absence of the status value was
confirmed corpus-wide).
