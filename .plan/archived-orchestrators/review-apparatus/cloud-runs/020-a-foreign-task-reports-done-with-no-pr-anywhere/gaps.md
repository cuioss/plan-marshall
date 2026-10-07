# Gaps — 020-a-foreign-task-reports-done-with-no-pr-anywhere

Actionable follow-up derived from `verification.md`. Each entry is a task a later plan can pick up
without re-deriving the analysis. Nineteen entries: **G1–G5 major, G6–G19 minor**, ordered by severity.
Every citation is against branch `claude/review-apparatus-analysis-mcf8md` at `500d8061`.

## G1 — Make the gate refuse when the deliverable payload carries no `foreign` classification

- **Severity:** major
- **Kind:** bug
- **Where:** `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/foreign_pr_gate.py:186-220`
  (`_foreign_paths_by_deliverable`) and `:280-288` (the empty-population early `clear`); the fail-open
  classifier it depends on at
  `marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/manage-solution-outline.py:524-527`
  (stated at `:518-522`); the posture it contradicts at `foreign_pr_gate.py:50-52`
- **Evidence:** driven directly, not reasoned. `check('p', deliverables_loader=…)` with a payload of
  `{'status': 'success', 'deliverables': [{'number': 1, 'affected_files': [{'path': '/elsewhere/other/x.py'}]}]}`
  — a success-shaped listing with **no `foreign` key on anything** — returns
  `{'status': 'clear', 'foreign_deliverable_count': 0, 'repos': []}`. So does a payload of
  `{'status': 'success'}` with no `deliverables` key at all. Both selections are bare truthiness tests on
  `entry.get('foreign')` / `deliverable.get('foreign')`. The module docstring states the opposite rule:
  *"The gate CLEARS only when it has POSITIVELY read a landing state … never on an absence of evidence."*
  `_annotate_foreign` produces exactly this payload whenever it cannot resolve the project root, and
  publishes no field saying so. CONFIRMED by execution.
- **Impact:** an unclassified population and a genuinely host-only one are the same bytes on the wire, and
  both archive cleanly. This is the only defect recorded here whose failure direction is a **false
  clear** — the outcome the plan exists to prevent. The gate's own `cwd_checkout_root()` guard
  (`:260-268`) does not cover it: that guard sees only the gate process's own root resolution, while the
  classification runs in the `list-deliverables` subprocess.
- **Task:** have `list-deliverables` publish whether classification was performed — e.g. a top-level
  `foreign_classification: resolved|unresolved` plus the `project_root` it used — and have the gate
  require it: `error` when the field is absent or `unresolved`, and `error` when a deliverable record
  carries no `foreign` key at all. Keep the column itself advisory and fail-open; move the certainty into
  the published status the gate reads.
- **Done when:** a gate test whose loader returns success-shaped deliverables with no `foreign` key
  yields `status: error`; a gate test whose loader reports an unresolved classification yields
  `status: error`; and the `clear` path asserts it saw a positively-classified population.
- **Suggested grouping:** phase-6-finalize / foreign-PR landing gate

## G2 — Pass the branch the foreign change is on to `ci pr landing-state`

- **Severity:** major
- **Kind:** bug
- **Where:** `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/foreign_pr_gate.py:147-164`
  (`_resolve_landing_state`); consumer contract at
  `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py:664-685`
  (`_resolve_landing_branch`); documented default at
  `marketplace/bundles/plan-marshall/skills/tools-integration-ci/standards/leaf-command-reference.md:34`;
  the discarded answer at `_github_pr.py:821` (the verb returns `branch`)
- **Evidence:** the gate builds
  `[sys.executable, executor, _CI_NOTATION, '--project-dir', repo_root, 'pr', 'landing-state']` — no
  `--branch`. The plan's D1 specifies the verb as `ci pr landing-state --project-dir P --branch B`.
  With `--branch` absent, `_resolve_landing_branch` falls back to
  `github_ops.run_git(['rev-parse', '--abbrev-ref', 'HEAD'])` in the foreign checkout. CONFIRMED by
  reading both files.
- **Impact:** the gate classifies whatever ref the foreign working tree has checked out at finalize time,
  not the ref the foreign change was committed to, and it asserts nothing about which ref that was. In
  the ordinary flow — the foreign checkout still on the branch just committed to — the fallback names the
  right ref and the verdict is correct; the defect is the dependence on that coincidence. Reasoned from
  the handler body: a foreign checkout sitting on a pushed default branch yields no tip-matching PR and a
  non-empty `git branch -r --contains`, i.e. `pushed_no_pr` — a false archive refusal for a plan whose
  foreign work is complete. A checkout switched away from the work branch means the work branch is never
  examined at all. The verb already returns the `branch` it used; the gate drops it.
- **Task:** carry the foreign change's branch to the verb. Either (a) record the branch alongside the
  foreign path when the foreign change is committed and thread it into `_resolve_landing_state` as
  `--branch`, or (b) if no branch record exists, make the gate resolve the branch explicitly and pass it,
  failing closed with a named reason when it cannot be determined — never silently classifying HEAD. In
  either case echo the returned `branch` into the gate's `repos[]` rows so the verdict names its subject.
- **Done when:** `_resolve_landing_state` emits `--branch` on every invocation, a test drives the real
  `_resolve_landing_state` (not the injected seam) and asserts the argv contains `--branch` with the
  expected value, a test asserts the gate errors rather than classifying when the branch cannot be
  resolved, and each `repos[]` row carries the branch it classified.
- **Suggested grouping:** phase-6-finalize / foreign-PR landing gate

## G3 — Refuse `unpushed` as well as `pushed_no_pr`, or state in the gate why it does not

- **Severity:** major
- **Kind:** bug
- **Where:** `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/foreign_pr_gate.py:78`
  (`BLOCKING_LANDING_STATE = 'pushed_no_pr'`), the single comparison at `:328` and the status assignment
  at `:334`; the test that locks the behaviour in at
  `test/plan-marshall/phase-6-finalize/test_foreign_pr_gate.py:101`
  (`test_unpushed_foreign_deliverable_clears`); operator-facing text at
  `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/archive-plan.md:38` and `:50`
- **Evidence:** the gate refuses on exactly one state. The plan's Goal reads *"A foreign task cannot
  reach `done` while its change has no pull request"*; the plan's D1 body reads *"refuse to archive
  while any is `pushed_no_pr`"*. `unpushed` means the change is on no remote at all, so it certainly has
  no pull request — and the test asserts `result['status'] == 'clear'`. CONFIRMED by reading the gate and
  running the test file (56 passed).
- **Impact:** the strictly worse case passes the gate. A foreign change committed locally and never
  pushed archives cleanly — the same "reports done with no PR anywhere" outcome the plan exists to
  prevent, one step earlier in the lifecycle. G9 compounds it: a branch that really was pushed can also
  read `unpushed`.
- **Task:** decide the intended set explicitly. Either widen the refusal to
  `{'pushed_no_pr', 'unpushed'}` — renaming the constant to a set, e.g. `BLOCKING_LANDING_STATES` —
  updating `archive-plan.md`, the module docstring and the tests together; or, if `unpushed` is
  genuinely meant to clear, say so in the gate docstring and in `archive-plan.md` with the reason, and
  reconcile the plan's Goal sentence in the same change.
- **Done when:** a single named constant holds the blocking set, `archive-plan.md` and the docstring
  agree with it, and a test asserts the gate's disposition for `unpushed` against that constant rather
  than against a literal.
- **Suggested grouping:** phase-6-finalize / foreign-PR landing gate

## G4 — Settle whether read-intent and survey-scope paths belong in the gate's blocking population

- **Severity:** major
- **Kind:** bug
- **Where:** `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/foreign_pr_gate.py:186-220`
  (`_foreign_paths_by_deliverable`, three-field loop at `:205`);
  `marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/manage-solution-outline.py:505-547`
  (`_annotate_foreign`); the write-set rule at
  `marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/_plan_parsing.py:456`
  (`deliverable_write_set`); the read default at `_plan_parsing.py:413` (`extract_survey_scope`); the
  test that pins survey-scope inclusion at `test/plan-marshall/phase-6-finalize/test_foreign_pr_gate.py:214`
- **Evidence:** both selectors read `entry.get('foreign')` alone and never `entry['intent']`, although
  `_extract_affected_files` returns `{'path': str, 'intent': str | None}` (`_plan_parsing.py:447`) and
  `deliverable_write_set`'s docstring states the repository's own rule: *"every `affected_files` **or**
  `mutation_scope` entry whose declared intent is not `STEP_INTENT_READ`"*. Driven end-to-end: a
  deliverable declaring only ``- `/elsewhere/other-repo/src/Ref.java` (read)``, passed through
  `extract_deliverables` → `_annotate_foreign` → `_foreign_paths_by_deliverable`, yields
  `[(1, ['/elsewhere/other-repo/src/Ref.java'])]`. CONFIRMED by execution.
- **Impact:** a foreign path a deliverable declares `(read)` — a file consulted in another repository and
  left untouched — enters the gate's population. The gate then demands a landing state, and can refuse to
  archive, for a repository the plan never wrote to. `survey_scope` is by definition the read-only field
  and is stamped and iterated in full.
- **Task:** decide the rule, then apply it in one place. Two constraints the change must honour:
  `deliverable_write_set` did **not** exist when this gate landed (it arrived with `aeab5ab5`, #1283), so
  the write-set rule is a later standard the gate has never been reconciled with; and `survey_scope` is
  in the field list **deliberately**, added by `63943f55` (#1295) with a test asserting "the population
  this gate iterates must be the whole declared surface". Either route the population through
  `deliverable_write_set` and rewrite that test with its reason, or keep the whole declared surface and
  state in the gate docstring why a read-only foreign path is still a landing obligation. Note the
  pinning test's fixture entries carry no `intent` key, so an intent filter would leave it green while
  changing real behaviour — the test needs intent-bearing fixtures either way.
- **Done when:** one helper owns the rule for both `_annotate_foreign` and the gate; a gate test with an
  intent-bearing foreign `(read)` entry and an intent-bearing foreign `survey_scope` entry asserts the
  chosen disposition explicitly; and a foreign `(write-new)` entry in the same deliverable still blocks.
- **Suggested grouping:** phase-6-finalize / foreign-PR landing gate

## G5 — Correct the D0 single-seam finding: `done` is written in two places

- **Severity:** major
- **Kind:** false-report-claim
- **Where:** `doc/plans/review-apparatus/020-a-foreign-task-reports-done-with-no-pr-anywhere/report-01.md`
  § D0 ("`done` is written in exactly one place: `manage-tasks/scripts/_tasks_crud.py::cmd_update`");
  the unreported second writer is
  `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_cmd_step.py:73`
- **Evidence:** `_cmd_step.py:73` reads
  `task['status'] = 'failed' if has_failed else 'done'`, inside the `all_terminal` branch of the
  `manage-tasks step` verb. `git show 9c679c99^:.../_cmd_step.py | grep -n "task\['status'\]"` returns
  the same line 73, so it was present when the report was written. Backing search:
  `grep -rn "'status'\] = " marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/*.py`
  → four hits, three in `_cmd_step.py` (one of them a *step's* status), one in `_tasks_crud.py:667`.
  The report's own line reference is also off: `_tasks_crud.py:662-667` is an `is not None` guard plus a
  membership check, not an `args.status == 'done'` branch. CONFIRMED.
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

## G6 — Prove the archive refusal at the archive step, not only at `check()`

- **Severity:** minor
- **Kind:** missing-test
- **Where:** the only invocation site is
  `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/archive-plan.md:42-45`; the only
  refusal assertion is `test/plan-marshall/phase-6-finalize/test_foreign_pr_gate.py:71`
  (`test_pushed_no_pr_foreign_deliverable_is_refused_at_archive`, which asserts on `check()`)
- **Evidence:** `grep -rn "foreign_pr_gate"` over the tracked tree returns four sites: the prose
  invocation, the module docstring (`foreign_pr_gate.py:58`), and two test files. No code path calls the
  gate. **This is the house convention, not an anomaly** — all eight scripts in
  `phase-6-finalize/scripts/` are invoked only from fenced blocks in `SKILL.md` / `standards/*.md`
  (`grep -rn "execute-script.py plan-marshall:phase-6-finalize"`), and `archive-plan.md` is itself a
  registered step (`order: 1100`, `default_on: true`). What is missing is the proof: the plan's D1
  *Done when* asks that the plan be "refused **at archive**", and nothing exercises the archive path, so
  deleting the entire § "Pre-Archive Foreign-PR Landing Gate" section breaks no test (the tests that
  mention `default:archive-plan` assert step ordering from frontmatter, not the document body).
  CONFIRMED.
- **Impact:** the gate's enforcement rests on a section that no assertion protects. A dispatcher that
  skips it, or an edit that removes it, archives a plan with a stranded foreign change and nothing
  detects the regression.
- **Task:** add an enforcement test at the archive boundary — either a document-contract test asserting
  `archive-plan.md` carries the gate invocation and the `blocked`/`error` STOP handling ahead of the
  `manage-status archive` call, or (stronger) have `manage-status archive` refuse without a recorded
  `clear` verdict for the plan and test that refusal.
- **Done when:** a test fails if the gate section is removed from `archive-plan.md` or if the archive
  path stops honouring a `blocked` verdict.
- **Suggested grouping:** phase-6-finalize / foreign-PR landing gate

## G7 — Reconcile the two bases used to resolve a relative foreign path

- **Severity:** minor
- **Kind:** bug
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/_plan_parsing.py:95`
  (joins a relative path onto `project_root`) vs
  `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/foreign_pr_gate.py:123-144`
  (`_resolve_repo_root`: `os.path.dirname(path)` + `os.path.isdir()` against the process cwd)
- **Evidence:** `is_foreign_path` computes
  `os.path.normpath(candidate if os.path.isabs(candidate) else os.path.join(root, candidate))`;
  `_resolve_repo_root` computes `directory = os.path.dirname(path) or path` and calls
  `os.path.isdir(directory)` with no anchoring. CONFIRMED by reading both.
- **Impact:** a `../other-repo/...` entry is classified against the git toplevel and then resolved
  against whatever cwd the gate runs in. They coincide only when the gate runs from the checkout root;
  otherwise the path is classified foreign and then reported unresolvable, which fails the gate closed
  for the wrong reason. Related: `check()` resolves `project_root` at `:261` and never uses it for
  classification, because `list-deliverables` (which does the classifying, in a subprocess) accepts only
  `--plan-id` and has no way to be told a root — see G1, which fixes the reporting half.
- **Task:** anchor `_resolve_repo_root` on the same `project_root` the gate resolved — join relative
  paths onto it before `dirname`/`isdir` — and give `list-deliverables` an explicit project-root
  argument the gate passes, so the two agree by construction rather than by cwd inheritance.
- **Done when:** a gate test with a `../`-relative foreign path and a cwd that is not the checkout root
  resolves the same repository root as the classifier, and the `project_root` the gate resolves is
  either used or documented as advisory.
- **Suggested grouping:** phase-6-finalize / foreign-PR landing gate

## G8 — Give the gate's third subprocess a timeout, and keep a timeout inside the TOON contract

- **Severity:** minor
- **Kind:** bug
- **Where:** `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/foreign_pr_gate.py:135-140`
  (`git rev-parse --show-toplevel`, no `timeout`) against `:107` and `:165` (`timeout=120`); the
  unguarded call sites relative to the `try` blocks at `:117-120` and `:175-178`; the standard at
  `marketplace/bundles/pm-plugin-development/skills/plugin-script-architecture/standards/cross-skill-integration.md:266`
  and its example at `:283`
- **Evidence:** the parameter table states *"`timeout=N` | Always recommended for external calls"* and
  the worked example is `subprocess.run(['git', 'status'], check=True, timeout=30)`. The gate's two
  executor calls comply; its `git rev-parse` call does not. Separately, both `subprocess.run` calls sit
  outside the `try` that guards `parse_toon`, so `subprocess.TimeoutExpired` propagates out of `check()`
  and `cmd_check` uncaught. CONFIRMED by reading.
- **Impact:** a `git rev-parse` that blocks — a foreign path on an unresponsive mount, or git waiting on
  a credential prompt — hangs the finalize step with no deadline. And when either bounded call does time
  out, the gate exits on a traceback with no TOON on stdout, while `archive-plan.md:51` instructs the
  dispatcher to "return the error TOON verbatim". The direction is fail-closed; the shape is off-contract.
- **Task:** pass an explicit `timeout` to the `git rev-parse` call, and catch `subprocess.TimeoutExpired`
  at all three seams, returning the module's `{'status': 'error', 'error': …}` shape naming the command
  that timed out.
- **Done when:** every `subprocess.run` in the module passes a `timeout`, and a test that raises
  `TimeoutExpired` from a patched `subprocess.run` gets a TOON `status: error` payload and exit code 1
  rather than a traceback.
- **Suggested grouping:** phase-6-finalize / foreign-PR landing gate

## G9 — Stop deriving "not pushed" from remote-tracking refs nothing refreshes

- **Severity:** minor
- **Kind:** bug
- **Where:** `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py:706-723`
  (`_branch_pushed_state`), consumed at `:807-815` and `ci_base.derive_landing_state`
  (`marketplace/bundles/plan-marshall/skills/tools-integration-ci/scripts/ci_base.py:820`)
- **Evidence:** the whole pushed/unpushed axis is `git branch -r --contains <branch>`, and the docstring
  asserts *"`rc == 0` with empty output proves it is not [on a remote]"*. That is a statement about the
  local remote-tracking refs, not about the remote. `grep -n "fetch\|ls-remote"` over `_github_pr.py`
  returns only PR-comment helpers — nothing in the landing-state path refreshes refs. CONFIRMED (code);
  the runtime consequence is reasoned, not observed against a stale checkout.
- **Impact:** in a foreign checkout whose remote-tracking refs are behind (a tree that did not itself
  perform the push, or was not fetched since), a pushed branch reads `unpushed` — which under G3 clears
  the gate. The handler's advertised fail-closed posture covers *unreadable* evidence and not *stale but
  readable* evidence, so the wrong verdict is delivered with full confidence.
- **Task:** either refresh the ref the verdict rests on (`git fetch --quiet <remote> <branch>` or
  `git ls-remote --heads <remote> <branch>` compared against the tip SHA) before deciding, or state in
  the docstring and in `leaf-command-reference.md:34` that `unpushed` means "not on a known remote-
  tracking ref" and treat it accordingly wherever it is consumed.
- **Done when:** the pushed/unpushed decision rests on a ref the run refreshed, or the verb's documented
  contract says which local artefact it read, and a test pins whichever behaviour is chosen.
- **Suggested grouping:** tools-integration-ci / landing-state verb

## G10 — Give the gate an actionable message on a provider that has no `landing-state`

- **Severity:** minor
- **Kind:** omission
- **Where:** registration is github-only at
  `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_ops.py:1834-1868`;
  the gate has no provider check at
  `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/foreign_pr_gate.py:147-178`;
  the constraint is stated only at
  `marketplace/bundles/plan-marshall/skills/tools-integration-ci/standards/leaf-command-reference.md:34`
  ("**GitHub provider only.**")
- **Evidence:** `grep -rn "landing"` over `workflow-integration-gitlab/` returns only an unrelated
  "landing poll" docstring line in `gitlab_ops.py`. On a GitLab-configured project the gate's subprocess
  hits an argparse rejection; `_resolve_landing_state` sees no stdout and returns
  `{'status': 'error', …}`, so every foreign repository lands in `unresolved[]` and the gate errors.
  CONFIRMED (code) — the runtime sequence is reasoned from the router and handler, not executed against a
  GitLab project.
- **Impact:** on GitLab, every plan with a foreign deliverable is refused at archive with an argparse
  error text, not a statement that the verb is unsupported on this provider. The operator has no remedy
  named.
- **Task:** either implement `pr landing-state` on the gitlab provider, or have the gate detect the
  configured provider and return `status: error` with an explicit
  `error: landing_state_unsupported_on_provider` naming the provider and the remedy.
- **Done when:** a gate test with a non-github provider yields the named error code and a message that
  names the provider, rather than an argparse rejection surfaced verbatim.
- **Suggested grouping:** tools-integration-ci / provider parity

## G11 — Cover the gate's three subprocess seams with real tests

- **Severity:** minor
- **Kind:** missing-test
- **Where:** `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/foreign_pr_gate.py:90-178`
  (`_list_deliverables`, `_resolve_repo_root`, `_resolve_landing_state`);
  `test/plan-marshall/phase-6-finalize/test_foreign_pr_gate.py:38-63` (`_run` injects all three)
- **Evidence:** `Grep _resolve_landing_state|_list_deliverables|_resolve_repo_root` over `test/`
  returns matches only in `audit-archived-plan-retrospectives`, `manage-architecture` and
  `manage-solution-outline` — all unrelated symbols. Every gate test passes
  `deliverables_loader` / `root_resolver` / `landing_resolver`. CONFIRMED.
- **Impact:** the argv the gate actually builds (G2's defect), the TOON parse paths, the empty-stdout
  branches and the `git rev-parse --show-toplevel` handling are exercised by nothing. The seams were
  split out "so the orchestration body is testable" and the seams themselves were then left untested.
- **Task:** add tests that call each seam with `subprocess.run` monkeypatched, asserting the argv
  (including `--project-dir`, and `--branch` once G2 lands), the empty-stdout error shape, and the
  unparseable-TOON error shape.
- **Done when:** each of the three seam functions is entered by at least one test, and one of them
  asserts the full argv list.
- **Suggested grouping:** phase-6-finalize / foreign-PR landing gate

## G12 — Extend the doc-parity test from `checks` verbs to `pr` verbs

- **Severity:** minor
- **Kind:** missing-test
- **Where:** `test/plan-marshall/tools-integration-ci/test_ci_base.py:1197-1231` (`_LEAF_COMMAND_REFERENCE`,
  `_CHECKS_ROW` at `:1212`, `_documented_checks_verbs` at `:1215`)
- **Evidence:** the existing parity test derives the documented population from a
  ``^\|\s*`checks (?P<verb>…)` `` row regex against `leaf-command-reference.md`. `Grep _PR_ROW|pr \(\?P<verb>`
  over `test/` → no matches. CONFIRMED — nothing enforces that a registered `pr` sub-verb is documented.
- **Impact:** G13 landed and stayed. Any future `pr` verb can be added with no documentation and no
  test failure.
- **Task:** mirror the `checks` parity check for `pr`: derive the registered sub-verbs from the
  provider handler map (`github_ops.py`'s `('pr', …)` dispatch table) and assert every one has a row
  in `leaf-command-reference.md` and in `api-contract.md`, with a documented exemption list for
  provider-specific verbs if one is genuinely needed. Note `api-contract.md` splits `pr` verbs across two
  tables — read verbs at `:135-148`, state transitions at `:549-556` — so the assertion must accept
  either.
- **Done when:** the new test fails if a `pr` sub-verb is registered without a documentation row, and
  passes on the tree once G13 is done.
- **Suggested grouping:** tools-integration-ci / documentation

## G13 — Document `pr landing-state` on the three surfaces that still omit it

- **Severity:** minor
- **Kind:** stale-doc
- **Where:**
  - `marketplace/bundles/plan-marshall/skills/tools-integration-ci/SKILL.md:310` — § Canonical
    invocations, `### pr`, the `Sub-verbs:` enumeration
  - `marketplace/bundles/plan-marshall/skills/tools-integration-ci/standards/api-contract.md:135-148`
    — § "PR Operations" response-field table
  - `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md:1814-1822` — § Scripts
    inventory table
- **Evidence:** the sub-verb line reads
  `` `view`, `list`, `reply`, `resolve-thread`, `thread-reply`, `reviews`, `comments`,
  `wait-for-comments`, `merge`, `auto-merge`, `safe-merge`, `merge-queue`, `update-branch`, `close`,
  `ready`, `submit-review`, `edit`, `prepare-body`, `prepare-comment`, `create`. `` — no
  `landing-state`. The api-contract PR table gives a "Response fields" row for every other `pr` **read**
  verb (`view`, `list`, `reviews`, `comments`, `wait-for-comments`); `landing-state`'s fields (`branch`,
  `tip_sha`, `pushed`, `pr_count`, `landing_state`, `landing_states`, per `_github_pr.py:817-829`)
  appear nowhere. `ls phase-6-finalize/scripts/` lists eight scripts and the Scripts table has seven
  rows; the missing one is `foreign_pr_gate.py`. CONFIRMED. Two surfaces **are** updated and need no
  work: `leaf-command-reference.md:34` and `workflow-integration-github/SKILL.md:280`.
- **Impact:** the verb and the gate are invisible to a reader working from the canonical surfaces, and
  their contracts are unstated where every sibling's contract lives.
- **Task:** add `landing-state` to the `### pr` sub-verb list with a fenced canonical invocation; add a
  `pr landing-state` row to the api-contract PR Operations table naming its required/optional args and
  its response fields; add a `scripts/foreign_pr_gate.py` row to the phase-6-finalize Scripts table.
  The § Canonical invocations preamble at `phase-6-finalize/SKILL.md:1826` also omits the script — but it
  omits `ci_verify.py` and `derive_gate_bundles.py` too, so extending it is a separate, whole-skill
  cleanup rather than part of this entry, and the plugin-doctor `missing-canonical-block` rule is already
  satisfied by the explicit inline call in `archive-plan.md:42-45`.
- **Done when:** the three surfaces above name the verb/script, and the response-field row matches the
  dict returned by `cmd_pr_landing_state`.
- **Suggested grouping:** tools-integration-ci + phase-6-finalize / documentation

## G14 — Distinguish the two kinds of row in the gate's `unresolved[]`

- **Severity:** minor
- **Kind:** stale-doc
- **Where:** `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/foreign_pr_gate.py:30`
  (the field comment), against its two writers at `:300` and `:324`; operator-facing text at
  `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/archive-plan.md:51`
- **Evidence:** the docstring documents the row as
  `unresolved[K]{path,reason}: … # foreign paths whose repo could not be resolved`. `:300` appends a
  declared **file path** with reason "repository root not resolvable"; `:324` appends a resolved
  **repository root** with reason "landing-state unresolved". CONFIRMED by reading.
- **Impact:** the operator is told to "resolve every `unresolved[]` item" from a list whose `path` field
  means two different things, with only the free-text reason to tell them apart. The field comment is
  wrong for half its rows.
- **Task:** either add a `kind` discriminator (`declared_path` / `repo_root`) to the row, or split into
  two named lists, and correct the docstring and `archive-plan.md` to match.
- **Done when:** each `unresolved[]` row states which kind of path it carries, and a test asserts both
  kinds appear with their discriminator in a run that produces one of each.
- **Suggested grouping:** phase-6-finalize / foreign-PR landing gate

## G15 — Fix the `LANDING_STATES` ordering comment

- **Severity:** minor
- **Kind:** stale-doc
- **Where:** `marketplace/bundles/plan-marshall/skills/tools-integration-ci/scripts/ci_base.py:814`
- **Evidence:** the comment reads *"#: The closed set of landing states, in refuse-most-first
  precedence order."* immediately above
  `LANDING_STATES: tuple[str, ...] = ('merged', 'pr_open', 'pushed_no_pr', 'unpushed')` (`:817`). The
  tuple is ordered landed-first — matching `derive_landing_state`'s check order (`:848-852`) — and the
  only refused state, `pushed_no_pr`, is third. CONFIRMED.
- **Impact:** a reader deriving refusal precedence from the tuple order gets the opposite of the
  intended reading, and a future consumer that iterates the tuple "refuse-most-first" would be wrong.
- **Task:** reword to describe the actual ordering (most-landed first, matching the check order in
  `derive_landing_state`), or reorder the tuple and update every consumer that relies on its order.
- **Done when:** the comment and the tuple agree, and `derive_landing_state`'s check order matches the
  documented reading.
- **Suggested grouping:** tools-integration-ci / landing-state verb

## G16 — Stamp `foreign` on the single-deliverable read verbs, and document the column

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

## G17 — Make some coverage ratio actually separate host from foreign paths

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

## G18 — Move the owed API-Sheriff re-review out of a run report and into something tracked

- **Severity:** minor
- **Kind:** omission
- **Where:** recorded only in
  `doc/plans/review-apparatus/020-a-foreign-task-reports-done-with-no-pr-anywhere/report-01.md`
  § Residue and § Verification of `plan.md`
- **Evidence:** `grep -rln "API-Sheriff" doc/ marketplace/` returns this plan's own directory and
  `marketplace/bundles/plan-marshall/skills/automatic-review/standards/pr-agent.md:26`, which grounds
  on `cuioss/API-Sheriff` PR **#103** — a different PR, and a grounding record rather than the owed
  re-review. No other plan in `doc/plans/` mentions it. CONFIRMED.
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

## G19 — Label the two test-count figures in the run report

- **Severity:** minor
- **Kind:** inconsistent-report
- **Where:** `report-01.md` § Build gate ("**`./pw verify plan-marshall`: green — `15848 passed,
  1 skipped`**") vs § Contract check step 5 ("final green run **15859 passed, 1 skipped, verify:
  SUCCESS**")
- **Evidence:** both figures are presented in the same report as the green verify result. CONFIRMED by
  reading both sections. The difference is reconcilable — § Findings records a later fix commit that
  added tests, and the PR body carries the 15848 figure — but § Build gate presents 15848 as the run's
  result without saying it predates the fix.
- **Impact:** small, but it is a numeric claim about the same event stated two ways, in a document
  whose whole subject is signals that assert more than they establish.
- **Task:** state which figure belongs to which commit, or keep only the final figure.
- **Done when:** `report-01.md` carries one green-verify figure per commit it describes, each labelled.
- **Suggested grouping:** review-apparatus / run report hygiene
