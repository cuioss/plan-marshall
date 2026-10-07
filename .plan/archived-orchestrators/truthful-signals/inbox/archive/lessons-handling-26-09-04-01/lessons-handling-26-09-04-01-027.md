envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-09-04-01
epic=truthful-signals
kind=candidate-lesson
created=2026-09-08T10:39:04Z

component=plan-marshall:build-maven
category=bug

⛔ **FOLD REQUEST — this is the THIRD relay of this class from this repository**, after `-006` (the wrapper reporting only the last summary line) and `-018` (`tests_run=0` with `tests_population=measured` over 3,048 passing tests, reproduced on three builds). Please fold rather than open a third item — the recurrence count is the signal.

Relayed from Token-Sheriff PLAN-12 (PR #720 / `e52ec470`).

# Candidate lesson: Maven build wrapper reports tests_run 0 with tests_population measured on a green run that ran tests

**Component**: `plan-marshall:build-maven`
**Signal class**: truthful-signal defect observed across every green run in this plan
**Landed in**: PR #720, squash commit `e52ec470`.

## Observation

Every green `verify -Ppre-commit` run in this plan returned:

```text
tests_run: 0
tests_population: measured
```

while surefire reports were being written on disk by the same invocation. The zero is therefore
almost certainly a report-parsing gap, not a real zero.

## Why the pairing is the defect, not the zero

`tests_population: measured` is a strictly stronger claim than an unmeasured or unknown
population: it says the wrapper looked and counted. Paired with `tests_run: 0` it asserts
"I counted the tests and there were none" over a run that in fact executed tests. A consumer
gating on "did this run exercise any test" reads a confident, wrong negative — the same
which-kind-of-zero failure the store-resolution discriminators elsewhere in the system exist
to abolish, appearing here on the build surface.

An unmeasured zero would have been benign; the `measured` stamp is what makes it a defect.

## Suggested direction (for orchestrator judgement)

Either fix the surefire-report parse for this invocation shape, or make the population field
report `unmeasured` whenever the parse found no report to count — never `measured` on a count
the parser did not actually take.
