envelope_version=1
sender_type=plan
sender_id=audit-report-path-ignores-plan-dir
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-07-30T08:05:45Z

component=plan-marshall:phase-3-outline
category=anti-pattern
title=A reported defect location is a sample, not the defect — verify the named site before scoping to it

# A reported defect location is a sample, not the defect

## Observation

The plan spec for `audit-report-path-ignores-plan-dir` named `write_persisted_report` as the function that ignored the plan directory by calling `Path.cwd()`. Outlining scoped D1 to that function.

The hypothesis was **refuted on contact**: `write_persisted_report` never calls `Path.cwd()` at all — it receives `repo_root` as a parameter. The single cwd-dependent site was its transitive caller, `audit.py` `main()`:7065, and that one resolved value threads into **six** consumers. The blast radius was 6x the reported one, and the fix belonged at a different function than the one named.

## The recurring shape

This is the same archetype as "a reviewer's list of call sites is a SAMPLE, not an enumeration" — generalised one step further. Whoever reports a defect reports **where they observed it**, which is a symptom site. The defect lives wherever the bad value is *produced*, and the impact set is every consumer of that value.

## Rule

Before scoping an outline deliverable to a reported location:

1. **Verify the named site actually exhibits the reported behaviour.** Read it. Do not treat the spec's function name as an established fact.
2. **Walk to the producer.** If the named site consumes a value rather than producing it, the defect is upstream.
3. **Enumerate the producer's consumers** and state the count in the outline. That count, not the reported site, is the deliverable's scope.

A refuted hypothesis is a successful outline step, not a scope failure — record the refutation explicitly so the spec's claim is not silently re-inherited by a later plan.

## Corroborating evidence from the same plan

D3's sibling sweep was resolved as "none found" **by enumeration over five widened patterns** (`Path.cwd`, `os.getcwd`, `Path(".")`, `Path("")`, bare relative I/O) rather than by spot-check. That is the population-derived form of the same discipline, and it is what makes the "none found" verdict trustworthy.
