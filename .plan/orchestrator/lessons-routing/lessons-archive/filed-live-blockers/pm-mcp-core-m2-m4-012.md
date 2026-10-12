envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-10T15:10:00Z

# Candidate lesson: Re-run the project's completion gates on the head that merges

- Component: plan-marshall:phase-6-finalize
- Category: improvement
- Origin: pm-mcp-core lessons store, lesson 2026-10-10-07-020 (created 2026-10-10), epic pm-mcp-core-m2-m4

## Source

Retrospective of plan primitive-spi-and-validators (request-result alignment, chat history, manifest decisions). Checked against the decision log and the leaves' reports in the session.

## Context

The standing constraint of the epic and deliverable 5 require four green builds before the package is marked done: `verify`, `verify -Ppre-commit`, `verify -Pcoverage`, `verify -Pintegration-tests -pl pm-core -am`. They ran once: coverage and integration tests on 3105d88, the quality gate again on 3853d09. The row was set to `done` in 3853d09. Finalize then added four fix commits (0ef021d, 3144ca4, 8b6243c, df4ea82) over three rounds. On those heads the leaves ran the quality gate and `verify -pl pm-core -am`; the last round's report states "Coverage (`verify -Pcoverage`): not run". The merged head df4ea82 therefore has no local coverage run and no local integration-test profile run.

## Root cause

The manifest composed only `verify:quality-gate` and `verify:module-tests` as verification steps. The two further gates existed only in the text of TASK-8, a task that ran once. A loop-back re-runs manifest steps, not the criteria of a task that is already done. The plan phase reported this at the time: the deliverable-5 gates "are enforced only through the TASK-8 description and criteria, not by the manifest".

## Evidence

- Decision log e8f1aa: coverage and integration tests ran on 3105d88, before the README change.
- Execute report of the third fix round: coverage not run; new-code coverage "argued from the test rows, not measured".
- Manifest: `phase_5.verification_steps` holds two entries.
- Mitigating, and why this is not a known red gate: CI ran its integration-test job green on df4ea82 (run 38031162852), and the remote analysis reported 99.2 percent new-code coverage. The project's own 80 percent per-module minimum was not evaluated locally on that head.

## Proposed action

- When a deliverable names project gates beyond the two composed steps, compose them as verification steps so every loop-back re-runs them, or have the pre-push step read them from the build commands the project declares.
- Do not let a "mark done" edit be the last task before review: either it is the last commit after the review rounds, or the report that closes the plan states on which head each gate last ran.
