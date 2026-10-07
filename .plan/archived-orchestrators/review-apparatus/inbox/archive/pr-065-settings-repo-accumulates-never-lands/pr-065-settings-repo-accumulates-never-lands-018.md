envelope_version=1
sender_type=plan
sender_id=pr-065-settings-repo-accumulates-never-lands
epic=review-apparatus
kind=candidate-lesson
created=2026-09-14T19:22:42Z

component=plan-marshall:phase-3-outline
category=anti-pattern
source_signal=qgate_finding
source_plan=pr-065-settings-repo-accumulates-never-lands
evidence=qgate finding d08f9a (3-outline, accepted)

# A deliverable's verification command could not collect the guards it claimed to exercise

Deliverable 10 — the plan's TERMINAL verification deliverable — ran
`pyproject_build run --command-args "module-tests plan-marshall"` under the
criterion "the pack guards still pass unchanged". The guards live in
`test/marketplace/targets/pr_agent/test_charter_invariants.py`, which
`architecture which-module --path` resolves to module `default`, not
`plan-marshall`. The scoped command never collects them.

The command would therefore have reported GREEN without having exercised the
criterion it was written to prove — a vacuous pass on the plan's own terminal
gate.

## Why it matters to this epic

This is the volume-read-as-coverage archetype at its most load-bearing position:
the last gate, where a green result is what licenses shipping. The failure is
silent by construction — a module-scoped test run that collects zero of the
relevant tests looks identical to one that collects them all and they pass.

## Candidate rule

A verification command scoped to a module must be checked against the module that
OWNS the files the criterion names — `which-module --path` on the criterion's
own artifacts, before the command is written down. More generally: a test command
whose collected-test count is not observed cannot support a coverage claim, and a
criterion naming specific files should verify those files were collected.

## Disposition in this run

Accepted rather than fixed, on verified evidence that no risk rode on it: the
realized footprint touches zero files under `marketplace/targets/pr_agent/`, and
the publish-workflow change is branch/PR lifecycle only. The gap is in the
planning artifact, not in the shipped result.
