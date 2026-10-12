envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-11T16:59:12Z

# Candidate lesson: the outline of a cross-repository documentation deliverable cited a nonexistent ci flag and put finalize-time events into a phase-5 deliverable

**Signal source**: Q-Gate findings 3-outline `fa9f69` (error), `153bf7` (warning) and user-review findings `876862`, `879c28`. All four were taken_into_account in-run.

**Component (suggested)**: `plan-marshall:phase-3-outline` (cross-repository deliverables), `plan-marshall:tools-integration-ci`

## Evidence

- `fa9f69`: Deliverable 5 opened the documentation PR through `plan-marshall:tools-integration-ci:ci` with `--project-dir ../plan-marshall-documentation`. Live `--help` declares no `--project-dir` on the ci router, `ci pr` or `ci pr create`, and ci always acts on the repository of the current checkout.
- `153bf7`: D5's success criteria ("merges after the code PR"; links green on the code PR branch) depend on code-PR events that exist only in 6-finalize, so they could not be verified in 5-execute.
- Operator resolution (`876862`, `879c28`): D5 only edits and commits on `docs/workflow-dsl-parser-and-ast` and runs `trace.py` in 5-execute. Push, `gh pr create --repo plan-marshall/plan-marshall-documentation` (body names the code PR) and the automatic merge after the code PR merges move to a Finalize Hand-off section. The orchestrator then carried this out by hand in 6-finalize (decision log 07:00:37Z, 15:26:20Z).

## Why it matters

The project's working rule says that a plan which changes a specification updates the documentation repository in the same plan. So this pattern repeats for every such plan in the epic. plan-marshall has no supported cross-repository PR path (ci has no repository-target flag), and no finalize step for a companion PR. The workaround is a raw `gh` call against the other repository plus orchestrator-driven hand-off prose.

## Suggested direction (for orchestrator classification)

Either add a repository target to the ci PR verbs (or a companion-repository finalize step that opens and merges a linked PR after the code PR), or document the cross-repository deliverable pattern for outline authors: in 5-execute, edits and commits only; PR open and merge in finalize.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `workflow-dsl-parser-and-ast-009.md` from plan workflow-dsl-parser-and-ast (PLAN-07, #27)
