envelope_version=1
sender_type=plan
sender_id=one-format-several-implementations-that-disagree
epic=truthful-signals
kind=candidate-lesson
created=2026-09-07T18:41:16Z

category=insight
component=plan-marshall:phase-6-finalize
title=External review found what three internal self-review rounds missed, five rounds running

## The measurement

On PR #1427 the two review layers were run against the same artifact and can be
compared directly:

| Layer | Rounds | Instances of the vacuous-guard archetype found |
|---|---|---|
| `pre-submission-self-review` (internal) | 3 | 0 |
| CodeRabbit (external) | 5 consecutive | 5 — one per round |

Each external round found the archetype **inside the previous round's fix**. The
sequence, in order: a `raise` guarded by an `if`; a `raise` inside a function
merely *defined* in the handler; a `return substitute` leaving the `raise` below
it dead; then the handler-set enumeration gap.

The internal rounds were not idle — they found and fixed eight other findings.
They simply never found this one, five times.

## Why external review had the advantage here

The final finding is the clearest case. The defect was not in code but in a
**justification comment**: a hand-written exception-name set whose comment argued
the three chosen names were the broadest, and therefore the ones that mattered.
Catching it required reading the justification and disagreeing with its *axis* —
breadth versus relatedness — rather than checking the code against the comment.

Self-review re-reads its own reasoning and tends to re-derive the same conclusion.
That is not a discipline failure; it is the structural limit of reviewing one's own
argument.

## The practical rule

**Do not shorten the external review loop under time pressure.** This run was
under exactly that pressure — a mandatory review behind an hourly rate limit, three
operator-owned waits, roughly five hours of wall-clock — and every one of the five
rounds paid for itself. The temptation at round 5 or 6 is to conclude the guard is
now correct and stop; on this evidence that conclusion would have been wrong four
times in a row.

## The escape from the loop

Worth recording alongside, because "run more rounds" is not the whole lesson: the
cycle ended when round 4 stopped refining the answer and **changed the question**.
The clause had been asking "does this handler propagate?" — a reachability
question no AST shape test decides — and each fix was correct for the case it was
shown and evaded by the next. Rewritten to ask a positional question
(`is handler.body[0] a raise?`), it became decidable, sound, deliberately
incomplete, and structurally un-evadable: every escape must place a statement
before the `raise`, and `raise` is a keyword that cannot be shadowed.

**When successive review rounds keep finding the same archetype inside the
previous fix, the signal is that the predicate is asking an undecidable question —
not that it needs one more special case.**
