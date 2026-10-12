envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-10T15:09:57Z

# Candidate lesson: For a Maven project the pre-push quality gate derives no module from the changed Java files

- Component: plan-marshall:build-maven
- Category: bug
- Origin: pm-mcp-core lessons store, lesson 2026-10-10-07-016 (created 2026-10-10), epic pm-mcp-core-m2-m4

## Source

Observed by the orchestrator during plan primitive-spi-and-validators. Only partly confirmed from the decision log.

## What happened (as reported by the orchestrator)

The pre-push quality gate derived zero bundles: all 22 Java paths "matched a build_map glob but resolved to no bundle". Neither `test-compile` nor `module-tests` resolves at default scope. The gate therefore degraded to the whole-tree quality gate alone.

## Verification of the wording

- NOT confirmed from the decision log: the count of 22 paths, the quoted message, and the statement about `test-compile` and `module-tests`. The log has no such entry; they may be in the work log or in the step's own output, which this step did not read.
- Related and confirmed: at plan time the manifest kept the step on an unknown verdict — "pre_push_quality_gate_inactive — kept pre-push-quality-gate on an unknown build verdict: plan footprint unresolvable — no materialized worktree carries evidence of what this plan changed" (4ffcc8, twice).
- Related and confirmed: the step ran four times and was recorded `executed` each time (f5ec40), with no token or duration measure.
- Related: for the README-only deliverables the log records "No buildable module" (79faf8, b926b9) and "plan footprint touches no build_map glob" (af87e8). Those concern non-Java files and are correct as such; they do not show the Java case.

## Proposed rule

The mapping from a changed path to its build unit must work for Maven modules (`pm-core/src/main/java/...` resolves to module `pm-core`), not only for the bundle layout of the marketplace. When a path matches a build glob and resolves to no unit, that is reported as a defect of the mapping, and the scoped commands (`test-compile`, `module-tests`) resolve per Maven module.

## Evidence

- Decision log 4ffcc8, f5ec40, 79faf8, b926b9, af87e8.


## Recurrence: plan workspace-confinement (PLAN-03 of epic pm-mcp-core-m2-m4), inbox message workspace-confinement-015.md

**Candidate: the pre-push check resolved no build group for a Maven multi-module change and could not run its divergence test**

Source: run observation, not a finding record. Verified against the logs.
Plan: `workspace-confinement` (PLAN-03), pull request https://github.com/plan-marshall/pm-mcp-core/pull/19, merged.

## Evidence

- Work log `c6adbd` (2026-10-09T23:04:38Z, WARNING, pre-push-quality-gate): "Footprint paths matched a build_map glob but resolved to no bundle", listing all 10 changed Java files of `pm-core` and `pm-runtime`, "proceeding; these are not gated as a bundle".
- Work log `93eee2` (23:07:17Z, WARNING, pre-push-quality-gate): "No module-tests canonical resolves in this project, so no pytest could be run and the divergence question cannot be answered — the scoped-green / whole-tree-red divergence class (PLAN-08) is UN-GATED at finalize for this push. Proceeding on honest degradation."
- Decision log `4ffcc8` (at plan time): "kept pre-push-quality-gate on an unknown build verdict: plan footprint unresolvable".
- Work log `0a2df5` (22:53:43Z, WARNING): "TASK-5 missing verification — falling back to architecture resolve".

## What happened

For this Maven multi-module repository the step that derives which build groups a change touches returned none, although every changed file matched a build mapping. The step then looked for a project-wide test command, found none at default scope, and named `pytest` as the thing it could not run, in a repository that has no Python tests. It proceeded on both warnings; the step ran three times in this plan and the first run logged both.

The whole-tree Maven verify did run in the execute phase each time (work log `a9924a`, `d98222`, `04aebb`), so the change was not shipped untested. What did not run is the specific comparison of module-scoped results against whole-tree results.

## Why it may be a lesson

The check degrades silently into a pass for every plan of this repository, and its warning text assumes a Python project. Whether the cause is the repository's build mapping or the derivation itself is not established by the log.

Classification is left to the pickup.

## Recurrence

Recurred in plan lock-manager-and-leases (PR #20, inbox `lock-manager-and-leases-004.md`): all 63 Java paths under pm-core/src and pm-runtime/src matched a build_map glob but resolved to no bundle, no `module-tests` canonical resolved, and decision 4ffcc8 recorded `pre_push_quality_gate_inactive`. Also seen as DEGRADED in workspace-confinement (#19).
