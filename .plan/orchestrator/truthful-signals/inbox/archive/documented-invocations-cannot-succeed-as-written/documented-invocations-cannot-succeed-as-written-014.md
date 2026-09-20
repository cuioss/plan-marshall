envelope_version=1
sender_type=plan
sender_id=documented-invocations-cannot-succeed-as-written
epic=truthful-signals
kind=candidate-lesson
created=2026-09-03T19:00:04Z

component=pm-plugin-development:ext-self-review-plan-marshall
category=anti-pattern

# The defect class a plan exists to close recurs inside that plan's own change — including inside its own fix

This plan's subject was *documented invocations that cannot succeed as written*. The same class
reproduced **three times** inside the plan's own diff, and one of the three was authored by the fix
for an earlier instance.

## The three instances

**1. A rejection that is real but names the wrong cause.** Q-Gate `b76f9f` (5-execute,
`test-failure`): after the `toon_parser` delegation, the outer-quote guard stopped firing, so the
input reached the intent-marker validator and was rejected for the wrong reason. The finding's own
text: *"NOTE THE IRONY AND DO NOT MISS IT — this is precisely the defect class this plan exists to
close: the rejection is real but names the wrong cause, sending a caller to add an intent marker when
the actual problem is the outer quoting."*

**2. The PR's thesis inside the PR's diff.** CodeRabbit `74cb2d` (Major,
`.claude/skills/finalize-step-deploy-target/SKILL.md:83`): the finalize step's parse table named
three TOON fields (`status`, `emitted_count`, `error`) that `generate.py` never emits — and the
**pre-existing contract test restated the same wrong claim rather than catching it**. A documented
invocation that cannot succeed as written, shipped inside the change repairing documented invocations
that cannot succeed as written.

**3. A self-seeded doc claim: the fix became the next finding.** Q-Gate `861e68` (6-finalize,
`contract_drift`), stated verbatim in the finding:

> This prose was authored by THIS ROUND's fix for `f5dbc5`, so it is a self-seeded doc claim.

Round 1 fixed `f5dbc5` by widening the Outer-quotes prose to state both guard conjuncts. Round 2 found
that the widened prose over-claimed: it ranged over `steps`, `skills` and `verification.commands`,
while `_build_task_record` makes exactly **two** guard calls — `skills` is never guarded. The
repair introduced the next instance of the class it repaired.

## Rule

Two things are worth carrying forward, and the second is the sharper one:

- **A fix for a contract-drift finding is itself a contract claim** and must be re-derived against the
  code it describes, not against the finding's narrative. `861e68` was caught only because a second
  self-review round ran; a plan whose settle band fires once would have shipped it.
- **When a plan's subject IS a defect class, that class is the highest-prior candidate for its own
  diff.** All three instances here were caught (by module tests, by CodeRabbit, by round-2
  self-review) — but none by a check that knew what the plan was about. A pre-submission pass that
  reads the plan's own defect class and sweeps the diff for it would have been aimed correctly by
  construction.
