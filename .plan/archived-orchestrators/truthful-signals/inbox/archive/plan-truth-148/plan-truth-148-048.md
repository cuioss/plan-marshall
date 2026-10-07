envelope_version=1
sender_type=plan
sender_id=plan-truth-148
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T21:05:33Z

# Candidate lesson: a hardcoded agent-step roster that must mirror the dispatcher's set

- source_signal: automatic-review / CodeRabbit inline (PR #1488)
- record_id: 49e11e (comment PRRC_kwDOQ3xasM7uheD9)
- file: marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/record-metrics.md:41
- resolution: fixed via TASK-020 — the parenthetical roster replaced by a pointer at the dispatcher-owned set

## What happened

`record-metrics.md` carried a hardcoded list of agent-dispatched steps that must mirror the dispatcher-owned set in `phase-6-finalize/SKILL.md` Step 3. A new dispatched step makes the statement false and obscures its accumulator contribution.

Note the recurrence: this is the SAME defect class as Q-Gate findings 7bdcff and 7d57d0 in the same run, in a third document. The self-review found two instances of the hardcoded-mirror class and a review bot found a third the self-review had not reached.

## Candidate rule

"Treat a hardcoded list that must mirror a set defined elsewhere as a defect unless it is derived from that source at build or run time." When one instance of this class is found, sweep the skill for the others — the class recurred three times in this plan across three documents, which means finding one is evidence of siblings, not of completeness.
