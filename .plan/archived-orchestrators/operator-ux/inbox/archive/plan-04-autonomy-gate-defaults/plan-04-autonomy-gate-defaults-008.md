envelope_version=1
sender_type=plan
sender_id=plan-04-autonomy-gate-defaults
epic=operator-ux
kind=candidate-lesson
created=2026-09-07T12:45:09Z

# Closure claims were written five times without the arithmetic that would make them checkable

component: plan-marshall:persona-plan-marshall-agent
category: anti-pattern
confidence: high
source_signal: qgate findings 942b81, f95edc, c53c11, 9409e3, f4bda1 (6-finalize); 143cee, 1cf925, 5c519f (3-outline); pr-comment 01f18a
dedupe_note: The rule this violates already exists. What is new is that it was violated eight times in one run by the authoring pass, and that every fix independently converged on the same remedy — which the rule does not name.

## The defect

`agent-behavior-rules.md` already carries *"Never assert closure over an enumeration without re-checking it against its declaring source"* and its index-completeness sibling. This run wrote closure claims that failed that rule **eight times**, across two separate authoring passes, in artifacts the plan itself authored:

At outline (3): a sweep-derived success criterion whose 23-file population left one site owned by no deliverable (`143cee`); an exclusion set presented as closed that omitted two sites (`1cf925`); a count claim of *"eight files"* against a sweep returning twelve (`5c519f`).

At finalize self-review (5): a census heading *"Every gate that can still stop a run"* that omitted `re_review_on_timeout` (`f95edc`); the same census never stating **which tier** it was closed over, omitting `orchestrator.auto_emit` (`9409e3`); a parity-test docstring claiming six documents when the extractors already matched eight (`c53c11`); the same docstring claiming six knobs *"decide whether a plan run pauses"* against a census of ~25 (`f4bda1`); two census rows stating a lane default no declaring source carried (`942b81`).

CodeRabbit then filed the ninth from outside (`01f18a`): the census is *"a maintained table"* that mirrors a set defined elsewhere.

## What is genuinely new: every fix converged on one of two remedies

The rule tells an author to re-check. It does not tell them what to leave behind so the next reader can re-check. All eight fixes independently landed on one of exactly two forms, and both are reusable:

1. **Derive the population.** `c53c11` replaced a hand-listed six-document tuple with `_DOC_ROOTS` + `_derive_documents()`, then added `test_the_derived_population_is_not_silently_empty` so a mistyped root cannot report green over nothing.
2. **State the arithmetic.** `1cf925` replaced prose closure with `23 files returned = 18 declared + 5 excluded`, each exclusion carrying its ground. `f95edc` enumerated the whole live finalize step-param surface (25 steps) instead of re-running a literal that only ever matches one shape, and wrote the one deliberate exclusion **into** the predicate so the boundary is checkable.

A closure claim carrying neither a derivation nor an arithmetic is unverifiable by construction — a reader auditing it *"cannot tell a deliberately-excluded site from an unexamined one"* (`1cf925`, verbatim).

## Corrective

Extend the existing rule with its discharge condition: a closure claim is admissible only when it ships with either (a) a runtime derivation of the population, or (b) the arithmetic — total returned, total accounted for, and each exclusion's ground. Prose closure with neither is the defect, regardless of whether the enumeration happens to be correct on the day it was written.

## Boundary against the sibling candidate

This is the **claim** half. The sibling candidate is the **coverage** half — sites a sweep never reached, carrying no claim at all. Different remedy: re-run the query there, record the arithmetic here.
