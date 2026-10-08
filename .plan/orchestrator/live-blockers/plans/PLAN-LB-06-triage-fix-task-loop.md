# PLAN-LB-06: Triage can create and schedule its own fix tasks

epic: live-blockers
workstream: WS-01

> ⛔ **SUPERSEDED — do not launch.** Regrouped on 2026-10-08: PLAN-LB-26 (all deliverables).
> This file is kept as the audit record of the original cut. The successor carries its
> deliverables, claim labels and surface entries unchanged.

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-LB-06-triage-fix-task-loop.md` and is queued as one row file,
> `queue/PLAN-LB-06.json`, in the epic ledger. The orchestrator EMITS the command below; it never
> launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

When a build fails during execute, triage is supposed to create a fix task and the executor is
supposed to run it. Neither half works as documented: the triage document tells the agent to write
`deliverable: 0`, which the task validator refuses, and a fix task that does get created carries no
envelope number, so no envelope dispatch ever selects it. In one run a single failing test was
re-triaged once per deliverable — five triage dispatches and six 7–17-minute test runs — while the fix
task that owned it sat unrunnable. This plan makes a triage-created fix task valid, schedulable and
scheduled first, stops a known failure from being triaged again, and closes two contract gaps that
keep the loop from terminating. Carries forward process-compliance PLAN-19 deliverables D1–D5.

## Deliverables

1. **Triage's documented fix task is accepted.** `triage.md` § FIX says to write the task with
   `deliverable: 0` and names no `origin`; the validator defaults `origin` to `plan` and refuses
   `deliverable == 0` unless `origin == 'holistic'`, reporting "Missing required field: deliverable".
   The triager then guesses an owning deliverable. Make the documented form valid: either the triage
   document sets an origin the validator accepts with `0`, or the validator accepts `0` for the
   fix-class origins a triage writes. One rule, stated in `triage.md`, `task-contract.md` and the
   validator's error text. Done when: `commit-add` of the exact task shape `triage.md` prescribes
   succeeds; `commit-add` with the `deliverable` field absent and a plain `plan` origin still refuses;
   `batch-add`, which carries a second copy of the same check, behaves identically.
2. **A fix task created after planning is schedulable and runs first.** `commit-add` writes no
   `envelope_id`, and the executor runs only tasks whose `envelope_id` equals the envelope it was
   dispatched with, so a fix task is reachable only through an undocumented `envelope_id: null`
   dispatch. `next` also returns tasks in number order, which puts a new fix task behind every
   remaining deliverable whose build it blocks. Define one mechanism and document it in
   `execution.md` and `phase-5-execute/SKILL.md`: a task created after envelope packing is assigned
   to an envelope at creation (or the null-envelope dispatch becomes a defined, named dispatch), and
   it is ordered ahead of the pending tasks whose verification it blocks. `manage-tasks get` returns
   `envelope_id` (today only `next` does). Done when: a test creates a task through `commit-add` on a
   plan whose tasks are already packed and reads a non-null `envelope_id` back from `get` (or, under
   the alternative, the documented null-envelope dispatch selects it); a test shows `next` returning
   the fix task before the remaining pending deliverable tasks.
3. **A failure a pending fix task already owns is not triaged again.** `execution.md` routes every
   `triage_required` return and every failed orchestrator-tier build into a fresh
   `verification-feedback` dispatch, with no check for a finding identical to one a pending fix task
   was created for. Add the short-circuit: before dispatching triage, the orchestrator compares the
   pending findings with the findings already resolved "will be addressed by TASK-N" whose task is
   still not done; when every pending finding matches one, it skips the dispatch and schedules the
   fix task. State in the same place which store a build's failures land in, so the orchestrator
   does not file a further copy by hand. Done when: a deterministic verb or documented query returns
   "all owned by TASK-N" for a repeated identical failure and "new findings" when one differs, with a
   test for each; `execution.md` names the store and the short-circuit before the dispatch block.
4. **The end-of-execute re-dispatch rules agree.** In `execution.md` the orchestrator-tier table says
   a green build means "Re-dispatch phase-5-execute … the freshness gate (Step 12a) now sees the
   stamp", while the pre-dispatch queue peek in the same file says the orchestrator "MUST NOT
   re-dispatch" when `loop-exit-guard` reports no pending and no in-progress task. At the end of
   execute both apply, and Step 12a was not re-entered. Make one rule win in words: name the
   post-build re-entry as an exception to the peek, or move the freshness check to where the peek
   leads. A leaf that returns because it owes the orchestrator a build says so in a defined return
   field that every termination branch honours, instead of free text beside `budget_yield`. Done
   when: the two passages no longer contradict (a doc test pins the exception or the relocation), and
   the return-field name appears in both `execution.md`'s termination table and
   `phase-5-execute/SKILL.md`'s return contract.
5. **A module-testing task is not `done` before its test ran.** `finalize-step` closes a task `done`
   as soon as its last step is terminal, with no branch for the task's profile, so a `module_testing`
   task whose only verification is an orchestrator-tier test run reads `done` before that run starts,
   and a failure has no task to reopen. Keep such a task open until its verification build reports,
   or give the failure a defined reopen path that the orchestrator-tier `error` row uses. Done when:
   a test closes the last step of a `module_testing` task that has an orchestrator-owed verification
   and reads a non-`done` status (or, under the alternative, a test shows the documented reopen verb
   returning the task to a runnable state and `next` selecting it).

## Claim Labels

- OBSERVED: `triage.md` prescribes "title, deliverable: 0, domain matching the finding, profile: implementation" with no `origin` — `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/triage.md:191`
- OBSERVED: the validator defaults `origin` to `plan`, coerces an absent or blank `deliverable` to `0`, and raises "Missing required field: deliverable" when `deliverable == 0 and origin_raw != 'holistic'` — `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_tasks_core.py:837`, `:881-886`; the batch path carries its own copy at `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_tasks_crud.py:436`
- OBSERVED: the contract documents "`0` only valid when `origin == "holistic"`" and the origin set `plan, fix, sonar, pr, lint, security, documentation, holistic` — `marketplace/bundles/plan-marshall/skills/manage-tasks/standards/task-contract.md:502`, `:528`, `:531`; the mechanical checker already treats `deliverable=0` as the holistic sentinel at `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_cmd_qgate_mechanical.py:261`
- OBSERVED: `commit-add` builds the task record without an `envelope_id` key — `cmd_commit_add` at `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_tasks_crud.py:261-275`; an `update --envelope-id` path exists at `_tasks_crud.py:734-737`
- OBSERVED: `get` (`cmd_read`) returns no `envelope_id`; `next` does — `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_tasks_query.py:117-136`, `:271`
- OBSERVED: the executor "runs only tasks whose `envelope_id` equals `{E}`", and a `budget_yield` is handled by incrementing the envelope number — `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/execution.md:171`, `:178`, `:357`; no passage describes a task with a null envelope
- OBSERVED: `next` returns the first in-progress task, else the first pending task in file order whose `depends_on` are done; nothing orders a later-numbered fix task first — `cmd_next` at `_tasks_query.py:159-203`
- OBSERVED: `execution.md` § "Verification-feedback triage" dispatches `verification-feedback` on every `triage_required` return and § "Orchestrator-tier phase-5 verification" routes every build `error` into the same triage; neither has a known-failure check — `execution.md:287-330`, `:379`
- OBSERVED: the two re-dispatch rules — "Re-dispatch phase-5-execute … Step 12a" at `execution.md:378` and "MUST NOT re-dispatch the execution-context" on `pending_count: 0` and `in_progress_count: 0` at `execution.md:258`
- OBSERVED: `finalize-step` sets `task['status']` to `done` (or `failed`) when every step is terminal, with no profile branch; the file contains no reference to `module_testing` — `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_cmd_step.py:100-115`
- OBSERVED: no file under `marketplace/bundles/plan-marshall/skills/` contains `orchestrator_build_owed`; the name comes from a run report and is not a defined field at HEAD
- HYPOTHESIS: a daemon-routed failing build persists each failing test as a finding twice (once by the inner wrapper, once by the outer one re-storing the inner run's `routed_errors`), and the plan-scoped store appends without de-duplication — confirm/refute at `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_shared.py` § `cmd_run_common` (the `routed_errors` branch and the `_store_build_findings` call) and `marketplace/bundles/plan-marshall/skills/manage-findings/scripts/_findings_core.py` § `add_finding` (verify-at-outline)
- HYPOTHESIS: `verification-feedback.md` creates fix tasks only through `triage.md` § FIX and has no second task-creation recipe — confirm/refute at `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/verification-feedback.md` (a search for `prepare-add`, `commit-add` and `deliverable` in that file returned nothing) (verify-at-outline)
- HYPOTHESIS: fix tasks created after packing also lack `cost_size` and `predicted_cost_tokens`, which the packer needs to place them — confirm/refute at `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_tasks_envelope.py` and the fields `cmd_commit_add` writes (verify-at-outline)
- Verify-first clause: before scoping deliverable 2, decide between "assign an envelope at creation" and "define the null-envelope dispatch". The first needs a rule for which envelope (the current one, or a new trailing one with the manifest's `envelope_count` updated); the second needs the leaf's "is the next task in my envelope" equality check to treat null explicitly. Read `phase-5-execute/SKILL.md` § "Deterministic exit clause (envelope-group read)" and the manifest's `envelope_count` writer first; do not implement both.
- Verify-first clause: before scoping deliverable 3, establish how a triaged finding names its fix task. Today the link is free text in `resolution_detail` ("Will be addressed by TASK-{N}", `triage.md:203`). If the short-circuit would have to parse that text, add a structured task reference on the resolve call instead and match on it.
- Verify-first clause: for deliverable 5, list which task profiles can have an orchestrator-owed verification at close time before choosing between "stay open" and "reopen path"; a rule keyed on the literal profile name `module_testing` alone must be justified against that list.

## Expected Surface

- DERIVED — this spec is superseded and claims no surface of its own. The entries it declared are
  recorded in the next section and are now declared by the successor named in the banner above.

## Superseded Surface (record only)

- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/triage.md` — § FIX task shape (D1), structured task reference on resolve (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_tasks_core.py` — `deliverable: 0` rule (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_tasks_crud.py` — batch copy of the rule (D1), `commit-add` envelope assignment (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_tasks_query.py` — `get` returns `envelope_id`, `next` ordering (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_cmd_step.py` — task auto-close (D5)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-tasks/standards/task-contract.md` — `deliverable` and `origin` rows (D1), `envelope_id` (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-tasks/SKILL.md` — verb reference for `get`, `commit-add`, `finalize-step` (D1, D2, D5)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/execution.md` — envelope dispatch, triage short-circuit, re-dispatch rules, termination table (D2, D3, D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-5-execute/SKILL.md` — envelope-group read and return contract (D2, D4)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/verification-feedback.md` — triage return fields the short-circuit reads (D3) (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_tasks_envelope.py` — only if deliverable 2 assigns envelopes through the packer (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-findings/scripts/_findings_core.py` — only if deliverable 3 adds a structured task reference to the resolve call (verify-at-outline)
- OBSERVED: `test/plan-marshall/manage-tasks/test_manage_tasks_add.py` — `deliverable: 0` and envelope-at-creation tests (D1, D2)
- OBSERVED: `test/plan-marshall/manage-tasks/test_manage_tasks_get.py` — `envelope_id` on `get` (D2)
- OBSERVED: `test/plan-marshall/manage-tasks/test_manage_tasks_next.py` — fix-task ordering (D2)
- OBSERVED: `test/plan-marshall/manage-tasks/test_manage_tasks_finalize_step.py` — auto-close rule (D5)
- OBSERVED: `test/plan-marshall/manage-tasks/test_manage_tasks_batch_add_batch.py` — batch copy of the rule (D1)
- OBSERVED: `test/plan-marshall/phase-5-execute/test_dispatch_envelope_contracts.py` — envelope and re-dispatch wording (D2, D4)

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: PLAN-LB-05 (`execution.md` § "Orchestrator-tier phase-5 verification" — that plan rewrites how the build is waited for, this plan rewrites what happens after it reports; sequence, and whichever lands second re-reads the section), PLAN-LB-07 (`phase-5-execute/SKILL.md`, a different step), PLAN-LB-01 (the freshness gate Step 12a reaches; this plan only keeps it reachable and changes nothing in `_freshness_crosscheck.py`), PLAN-LB-08 (`_findings_core.py`, only if deliverable 3 adds a field to the resolve call).
- Adjacent to: PLAN-LB-08. Deliverable 3 stops a repeated failure from being triaged again; PLAN-LB-08 stops a re-emitted finding from losing its resolution. They meet at the findings store but change different functions.
- Left out on purpose: the envelope packer placing a task behind a `depends_on` edge into a later envelope, and its blindness to orchestrator-tier build yields when counting dispatches; the `phase-6-finalize/SKILL.md` item 7b wording that re-loads `phase-5-execute` inline while that skill describes itself as dispatched; removing the double persistence of build findings at its source (deliverable 3 only states which store holds them). Each is a real defect from the same runs and none blocks the triage loop once deliverables 1–3 land.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/live-blockers/plans/PLAN-LB-06-triage-fix-task-loop.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
