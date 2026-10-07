envelope_version=1
sender_type=plan
sender_id=finalize-step-records-are-prose-not-facts
epic=truthful-signals
kind=candidate-lesson
created=2026-08-02T11:39:14Z

component=plan-marshall:phase-6-finalize
category=anti-pattern
bundle=plan-marshall
source_plan=finalize-step-records-are-prose-not-facts
source_pr=1076
source_review=coderabbit
source_finding=415a1c

# RECURRENCE: the population-derived-detector rule broke INSIDE the module that follows it

## Observation

`test/plan-marshall/phase-6-finalize/test_step_records_facts_contract.py` is a deliberately
population-derived test module: assertions 1-7 derive their population from the discovered finalize-step
implementor set, and only 8-9 are labelled targeted anchors. That design was chosen on purpose and stated
in the outline.

One constant inside it regressed off the rule. `_SONAR_SCAN_FACTS` **hard-coded three of the four keys**
that `sonar-roundtrip.md` declares in its own `records_facts` frontmatter. The leakage check in
`test_sonar_branch_c_records_only_that_no_work_was_performed` iterated that fixed tuple. Add a fourth
scan-only fact to the declaration and the test would keep passing while silently checking one fewer key —
assertion (9)'s coverage narrows with no failure anywhere.

CodeRabbit caught it on PR #1076 and cited the existing standing rule back at us:

> For every set-guarding detector, derive the population from its authoritative source at build time or
> runtime rather than maintaining hard-coded lists that mirror parser arguments, registry entries, build
> goals, enum constants, registered handlers, or dispatch tables.

## Why this recurrence is worth recording separately

The prior instances of this archetype were detectors written by authors who had not internalised the rule.
This one is different in a way that matters:

- The module's **stated design** was population-derived.
- Its **other assertions** were population-derived.
- The **authoritative source was already loaded** in the same test file — the step record's own `facts`
  declaration was one call away.
- The hard-coded set was still written.

So the rule being *known*, *stated in the same file*, and *followed by the surrounding code* was NOT
sufficient. Whatever mechanism currently propagates this rule (prose in a standard, reviewer memory) does
not survive contact with a single "just a small constant" convenience.

## Rule

1. A set-guarding constant is a **detector**, no matter how small or how local. It gets the same
   population-derivation obligation as the assertion it feeds.
2. Inside a module already declared population-derived, a literal collection of domain keys should be
   treated as a defect on sight during self-review — the surrounding design is precisely what makes it
   invisible.
3. Prefer a **structural** guard over a prose rule: where a test module derives a population, it should
   have no module-level literal tuples/sets of domain keys at all. That is mechanically checkable in a way
   "remember to derive" is not. Consider whether `ext-self-review-plan-marshall` can surface
   module-level literal key collections in a file that also calls a population-discovery API.

## Resolution in-plan

TASK-010 derived the set from the step record's own `facts` minus `work_performed` and deleted the constant,
so assertion (9) cannot silently narrow when a scan fact is added to the declaration.

## Companion finding from the same review

The same CodeRabbit review flagged that `manage-status/SKILL.md`'s Error Responses table omitted
`invalid_fact` — the one error code the PR introduced. The table listed every other `mark-step-done` code.
TASK-009 added the row. Low severity on its own, but it is the same shape as the two contract-drift findings
pre-submission self-review caught on this PR: **a change that adds a code/field routinely fails to update the
one table that claims to be the complete reference for that code/field's family.**
