# PLAN-LB-164: A daemon-routed build writes its job log inside the submitting project's tree

epic: live-blockers
workstream: WS-02

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.
> Plan C of the module regrouping of 2026-11-18: everything here lives in the build server (`manage-build-server`) and its documents and tests, so the plan runs in parallel with plans in other modules.

## Objective

A build routed through the `marshalld` build server runs its child inside the project tree (`python3 {tree}/.plan/execute-script.py …`), but the daemon writes the job's log under its machine-global state directory (`job_log_dir()` returns `daemon_dir() / 'job-logs'`, which is `~/.plan-marshall/marshalld/job-logs/`). The result's `log_file` therefore names a path outside the project. The runbook lane forbids reading anything outside the repository root (`runbook-lane/SKILL.md` line 462) and tells the lane to open the `log_file` a build result names (line 710), so a lane that follows the second rule breaks the first on every daemon-routed build. The PLAN-LB-102 landing reported it and the PLAN-LB-160 landing disclosed it again.

The operator ruled on 2026-11-18 that this is a BUG of the build server, not a gap in the lane's rule: builds stay in the project, the worktree and the build directory, and so do their logs ("why not the logs as well; this is a bug for me"). A carve-out in the stay-inside rule was proposed and rejected. The daemon writes each job's log inside the submitting project's tree and the result's `log_file` names that in-tree path; the stay-inside rule stays unchanged.

## Deliverables

1. The daemon writes each job's log inside the submitting project's tree. In `marshalld.py` and `_marshalld_supervisor.py` the job log is created under a directory of the submitting project's tree (the project the job was submitted for, which for a plan worktree is that worktree), and the build result's `log_file` names that in-tree path. Where in the tree it lives, and the file naming that keeps two jobs of one project apart, the outline chooses and records; the choice must be a path the project's `.gitignore` already covers or one the plan adds to the ignored set, so a log never appears as an untracked change.
   - Skills: plan-marshall:ref-code-quality, pm-dev-python:python-core, plan-marshall:manage-build-server
   - Persona: implementer
2. The log's life follows the tree. A job log written in a worktree is removed with that worktree (no separate retention sweep for it), the daemon's journal and retention keep recording the job without depending on the log's location, and a log that cannot be written in the tree (a read-only tree, a missing directory) is a recorded failure of the job's logging, never a silent fall-back to the machine-global directory that would re-open the defect. How the journal's retention and GC see an in-tree log the outline reads and records.
   - Skills: plan-marshall:ref-code-quality, pm-dev-python:python-core, plan-marshall:manage-build-server
   - Persona: implementer
3. The documents state the new location. `manage-build-server/SKILL.md` (the line that lists `job-logs/` beside the journal), `doc/developer/build-architecture.adoc` (the diagram that shows `job-logs/` under `~/.plan-marshall/marshalld/`) and `manage-locks/standards/machine-global-config-scope-audit.md` (the one mention) describe the in-tree log; nothing else in them is reworded. `runbook-lane/SKILL.md` line 710 ("Open the `log_file` it names") needs no edit once the log is in the tree and is NOT touched by this plan.
   - Skills: plan-marshall:ref-code-quality, pm-plugin-development:plugin-architecture
   - Persona: documenter
4. Tests pin deliverables 1 to 3, each written against the unfixed tree first: a routed build's result `log_file` lies inside the submitting project's tree and the file exists and holds the job's output; two jobs of one project do not overwrite each other's log; a log that cannot be written in the tree is reported as a logging failure and does not fall back to the daemon directory; removing the worktree removes its logs. The existing build-server tests that name `job-logs` (acceptance status, idempotent submit, reap survival, ping counts, max-slots resolution, explicit-timeout routing, audit correlation, job-fate reporting, scheduler) are updated where they pinned the old location and stay otherwise unchanged.
   - Skills: plan-marshall:ref-code-quality, pm-dev-python:python-core, pm-dev-python:pytest-testing
   - Persona: module-tester

## Standing Constraints

- The stay-inside rule of the runbook lane is unchanged: no carve-out is added anywhere, and the lane skill is not edited.
- The daemon's registry wall stays: the daemon writes only inside a project that is enrolled in the machine-global registry, and a job for a project that is not enrolled is refused as today.
- The machine-global daemon directory keeps what is machine-global (socket, pid, daemon log, registry, journal); only the per-job build logs move.
- Order inside the plan: deliverables 1 and 2 first (they share the supervisor), then 3, then 4 written against the unfixed tree.
- No file outside `manage-build-server`, `manage-locks` standards (the one mention), `doc/developer/build-architecture.adoc` and the build-server tests is touched.
- No change under `.plan/orchestrator/` other than the plan's own inbox message.
- Scope-bloat note: four deliverables, under the presumptive-split guard.

## Claim Labels

- OBSERVED (re-read at `main` on 2026-11-18): `marshalld.py` lines 132-134 return `daemon_dir() / 'job-logs'`, the machine-global state directory; the child runs `{tree}/.plan/execute-script.py` inside the project tree (`doc/developer/build-architecture.adoc` line 38) and the document shows `job-logs/` under `~/.plan-marshall/marshalld/` (lines 40-42).
- OBSERVED (re-read at `main` on 2026-11-18): `runbook-lane/SKILL.md` line 462 forbids reading anything outside the repository root and line 710 tells the lane to open the `log_file` a build result names; no design note states a reason for the machine-global location.
- HYPOTHESIS: the daemon may write into an enrolled project under its registry wall; confirm at the supervisor and the registry code (verify-at-outline).
- HYPOTHESIS: the direct (non-daemon) build route already writes its log in the tree (the lanes cite logs such as `plan-marshall/python-2026-11-17-194004.log`, which suggests it does); confirm, and if so reuse that directory convention for the daemon route (verify-at-outline).
- HYPOTHESIS: the journal's retention and GC do not depend on the log's location; confirm at the journal code (verify-at-outline).
- Verify-first clause: the outline settles (a) the in-tree directory and file naming, and that it is covered by `.gitignore`; (b) the cleanup path with the worktree; (c) how the failure to write is reported; (d) which build-result writer (`_build_result.py`, `_build_execute_factory.py`, the supervisor) sets `log_file`, and whether any of them is outside the build-server module, in which case the outline records it as a named extension of the surface.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-build-server/scripts/marshalld.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-build-server/scripts/_marshalld_supervisor.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-build-server/SKILL.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-locks/standards/machine-global-config-scope-audit.md`
- OBSERVED: `doc/developer/build-architecture.adoc`
- OBSERVED: `test/plan-marshall/build-server/`

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: none staged or running; PLAN-LB-162 edits the runbook lane and the review gate, and the other plans of the 2026-11-18 regrouping touch other modules.
- Adjacent to: `runbook-lane/SKILL.md` line 710, which stays unchanged on purpose.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-164-build-daemon-job-log-in-project-tree.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits NO file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message.
