# Fix-Target Gate Examples

Examples illustrating the process-vs-data distinction in verification mode.

## Scenario 1: Solution outline has malformed deliverables

| | Approach | Fix target |
|---|---|---|
| WRONG | Edit `solution_outline.md` to fix the format | `.plan/plans/*/solution_outline.md` (data) |
| RIGHT | Find which skill/agent wrote the outline, fix its template or instructions | `marketplace/bundles/**/SKILL.md` (process) |

## Scenario 2: Task file is missing required `delegation.context_skills` field

| | Approach | Fix target |
|---|---|---|
| WRONG | Add the missing field to `TASK-003.toon` | `.plan/plans/*/tasks/TASK-003.toon` (data) |
| RIGHT | Find the task-creation logic in `manage-tasks` script or the planning skill, fix validation or template | `marketplace/bundles/**/scripts/**` (process) |

## Scenario 3: Agent produces invalid output, retries, second attempt succeeds

| | Approach | Fix target |
|---|---|---|
| WRONG | "The retry succeeded, continuing..." | Nothing (silent acceptance) |
| RIGHT | STOP. The agent failed on first attempt. WHY? Fix the agent instructions so it succeeds on first attempt | `marketplace/bundles/**/agents/**` (process) |

## Scenario 4: Status shows wrong phase after transition

| | Approach | Fix target |
|---|---|---|
| WRONG | Manually update `status.toon` to correct phase | `.plan/plans/*/status.toon` (data) |
| RIGHT | Find the lifecycle/status script that failed to update, fix the transition logic | `marketplace/bundles/**/scripts/**` (process) |
