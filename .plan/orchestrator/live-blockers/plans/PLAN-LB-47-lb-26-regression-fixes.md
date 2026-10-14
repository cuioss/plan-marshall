# PLAN-LB-47: Fix what PLAN-LB-26 left broken in the execute loop

epic: live-blockers
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-LB-47-lb-26-regression-fixes.md` and is queued as one row file, `queue/PLAN-LB-47.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged from the adversarial landing analysis of PLAN-LB-26 (#1769, `501aeb313`), recorded at
> `landings/PLAN-LB-26.md`. Every OBSERVED claim below was read at `501aeb313` by the
> orchestrator or a delegated read-only agent; the high-severity ones were re-read by the
> orchestrator.

## Objective

PLAN-LB-26 shipped the execute-loop triage changes with three regressions and four gaps against
its own spec:

- **A red orchestrator-tier build can skip triage.** Build failures go to the plan-scoped store,
  but the new short-circuit guard reads only the Q-Gate pending set, finds it empty, and resumes
  without dispatching triage.
- **The short-circuit can never see an owner.** Triage records the fix task through a verb that
  refuses Q-Gate findings, and a refiled failure is reopened with `--reopen`, so a known failure
  reads as new and gets a second fix task.
- **A `module_testing` task never closes when its tests ran inside the task.** The hold is keyed on
  the profile name whatever the tier, and only the orchestrator-tier success path closes it.
- **A per-task build can hand a `running` status to a leaf** that has no rule for it.

This plan makes each path do what PLAN-LB-26's spec asked, and adds the doc test that spec
required and did not get.

## Deliverables

1. **The owed-verification hold applies only when verification is owed.**
   - `finalize-step` holds a task `in_progress` with `verification_owed` only when the caller says
     verification is owed (`--verification-owed`); the profile name alone no longer triggers it.
   - The leaf passes `--verification-owed` exactly when its task's verification resolved to the
     orchestrator tier (`phase-5-execute/SKILL.md`, `execute-task` if it closes steps), and the
     orchestrator-tier `success` row keeps closing it with `--verification-complete`.

   *Done when:* a test closes the last step of a `module_testing` task without the flag and reads
   `done`; with the flag it reads `in_progress` + `verification_owed`; a doc test asserts the leaf
   document passes the flag only on the orchestrator-tier branch. The first test fails at
   `501aeb313`.

2. **A failure triaged into a fix task is recognised when it recurs, and a red build always
   reaches triage.**
   - Triage records the owning task on the record the guard reads: for a Q-Gate finding,
     `triage.md` § FIX Shape 1 uses `qgate resolve … --task-number {N}`, so `fix_task_number`
     survives the `--reopen` refile.
   - The guard in `execution.md` § "Verification-feedback triage" reads the store the failures
     actually land in. For the orchestrator-tier `error` row, either the build failures are
     persisted to the Q-Gate 5-execute slice the guard reads, or the guard reads the plan-scoped
     build store too. Choose one and name it in the doc; an `error` build with findings never
     takes the `no-pending` branch.

   *Done when:* an end-to-end test triages a failure into TASK-N, refiles it unchanged with
   `--reopen`, and the guard query returns `all-owned-by-TASK-N`; a second test with an
   orchestrator-tier `error` build carrying findings returns `new-findings`, never `no-pending`.
   Both fail at `501aeb313`.

3. **The `running` hand-back has one documented contract on every tier.**
   - A `per_task` build never returns `running` to a leaf: the wrapper's bound for a per-task
     call is at least the per-call ceiling, or the leaf contract (`phase-5-execute/SKILL.md`
     Steps 11/11b, `canonical_verify.md`) defines what a leaf does with `running`. Choose one.
   - `execution.md`'s orchestrator-tier outcome table gains a `running` row with the re-attach
     procedure, including how findings are obtained after a re-attach.
   - `execution.md` ("the only component permitted to background a build") and
     `ref-workflow-architecture/standards/agents.md` are reconciled with the daemon rule, and
     `test_build_wait_doc_contract.py` is rewritten so it fails on that original contradiction.

   *Done when:* a test drives a per-task routed build that outlives 300 s and the leaf receives
   a terminal status (or the documented leaf handling); the rewritten doc test fails at
   `501aeb313`.

4. **The PLAN-LB-26 documentation deliverables are completed.**
   - Add the D10 doc test: no document under `marketplace/bundles/plan-marshall/skills/` states
     that `qgate add` reopens a resolved finding without naming the opt-in, and the status values
     listed in `manage-findings/SKILL.md` equal `QGATE_PERSIST_OK`.
   - Put `pending_verify_steps` in `execution.md`'s termination-cause table (D4).
   - State the `deliverable: 0` rule in the validator's error text (D1).

   *Done when:* the D10 doc test exists and fails if `manage-findings/SKILL.md` drops a status; a
   doc test reads `pending_verify_steps` inside the termination table rows.

5. **Two small truthfulness fixes from the same landing.**
   - `scope_creep_check` reports `finding_emitted: false` with the re-observed counts on a `kept`
     outcome, as its docstring says; the pinning test is corrected.
   - `phase-6-finalize/templates/pr-template.md` drops the "Generated by plan-finalize skill"
     footer; the project rule is that PR bodies carry no attribution footer.

   *Done when:* the `kept` test reads `finding_emitted: false`; a test asserts the rendered PR
   body has no footer line.

Split guard: five deliverables, all repairs of one landing; no split.

## Claim Labels

- OBSERVED: `_build_shared.py:381` stores build failures with `add_finding` (plan-scoped store), not `add_qgate_finding` — read at `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_shared.py` § `_store_build_findings`.
- OBSERVED: the guard reads `manage-findings qgate list --phase 5-execute --resolution pending` and an empty set takes `no-pending` without re-dispatch — `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/execution.md:292-307`; the orchestrator-tier `error` row routes into that section — `execution.md:396`.
- OBSERVED: `triage.md:213-216` resolves FIX Shape 1 with `manage-findings resolve … --task-number {N}`; `triage.md` contains no `qgate resolve`.
- HYPOTHESIS: plain `manage-findings resolve` refuses a Q-Gate hash — reported pinned by `test/plan-marshall/manage-findings/test_findings_absent_store_regression.py::test_a_write_verb_handed_a_sibling_store_hash_refuses_and_writes_nothing[resolve-qgate]` — confirm by running it (verify-at-outline).
- OBSERVED: commit `050e23560` makes the phase-5 Step 11c build-failure refile pass `qgate add --reopen` — `marketplace/bundles/plan-marshall/skills/phase-5-execute/SKILL.md` § 11c.
- OBSERVED: `_cmd_step.py:49` `_ORCHESTRATOR_OWED_VERIFICATION_PROFILES = ('module_testing',)`; `:137-138` holds the task when the profile matches OR the flag is passed; only `manage-tasks/SKILL.md`, `manage-tasks.py`, `_cmd_step.py` and `execution.md` mention `--verification-complete`.
- OBSERVED: `_build_execute_factory.py` `_DAEMON_WAIT_BOUND_SECONDS = 300` and `_running_hand_back`; a live `module-tests plan-marshall` call returned `status: running` after 300 s (delegated agent, job `38bdc991…`).
- OBSERVED: `execution.md:182` and `ref-workflow-architecture/standards/agents.md:170` still name the await-long-running seam as the only component permitted to background a build; `test_build_wait_doc_contract.py` flags only paragraphs naming "daemon-routed", which those passages never do.
- OBSERVED: no test under `test/` asserts the D10 conditions (content search by the delegated agent).
- OBSERVED: `scope_creep_check.py:582` sets `emitted = True` on any non-rejected persist, including `kept`; its docstring (~`:86-89`) says `finding_emitted: false`; `test_qgate_persist_contract.py` pins `True`.
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/templates/pr-template.md:31-32` ends with `---` / `Generated by plan-finalize skill`; `CLAUDE.md` § Commit Trailer: "PR bodies carry no attribution footer at all."
- HYPOTHESIS: phase-4 task creation goes through `commit-add` and now logs `manifest_missing` for every plan — confirm at `phase-4-plan/SKILL.md` and `_tasks_crud.py` `cmd_commit_add`; if so, report it in the PR, do not fix here (verify-at-outline).
- HYPOTHESIS: an owed `module_testing` task keeps its envelope live so a later fix task joins an already-passed envelope (N5) — confirm at `_tasks_envelope.py` `assign_envelope_at_creation`; deliverable 1 removes the common trigger; if a residue remains, report it (verify-at-outline).
- Verify-first clause: for deliverable 2, read how PLAN-LB-44 (staged, red-CI triage route) will extend `verification-feedback.md` and keep this plan's guard change in `execution.md` and `triage.md` only.
- Verify-first clause: for deliverable 3, prefer raising the per-task bound over a new leaf contract if the per-call ceiling is known to the wrapper; record the choice.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_cmd_step.py` (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-tasks/SKILL.md` (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-5-execute/SKILL.md` (D1, D2, D3)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/execute-task/SKILL.md` — only if it closes steps (verify-at-outline) (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/execution.md` (D2, D3, D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/triage.md` (D2)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_shared.py` — only if D2 moves build failures to the Q-Gate slice (verify-at-outline)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_execute_factory.py` (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-5-execute/standards/canonical_verify.md` (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/ref-workflow-architecture/standards/agents.md` (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_tasks_core.py` — error text (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-5-execute/scripts/scope_creep_check.py` (D5)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/templates/pr-template.md` (D5)
- OBSERVED: `test/plan-marshall/manage-tasks/test_manage_tasks_finalize_step.py` (D1)
- OBSERVED: `test/plan-marshall/phase-5-execute/test_dispatch_envelope_contracts.py` (D1, D4)
- OBSERVED: `test/plan-marshall/manage-findings/test_manage_findings_qgate.py` (D2)
- OBSERVED: `test/plan-marshall/script-shared/test_build_execute_factory.py` (D3)
- OBSERVED: `test/plan-marshall/script-shared/test_build_wait_doc_contract.py` (D3)
- HYPOTHESIS: `test/plan-marshall/manage-findings/test_qgate_doc_contract.py` — new D10 doc test (verify-at-outline) (D4)
- OBSERVED: `test/plan-marshall/phase-5-execute/test_qgate_persist_contract.py` (D5)
- HYPOTHESIS: `test/plan-marshall/phase-6-finalize/` — PR-body footer test (verify-at-outline) (D5)

## Dependencies and Sequencing

- Depends on: none. High priority: N1–N3 are live regressions on `main`.
- Overlaps with: PLAN-LB-39 (running) on `phase-5-execute/SKILL.md`, `plan-marshall/workflow/execution.md`, `triage.md` and `test/plan-marshall/phase-6-finalize/` — the gate will ask; PLAN-LB-42 (staged) on nothing declared; PLAN-LB-44 (staged) adjacent on `verification-feedback.md`, which this plan does not edit; PLAN-LB-41 (staged) on `test/plan-marshall/phase-6-finalize/` (directory only).
- Adjacent to: the head-dependent-gate gap at merge (`lessons-routing-016`, owned by PLAN-LB-39) and the review barrier's quota-refusal masking (PLAN-LB-46 surface) — not here.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/live-blockers/plans/PLAN-LB-47-lb-26-regression-fixes.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
