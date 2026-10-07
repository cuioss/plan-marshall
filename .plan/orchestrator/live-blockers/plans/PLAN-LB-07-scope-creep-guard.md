# PLAN-LB-07: The scope-creep guard can report, and measures the plan's own changes

epic: live-blockers
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-LB-07-scope-creep-guard.md` and is queued as one row file,
> `queue/PLAN-LB-07.json`, in the epic ledger. The orchestrator EMITS the command below; it never
> launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

The per-task scope-creep guard in phase 5 fails every time it has something to say. It files its
finding with the type `scope_creep_warning`, which the findings store rejects, so every over-threshold
run exits with `finding_persist_failed` and halts the envelope. It also measures the wrong set: it
diffs the commit that was HEAD when the plan was created against the worktree HEAD, so every file
merged from the base branch since then counts as the plan's creep (470 and 738 residual files against a
threshold of 5, on a plan whose own diff was 19 declared files), while the task's own uncommitted edits
are not in the diff at all. Agents respond by passing `--threshold 1000`, which switches the guard off
and would hide real creep. This plan closes the type gap, measures the plan's own changes against the
merge base, and updates the tests that currently assert the rejection and the creation-commit base as
intended behaviour. Carries forward process-compliance PLAN-27 deliverable D1 and truthful-signals
PLAN-TRUTH-178 deliverables D0–D2.

## Deliverables

1. **An over-threshold run persists its finding.** Close the type gap one way only: either add one
   member to `FINDING_TYPES` for this signal (following the `arch-constraint` precedent recorded in
   the taxonomy comment, and the taxonomy's hyphenated naming), or emit under an existing member and
   document why that member is the honest one. Not both — a remapped emission beside a newly admitted
   type is two vocabularies for one signal. Whatever is chosen, `phase-5-execute/SKILL.md` Step 6.5
   names the same type and says which triage dispositions apply to it. Done when: a test that drives
   the real `add_qgate_finding` (no stub) with a residual above the threshold exits 0 with
   `finding_emitted: true`, and the finding reads back from the `5-execute` Q-Gate store with its
   type, title and detail intact; a residual at the threshold still emits nothing and exits 0.
2. **The guard measures the plan's own changes.** Replace `git diff --name-only
   {plan_creation_sha}..HEAD` with the plan-branch-only set: the three-dot diff against the resolved
   base ref (merge base to HEAD) united with the working-tree state, so files that arrived from the
   base branch through a rebase or merge are excluded and the current task's uncommitted edits are
   included. `manage-references` already has both halves (`resolve_base_ref`,
   `compute_plan_branch_diff`); reuse them rather than writing a second derivation. When no base ref
   resolves, return `could_not_look` with a reason naming the missing base, not an error and not a
   zero. Done when: a test in a real temporary git repository — plan branch created, base branch
   advanced by ten unrelated files, branch rebased onto it, one declared file changed and left
   uncommitted — reports `residual_count: 0`; the same repository with six undeclared files changed
   on the branch reports `residual_count: 6` and emits the finding; the test fails against the
   current two-dot creation-commit diff.
3. **The declared set includes the task step targets.** `_collect_declared_files` globs
   `TASK-*.json` directly under the plan directory, while task files are written to the plan's
   `tasks/` subdirectory, so the step-target half of the declared set is empty on a real plan and
   every file a task targets but `affected_files` omits counts as creep. Read tasks from the
   directory `manage-tasks` writes them to (through its path helper, not a second literal). Done
   when: a test that creates a task through the real `manage-tasks` add path, with a step target
   absent from `affected_files`, sees that target excluded from the residual; the existing fixture
   that writes `TASK-001.json` at the plan root is moved to the real location.
4. **Raising the threshold is no longer the way through.** The docstring and Step 6.5 promise a
   `phase_5.scope_creep_threshold` configuration source that the script never reads — the threshold
   is the CLI flag or the default 5. Either read the configured value (precedence: flag,
   configuration, default) or delete the promise from both places. The result reports which source
   supplied the threshold, and Step 6.5 states that a leaf does not pass `--threshold`: the
   configured value is the operator's knob and an over-threshold result is triaged, not tuned away.
   Done when: a test shows the configured value taking effect with no flag (or, under the
   alternative, a doc test shows the key is gone from both files); the output carries the threshold
   source on every measured shape.
5. **The tests stop asserting the defects, and every hardcoded finding type is a taxonomy member.**
   Rewrite the assertions that pin the old behaviour (listed under Claim Labels): the scope-creep
   type as "deliberately un-taxonomised", the real-primitive rejection driven through the scope-creep
   path, and the pinned creation-commit base. The loud-on-rejection contract those tests protect
   stays covered, driven by an input the primitive genuinely rejects (an invalid phase or severity,
   or a type injected for the test). Add one population test: every literal finding type passed to
   `add_finding` / `add_qgate_finding` / `--type` on a `manage-findings` call in
   `marketplace/bundles/**/scripts/*.py` is a member of `FINDING_TYPES`, with the swept count
   asserted to be non-zero. Done when: the three rewritten test groups pass against deliverables 1–3
   and fail against HEAD; the population test fails if `scope_creep_warning` (or any non-member) is
   reintroduced.

## Claim Labels

- OBSERVED: the guard passes `finding_type='scope_creep_warning'` to `add_qgate_finding` — `marketplace/bundles/plan-marshall/skills/phase-5-execute/scripts/scope_creep_check.py:176-185`
- OBSERVED: `FINDING_TYPES` has fourteen members and `scope_creep_warning` is not one; `add_qgate_finding` returns `status: error` "Invalid finding type" for a non-member, and the `qgate add` CLI restricts `--type` to the same set — `marketplace/bundles/plan-marshall/skills/tools-file-ops/scripts/constants.py:96-121`, `marketplace/bundles/plan-marshall/skills/manage-findings/scripts/_findings_core.py:1051-1052`, `marketplace/bundles/plan-marshall/skills/manage-findings/scripts/manage-findings.py:456`
- OBSERVED: a rejected persist makes `cmd_check` print `status: error` / `error: finding_persist_failed` and return 1, so every over-threshold run fails — `scope_creep_check.py:232-252`
- OBSERVED: the diff is `git diff --name-only {base_sha}..HEAD` with `base_sha` read from `references.json` `plan_creation_sha` — `scope_creep_check.py:105-113`, `:209-224`; the two-dot form compares the two commits' trees, so base-branch commits reachable from HEAD after a rebase or merge are counted, and uncommitted edits are not
- OBSERVED: `plan_creation_sha` is `git rev-parse HEAD` at the moment `manage-references create` runs, pinned on purpose "so the scope-creep guard survives later base moves" — `marketplace/bundles/plan-marshall/skills/manage-references/scripts/_references_crud.py:107-113`, `marketplace/bundles/plan-marshall/skills/manage-references/scripts/_references_core.py:31-35`
- OBSERVED: a merge-base derivation already exists — `resolve_base_ref` and `compute_plan_branch_diff` (three-dot `{base_ref}...HEAD` united with porcelain working-tree state) at `_references_core.py:220-266`, `:308-340`
- OBSERVED: Step 6.5 runs "after Step 6 completes its file-system changes but BEFORE running task verification", documents the `{plan_creation_sha}..HEAD` diff, and says the finding is persisted "via `manage-findings qgate add --type scope_creep_warning`" — `marketplace/bundles/plan-marshall/skills/phase-5-execute/SKILL.md:595`, `:602`, `:637`
- OBSERVED: `_collect_declared_files` globs `plan_dir.glob('TASK-*.json')`, while tasks are stored under `get_plan_dir(plan_id) / DIR_TASKS` with `DIR_TASKS = 'tasks'` — `scope_creep_check.py:125-139`, `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_tasks_core.py:273-275`, `constants.py:218`; the test fixture writes `TASK-001.json` at the plan root, matching the script rather than the real layout — `test/plan-marshall/phase-5-execute/test_scope_creep_check.py:63-67`
- OBSERVED: the threshold is `args.threshold` or `DEFAULT_THRESHOLD`; nothing reads `phase_5.scope_creep_threshold`, which appears only in the script docstring and Step 6.5 — `scope_creep_check.py:41-45`, `:198`, `phase-5-execute/SKILL.md:639` (a search of `marketplace/bundles/plan-marshall/skills` for the key returns those two files only)
- OBSERVED: tests assert the rejection as intended — `test/plan-marshall/phase-5-execute/test_scope_creep_check.py:186-190` ("the (deliberately un-taxonomised) scope_creep_warning", `assert call['finding_type'] == 'scope_creep_warning'`), `:280-307` (rejection message naming the type), and `test/plan-marshall/phase-5-execute/test_qgate_persist_contract.py:50-53`, `:88-121` (drives the real primitive through the scope-creep path, asserts `finding_persist_failed` and that the store file does not exist)
- OBSERVED: a test pins the creation-commit base — `test_diff_grades_pinned_sha_despite_moved_base`, `test/plan-marshall/phase-5-execute/test_scope_creep_check.py:383-425`; `test_scope_creep_could_not_look.py` pins the `no_baseline_sha` reason
- OBSERVED: among literal `finding_type='…'` arguments in `marketplace/bundles/**/*.py`, the values are `anti-pattern`, `bug`, `pr-comment`, `sonar-issue`, `build-error`, `tip` and `scope_creep_warning`; only the last is outside the taxonomy — derived by one pattern search at HEAD, which does not cover types passed through a variable
- HYPOTHESIS: residual counts of 470 and 738 against 19 own files, and leaves passing `--threshold 1000`, as reported from two runs — confirm/refute by running the guard in a worktree whose base has advanced since plan creation, before and after deliverable 2 (verify-at-outline)
- HYPOTHESIS: a Q-Gate finding of the chosen type filed in phase `5-execute` is picked up by the Step 11 triage as Step 6.5 claims ("flows into the Step 11 triage loop alongside other verify findings") — confirm/refute at `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/verification-feedback.md` and `triage.md` § the finding-type filter the `build-runner` producer mode applies (verify-at-outline)
- HYPOTHESIS: nothing other than this guard consumes `plan_creation_sha` — a file-name search finds it only in `scope_creep_check.py`, `phase-5-execute/SKILL.md` and the two `manage-references` scripts; confirm/refute across `test/` and `.claude/` before deciding whether the field stays (verify-at-outline)
- Verify-first clause: decide the type question (new member versus existing member) before any code. A new member also becomes a legal plan-scoped store file name and a legal `--type` choice on every `manage-findings` verb, and must be placed in or out of the promotion subsets (`LESSON_TYPES`, `ARCHITECTURE_TYPES`) and documented in `manage-findings/standards/jsonl-format.md`. Record the choice and its reason in the plan's outline.
- Verify-first clause: confirm on a live plan directory that task files are under `tasks/` and that the guard's step-target union is empty there, before sizing deliverable 3.
- Verify-first clause: check what the base ref resolves to in the plan's worktree when `origin/{base_branch}` is absent or stale (offline, or a fork). `resolve_base_ref` falls back to the local branch name; decide whether a stale local base is measured or reported as `could_not_look`.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-5-execute/scripts/scope_creep_check.py` — type, diff base, declared set, threshold source (D1–D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-5-execute/SKILL.md` — Step 6.5 only (D1, D2, D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/tools-file-ops/scripts/constants.py` — `FINDING_TYPES` and the promotion subsets, only if a member is added (D1)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-findings/standards/jsonl-format.md` — type table, only if a member is added (D1) (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-findings/SKILL.md` — type list, only if a member is added (D1) (verify-at-outline)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-references/scripts/_references_core.py` — `resolve_base_ref` / `compute_plan_branch_diff` reused; the `plan_creation_sha` comment corrected (D2)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-references/scripts/_references_crud.py` — the creation-commit comment, and the field itself if the verify-first sweep finds no other consumer (D2) (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/triage.md` — disposition guidance for the finding type, if Step 11 triage needs it (D1) (verify-at-outline)
- OBSERVED: `test/plan-marshall/phase-5-execute/test_scope_creep_check.py` — type assertion, rejection fixture, pinned-base test, task fixture location (D5)
- OBSERVED: `test/plan-marshall/phase-5-execute/test_qgate_persist_contract.py` — real-rejection contract re-driven through a genuinely invalid input (D5)
- OBSERVED: `test/plan-marshall/phase-5-execute/test_scope_creep_could_not_look.py` — baseline reasons (D2)
- HYPOTHESIS: `test/plan-marshall/phase-5-execute/test_scope_creep_merge_base.py` — new real-repository test for D2 (verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/manage-findings/test_finding_type_literal_population.py` — new population test for D5 (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: PLAN-LB-06 (`phase-5-execute/SKILL.md` — that plan edits the envelope and return-contract sections, this one Step 6.5 only; `triage.md` if this plan adds disposition guidance), PLAN-LB-08 (`manage-findings` — that plan changes what a re-emitted Q-Gate finding does; this guard re-emits the same title and detail on every task while the residual is unchanged, so once PLAN-LB-08 lands an accepted scope-creep finding stays accepted instead of being reopened per task. No file collision unless a type member is added to documents PLAN-LB-08 also edits; sequence if so).
- Adjacent to: `manage-references` footprint verbs (`compute-footprint`, `capture-footprint`), which already use the merge-base derivation and are not changed.
- Left out on purpose: the `WORKTREE:` dispatch-header shape (process-compliance PLAN-27 deliverable D2) — a separate contract with a separate surface.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/live-blockers/plans/PLAN-LB-07-scope-creep-guard.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
