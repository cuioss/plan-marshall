# Gaps — 190-frozen-manifest-diverges-from-live-config

The plan landed and every deliverable is present in the tree. What remains splits four ways.

**One defect in D3 is high.** The on-disk post-assertion that is supposed to keep
`executor_regenerated` honest (`executor_landed`, the round-1 F7 fix) is a *presence* check, and the
rebase population always has an executor present — `prepare_execute` generates one at phase-5 move-in
and self-heals it if it goes missing. So the guard cannot fire where it matters, and a generation
that wrote nothing is reported as a successful refresh over the stale file it failed to replace (G15,
measured).

**Two scope limits inside D2** are reachable and unstated: the reconciliation is structurally blind to
external (`project:` / `bundle:skill`) steps, so the self-modifying case it exists for is unhelped
whenever the deleted step is a project step; and its backfill direction inserts a newly-configured
step into `phase_6.steps` without any of the pre-filters, ceremony gates, or lane resolution the
composer applies. **A second D3 contract** — the seam's "never raises" promise — is only partly
implemented, and one of the three documented callers discards the payload it now receives. **Three
counts in the run report** were never re-derived against what actually landed. All four residue items
the report itself declared are still open. Sixteen entries, one per instance.

## G1 — Make `reconcile` able to classify an external step as stale

- **Kind:** incomplete
- **Severity:** medium
- **Topic:** architecture-core
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/manage-execution-manifest.py:2957`
  (`cmd_reconcile`, the partition loop), via
  `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/_manifest_validation.py:464-469`
  (`_check_step_loadable`)
- **Evidence:** the partition's only oracle is `verdict = _check_step_loadable(step)`, and that
  function opens with `if _is_external_step(step_id): return {…, 'loadable': True}`. Its docstring
  states the rule outright: *"External steps are short-circuited to `loadable: true` with an empty
  standards_path because their loadability is owned by the host plugin cache."* Every `project:` /
  `bundle:skill` entry therefore lands in `retained` at `:2959` and the `elif` at `:2960` — the stale
  branch — is unreachable for it.
- **Why it matters:** this repository schedules project steps in phase 6 (`project:finalize-step-sync-plugin-cache`
  at order 85, `project:finalize-step-era-stamp-fill`, `project:finalize-step-plugin-doctor`, …). A
  meta-project plan that deletes one of its own project skills and sweeps `marshal.json` — precisely
  the self-modifying population D2 was written for — reaches Step 1.5 holding a frozen
  `project:finalize-step-X` that reconcile silently retains. Finalize then fails mid-dispatch with a
  `Skill: {ref}` resolution error, which is the confusing failure Step 1.5 exists to convert into an
  actionable phase-entry message. The plan's D2 *Done when* ("a frozen manifest referencing a deleted
  step reconciles") is satisfied for built-in steps only.
- **Action:** in `cmd_reconcile`, resolve external steps through the resolver that already exists for
  them — `_check_step_resolvable(step_id, phase)` at `_manifest_validation.py:634`, used today only
  by `compose` — and feed its verdict into the same stale/broken partition. Keep the partition rule
  unchanged: unresolvable **and** absent from the live candidate set → `stale`; unresolvable **but**
  still listed → `broken`. Built-in steps keep using `_check_step_loadable`.
- **Done when:** a test seeds a manifest whose frozen `phase_6.steps` carries a `project:` step that
  resolves to nothing, with that step absent from `marshal.json`, and `cmd_reconcile` returns it in
  `stale[]` and drops it under `--apply`; a sibling test with the step **still** in `marshal.json`
  returns `error: unreconcilable_step`.
- **Effort:** M
- **Risk if fixed:** external-step resolution is plugin-cache-dependent, so a resolver that returns
  "unresolvable" in an environment where the cache is merely not yet synced would drop a live step.
  The fail-closed rule already in `cmd_reconcile` (unreadable live config ⇒ everything `broken`) is
  the template: prefer `broken` over `stale` whenever the resolution itself is indeterminate.

## G2 — State reconcile's built-in-only scope in its own documentation

- **Kind:** doc-defect
- **Severity:** low
- **Topic:** bundle-docs
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/SKILL.md:376-386`
  (§ `reconcile`, the fail-direction table) and
  `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/required-steps.md:83-102`
  (§ "Reconciliation Contract")
- **Evidence:** the table's rows are keyed on the bare word "unloadable" with no qualification, and
  neither section mentions external steps. Its sibling contract does the opposite: § "Loadability
  Contract" at `required-steps.md:114-120` opens with *"**Scope**: the contract covers **built-in**
  steps only"*, and `phase-6-finalize/SKILL.md:401` repeats it. A reader who has just read the
  loadability scope note reasonably assumes reconcile carries none, because reconcile's own section
  declares none.
- **Why it matters:** a plan author who deletes a project step and sweeps `marshal.json` will read
  § "Reconciliation Contract", conclude the divergence is handled, and be surprised at dispatch. The
  documentation currently over-promises the verb's reach.
- **Action:** add a **Scope** paragraph to `SKILL.md` § `reconcile` naming which step kinds the
  partition covers, and cross-reference it from § "Reconciliation Contract". If G1 is fixed first,
  this becomes a statement that both kinds are covered and by which resolver.
- **Done when:** `SKILL.md` § `reconcile` states the step-kind scope explicitly, and the statement
  agrees with what `cmd_reconcile` actually does at that moment.
- **Effort:** S
- **Risk if fixed:** none beyond ordinary doc drift; sequence it after G1 so the text is not written
  twice.

## G3 — Subject a backfilled step to the composer's narrowing, or state that it is exempt

- **Kind:** bug
- **Severity:** medium
- **Topic:** architecture-core
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/manage-execution-manifest.py:2998-3004`
  (the `backfill` list comprehension in `cmd_reconcile`)
- **Evidence:**

  ```python
  backfill = [
      step
      for step in live_candidates
      if step not in composed_set
      and step not in frozen_set
      and _check_step_loadable(step)['loadable']
  ]
  ```

  Those are the only three conditions. `compose` runs considerably more before a candidate becomes a
  step: `_apply_commit_push_disabled` (`:1975`), `_apply_pre_push_quality_gate_inactive` (`:1980`),
  `_apply_simplify_inactive` (`:1994`), `_apply_security_class_inactive` (`:2023`),
  `_apply_scope_gated_finalize` (`:2043`), the six-row matrix,
  `_apply_ceremony_finalize_selection` (`:2232`), and `_apply_lane_resolution` (`:2254`). None of
  them runs here.
- **Why it matters:** `_apply_lane_resolution` is the execution-profile cutoff. A step added to
  `marshal.json` after compose is written straight into `phase_6.steps` regardless of its lane tier,
  so a `tier: full` step can be backfilled into a plan whose operator selected the `minimal` posture
  and will then be dispatched. The same holds for a step the `commit_push_disabled` or
  `simplify_inactive` pre-filter would have removed. `SKILL.md:448` promises reconcile *"never
  re-runs the decision matrix, never re-derives the list from current rules, and never re-adds a
  candidate the matrix already dropped"* — all true, and all about the **re-add** direction; nothing
  discloses that a **new** candidate is admitted with no narrowing at all.
- **Action:** decide which of the two the design wants and implement it. Either (a) run the
  backfill set through the lane-resolution pass and the pre-filters that do not depend on
  compose-time-only inputs, using the same helpers `compose` calls, dropping what they drop and
  reporting the drops on the payload; or (b) keep the current behaviour and state it plainly in
  `SKILL.md` § `reconcile` under "Backfill is narrow by construction" — that a backfilled candidate
  is admitted unfiltered, and why that is the lesser risk.
- **Done when:** a test composes a manifest under `execution_profile: minimal`, adds a `tier: full`
  step to `marshal.json`, runs `reconcile --apply`, and asserts the documented outcome — either the
  step is dropped with a reported reason (option a) or it is present and the SKILL.md text says so
  (option b).
- **Effort:** M
- **Risk if fixed:** option (a) re-introduces composer coupling into a verb whose whole design point
  is not to re-derive the selection, and several pre-filters read compose-time inputs
  (`affected_files_count`, `commit_and_push`) the manifest does not persist. Restricting the pass to
  lane resolution alone — which reads only the step's own `lane:` block and the persisted posture —
  is the low-risk subset.

## G4 — Make `_run_generate_executor` honour its "never raises" contract

- **Kind:** bug
- **Severity:** medium
- **Topic:** dispatch/finalize
- **Where:** `marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/git-workflow.py:828-846`
  (`_run_generate_executor`), consumed at `:1709` in `cmd_worktree_rebase_to`
- **Evidence:** the docstring ends *"Returns `(returncode, stdout, stderr)`; never raises."* and
  `_refresh_worktree_executor`'s says *"Every failure mode is reported in the return value and none
  is raised."* The implementation catches exactly two exceptions:

  ```python
  except FileNotFoundError:
      return 127, '', 'python3 executable not found on PATH'
  except subprocess.TimeoutExpired:
      return 124, '', f'generate_executor {verb} timed out'
  ```

  `subprocess.run` can raise other `OSError` subclasses — `PermissionError` when `python3` is present
  but not executable, `OSError` when the pinned `cwd` has become inaccessible, `MemoryError`/`OSError`
  on fork failure. `_refresh_worktree_executor` has no handler, and neither does the call site at
  `:1709`.
- **Why it matters:** the refresh runs **after** `git rebase` succeeded and HEAD moved
  (`:1701-1710`). An escaping exception turns a rebase that worked into a crash reported to the
  caller — `finalize-step-sync-baseline` (order 3), `automatic-review` (order 30),
  `branch-cleanup` (order 70) — which is verbatim the outcome `:867-870` argues must be prevented:
  *"converting a refresh failure into a rebase failure would make callers abort a rebase that
  worked."* The guard reads as total and is not.
- **Action:** widen the seam's handler to `except OSError as exc:` (which subsumes `FileNotFoundError`
  and `PermissionError`), keeping `TimeoutExpired` as its own arm and preserving the distinct return
  codes where they are already meaningful; report the exception text in the third tuple element so it
  reaches `executor_detail`.
- **Done when:** a test monkeypatches `git_workflow.subprocess.run` to raise `PermissionError`,
  invokes `cmd_worktree_rebase_to` on a rebase that replayed commits, and asserts
  `result['status'] == 'success'`, `result['executor_regenerated'] is False`, and a non-empty
  `result['executor_detail']`.
- **Effort:** S
- **Risk if fixed:** a blanket `OSError` arm could mask a programming error that today surfaces
  loudly. Scope it to the `subprocess.run` call only — which it already is — and keep the message in
  the payload so the failure is legible rather than silent.

## G5 — Pin the non-fatal property against a raising seam, not only a non-zero return code

- **Kind:** test-gap
- **Severity:** low
- **Topic:** tests
- **Where:** `test/plan-marshall/workflow-integration-git/test_worktree_rebase_executor_refresh.py:193-205`
  (`TestRefreshIsNonFatal::test_failed_generation_does_not_fail_the_rebase`)
- **Evidence:** the only non-fatal test drives `_GeneratorSpy(drift_status='drift', generate_rc=1)` —
  a clean non-zero **return**. No test in the file makes the seam raise. `TestSubprocessSeamShape`
  patches `subprocess.run` (`:285`) but only to capture argv, returning a stub result.
- **Why it matters:** "non-fatal by contract" is a two-part property — it must hold for a failing
  return code **and** for a raising call — and only the first half is pinned. G4's defect is exactly
  the unpinned half, which is why it survived three verification rounds.
- **Action:** add a test to `TestRefreshIsNonFatal` that monkeypatches `git_workflow.subprocess.run`
  to raise, and asserts the rebase still reports `status: success` with the failure named on
  `executor_detail`. Land it with G4.
- **Done when:** the new test exists, is red against the current `except` clauses, and green after
  G4's widening.
- **Effort:** S
- **Risk if fixed:** none.

## G6 — Consume the executor-refresh payload in `automatic-review`'s refusal-recovery rebase

- **Kind:** omission
- **Severity:** low
- **Topic:** dispatch/finalize
- **Where:** `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md:545-559`
- **Evidence:** the step dispatches `git-workflow worktree-rebase-to --plan-id {plan_id} --base
  origin/{base_branch}` and proceeds directly to `force-push-with-lease` and a decision-log line; it
  neither parses nor logs `executor_drift` / `executor_regenerated` / `executor_detail`. Both sibling
  callers do: `phase-6-finalize/standards/finalize-step-sync-baseline.md:184-188` emits a `[STATUS]`
  work-log line carrying all three fields, and `.../branch-cleanup.md:384` documents the same
  consumption. `.../workflow-integration-git/standards/worktree-handling.md:446` names all three
  callers, so this one is a known member of the roster.
- **Why it matters:** the refresh is non-fatal by design, which makes the payload the *only* signal
  that it degraded. On the refusal-recovery path a `drift`-detected-but-not-regenerated outcome —
  the case that leaves every later dispatch in that worktree resolving against a stale map — is
  discarded silently, and the operator learns nothing until a notation fails to resolve.
- **Action:** add the same `[STATUS]` work-log emission the sync-baseline step uses, immediately
  after the `worktree-rebase-to` call, interpolating the three fields.
- **Done when:** `automatic-review/SKILL.md`'s recovery path emits a line naming
  `executor_drift`, `executor_regenerated`, and `executor_detail`, matching the wording at
  `finalize-step-sync-baseline.md:188`.
- **Effort:** S
- **Risk if fixed:** one extra log line on a rarely-taken path; none behavioural.

## G7 — Document Step 1.5's handling of a reconcile error that is not `unreconcilable_step`

- **Kind:** doc-defect
- **Severity:** low
- **Topic:** bundle-docs
- **Where:** `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md:368-370`
- **Evidence:** the step instructs *"Parse the returned TOON and branch on `status`"* and then gives
  exactly two branches: `status: success` and `status: error, error: unreconcilable_step`.
  `cmd_reconcile` can also return `error: file_not_found` (`manage-execution-manifest.py:2917-2922`)
  and `error: invalid_manifest` on a missing or malformed `phase_6` block (`:2926-2939`). Neither is
  named.
- **Why it matters:** the dispatcher is an LLM following prose. An unenumerated `status: error`
  leaves it improvising at a phase-entry gate — the one place the plan's own D1 argued must have a
  deliberately chosen direction. `file_not_found` in particular already has a documented handling
  fifteen lines above for the `read` call (*"abort finalize with an explicit error"*), so the correct
  answer exists and is simply not carried forward.
- **Action:** add a third bullet covering any other `status: error` — abort finalize with the
  returned `message`, since a manifest reconcile that cannot even read the manifest is not a state
  the dispatch loop may proceed from.
- **Done when:** `phase-6-finalize/SKILL.md` Step 1.5 enumerates a catch-all error branch alongside
  the two specific ones.
- **Effort:** S
- **Risk if fixed:** none.

## G8 — Stop `reconcile --apply` silently deleting a non-string `phase_6.steps` entry

- **Kind:** bug
- **Severity:** medium
- **Topic:** architecture-core
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/manage-execution-manifest.py:2940`
  and `:3009-3010`
- **Evidence:** `frozen_steps = [step for step in frozen if isinstance(step, str)]` discards
  non-string entries; `merged = _sort_steps_by_frontmatter_order(retained + backfill)` is built only
  from `frozen_steps`; `phase_6['steps'] = merged` then writes that back. A non-string entry appears
  in neither `stale[]` nor `broken[]` nor the decision log — it simply vanishes on any `--apply` that
  finds something to reconcile. The sibling choke point disagrees explicitly:
  `_manifest_validation.py:390-393` documents that *"Entries whose order resolves to `None` —
  non-string entries and external `bundle:skill` steps with no resolvable source file — keep their
  exact original index, acting as fixed pins"*, i.e. that function was written to preserve exactly
  what `cmd_reconcile` drops.
- **Why it matters:** `SKILL.md:450` explicitly sanctions editing `execution.toon` directly, so a
  malformed entry is a reachable state rather than a theoretical one, and a verb whose entire premise
  is "never silently drop work the project still schedules" silently drops it.
- **Action:** carry non-string entries through unchanged (append them to `retained` before the sort,
  which `_sort_steps_by_frontmatter_order` already handles), or reject the manifest with
  `error: invalid_manifest` naming the offending index. Do not keep the silent third option.
- **Done when:** a test seeds `phase_6.steps` containing a non-string entry alongside a genuinely
  stale one, runs `reconcile --apply`, and asserts the non-string entry is either still present or
  the call errored — never that it disappeared without a report.
- **Effort:** S
- **Risk if fixed:** preserving the entry keeps a malformed manifest malformed for downstream
  readers; erroring blocks a finalize that would otherwise have proceeded. Erroring is the safer
  choice given the verb's fail-loud posture, but it changes behaviour for an existing malformed
  manifest — check no fixture relies on the current silence.

## G9 — Correct the run report's build-gate file enumeration

- **Kind:** report-defect
- **Severity:** low
- **Topic:** plan-lane-contract
- **Where:** `doc/plans/code-intelligence-substrate/190-frozen-manifest-diverges-from-live-config/report-01.md:119-126`
- **Evidence:** the report states *"`git diff --name-only origin/main...HEAD -- '*.py'` → **4 Python
  files changed**"*, lists four paths, and closes *"(plus three new test files.)"*. Re-derived from
  the landed commit with `git show --numstat --format="" d2e94b4 | grep '\.py$'`: **nine** `.py`
  paths. Production: the four listed **plus**
  `marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/_executor_slot.py`
  (+59, new). Test: three new **plus** a modified
  `test/plan-marshall/phase-6-finalize/test_manifest_loadability_guard.py` (+51/−12).
- **Why it matters:** the enumeration is the report's stated evidence that the build gate fired over
  the right surface. `_executor_slot.py` is a new production module created in the `c81aee6` round;
  a reader auditing which files the gate covered would conclude it was never in scope. The number
  was recorded once and not re-derived after the fix rounds — the same class of defect the report
  itself records as finding #7.
- **Action:** correct the count to 9 `.py` paths, list all five production files, and describe the
  test set as "three new plus one modified".
- **Done when:** the § Build gate list matches `git show --numstat --format="" d2e94b4 | grep '\.py$'`
  exactly.
- **Effort:** S
- **Risk if fixed:** none.

## G10 — Correct the run report's per-file test counts

- **Kind:** report-defect
- **Severity:** low
- **Topic:** plan-lane-contract
- **Where:** `doc/plans/code-intelligence-substrate/190-frozen-manifest-diverges-from-live-config/report-01.md:109-111`
- **Evidence:** the D5 table annotates the three files *"(15 tests)"*, *"(6 tests)"*, *"(7 tests)"*.
  What landed at `d2e94b4` is 19 / 10 / 8 (`git show d2e94b4:<file> | grep -c "def test_"`), which is
  also the count today at `61a43e5`, and the three files run `37 passed`. The PR description's
  *"32 tests across `test_reconcile.py`, `test_worktree_rebase_executor_refresh.py`, and
  `test_title_token_repeat_suppression.py`"* is wrong by five against the same commit.
- **Why it matters:** the counts sit beside the file paths and read as the files' contents; the PR
  body states a total with no pre-fix qualifier at all. A later retrospective totalling test yield
  across plans will under-count this one.
- **Action:** annotate the table's counts explicitly as pre-fix (e.g. "15 → 19 tests") and correct
  the PR description's total to 37.
- **Done when:** the report's D5 table distinguishes the pre-fix count from the landed count, and no
  stated total contradicts `grep -c "def test_"` over the three files.
- **Effort:** S
- **Risk if fixed:** none.

## G11 — Correct the run report's stale diff-size figure

- **Kind:** report-defect
- **Severity:** low
- **Topic:** plan-lane-contract
- **Where:** `doc/plans/code-intelligence-substrate/190-frozen-manifest-diverges-from-live-config/report-01.md:322`
- **Evidence:** the residue entry justifies the `sourcery-ai` size refusal with *"(2053 insertions
  across 23 files)"*. The PR reports `additions: 2115, deletions: 50, changed_files: 23`; the merge
  commit's `--stat` agrees (`2115 insertions(+), 50 deletions(-)`). The file count holds; the
  insertion figure is 62 low — plausibly true when the refusal fired at `d1e6a37`, and never
  re-derived at report time.
- **Why it matters:** the residue entry is explicitly framed as an epic-level lesson ("plans of this
  size will systematically lose this reviewer"), so the number is the whole point of the sentence.
- **Action:** restate as the final landed figure, or attribute the 2053 to the head the refusal
  actually fired against.
- **Done when:** the figure in § Residue matches a re-derivable measurement and names which head it
  was taken at.
- **Effort:** S
- **Risk if fixed:** none.

## G12 — Close D2's owed observation point

- **Kind:** omission
- **Severity:** medium
- **Topic:** architecture-core
- **Where:** `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md:364` — the one and
  only `reconcile --plan-id {plan_id} --apply` call site in the tree
- **Evidence:** `grep -rn "reconcile --plan-id {plan_id} --apply" marketplace/bundles/` returns
  exactly one hit (control-checked: the same grep against the `[--apply]` form finds the
  documentation site at `manage-execution-manifest/SKILL.md:368`, so the pattern does match where
  text exists). The plan states and the report repeats that *"a green finalize here is evidence of
  NOTHING for this deliverable"*, and that this run compounded it by executing in the `doc/plans/`
  lane, which never runs `phase-6-finalize` at all. Nothing in the tree records a run that has since
  reached Step 1.5.
- **Why it matters:** the entire finalize-entry integration — that `compose` writes
  `phase_6.candidate_steps`, that Step 1.5's dispatcher parses the TOON correctly, that a
  `reconciled: true` triggers the mandated manifest re-read before the loadability loop — is verified
  only by unit tests calling `cmd_reconcile` directly. The wiring itself has never executed.
- **Action:** on the next plan-marshall-lifecycle plan that reaches `phase-6-finalize`, capture the
  reconcile TOON and confirm `candidate_source: marshal.json` and `backfill_determinable: true` on a
  freshly-composed manifest — a `false` there means `compose` failed to write
  `phase_6.candidate_steps`. Record the observation where a later audit can find it.
- **Done when:** a plan's artifacts contain a `reconcile` payload from a real Step 1.5 run showing
  `candidate_source: marshal.json` and `backfill_determinable: true`.
- **Effort:** S (an observation, not a change — but it cannot be scheduled inside the `doc/plans/`
  lane, which never runs phase 6)
- **Risk if fixed:** none; if the observation fails it exposes a real compose defect, which is the
  point.

## G13 — Give phase 5 the same frozen-view reconciliation, or record why it does not need one

- **Kind:** omission
- **Severity:** low
- **Topic:** architecture-core
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/manage-execution-manifest.py`
  — `phase_5.verification_steps` has no candidate snapshot and no reconcile
- **Evidence:** grep for `candidate_steps` under `manage-execution-manifest/` returns `phase_6` hits
  only; there is no `phase_5.candidate_verification_steps` and `cmd_reconcile` reads `phase_6`
  exclusively (`:2924-2939`). The report declares this as residue at `report-01.md:320` and it is
  unchanged. `phase_5.verification_steps` is frozen by the same `compose` call, at the same moment,
  and consumed later by `phase-5-execute` — structurally the identical exposure.
- **Why it matters:** a plan that edits `marshal.json::plan.phase-5-execute.verification_steps`
  during its own run hits the same divergence with no guard at all — phase 5 has neither a reconcile
  nor a loadability check equivalent.
- **Action:** either extend the snapshot-and-reconcile pattern to phase 5 (snapshot
  `phase_5.candidate_verification_steps` in `compose`, add a `--phase` argument to `reconcile`, wire
  it at phase-5 entry), or record in `manage-execution-manifest/SKILL.md` § "Manifest-on-Write
  Semantics" why phase 5's exposure does not warrant one.
- **Done when:** either `reconcile` covers `phase_5` with a test mirroring `test_reconcile.py`'s drop
  and fail-loud cases, or `SKILL.md` names the asymmetry and its justification.
- **Effort:** M
- **Risk if fixed:** phase 5's step ids use a different vocabulary (`default:verify:{canonical}`) with
  role derivation from the trailing segment; the boundary normalization and loadability oracle would
  both need phase-aware handling rather than reuse.

## G14 — Resolve the open contract-change proposal on the lane's post-PR push cost

- **Kind:** omission
- **Severity:** low
- **Topic:** plan-lane-contract
- **Where:** `.claude/skills/cloud-plan-lane/SKILL.md` — § Step 7 (PR creation) and § Step 8
  conditions 1 and 4
- **Evidence:** the report presents a two-part proposal at `report-01.md:304-314` and records it as
  *"presented, never self-approved … **It has not been shipped.**"* Checked at `61a43e5`: the
  underlying *fact* has since landed — `:456-461` now reads *"changes the head mid-review, which
  aborts a bot's in-progress review **and consumes its rate window**"* — but neither proposed edit
  did. `grep -n "bookkeeping"` returns only `:1131` and `:1580`, both unrelated; there is no rule
  telling a run to batch its known-pending post-PR edits into one push, and no note at `:1424-1435`
  that the report-push condition and the green-on-head condition are sequenced rather than
  simultaneous. The document has been renumbered since (the report's "condition 3" is now condition
  4), so the proposal cannot be applied verbatim.
- **Why it matters:** the operator decision the report asked for was never recorded as taken or
  declined, so the proposal is neither shipped nor closed — it is simply lost. The evidence behind
  it (this run consumed CodeRabbit's window with a one-line report edit) is real and re-usable.
- **Action:** re-present the two edits against the *current* section numbering as a `chore/` PR
  touching only `.claude/skills/cloud-plan-lane/SKILL.md`, or record the operator's rejection in the
  plan directory so the proposal stops being open.
- **Done when:** either the lane contract carries a post-PR push-batching rule and a conditions-1/4
  sequencing note, or a note in this plan directory records the proposal as declined.
- **Effort:** S
- **Risk if fixed:** a batching rule must not read as licence to withhold a commit; the durability
  rule outranks it and the new text has to say so, which is exactly what the proposal's own wording
  ("The lever is ordering, never withholding a commit") already handles.

## G15 — Make the executor-refresh success verdict distinguish a NEW executor from the stale one it failed to replace

- **Kind:** bug
- **Severity:** high
- **Topic:** dispatch/finalize
- **Where:** `marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/git-workflow.py:916-936`
  (`_refresh_worktree_executor`, the post-generation verdict), via
  `marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/_executor_slot.py:38-59`
  (`executor_landed`)
- **Evidence:** three measurements, each of which could have come back the other way.

  1. `executor_landed` is a **presence** check: `is_file() and not is_symlink() and st_size > 0`. It
     has no way to tell an executor this generation wrote from one that was already sitting in the
     slot.
  2. The rebase population always has one in the slot. `prepare_execute` generates the worktree
     executor at phase-5 move-in and *self-heals* it when it is missing
     (`prepare_execute.py:253-262`, `:318-327`, `:598`) — so by the time a finalize rebase runs in
     that worktree, `worktree_executor_path(worktree)` is occupied. The `not landed` branch at
     `git-workflow.py:922-931` is therefore effectively unreachable in production; it fires only in
     the test fixture, whose cloned worktree has no `.plan/execute-script.py` at all
     (`test_worktree_rebase_executor_refresh.py:60-91` never creates one).
  3. The exit code is not a fallback. `generate_executor.py`'s `main` prints the TOON and
     `return 0` unconditionally (`generate_executor.py:2418-2419`), so a `cmd_generate` that
     returns `{'status': 'error'}` still exits 0. Measured directly:
     `generate_executor.py generate --marketplace-root <dir-with-no-bundles>` prints
     `status: error` and exits **RC=0**. `cmd_generate`'s own comment at `:1961-1965` asserts the
     opposite ("surfaces here as the command's status: error (non-zero exit via the safe_main
     contract), preserving any pre-existing working executor") — `safe_main` converts only raised
     exceptions to exit 1, never a returned error payload.

  Adding a pre-existing executor to the fixture and re-running the landed-check test turns it red
  the other way: with `drift_status='drift'` and a generator that writes nothing, the verb returns
  `executor_regenerated: True` and `executor_detail: 'script set changed by the rebase; worktree
  executor regenerated'`, while the stale bytes in the slot are untouched.
- **Why it matters:** D3's *Done when* is an on-disk outcome ("a rebase changing the script set
  leaves a regenerated executor"), and F7 was recorded as the behavioural fix that tied the verdict
  to disk rather than to intent. It is tied to disk, but to the wrong property. The refresh is
  non-fatal by design, which makes the payload the **only** signal that it degraded (this is exactly
  G6's argument), and the payload now reports success for the one outcome the refresh exists to
  prevent: every later dispatch in that worktree resolving notations against a stale map, with the
  work-log line at `finalize-step-sync-baseline.md:188` reporting `regenerated=True`.
- **Action:** stop deriving the verdict from presence alone. Require **both** that the generator's
  own TOON reports `status: success` (parse `gen_out` the way the drift probe already parses its
  stdout — the exit code carries no information here) **and** that the slot is occupied. Report the
  generator's `error` text in `executor_detail` when it is not.
- **Done when:** a test seeds `worktree_executor_path(worktree)` with a pre-existing file **before**
  the rebase, drives a `drift` verdict with a generation that exits 0 without writing (or whose TOON
  carries `status: error`), and asserts `executor_regenerated is False` with the generator's failure
  named in `executor_detail`; the existing
  `TestSuccessIsDerivedFromDiskNotExitCode::test_generation_exiting_zero_without_landing_a_file_is_not_success`
  still passes.
- **Effort:** S
- **Risk if fixed:** a byte-comparison approach (hash the slot before and after) would misreport a
  legitimate regeneration that happens to produce identical output as a failure — which is why the
  fix is the generator's own `status` field plus the existing presence check, not a content diff.

## G16 — Close or pin the interpreter-version-sensitive guard predicate

- **Kind:** test-gap
- **Severity:** low
- **Topic:** tests
- **Where:** `test/plan-marshall/phase-6-finalize/test_branch_cleanup_merge_queue_routing.py:589`
- **Evidence:** the predicate reads
  `if token.type != tokenize.NAME or token.string == own_symbol:` — it scans `tokenize` **NAME**
  tokens for queue/train vocabulary. Before PEP 701 (Python < 3.12) an f-string is a single `STRING`
  token, so an identifier interpolated into an f-string produces no NAME token and the guard finds
  nothing. The report records this as the root cause of the withdrawn finding F15
  (`report-01.md:196`) and lists it as residue (`:324`). Unchanged at the audited tree; pre-existing
  in a file this plan never touched.
- **Why it matters:** the guard goes **vacuous-then-red** rather than loudly wrong if the
  `requires-python` floor ever moves below 3.12, and it already cost one verification round to
  diagnose. Nothing in the file records the dependency, so the next reader re-derives it.
- **Action:** either add an explicit `sys.version_info >= (3, 12)` assertion (or a `pytest.skip`
  with the reason) at the top of the predicate's test class, or state the dependency in the
  predicate's own docstring naming PEP 701 and the `requires-python` floor it relies on.
- **Done when:** `test_branch_cleanup_merge_queue_routing.py` names the ≥3.12 tokenization
  dependency either as an executable assertion or in the predicate's docstring, so a floor change
  produces a stated failure rather than a silent vacuity.
- **Effort:** S
- **Risk if fixed:** none; `pyproject.toml` already pins `requires-python >= 3.12` and
  `UV_PYTHON = "3.12"`, so an assertion cannot fail on a supported toolchain.
