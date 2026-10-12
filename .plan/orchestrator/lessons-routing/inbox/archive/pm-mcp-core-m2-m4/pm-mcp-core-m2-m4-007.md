envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-10T15:09:56Z

# Candidate lesson: Whole-tree builds were handed back from the execute step, and the closing README commit made the build result stale

- Component: plan-marshall:manage-execution-manifest
- Category: bug
- Origin: pm-mcp-core lessons store, lesson 2026-10-10-07-015 (created 2026-10-10), epic pm-mcp-core-m2-m4

## Source

Observed by the orchestrator during plan primitive-spi-and-validators. Checked against the decision log of the plan; the log supports the effect and contradicts one part of the stated cause.

## What happened (as reported by the orchestrator)

The plan-time manifest stamped `verify:quality-gate` as orchestrator tier while the live resolve returned `per_task`. The first execute envelope yielded four whole-tree builds back. The README commit that sets the package to "done" then made the freshness gate stale, which required one more build before the phase transition.

## Verification of the wording

- Confirmed: the manifest stamp `verify:quality-gate=orchestrator, verify:module-tests=per_task`, marked "advisory snapshot — leaf re-resolves live at execute time" (decision log a42adf).
- Confirmed: four gates handed back. Log 8ab0e2: the four gates of TASK-8 (verify, quality-gate, coverage, integration-tests pm-core) "all resolve live to execution_tier=orchestrator and are not runnable inside this step".
- Confirmed: stale build result after the README commit 3853d09 and one extra `verify -Ppre-commit` by the orchestrator (e8f1aa). The same entry records that coverage and integration tests ran on 3105d88, before the one-cell README change, and that the leaf steps 11b/11c were not run by a leaf.
- CONTRADICTED by the log: "the live resolve returned per_task". Both 8ab0e2 and af87e8 record the live resolve as orchestrator tier for these gates. The only `per_task` in the log is the stamp for `verify:module-tests`.
- Differs in detail: the log attributes the hand-back to the second envelope dispatch (22:16:44Z, after 6f0cde "envelope 1 exhausted after TASK-6"), not the first.

## What the record does support

A task whose own steps are four whole-tree builds (TASK-8) cannot run inside the execute step at all, so it is handed back whole. And a deliverable whose last change is a tracked one-cell status edit invalidates the build result that was just produced for the same tree.

## Proposed rule

- A task consisting only of orchestrator-tier builds is planned as a verification step, not as a task inside an envelope.
- The status edit that closes a package is committed before the final builds, or the freshness check treats a change outside every buildable path as not affecting the result.

## Evidence

- Decision log a42adf, af87e8, 6f0cde, 8ab0e2, e8f1aa.
