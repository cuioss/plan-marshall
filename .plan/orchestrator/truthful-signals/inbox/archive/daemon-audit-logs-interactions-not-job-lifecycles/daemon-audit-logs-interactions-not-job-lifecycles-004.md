envelope_version=1
sender_type=plan
sender_id=daemon-audit-logs-interactions-not-job-lifecycles
epic=truthful-signals
kind=candidate-lesson
created=2026-07-28T15:47:41Z

component=plan-marshall:phase-3-outline
category=anti-pattern
bundle=plan-marshall

# Premise verification checks the spec's CITATIONS but not the spec's own ASSERTIONS

## What was observed

This plan's deliverable D4(b) required "a daemon-restart-renders-`unknown` test". The
premise behind it — that a daemon restart mid-flight yields an *undeterminable* fate —
is false. The journal's `replay_on_restart` forces every job left `queued`/`running` by
a dead daemon to `killed`, which is a **real terminal fate**, not an unknown one. The
deliverable was re-grounded during execution (Q-Gate finding `4bd90f`, "outline
clean-break false premise") and the genuinely-unknowable set corrected to exactly two
conditions: a journal entry already GC'd past its 3600 s window, and a daemon that died
and never came back.

## Why this slipped

The refine phase DID run a source-premise verification pass, and it worked — it
resolved the "HYPOTHESIS: the scheduler module owning job state" pointer to
`_marshalld_journal.py` and recorded "All other file/line references cited in the
Mechanism and Expected Surface sections were verified against current code and are
accurate — no stale or invalid premises found."

That pass verified **citations**: every file/line reference the spec pointed at. It did
not verify the spec's own **behavioural assertion**, which cited nothing and therefore
presented no reference to check. The clean verification report is accurate on its own
terms and still left a false premise standing in a deliverable's acceptance criterion.

Compounding it: `_marshalld_journal.py`'s module docstring states the correct behaviour
explicitly ("any job that was `queued` / `running` when the daemon died is marked
`killed`") in the very file the verification pass had just resolved and opened.

## Why it matters to this epic

Exactly this epic's archetype at the process layer: **"no invalid premises found" is a
confident green whose scope is narrower than its wording**. It certifies the citations,
and reads as certifying the spec.

## Proposed rule

Premise verification must cover a spec's uncited behavioural assertions, not only its
file/line citations. Concretely: every assertion of the form "X yields / cannot / always
renders Y" in a deliverable's acceptance criteria is a premise requiring a named
verification source, and an assertion with no citation is the higher-risk case, not the
exempt one. A verification report should state its own scope
("N citations checked, M assertions checked") rather than the unqualified
"no invalid premises found".

## Recurrence context

Related to the epic's standing archetypes **vacuous-authority / defending-documentation**
and **volume-read-as-coverage**: the report's confidence came from what it *did* check,
with no statement of what it did not.
