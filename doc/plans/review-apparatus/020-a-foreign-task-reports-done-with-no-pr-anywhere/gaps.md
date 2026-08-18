# Gaps — 020-a-foreign-task-reports-done-with-no-pr-anywhere

Actionable follow-up derived from `verification.md`. Each entry is a task a later plan can pick up
without re-deriving the analysis.

## G1 — Pass the branch the foreign change is on to `ci pr landing-state`

- **Severity:** major
- **Kind:** bug
- **Where:** `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/foreign_pr_gate.py:155-166`
  (`_resolve_landing_state`); consumer contract at
  `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py:664-684`
  (`_resolve_landing_branch`); documented default at
  `marketplace/bundles/plan-marshall/skills/tools-integration-ci/standards/leaf-command-reference.md:34`
- **Evidence:** the gate builds
  `[sys.executable, executor, _CI_NOTATION, '--project-dir', repo_root, 'pr', 'landing-state']` — no
  `--branch`. The plan's D1 specifies the verb as `ci pr landing-state --project-dir P --branch B`.
  With `--branch` absent, `_resolve_landing_branch` falls back to
  `github_ops.run_git(['rev-parse', '--abbrev-ref', 'HEAD'])` in the foreign checkout. CONFIRMED by
  reading both files at HEAD `61a43e53`.
- **Impact:** the gate classifies whatever ref the foreign working tree happens to have checked out at
  finalize time, not the ref the foreign change was committed to. Reasoned from the handler body: a
  foreign checkout sitting on a pushed default branch yields no tip-matching PR and non-empty
  `git branch -r --contains`, i.e. `pushed_no_pr` — a **false archive refusal** for a plan whose
  foreign work is complete. A checkout switched away from the work branch means the work branch is
  never examined at all.
- **Task:** carry the foreign change's branch to the verb. Either (a) record the branch alongside the
  foreign path when the foreign change is committed and thread it into `_resolve_landing_state` as
  `--branch`, or (b) if no branch record exists, make the gate resolve the branch explicitly (e.g. the
  foreign checkout's branch that contains the deliverable's declared paths' latest commit) and pass it,
  and fail closed with a named reason when it cannot be determined — never silently classify HEAD.
- **Done when:** `_resolve_landing_state` emits `--branch` on every invocation, a test drives the real
  `_resolve_landing_state` (not the injected seam) and asserts the argv contains `--branch` with the
  expected value, and a test asserts the gate errors rather than classifying when the branch cannot be
  resolved.
- **Suggested grouping:** phase-6-finalize / foreign-PR landing gate

## G2 — Refuse `unpushed` as well as `pushed_no_pr`, or state in the gate why it does not

- **Severity:** major
- **Kind:** bug
- **Where:** `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/foreign_pr_gate.py:78`
  (`BLOCKING_LANDING_STATE = 'pushed_no_pr'`) and `:334`; test that locks the behaviour in at
  `test/plan-marshall/phase-6-finalize/test_foreign_pr_gate.py:101`
  (`test_unpushed_foreign_deliverable_clears`); operator-facing text at
  `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/archive-plan.md:49`
- **Evidence:** the gate refuses on exactly one state. The plan's Goal reads *"A foreign task cannot
  reach `done` while its change has no pull request"*; the plan's D1 body reads *"refuse to archive
  while any is `pushed_no_pr`"*. `unpushed` means the change is on no remote at all, so it certainly
  has no pull request — and the test asserts `result['status'] == 'clear'`. CONFIRMED by reading the
  gate and running the test file (56 passed).
- **Impact:** the strictly worse case passes the gate. A foreign change committed locally and never
  pushed archives cleanly, which is the same "reports done with no PR anywhere" outcome the plan
  exists to prevent, one step earlier in the lifecycle.
- **Task:** decide the intended set explicitly. Either widen the refusal to
  `{'pushed_no_pr', 'unpushed'}` — renaming the constant to a set, e.g. `BLOCKING_LANDING_STATES` —
  updating `archive-plan.md`, the module docstring and the tests together; or, if `unpushed` is
  genuinely meant to clear, say so in the gate docstring and in `archive-plan.md` with the reason,
  and reconcile the plan's Goal sentence in the same change.
- **Done when:** a single named constant holds the blocking set, `archive-plan.md` and the docstring
  agree with it, and a test asserts the gate's disposition for `unpushed` against that constant rather
  than against a literal.
- **Suggested grouping:** phase-6-finalize / foreign-PR landing gate

## G3 — Exclude read-intent paths from the gate's blocking population

- **Severity:** major
- **Kind:** bug
- **Where:** `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/foreign_pr_gate.py:186-222`
  (`_foreign_paths_by_deliverable`);
  `marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/manage-solution-outline.py:505-547`
  (`_annotate_foreign`); the existing helper it should use at
  `marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/_plan_parsing.py:455`
  (`deliverable_write_set`)
- **Evidence:** both functions select on `entry.get('foreign')` alone and never read
  `entry['intent']`, although `_extract_affected_files` returns `{'path': str, 'intent': str | None}`
  (`_plan_parsing.py:447`) and `deliverable_write_set`'s docstring states the repository's own rule:
  *"every `affected_files` **or** `mutation_scope` entry whose declared intent is not
  `STEP_INTENT_READ`"*. CONFIRMED by reading all three functions.
- **Impact:** a foreign path a deliverable declares `(read)` — a file consulted in another repository
  and left untouched — enters the gate's population. The gate then demands a landing state, and can
  refuse to archive, for a repository the plan never wrote to. `survey_scope` is by definition the
  read-only field and is stamped and iterated in full.
- **Task:** derive the gate's population from the declared **write** set, not the declared surface.
  Have `_annotate_foreign` stamp intent-bearing entries as today (the column is advisory and should
  keep describing the whole surface) but have `_foreign_paths_by_deliverable` drop entries whose
  `intent` is `STEP_INTENT_READ`, and drop `survey_scope` from its field list — or route it through
  `deliverable_write_set` so one helper owns the rule.
- **Done when:** a gate test with a foreign `(read)` `affected_files` entry and a foreign
  `survey_scope` entry yields `foreign_deliverable_count: 0` / `status: clear`, while a foreign
  `(write-new)` entry in the same deliverable still blocks.
- **Suggested grouping:** phase-6-finalize / foreign-PR landing gate

## G4 — Correct the D0 single-seam finding: `done` is written in two places

- **Severity:** major
- **Kind:** false-report-claim
- **Where:** `doc/plans/review-apparatus/020-a-foreign-task-reports-done-with-no-pr-anywhere/report-01.md`
  § D0 ("`done` is written in exactly one place: `manage-tasks/scripts/_tasks_crud.py::cmd_update`");
  the unreported second writer is
  `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_cmd_step.py:73`
- **Evidence:** `_cmd_step.py:73` reads
  `task['status'] = 'failed' if has_failed else 'done'`, inside the `all_terminal` branch of the
  `manage-tasks step` verb. `git show 9c679c99^:.../\_cmd_step.py | grep -n "task\['status'\]"`
  returns the same line 73, so it was present when the report was written. Backing search:
  `grep -rn "'status'\] = " marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/*.py`
  → four hits, two in `_cmd_step.py`, one in `_tasks_crud.py`. CONFIRMED.
- **Impact:** the plan's HYPOTHESIS claim-label *"Task done-ness is decided at a single, locatable
  seam"* was recorded as confirmed on evidence the tree contradicts. Any later plan that reads this
  report and moves enforcement to "the" completion seam will change `cmd_update` and miss the
  step-driven path that the phase-5 task runner actually uses.
- **Task:** correct the D0 finding in place — name both writers, identify which one the phase-5 task
  runner drives, and restate the claim-label verdict as "two seams, both locatable" rather than one.
  If a later plan intends to enforce at the `done` transition, it must cover both.
- **Done when:** `report-01.md` § D0 names `_cmd_step.py:73` alongside `_tasks_crud.py:667`, and the
  claim-label verdict for the single-seam HYPOTHESIS is restated accordingly.
- **Suggested grouping:** manage-tasks / completion seam

## G5 — Give the pre-archive gate a caller that is not prose

- **Severity:** minor
- **Kind:** incomplete
- **Where:** only invocation site is
  `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/archive-plan.md:41-45`;
  no code path calls it — `grep -rn "foreign_pr_gate"` over the repo returns that prose site, the
  module's own docstring at `foreign_pr_gate.py:58`, and two test references
- **Evidence:** the gate's enforcement depends entirely on an LLM dispatcher executing a bash block in
  a standards document and correctly branching on the returned `status`. The plan's D2 states
  *"Prose that no gate reads must not be the record of a blocking condition"*. CONFIRMED by the
  repo-wide grep.
- **Impact:** the blocking condition this plan created is enforced by the same class of mechanism the
  plan was written to eliminate. A dispatcher that skips or misreads the section archives the plan
  with a stranded foreign change, and nothing detects it.
- **Task:** either register the gate as a real finalize step with its own frontmatter and `order`
  (running immediately before `archive-plan`), or have `manage-status archive` refuse when the gate
  has not recorded a `clear` verdict for the plan. Add a test that exercises the enforcement path, not
  just `check()`.
- **Done when:** a test fails if the enforcement is removed — i.e. it drives the archive path (step
  dispatch or `manage-status archive`) with a `pushed_no_pr` foreign deliverable and asserts the
  archive does not happen.
- **Suggested grouping:** phase-6-finalize / foreign-PR landing gate

## G6 — Document `pr landing-state` on the three CI surfaces that still omit it

- **Severity:** minor
- **Kind:** stale-doc
- **Where:**
  - `marketplace/bundles/plan-marshall/skills/tools-integration-ci/SKILL.md:310` — § Canonical
    invocations, `### pr`, the `Sub-verbs:` enumeration
  - `marketplace/bundles/plan-marshall/skills/tools-integration-ci/standards/api-contract.md:136-148`
    — § "PR Operations" response-field table
  - `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md:1813-1822` — § Scripts
    inventory table, and the § Canonical invocations preamble listing the skill's entry-point scripts
- **Evidence:** the sub-verb line reads
  `` `view`, `list`, `reply`, `resolve-thread`, `thread-reply`, `reviews`, `comments`,
  `wait-for-comments`, `merge`, `auto-merge`, `safe-merge`, `merge-queue`, `update-branch`, `close`,
  `ready`, `submit-review`, `edit`, `prepare-body`, `prepare-comment`, `create`. `` — no
  `landing-state`. The api-contract PR table gives a "Response fields" row for every other `pr` read
  verb; `landing-state`'s fields (`branch`, `tip_sha`, `pushed`, `pr_count`, `landing_state`,
  `landing_states`) appear nowhere. `grep -rn "foreign" phase-6-finalize/` returns only
  `archive-plan.md` and unrelated `foreign-safe` lock prose, so `foreign_pr_gate.py` is the only one of
  the eight scripts in that directory with no Scripts-table row. CONFIRMED.
- **Impact:** the verb and the gate are invisible to a reader working from the canonical surfaces, and
  their contracts are unstated where every sibling's contract lives.
- **Task:** add `landing-state` to the `### pr` sub-verb list with a fenced canonical invocation; add a
  `pr landing-state` row to the api-contract PR Operations table naming its required/optional args and
  its response fields; add a `scripts/foreign_pr_gate.py` row to the phase-6-finalize Scripts table and
  name it in the § Canonical invocations preamble with a `check --plan-id` block.
- **Done when:** all three surfaces name the verb/script, and the response-field row matches the dict
  returned by `cmd_pr_landing_state`.
- **Suggested grouping:** tools-integration-ci + phase-6-finalize / documentation

## G7 — Extend the doc-parity test from `checks` verbs to `pr` verbs

- **Severity:** minor
- **Kind:** missing-test
- **Where:** `test/plan-marshall/tools-integration-ci/test_ci_base.py:1205-1220` (`_CHECKS_ROW`,
  `_documented_checks_verbs`)
- **Evidence:** the existing parity test derives the documented population from a `^\|\s*`checks
  (?P<verb>...)`` row regex against `leaf-command-reference.md`. `Grep _PR_ROW|pr \(\?P<verb>` over
  `test/` → no matches. CONFIRMED — nothing enforces that a registered `pr` sub-verb is documented.
- **Impact:** G6 landed and stayed. Any future `pr` verb can be added with no documentation and no
  test failure.
- **Task:** mirror the `checks` parity check for `pr`: derive the registered sub-verbs from the
  provider handler map (`github_ops.py`'s `('pr', ...)` dispatch table) and assert every one has a row
  in `leaf-command-reference.md` and in `api-contract.md` § PR Operations, with a documented exemption
  list for provider-specific verbs if one is genuinely needed.
- **Done when:** the new test fails if a `pr` sub-verb is registered without a documentation row, and
  passes on the tree once G6 is done.
- **Suggested grouping:** tools-integration-ci / documentation

## G8 — Stamp `foreign` on the single-deliverable read verbs, and document the column

- **Severity:** minor
- **Kind:** incomplete
- **Where:**
  `marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/manage-solution-outline.py:495`
  (`_annotate_foreign` called only from `cmd_list_deliverables`) and `:550` (`_lookup_deliverable`,
  which backs both `read --deliverable-number` and `get-deliverable`); docs at
  `marketplace/bundles/plan-marshall/skills/manage-solution-outline/SKILL.md:410-414`
- **Evidence:** `_lookup_deliverable` calls `extract_deliverables` and returns the matched record with
  no annotation pass. `grep -rn "foreign"` over `manage-solution-outline/SKILL.md` and
  `standards/*.md` → no hits. The SKILL.md worked example still shows `affected_files` as bare path
  strings, with neither `intent` nor `foreign` and no deliverable roll-up. `SKILL.md:175` asserts the
  two single-deliverable read forms return "byte-identical output"; the divergence is now between them
  and `list-deliverables`. CONFIRMED.
- **Impact:** a consumer that fetches one deliverable gets a record shaped differently from the same
  deliverable fetched through `list-deliverables`, and the column's existence is discoverable only by
  reading the gate's source.
- **Task:** call `_annotate_foreign` from `_lookup_deliverable` (or from both `cmd_read` and
  `cmd_get_deliverable`) so all three verbs emit the same record shape; update the SKILL.md worked
  example to show `affected_files` entries as `{path, intent, foreign}` plus the deliverable roll-up;
  add a short § describing what `foreign` means and who consumes it.
- **Done when:** a test asserts `read --deliverable-number N` and `list-deliverables` return the same
  keys for the same deliverable, and the SKILL.md example matches the emitted shape.
- **Suggested grouping:** manage-solution-outline / foreign column

## G9 — Make some coverage ratio actually separate host from foreign paths

- **Severity:** minor
- **Kind:** incomplete
- **Where:** no site consumes the column — `grep -rn "foreign"` over
  `marketplace/bundles/plan-marshall/skills/manage-metrics/`,
  `.../plan-retrospective/` and `.../manage-execution-manifest/` → no hits. The nearest declared-file
  counter is `manage-metrics.py:2603` (`_count_affected_files`), which reads
  `references.json::affected_files`, a different substrate
- **Evidence:** the plan's D2 ⚠ clause justifies the column with *"every coverage ratio silently pools
  host paths with foreign ones — the plan whose failure motivated this one pooled 23 host paths with 8
  foreign ones in its own coverage figures"*. The column now exists and exactly one consumer (the
  gate) reads it. CONFIRMED by the greps above.
- **Impact:** the defect D2 names as its second, standalone reason is still present in every computed
  figure; only the data needed to fix it now exists.
- **Task:** identify the coverage figure the plan refers to (start from `manage-metrics`'
  `files_modified` denominator and the retrospective's declared-surface recall check), then either
  report host and foreign counts separately or exclude foreign paths from a host-scoped ratio with the
  exclusion stated in the payload.
- **Done when:** at least one emitted coverage figure carries a host/foreign split (or a documented
  exclusion), and a test asserts the split against a fixture containing both populations.
- **Suggested grouping:** manage-metrics / foreign column consumers

## G10 — Cover the gate's three subprocess seams with real tests

- **Severity:** minor
- **Kind:** missing-test
- **Where:** `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/foreign_pr_gate.py:88-180`
  (`_list_deliverables`, `_resolve_repo_root`, `_resolve_landing_state`);
  `test/plan-marshall/phase-6-finalize/test_foreign_pr_gate.py:38-63` (`_run` injects all three)
- **Evidence:** `Grep _resolve_landing_state|_list_deliverables|_resolve_repo_root` over `test/`
  returns matches only in `audit-archived-plan-retrospectives`, `manage-architecture` and
  `manage-solution-outline` — all unrelated symbols. Every gate test passes
  `deliverables_loader` / `root_resolver` / `landing_resolver`. CONFIRMED.
- **Impact:** the argv the gate actually builds (G1's defect), the TOON parse paths, the empty-stdout
  branches and the `git rev-parse --show-toplevel` handling are exercised by nothing. The seams were
  split out "so the orchestration body is testable" and the seams themselves were then left untested.
- **Task:** add tests that call each seam with `subprocess.run` monkeypatched, asserting the argv
  (including `--project-dir`, and `--branch` once G1 lands), the empty-stdout error shape, and the
  unparseable-TOON error shape.
- **Done when:** each of the three seam functions is entered by at least one test, and one of them
  asserts the full argv list.
- **Suggested grouping:** phase-6-finalize / foreign-PR landing gate

## G11 — Reconcile the two bases used to resolve a relative foreign path

- **Severity:** minor
- **Kind:** bug
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/_plan_parsing.py:95`
  (joins a relative path onto `project_root`) vs
  `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/foreign_pr_gate.py:120-140`
  (`os.path.dirname(path)` + `os.path.isdir()` against the process cwd)
- **Evidence:** `is_foreign_path` computes
  `os.path.normpath(candidate if os.path.isabs(candidate) else os.path.join(root, candidate))`;
  `_resolve_repo_root` computes `directory = os.path.dirname(path) or path` and calls
  `os.path.isdir(directory)` with no anchoring. CONFIRMED by reading both.
- **Impact:** a `../other-repo/...` entry is classified against the git toplevel and then resolved
  against whatever cwd the gate runs in. They coincide only when the gate runs from the checkout root;
  otherwise the path is classified foreign and then reported unresolvable, which fails the gate closed
  for the wrong reason. Related: `check()` resolves `project_root` at line 261 and never uses it for
  classification, because `list-deliverables` (which does the classifying, in a subprocess) accepts
  only `--plan-id` and has no way to be told a root.
- **Task:** anchor `_resolve_repo_root` on the same `project_root` the gate resolved — join relative
  paths onto it before `dirname`/`isdir` — and either give `list-deliverables` an explicit
  project-root argument the gate passes, or state in the gate docstring that the guard depends on cwd
  inheritance and assert that dependency in a test.
- **Done when:** a gate test with a `../`-relative foreign path and a cwd that is not the checkout root
  resolves the same repository root as the classifier, and the `project_root` the gate resolves is
  either used or documented as advisory.
- **Suggested grouping:** phase-6-finalize / foreign-PR landing gate

## G12 — Fix the `LANDING_STATES` ordering comment

- **Severity:** minor
- **Kind:** stale-doc
- **Where:** `marketplace/bundles/plan-marshall/skills/tools-integration-ci/scripts/ci_base.py:814`
- **Evidence:** the comment reads *"#: The closed set of landing states, in refuse-most-first
  precedence order."* immediately above
  `LANDING_STATES: tuple[str, ...] = ('merged', 'pr_open', 'pushed_no_pr', 'unpushed')`. The only
  refused state, `pushed_no_pr`, is third; the tuple is ordered landed-first. CONFIRMED.
- **Impact:** a reader deriving refusal precedence from the tuple order gets the opposite of the
  intended reading, and a future consumer that iterates the tuple "refuse-most-first" would be wrong.
- **Task:** reword to describe the actual ordering (most-landed first, matching the check order in
  `derive_landing_state`), or reorder the tuple and update every consumer that relies on its order.
- **Done when:** the comment and the tuple agree, and `derive_landing_state`'s check order matches the
  documented reading.
- **Suggested grouping:** tools-integration-ci / landing-state verb

## G13 — Give the gate an actionable message on a provider that has no `landing-state`

- **Severity:** minor
- **Kind:** omission
- **Where:** registration is github-only at
  `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_ops.py:1834-1868`;
  the gate has no provider check at
  `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/foreign_pr_gate.py:155-180`;
  the constraint is stated only at
  `marketplace/bundles/plan-marshall/skills/tools-integration-ci/standards/leaf-command-reference.md:34`
  ("**GitHub provider only.**")
- **Evidence:** `grep -rn "landing"` over `workflow-integration-gitlab/` returns nothing. On a
  GitLab-configured project the gate's subprocess hits an argparse rejection; `_resolve_landing_state`
  sees no stdout and returns `{'status': 'error', ...}`, so every foreign repository lands in
  `unresolved[]` and the gate errors. CONFIRMED (code) — the runtime sequence is reasoned from the
  router and handler, not executed against a GitLab project.
- **Impact:** on GitLab, every plan with a foreign deliverable is refused at archive with an argparse
  error text, not a statement that the verb is unsupported on this provider. The operator has no
  remedy named.
- **Task:** either implement `pr landing-state` on the gitlab provider, or have the gate detect the
  configured provider and return `status: error` with an explicit
  `error: landing_state_unsupported_on_provider` naming the provider and the remedy.
- **Done when:** a gate test with a non-github provider yields the named error code and a message that
  names the provider, rather than an argparse rejection surfaced verbatim.
- **Suggested grouping:** tools-integration-ci / provider parity

## G14 — Move the owed API-Sheriff re-review out of a run report and into something tracked

- **Severity:** minor
- **Kind:** omission
- **Where:** recorded only in
  `doc/plans/review-apparatus/020-a-foreign-task-reports-done-with-no-pr-anywhere/report-01.md`
  § Residue and § Verification of `plan.md`
- **Evidence:** `grep -rln "API-Sheriff" doc/ marketplace/` returns exactly three files: this plan's
  `plan.md` and `report-01.md`, and
  `marketplace/bundles/plan-marshall/skills/automatic-review/standards/pr-agent.md:26`, which grounds
  on `cuioss/API-Sheriff` PR **#103** — a different PR, and a grounding record rather than the owed
  re-review. No later plan in `doc/plans/review-apparatus/` mentions it. CONFIRMED.
- **Impact:** the check the plan explicitly carried "so it cannot lapse" now lives only in one archived
  run report, which nothing reads — the exact shape of failure this plan was written to remove, applied
  to the plan's own obligation.
- **Task:** carry the procedure into a place a later run will read — a deliverable in a subsequent
  `review-apparatus` plan, or a stated open item in
  `automatic-review/standards/` alongside the reviewer pack whose confirm/refute it is. Restate it in
  full: re-review `cuioss/API-Sheriff` #185 (26 inline items) or #154 (47) with the shipped
  language-specific reviewer pack installed and compare against this reviewer's recorded zero on the
  same diffs; a refutation is a publishable result.
- **Done when:** the procedure appears in a location outside an archived run report, and the plan or
  standard that owns it names who closes it.
- **Suggested grouping:** review-apparatus / owed checks

## G15 — Reconcile the two test-count figures in the run report

- **Severity:** minor
- **Kind:** false-report-claim
- **Where:** `report-01.md` § Build gate ("**`./pw verify plan-marshall`: green — `15848 passed,
  1 skipped`**") vs § Contract check step 5 ("final green run **15859 passed, 1 skipped, verify:
  SUCCESS**")
- **Evidence:** both figures are presented in the same report as the green verify result. CONFIRMED by
  reading both sections. The difference is reconcilable — the § Findings section records a later fix
  commit that added tests — but § Build gate presents 15848 as the run's result without saying it
  predates the fix.
- **Impact:** small, but it is a numeric claim about the same event stated two ways, in a document
  whose whole subject is signals that assert more than they establish.
- **Task:** state which figure belongs to which commit, or keep only the final figure.
- **Done when:** `report-01.md` carries one green-verify figure per commit it describes, each labelled.
- **Suggested grouping:** review-apparatus / run report hygiene
