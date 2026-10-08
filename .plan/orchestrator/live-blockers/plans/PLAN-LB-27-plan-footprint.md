# PLAN-LB-27: Plan footprint: commits stage through an allowlist and the scope-creep guard measures the plan's own changes

epic: live-blockers
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-LB-27-plan-footprint.md` and is queued as one row file, `queue/PLAN-LB-27.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Assembled on 2026-10-08 from PLAN-LB-07, PLAN-LB-11, which this spec supersedes in whole or in part.
> Deliverables, claim labels, surface entries and the carried sequencing notes are copied from those
> specs unchanged. Each deliverable is tagged with the spec and number it came from; inside carried
> text, "deliverable 2" or "D2" means that number of the SAME source spec, and a plan id below
> PLAN-LB-22 resolves through the id map at the end of § Dependencies and Sequencing.

## Objective

Nothing mechanical ties what a plan commits to what the plan declared. Staging is one prose sentence over the whole working tree, so an untracked secret or an unrelated deletion can enter a commit that is pushed minutes later; and the per-task scope-creep guard, the one check that does compare touched paths with the declared footprint, fails every time it has something to report and measures the base branch's changes instead of the plan's. This plan adds a staging verb that admits only footprint paths and refuses secret-shaped files, routes every plan commit through it, and repairs the guard so it persists its finding and measures against the merge base. The two sources are one plan because they apply the same containment rule to the same declared footprint and both edit `phase-5-execute/SKILL.md`.

### Carried from PLAN-LB-07: The scope-creep guard can report, and measures the plan's own changes

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

### Carried from PLAN-LB-11: Plan commits stage through a footprint allowlist

Every commit a plan makes — the per-deliverable commits of the execute phase and the commits the finalize dispatcher cuts after each source-mutating step — is staged by an agent following one sentence: "Stage specific files relevant to the logical change", after a `git status --porcelain` over the whole working tree. No script limits what `git add` receives, so an untracked `.env`, a key file or an unrelated edit sitting in the worktree can enter a commit that is pushed minutes later; the first finalize step that commits (`finalize-step-sync-baseline`) cannot be switched off, so the exposure exists on every plan. A review bot rated this Major (CWE-200) and the finding was accepted, not fixed. This plan adds one staging verb to `git-workflow.py` that stages only paths inside the plan's footprint, refuses secret-shaped files outright, reports everything it left out, and offers a logged escape for intentional extras; the commit workflow and its callers then use that verb instead of a hand-written `git add`. Carries forward truthful-signals PLAN-TRUTH-170 deliverable D5 and lesson `2026-09-08-22-001`.

## Deliverables

1. **[PLAN-LB-07 D1]** **An over-threshold run persists its finding.** Close the type gap one way only: either add one
   member to `FINDING_TYPES` for this signal (following the `arch-constraint` precedent recorded in
   the taxonomy comment, and the taxonomy's hyphenated naming), or emit under an existing member and
   document why that member is the honest one. Not both — a remapped emission beside a newly admitted
   type is two vocabularies for one signal. Whatever is chosen, `phase-5-execute/SKILL.md` Step 6.5
   names the same type and says which triage dispositions apply to it. Done when: a test that drives
   the real `add_qgate_finding` (no stub) with a residual above the threshold exits 0 with
   `finding_emitted: true`, and the finding reads back from the `5-execute` Q-Gate store with its
   type, title and detail intact; a residual at the threshold still emits nothing and exits 0.

2. **[PLAN-LB-07 D2]** **The guard measures the plan's own changes.** Replace `git diff --name-only
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

3. **[PLAN-LB-07 D3]** **The declared set includes the task step targets.** `_collect_declared_files` globs
   `TASK-*.json` directly under the plan directory, while task files are written to the plan's
   `tasks/` subdirectory, so the step-target half of the declared set is empty on a real plan and
   every file a task targets but `affected_files` omits counts as creep. Read tasks from the
   directory `manage-tasks` writes them to (through its path helper, not a second literal). Done
   when: a test that creates a task through the real `manage-tasks` add path, with a step target
   absent from `affected_files`, sees that target excluded from the residual; the existing fixture
   that writes `TASK-001.json` at the plan root is moved to the real location.

4. **[PLAN-LB-07 D4]** **Raising the threshold is no longer the way through.** The docstring and Step 6.5 promise a
   `phase_5.scope_creep_threshold` configuration source that the script never reads — the threshold
   is the CLI flag or the default 5. Either read the configured value (precedence: flag,
   configuration, default) or delete the promise from both places. The result reports which source
   supplied the threshold, and Step 6.5 states that a leaf does not pass `--threshold`: the
   configured value is the operator's knob and an over-threshold result is triaged, not tuned away.
   Done when: a test shows the configured value taking effect with no flag (or, under the
   alternative, a doc test shows the key is gone from both files); the output carries the threshold
   source on every measured shape.

5. **[PLAN-LB-07 D5]** **The tests stop asserting the defects, and every hardcoded finding type is a taxonomy member.**
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

6. **[PLAN-LB-11 D1]** **A `stage` verb in `git-workflow.py` that applies the allowlist.** `git-workflow stage --plan-id {plan_id} [--extra PATH --extra-reason TEXT]... [--dry-run]` resolves the worktree the way the file's other plan-bound verbs do, reads the candidate set from `git status --porcelain -z --untracked-files=all`, and partitions it: `allowed` (inside the allowlist), `outside_footprint` (tracked or untracked, not in the allowlist), `refused_sensitive` (matches the never-stage patterns of D2). It runs `git add -- <paths>` for `allowed` plus the named extras only — never `-A`, `-u` or `.` — and returns all three lists with counts and the allowlist's sources. If `outside_footprint` is non-empty and not fully covered by `--extra`, the verb stages nothing and returns `status: error, error: paths_outside_footprint` (exit 0, per the output contract), so the caller decides per path rather than getting a partial stage it did not ask for. The allowlist is the union of the plan's declared footprint (`references.json` `affected_files`), the paths already committed on the plan branch (`{base}...HEAD` name set), and tracked `.plan/` configuration the pipeline legitimately writes; the verify-first clause below settles the exact sources. If the allowlist cannot be established (no references, base ref unresolvable) the verb fails closed with a distinct error; it never falls back to "everything dirty". *Done when:* tests in a throwaway git worktree show (a) a dirty in-footprint file is staged, (b) a dirty tracked file outside the footprint yields `paths_outside_footprint` and an empty index, (c) the same file passes when named with `--extra` and a reason, (d) an unresolvable allowlist returns the distinct error and stages nothing.

7. **[PLAN-LB-11 D2]** **Secret-shaped files are never staged, with or without an escape.** Extend `standards/artifact-patterns.json` with a third pattern class beside `safe_patterns` and `uncertain_patterns` (for example `never_stage_patterns`: `.env`, `.env.*`, `*.pem`, `*.key`, `*.p12`, `*.pfx`, `id_rsa*`, `id_ed25519*`, `credentials*.json`, `*.keystore`), compiled by the existing `_compile_patterns` and matched with the same normalised relative path `scan_artifacts` already computes. `stage` refuses any candidate matching the class — reporting it under `refused_sensitive` and returning `status: error, error: sensitive_path_refused` — and `--extra` cannot override it; a file that really must be committed is committed by the operator by hand. `detect-artifacts` reports the same class as a separate list so the pre-commit scan and the staging verb read one pattern source. A tracked file that already matches (a committed test fixture) is not refused when merely modified, only reported, so existing repositories keep working. *Done when:* a test places an untracked `.env` and an untracked `server.pem` in the worktree beside an in-footprint edit, runs `stage`, and asserts the refusal, an index that contains neither file, and that adding `--extra .env --extra-reason x` changes nothing; a test asserts `detect-artifacts` lists both under the new key; a test asserts a tracked, modified fixture matching the class is reported and not refused.

8. **[PLAN-LB-11 D3]** **The escape is explicit and leaves a record.** Each `--extra` path requires a non-empty `--extra-reason`; for each one the verb writes a decision-log line naming the plan, the path, the reason and whether the path was tracked or untracked, and the result lists the extras under `staged_extra[]`. Extras are checked for containment in the worktree (no absolute path outside it, no `..` traversal, no path under a nested git boundary) before anything is staged. *Done when:* a test asserts the decision-log entry and the `staged_extra` row for an accepted extra; a test asserts `--extra` without a reason, and an extra that escapes the worktree, are refused with nothing staged.

9. **[PLAN-LB-11 D4]** **Every plan commit goes through the verb.** Rewrite Step 5 of `workflow-integration-git/SKILL.md` § "Workflow: Commit Changes" so staging is the `stage` call, its result is parsed, and a hand-written `git add` appears nowhere in the workflow; state what the caller does on each error (`paths_outside_footprint`: decide per path — leave it unstaged, or re-run with `--extra` and a reason; `sensitive_path_refused`: stop and report). Update the callers that load that workflow so they act on the new outcomes: the finalize dispatcher's commit instrumentation (`phase-6-finalize/SKILL.md` item 5f and the "Commit instrumentation contract" paragraph), the per-deliverable commit (`phase-5-execute/SKILL.md` Step 10a), the settlement commit in `plan-marshall/workflow/execution.md`, and the "Commit" operation in `phase-5-execute/standards/operations.md`. In item 5f, paths the step left dirty outside the footprint are named in the step's work-log line whether or not they were staged, so a swept-in file is distinguishable from a step-owned one. The four pathspec-bound `git add .plan/project-architecture` calls in `standards/architecture-refresh.md` are already limited to one tree and stay as they are. Record the enumeration of staging sites (document, section, form) in the PR body. *Done when:* a doc-contract test asserts that no document under `marketplace/bundles/plan-marshall/skills/` instructs a `git … add` other than the `stage` verb and the enumerated pathspec-bound exceptions, and that the Commit Changes workflow contains the `stage` invocation; the `workflow-integration-git/SKILL.md` canonical-invocation section documents `stage` and the argparse-parity check passes.

10. **[PLAN-LB-11 D5]** **An end-to-end regression for the original finding.** One test builds a plan fixture with a worktree, an in-footprint modification, an unrelated tracked modification and an untracked `.env`, runs the staging path the commit workflow documents, commits, and asserts via `git show --name-only` that the commit contains the in-footprint file only. *Done when:* that test fails against the current workflow's documented `git add` of the porcelain set and passes with the verb.

## Claim Labels

Carried in source order: bullets 1 to 18 from PLAN-LB-07; bullets 19 to 37 from PLAN-LB-11.

- OBSERVED: the guard passes `finding_type='scope_creep_warning'` to `add_qgate_finding` — `marketplace/bundles/plan-marshall/skills/phase-5-execute/scripts/scope_creep_check.py:176-185`
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: scope_creep_check.py _emit_finding (176-185) calls add_qgate_finding(..., finding_type='scope_creep_warning', ..., severity='warning').
- OBSERVED: `FINDING_TYPES` has fourteen members and `scope_creep_warning` is not one; `add_qgate_finding` returns `status: error` "Invalid finding type" for a non-member, and the `qgate add` CLI restricts `--type` to the same set — `marketplace/bundles/plan-marshall/skills/tools-file-ops/scripts/constants.py:96-121`, `marketplace/bundles/plan-marshall/skills/manage-findings/scripts/_findings_core.py:1051-1052`, `marketplace/bundles/plan-marshall/skills/manage-findings/scripts/manage-findings.py:456`
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: constants.py FINDING_TYPES (96-121) has 14 members, no scope_creep_warning; _findings_core.py 1051-1052 returns error 'Invalid finding type'; manage-findings.py 456 --type choices=FINDING_TYPES.
- OBSERVED: a rejected persist makes `cmd_check` print `status: error` / `error: finding_persist_failed` and return 1, so every over-threshold run fails — `scope_creep_check.py:232-252`
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: scope_creep_check.py cmd_check (232-252): failure from _emit_finding prints status error / error finding_persist_failed and returns 1.
- OBSERVED: the diff is `git diff --name-only {base_sha}..HEAD` with `base_sha` read from `references.json` `plan_creation_sha` — `scope_creep_check.py:105-113`, `:209-224`; the two-dot form compares the two commits' trees, so base-branch commits reachable from HEAD after a rebase or merge are counted, and uncommitted edits are not
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: scope_creep_check.py _git_diff_files (105-113) runs git diff --name-only {base_sha}..HEAD; cmd_check 209-224 reads plan_creation_sha from references.json.
- OBSERVED: `plan_creation_sha` is `git rev-parse HEAD` at the moment `manage-references create` runs, pinned on purpose "so the scope-creep guard survives later base moves" — `marketplace/bundles/plan-marshall/skills/manage-references/scripts/_references_crud.py:107-113`, `marketplace/bundles/plan-marshall/skills/manage-references/scripts/_references_core.py:31-35`
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: _references_crud.py _capture_creation_sha runs git rev-parse HEAD; cmd_create 109-113 pins it 'so the scope-creep guard survives later base moves'; _references_core.py 31-35 comment agrees.
- OBSERVED: a merge-base derivation already exists — `resolve_base_ref` and `compute_plan_branch_diff` (three-dot `{base_ref}...HEAD` united with porcelain working-tree state) at `_references_core.py:220-266`, `:308-340`
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: _references_core.py resolve_base_ref (220-266) and compute_plan_branch_diff (308-355): three-dot {base_ref}...HEAD diff unioned with status --porcelain --untracked-files=all.
- OBSERVED: Step 6.5 runs "after Step 6 completes its file-system changes but BEFORE running task verification", documents the `{plan_creation_sha}..HEAD` diff, and says the finding is persisted "via `manage-findings qgate add --type scope_creep_warning`" — `marketplace/bundles/plan-marshall/skills/phase-5-execute/SKILL.md:595`, `:602`, `:637`
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: phase-5-execute/SKILL.md Step 6.5: line 595 'BEFORE running task verification', line 602 {plan_creation_sha}..HEAD diff, line 637 'via manage-findings qgate add --type scope_creep_warning'.
- OBSERVED: `_collect_declared_files` globs `plan_dir.glob('TASK-*.json')`, while tasks are stored under `get_plan_dir(plan_id) / DIR_TASKS` with `DIR_TASKS = 'tasks'` — `scope_creep_check.py:125-139`, `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_tasks_core.py:273-275`, `constants.py:218`; the test fixture writes `TASK-001.json` at the plan root, matching the script rather than the real layout — `test/plan-marshall/phase-5-execute/test_scope_creep_check.py:63-67`
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: scope_creep_check.py _collect_declared_files globs plan_dir.glob('TASK-*.json'); _tasks_core.py get_tasks_dir = get_plan_dir/DIR_TASKS; constants.py 218 DIR_TASKS='tasks'; test fixture 63-67 writes TASK-001.json at plan root.
- OBSERVED: the threshold is `args.threshold` or `DEFAULT_THRESHOLD`; nothing reads `phase_5.scope_creep_threshold`, which appears only in the script docstring and Step 6.5 — `scope_creep_check.py:41-45`, `:198`, `phase-5-execute/SKILL.md:639` (a search of `marketplace/bundles/plan-marshall/skills` for the key returns those two files only)
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: scope_creep_check.py 198 uses args.threshold or DEFAULT_THRESHOLD; content search for scope_creep_threshold returns only scope_creep_check.py (docstring 43) and phase-5-execute/SKILL.md (639).
- OBSERVED: tests assert the rejection as intended — `test/plan-marshall/phase-5-execute/test_scope_creep_check.py:186-190` ("the (deliberately un-taxonomised) scope_creep_warning", `assert call['finding_type'] == 'scope_creep_warning'`), `:280-307` (rejection message naming the type), and `test/plan-marshall/phase-5-execute/test_qgate_persist_contract.py:50-53`, `:88-121` (drives the real primitive through the scope-creep path, asserts `finding_persist_failed` and that the store file does not exist)
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: test_scope_creep_check.py 186-190 and 280-307 assert the un-taxonomised type and rejection message; test_qgate_persist_contract.py 50-53, 88-121 drive the real primitive, assert finding_persist_failed and absent store.
- OBSERVED: a test pins the creation-commit base — `test_diff_grades_pinned_sha_despite_moved_base`, `test/plan-marshall/phase-5-execute/test_scope_creep_check.py:383-425`; `test_scope_creep_could_not_look.py` pins the `no_baseline_sha` reason
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: test_scope_creep_check.py test_diff_grades_pinned_sha_despite_moved_base at 406-425 (section from 383); test_scope_creep_could_not_look.py asserts reason no_baseline_sha with residual_count absent.
- OBSERVED: among literal `finding_type='…'` arguments in `marketplace/bundles/**/*.py`, the values are `anti-pattern`, `bug`, `pr-comment`, `sonar-issue`, `build-error`, `tip` and `scope_creep_warning`; only the last is outside the taxonomy — derived by one pattern search at HEAD, which does not cover types passed through a variable
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: Content search over category script: finding_type='...' literals outside {anti-pattern,bug,pr-comment,sonar-issue,build-error,tip,scope_creep_warning} = 0 hits; only scope_creep_warning is not in FINDING_TYPES.
- HYPOTHESIS: residual counts of 470 and 738 against 19 own files, and leaves passing `--threshold 1000`, as reported from two runs — confirm/refute by running the guard in a worktree whose base has advanced since plan creation, before and after deliverable 2 (verify-at-outline)
- HYPOTHESIS: a Q-Gate finding of the chosen type filed in phase `5-execute` is picked up by the Step 11 triage as Step 6.5 claims ("flows into the Step 11 triage loop alongside other verify findings") — confirm/refute at `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/verification-feedback.md` and `triage.md` § the finding-type filter the `build-runner` producer mode applies (verify-at-outline)
- HYPOTHESIS: nothing other than this guard consumes `plan_creation_sha` — a file-name search finds it only in `scope_creep_check.py`, `phase-5-execute/SKILL.md` and the two `manage-references` scripts; confirm/refute across `test/` and `.claude/` before deciding whether the field stays (verify-at-outline)
- Verify-first clause: decide the type question (new member versus existing member) before any code. A new member also becomes a legal plan-scoped store file name and a legal `--type` choice on every `manage-findings` verb, and must be placed in or out of the promotion subsets (`LESSON_TYPES`, `ARCHITECTURE_TYPES`) and documented in `manage-findings/standards/jsonl-format.md`. Record the choice and its reason in the plan's outline.
- Verify-first clause: confirm on a live plan directory that task files are under `tasks/` and that the guard's step-target union is empty there, before sizing deliverable 3.
- Verify-first clause: check what the base ref resolves to in the plan's worktree when `origin/{base_branch}` is absent or stale (offline, or a fork). `resolve_base_ref` falls back to the local branch name; decide whether a stale local base is measured or reported as `could_not_look`.
- OBSERVED: the commit workflow's staging step is one prose sentence followed by `git -C {worktree_path} add <specific-files>` — read at `marketplace/bundles/plan-marshall/skills/workflow-integration-git/SKILL.md` § "Workflow: Commit Changes" Step 5 (lines 130-137), at HEAD `6edefac32`; the workflow's stated purpose is "Commit all uncommitted changes" (line 67) and its Step 2 status read carries no path filter (line 91)
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: workflow-integration-git/SKILL.md: line 67 'Commit all uncommitted changes', Step 2 line 91 bare status --porcelain, Step 5 (130-137) one prose sentence then git -C {worktree_path} add <specific-files>.
- OBSERVED: `git-workflow.py` registers no staging verb; its verbs are `format-commit`, `analyze-diff`, `detect-artifacts` and the branch/worktree family, and the only `git add`-shaped call in the file is `git worktree add` — read at `marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/git-workflow.py` (function list and `main()` verb table, lines 2758 onward)
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: git-workflow.py main() verb table (2758-3097): format-commit, analyze-diff, detect-artifacts, branch/worktree verbs, baseline-reconcile; no staging verb; only add argv is 'worktree','add' at line 1569.
- OBSERVED: the related existing mechanism is the artifact scan: `scan_artifacts` walks the tree, drops plan state and ignored paths, and classifies matches against `safe_patterns` / `uncertain_patterns` loaded from `standards/artifact-patterns.json`; it detects build output and temp files for deletion and has no secret-shaped class and no effect on what is staged — read at `git-workflow.py` § `scan_artifacts` (lines 726-844), § `cmd_detect_artifacts` (lines 847-879) and `marketplace/bundles/plan-marshall/skills/workflow-integration-git/standards/artifact-patterns.json`
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: git-workflow.py scan_artifacts (726-844) and cmd_detect_artifacts (847-879) classify via safe/uncertain regexes; artifact-patterns.json has only build/temp/OS patterns, no secret class; nothing touches staging.
- OBSERVED: the only safeguard against committing secrets is the enforcement bullet "Never commit secrets, credentials, or `.env` files" — read at `workflow-integration-git/SKILL.md` line 17
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: workflow-integration-git/SKILL.md line 17 'Never commit secrets, credentials, or .env files'; content search finds no secret/credential/.env handling in git-workflow.py or artifact-patterns.json.
- OBSERVED: the finalize dispatcher commits after every `mutates_source: true` step by running a whole-tree `git status --porcelain` and, if non-empty, loading the Commit Changes workflow with a message and `push: false`; it passes no path set — read at `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md` item 5f (a)/(b) (lines 1251-1261) and the "Commit instrumentation contract" paragraph (line 545)
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: phase-6-finalize/SKILL.md item 5f (a) line 1253 whole-tree status --porcelain, (b) 1255-1261 loads workflow-integration-git with message, push false, no path set; line 545 commit instrumentation contract.
- OBSERVED: the execute phase uses the same workflow for the per-deliverable commit and the settlement commit, again with no path set — read at `marketplace/bundles/plan-marshall/skills/phase-5-execute/SKILL.md` Step 10a (lines 757-770), `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/execution.md` (lines 450-463) and `marketplace/bundles/plan-marshall/skills/phase-5-execute/standards/operations.md` § Git Operations → Commit
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: phase-5-execute/SKILL.md Step 10a (757-770), execution.md settlement commit (450-464) and operations.md Git Operations > Commit all load workflow-integration-git with message/push only, no path set.
- OBSERVED: the other staging calls in the bundle are four `git -C {worktree_path} add .plan/project-architecture` lines, each bound to one tracked tree — read at `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/architecture-refresh.md` lines 262, 398, 648, 712; `standards/push.md` loads Commit Changes only against an asserted-clean tree and stages nothing (lines 125-129) — ⛔ RE-SCOPED 2026-10-08 at `726ca857a`: incomplete. Those four lines and the `push.md` reading hold, but they are not the only other staging call in the bundle: `plan-orchestrator/scripts/_orchestrator_land.py` runs `git add -A -- {ledger root}` per ledger root for the `land` verb. It predates the commit this claim was read at, so it was missed, not added since. For PLAN-LB-11 D4 the staging-site population is therefore six, not five: the land script is path-bound to ledger roots and is not on the plan commit seam, so it stays as it is and is listed among the enumerated exceptions in the PR body, next to the `architecture-refresh.md` calls
  - verdict: contradicted | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: yes | evidence: architecture-refresh.md has the four add .plan/project-architecture lines and push.md 125-129 holds, but plan-orchestrator/scripts/_orchestrator_land.py line 338 also stages: _git(checkout,'add','-A','--',spec).
- OBSERVED: `manage-references compute-footprint` cannot serve as the allowlist: it returns the `{base}...HEAD` diff unioned with the porcelain working-tree state, so every dirty or untracked file is in the set by construction and a check against it passes everything — read at `marketplace/bundles/plan-marshall/skills/manage-references/scripts/_references_core.py` § `compute_plan_branch_diff` (lines 310-345)
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: _references_core.py compute_plan_branch_diff (308-355) returns set(diff {base_ref}...HEAD) | set(porcelain --untracked-files=all paths), so every dirty or untracked file is a member.
- OBSERVED: the declared footprint lives in `references.json` under `affected_files` (expected modifications; read-intent paths are kept under a separate key) — read at `marketplace/bundles/plan-marshall/skills/manage-references/scripts/_references_crud.py` lines 20-34
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: _references_crud.py 22-40: _AFFECTED_FILES_FIELD='affected_files' (expected modifications) and separate _READ_INTENT_FILES_FIELD='read_intent_files' for read-intent paths.
- OBSERVED: the source spec's cited location for the whole-tree read (`git-workflow.py:2295`) has moved; the porcelain read in that file is now in `_detect_worktree_state` at line 2335 and belongs to the rebase verb, not to the commit seam. The commit seam's whole-tree read is the workflow document's Step 2 and the dispatcher's item 5f(a), as cited above
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: git-workflow.py _detect_worktree_state (2296) runs status --porcelain at line 2335 for the worktree-rebase-to verb; content search shows it is the file's only porcelain read.
- HYPOTHESIS: finalize steps legitimately change tracked files outside the declared footprint often enough that a refuse-by-default verb would stall finalize unless the caller has a cheap, correct `--extra` path: `finalize-step-simplify` edits outside the plan footprint, the pre-push quality gate's `ruff` auto-fix rewrites files, lessons-housekeeping edits skill documents — confirm/refute by reading each `mutates_source: true` step document under `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/`, `workflow/` and `.claude/skills/finalize-step-*/SKILL.md` for the paths it may write (verify-at-outline)
- HYPOTHESIS: a `mutates_source: true` step's return TOON carries no list of the paths it changed today, so item 5f has no per-step entitlement to pass as extras — confirm/refute at `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-finalize-step.md` (return contract) and `phase-6-finalize/SKILL.md` item 5f (verify-at-outline)
- HYPOTHESIS: `affected_files` stores entries the verb can match with the containment rule the footprint code already has (named files, directories, globs) — confirm/refute at `marketplace/bundles/plan-marshall/skills/manage-references/scripts/_references_crud.py` § `cmd_sync_affected_files` (verify-at-outline)
- Verify-first clause: before scoping D1, settle the allowlist's sources against the first hypothesis. The floor is declared `affected_files` ∪ the committed `{base}...HEAD` set ∪ the tracked `.plan/` configuration paths the pipeline writes. Decide how a finalize step's legitimate out-of-footprint edits enter: (i) the step declares its writable paths in frontmatter and the dispatcher passes them, (ii) the step returns `changed_paths` and item 5f passes those as extras with the step id as the reason, or (iii) tracked-and-modified paths outside the footprint are staged but reported, and only untracked paths outside it are refused. Option (iii) is the smallest change and still stops the untracked-secret and stray-new-file cases; (i) or (ii) is stricter. Choose by what the step documents show, and record the choice in the PR body
- Verify-first clause: before scoping D4, re-derive the staging-site population by searching every document under `marketplace/bundles/` and `.claude/skills/` for `git … add`, `commit -a` and loads of the Commit Changes workflow, and compare it with the five sites named above; a site this spec missed is added to D4, not left on the old path
- Verify-first clause: the verb must run from a plan worktree and from the main checkout alike; confirm which resolver the plan-bound verbs in `git-workflow.py` use (`_resolve_worktree_path_for_plan`) and that the `--project-dir` form used by non-plan callers has a defined behaviour (refuse, since there is no plan footprint) before writing the parser
- OBSERVED: PR #1700 (`78ba60f41`, `fix(inbox): gate restart-check on live_count, keep closure after drain`) deleted all 2038 files under `.plan/archived-orchestrators/` from `main` while its description names five source and test files — `git show --stat 78ba60f41 -- .plan/archived-orchestrators` reports 2038 deletions, 184695 lines. The tree was restored from `78ba60f41^` afterwards. This is the defect of this plan in the destructive direction: a finalize commit staged far more than the plan's change, and a deletion of tracked files outside the footprint passed every gate
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: git show --shortstat 78ba60f41 -- .plan/archived-orchestrators: 2038 files changed, 184695 deletions; PR body lists 5 source/test files; b9ef6893e (#1708) later re-added the tree (restore source ^ not checked).
- HYPOTHESIS: the #1700 deletion entered through the prose staging seam (a whole-tree `git add` in a checkout where the directory was absent) — confirm/refute against that plan's archived work log and commit sequence; if it entered another way (a rebase or a merge resolution), the guard of this plan must also cover that path (verify-at-outline)
- Verify-first clause: the staging guard must treat a DELETION of a tracked path outside the plan's footprint as out-of-footprint exactly like an addition, and must not let the tracked-modified allowance (the default escape for finalize steps) cover deletions. Settle this before scoping the escape for legitimate out-of-footprint edits
- HYPOTHESIS: recurrence, folded in on 2026-10-08 from inbox message `lb-22-finalize-loop-control-002.md`: in plan `lb-22-finalize-loop-control` the guard returned `finding_persist_failed` on every call above the threshold (nine failures) and so never filed a finding, and it measured upstream history — its first residual set was three orchestrator ledger files no branch commit had touched, and after the finalize rebase it reported 5625 residual files. Reported by that plan's retrospective, not reproduced here; it matches the PLAN-LB-07 claims above and adds one detail for PLAN-LB-07 D2: commits that land on the base branch between plan creation and branch creation are counted too — confirm/refute at `marketplace/bundles/plan-marshall/skills/phase-5-execute/scripts/scope_creep_check.py` § the diff-base read (verify-at-outline)
- HYPOTHESIS: folded in on 2026-10-08 from inbox message `lb-22-finalize-loop-control-004.md`: `references.affected_files` does not grow when triage creates a fix task. In that plan the list held 48 entries through seven fix tasks while nine realized paths were undeclared, because `sync-affected-files` derives the list from the outline's deliverables and a fix task declares its files on the task — confirm/refute at `marketplace/bundles/plan-marshall/skills/manage-references/scripts/_references_crud.py` § `cmd_sync_affected_files` (verify-at-outline)
- Verify-first clause: if the hypothesis above holds, the declared footprint alone under-covers every plan that ran a fix task. For PLAN-LB-11 D1 the allowlist floor already unions the committed `{base}...HEAD` set, which covers a fix task's committed files; a fix task's files that are still uncommitted at stage time are in neither source, so admit them through the task step targets, the same source PLAN-LB-07 D3 reads. Consumers outside this plan that gate on `affected_files` (the plugin-doctor step choosing whole-tree mode is the reported one) are not fixed here: name them in the PR.

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
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/git-workflow.py` — new `stage` verb and handler; never-stage class wired into the pattern loader and `scan_artifacts` / `cmd_detect_artifacts` output (D1, D2, D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-git/standards/artifact-patterns.json` — `never_stage_patterns` class (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-git/SKILL.md` — Commit Changes Step 5, enforcement bullets, script table, `stage` reference and canonical invocation, `detect-artifacts` output (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md` — "Commit instrumentation contract" paragraph and item 5f (a)/(b) (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-5-execute/SKILL.md` — Step 10a per-deliverable commit (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/execution.md` — settlement commit (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-5-execute/standards/operations.md` — § Git Operations → Commit (D4)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-references/scripts/_references_core.py` — a committed-set-only helper beside `compute_plan_branch_diff`, if the verb cannot reuse the existing one without its porcelain half (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-finalize-step.md` — only under allowlist option (i) or (ii): a declared or returned path set for mutating steps (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/workflow-integration-git/standards/git-commit-standards.md` — only if it restates the staging rule (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/persona-security-expert/standards/secrets-handling.md` — cross-reference to the mechanical guard, only if it describes the commit seam (verify-at-outline)
- OBSERVED: `test/plan-marshall/workflow-integration-git/test_git_workflow_artifacts.py` — never-stage class in the scan output (D2)
- HYPOTHESIS: `test/plan-marshall/workflow-integration-git/test_git_workflow_stage.py` — new tests for the verb, the refusal, the escape and the end-to-end regression (verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/workflow-integration-git/test_commit_staging_doc_contract.py` — new doc-contract test over the staging-site population (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none.
- One containment rule serves both halves: the footprint match the staging verb applies and the declared set the guard compares against are the same rule, written once and shared.
- Overlaps with: PLAN-LB-22, PLAN-LB-24 and PLAN-LB-25 on `phase-6-finalize/SKILL.md` (this plan edits item 5f and the commit-instrumentation paragraph only); PLAN-LB-22 and PLAN-LB-26 on `plan-marshall/workflow/execution.md`; PLAN-LB-26 on `phase-5-execute/SKILL.md` and on `test/plan-marshall/phase-5-execute/test_scope_creep_check.py`. Sequence against those four.
- May run together with: PLAN-LB-23 and PLAN-LB-28, and with PLAN-LB-14, PLAN-LB-29, PLAN-LB-30 and PLAN-LB-31.

### Carried sequencing notes

Copied from the source specs. They use the plan ids from before the regrouping; resolve each through
the id map below. Where a carried "Depends on" or "Overlaps with" line disagrees with the bullets above,
the bullets above are current.

From PLAN-LB-07:

- Depends on: none.
- Overlaps with: PLAN-LB-06 (`phase-5-execute/SKILL.md` — that plan edits the envelope and return-contract sections, this one Step 6.5 only; `triage.md` if this plan adds disposition guidance), PLAN-LB-08 (`manage-findings` — that plan changes what a re-emitted Q-Gate finding does; this guard re-emits the same title and detail on every task while the residual is unchanged, so once PLAN-LB-08 lands an accepted scope-creep finding stays accepted instead of being reopened per task. No file collision unless a type member is added to documents PLAN-LB-08 also edits; sequence if so).
- Adjacent to: `manage-references` footprint verbs (`compute-footprint`, `capture-footprint`), which already use the merge-base derivation and are not changed.
- Left out on purpose: the `WORKTREE:` dispatch-header shape (process-compliance PLAN-27 deliverable D2) — a separate contract with a separate surface.

From PLAN-LB-11:

- Depends on: none.
- Overlaps with: PLAN-LB-07 (`phase-5-execute/SKILL.md` — the scope-creep guard compares touched paths with the declared footprint at the same chain-tail point; share the containment rule rather than writing a second one, and sequence the two); PLAN-LB-02, PLAN-LB-09 and PLAN-LB-10 (`phase-6-finalize/SKILL.md`, different items); PLAN-LB-05 and PLAN-LB-06 (`plan-marshall/workflow/execution.md`, different sections). All document overlaps; none blocks.
- Adjacent to: `phase-6-finalize/scripts/post_run_source_guard.py` observes dirty tracked paths after `mutates_source: false` steps and is a different guard — not merged with this one and not edited; `phase-6-finalize/standards/architecture-refresh.md` keeps its pathspec-bound `git add`; `.claude/skills/cloud-plan-lane/SKILL.md` has its own "never `git add -A`" rule for a lane with no executor and is not changed; `manage-references compute-footprint` keeps its current meaning.
- Left out on purpose: the rest of truthful-signals PLAN-TRUTH-170 (re-fire records and the `ci_verify` fold are PLAN-LB-10; `display_detail` enforcement, `[OUTCOME]` emission and the `head_at_completion` derivation are not in this epic); a scan of staged file CONTENT for secrets (this plan matches paths only); pushing the guard into a git pre-commit hook.

### Id map

| Id before the regrouping | Now |
|---|---|
| PLAN-LB-01 | PLAN-LB-23 (all deliverables) |
| PLAN-LB-02 | PLAN-LB-22 (all deliverables) |
| PLAN-LB-03 | PLAN-LB-28 (all deliverables) |
| PLAN-LB-04 | PLAN-LB-25 (all deliverables) |
| PLAN-LB-05 | D1 and D2 to PLAN-LB-25; D3 to PLAN-LB-24; D4 to PLAN-LB-26; D5 to PLAN-LB-22 |
| PLAN-LB-06 | PLAN-LB-26 (all deliverables) |
| PLAN-LB-07 | PLAN-LB-27 (all deliverables) |
| PLAN-LB-08 | PLAN-LB-26 (all deliverables) |
| PLAN-LB-09 | PLAN-LB-25 (all deliverables) |
| PLAN-LB-10 | PLAN-LB-22 (all deliverables) |
| PLAN-LB-11 | PLAN-LB-27 (all deliverables) |
| PLAN-LB-12 | PLAN-LB-23 (all deliverables) |
| PLAN-LB-13 | PLAN-LB-28 (all deliverables) |
| PLAN-LB-14 | unchanged, still PLAN-LB-14 |
| PLAN-LB-15 | PLAN-LB-29 (all deliverables) |
| PLAN-LB-16 | PLAN-LB-30 (all deliverables) |
| PLAN-LB-17 | PLAN-LB-29 (all deliverables) |
| PLAN-LB-18 | PLAN-LB-24 (all deliverables) |
| PLAN-LB-19 | PLAN-LB-24 (all deliverables) |
| PLAN-LB-20 | D1 to D3 to PLAN-LB-30; D4 and D5 to PLAN-LB-31 |
| PLAN-LB-21 | PLAN-LB-31 (all deliverables) |

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/live-blockers/plans/PLAN-LB-27-plan-footprint.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
