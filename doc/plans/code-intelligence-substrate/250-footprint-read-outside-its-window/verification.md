# Verification — 250-footprint-read-outside-its-window

**Audited:** `plan.md`, `report-01.md`, `footprint-read-population.md`
**Tree state:** `ed7f1ad` on `claude/code-intelligence-substrate-analysis-kah884`
**Landed as:** `d34f2b8` — *fix(plan-retrospective): a footprint read outside its window reports unknown, not zero (#1268)*
**Overall verdict:** CONFIRMED WITH GAPS

The plan's six deliverables are present in the tree and behave as the report describes. Every count in
the report and in the population document that could be re-derived here was re-derived and held. One
**high-severity residual instance of the plan's own defect class** survives in the very file the plan
changed: `verify_failure_scope._resolve_declared_footprint` still returns a main-checkout diff as the
plan's footprint when the plan's worktree is `pending`, reached through `worktree_path`'s documented
fallback rather than through the `Path.cwd()` fallback the PR review removed. Its docstring still
describes the removed behaviour as current.

## Deliverable verdicts

| # | Deliverable (short) | Report claim | Ground truth | Verdict |
|---|---|---|---|---|
| D1 | Derive the population of footprint reads (gate) | 13 files / 5 providers / 11 grading sites / 7 skills / 4 affected | All 11 sites exist and behave as tabulated; 13-file count reconciles; one further deciding consumer (`check_build_verdict_consistent`) is in neither the population nor the excluded table | PARTIAL |
| D2 | Third state at the read seam, with a reason token | Two sites fixed; both directions asserted | Both sites carry the third state; both directions asserted and mutation-proven. A named reason token is present at 3 of the 5 reader sites that report an unresolved footprint | PARTIAL |
| D3 | Fix the recall denominator | `extract_modification_intent_files` is the denominator; 3 filtered consumers + 1 deliberately unfiltered | Confirmed at `check-artifact-consistency.py:322`, both footprint consumers, and `request-result-alignment.md`; unfiltered composer consumer confirmed fail-closed | CONFIRMED |
| D4 | Composer fails CLOSED | Already satisfied; second option taken, discrepancy against literal *Done when* disclosed | All four predicates verified fail-closed; the literal *Done when* is indeed not met and the report says so | CONFIRMED (with disclosed deviation) |
| D5 | Blast radius on archived corpus | BLOCKED on corpus availability; 11 examined / 4 affected reported separately | `.plan/archived-plans` absent in this clone; the two counts are reported separately and are internally consistent | CONFIRMED (blocked, honestly) |
| D6 | Tests, each verified to FAIL pre-fix | (a) yes, (b) not reachable — disclosed, (c) yes, 21 tests, 18 failed / 3 passed at merge-base | All named tests exist and pass; merge-base re-run reproduces the direction and magnitude (19 failed / 2 passed with today's module) | CONFIRMED (with disclosed exception) |

## Per-deliverable detail

### D1 — derive the population of footprint reads

- **Required (plan):** *"the population is derived from source and published with its count"*, and the
  derivation must reach `manage-config`.
- **Claimed (report):** 13 files carry a footprint derivation; 5 providers; **11** grading/deciding read
  sites across **seven** skills, all in the `plan-marshall` bundle; 4 carried the collapse, 2 still did
  when the run began.
- **Found:** `doc/plans/code-intelligence-substrate/250-footprint-read-outside-its-window/footprint-read-population.md`.
  Every one of the 11 sites resolves in the tree:
  `check-artifact-consistency.py:389` / `:554`, `check-routing-decisions.py:759`,
  `analyze-logs.py:1532`, `verify_failure_scope.py:111`,
  `manage-execution-manifest.py:793` / `:2023`, `extension_base.py:667`,
  `manage-config/scripts/_cmd_build_map.py:158`, `pyproject_build.py:158`,
  `manage-tasks/scripts/_cmd_pre_commit_verify_freshness.py:374`.
  The five providers resolve too, including `_references_core.py:218` under `manage-references/scripts/`
  (the path the report records as self-corrected).
- **Checks run:** independent sweep of the three derivation primitives
  (`grep -rn "compute_plan_branch_diff\|realized_footprint\|modified_files\|resolve_footprint" --include=*.py marketplace/`),
  plus a truthiness-predicate sweep (`if not footprint|if footprint|footprint or |footprint else`).
  Distinct-file recount: 5 provider files + 8 consumer files, with `extension_base.py` shared → **13**,
  matching the published figure. Skill recount: 7 distinct skills, one bundle — matches.
- **Verdict:** PARTIAL — the published population is accurate for everything it lists, but the
  truthiness sweep surfaces one deciding consumer it does not account for:
  `_manifest_validation.check_build_verdict_consistent` (`_manifest_validation.py:1026`, `if not
  footprint:`), fed a footprint whose unresolvable state is normalized away one call earlier
  (`manage-execution-manifest.py:2021`, `live_footprint_paths = [] if live_footprint is None else …`).
  Its direction is safe (an unresolvable footprint disables the assertion), which is exactly why it
  belonged in the *"Adjacent, deliberately excluded"* table rather than nowhere. See **G5**.
  The `lsp_client.py:217` `if not footprint` hit was checked and is a different concept (a
  `WorkspaceEdit` footprint), correctly outside the population.
- **Split guard (plan's ⚠ on D1), assessed:** the plan requires a SPLIT if D1 finds the population
  *materially larger* than the named sites. The population is larger by count (11 sites versus the 3
  surfaces the plan named), and the run proceeded unsplit with a stated rationale — 9 of the 11 were
  already correct, so the remaining work was two sites. That rationale was re-derived here and holds:
  the population document's own "State when this run began" column names exactly two ❌ rows
  (`analyze-logs` ARTIFACT floor, `verify_failure_scope`), and both are the sites the commit changes.
  The guard's operative test is the work the population implies, not its cardinality, so the unsplit
  decision is a disclosed, evidence-backed deviation rather than an unmet obligation. Not charged as a
  gap.

### D2 — a third state at the read seam

- **Required (plan):** an absent source yields `unknown`/`skipped` **with a reason token**, never zero;
  a genuinely empty footprint still yields zero — **both asserted**.
- **Claimed (report):** two sites still collapsed at run start; both now return an explicit unresolvable
  sentinel with a reason token; six named tests assert both directions.
- **Found:**
  - `analyze-logs.py:1538-1550` — `if footprint is FOOTPRINT_UNRESOLVED:` emits
    `ARTIFACT_COVERAGE_UNMEASURABLE` at `severity: warning`; the measured floor stays on the `elif`
    (`:1551`).
  - `verify_failure_scope.py:152-163` — `if declared is None:` returns
    `footprint_resolved: False`, `unresolved_reason: plan_footprint_unresolvable`
    (`UNRESOLVED_REASON_FOOTPRINT`, `:58`), both counts zero, `exclusively_out_of_scope: False`,
    paths under `unclassified_paths`.
  - `check-artifact-consistency.py:517` / `:578` read state through `footprint_resolved()`
    (`_footprint_resolver.py:114`), never through emptiness.
- **Checks run:**
  - All eight test names the report cites exist:
    `test_unresolvable_footprint_reports_unmeasurable_not_silence` /
    `test_resolved_empty_footprint_stays_a_measured_zero` (`test_analyze_logs_behavior.py`),
    `test_unmeasurable_footprint_does_not_attribute_failures_as_foreign` /
    `test_measured_empty_footprint_still_classifies_as_foreign` (`test_verify_failure_scope.py`),
    `test_unresolvable_when_no_tier_answers` /
    `test_present_but_empty_key_is_a_resolved_empty_footprint` (`test_analyze_logs.py`), plus the two
    composer-side ones under D4.
  - A fourth both-directions control exists at the recall site that the report does not name:
    `test_check_artifact_consistency.py:866`,
    `test_resolved_but_empty_footprint_still_yields_a_measured_verdict` — `modified_files: []` →
    `recall_pct == 0.0`, `status == 'fail'`, `footprint_resolved is True`.
  - Mutation, `analyze-logs.py:1538` → `if False:` — `test_unresolvable_footprint_reports_unmeasurable_not_silence`
    goes red (`AssertionError: the unmeasurable state must be reported, not skipped`); restored from
    byte snapshot.
  - Mutation, `verify_failure_scope.py:104` `return None` → `return set()` — two tests go red
    (`test_unresolvable_worktree_does_not_classify_against_the_current_directory`,
    `test_footprint_resolver_never_diffs_the_current_directory`); restored.
- **Verdict:** PARTIAL — the third state is real, non-vacuous, and asserted in both directions at every
  site. The *reason token* half of the deliverable is applied at **3 of the 5** reader sites that report
  an unresolved footprint (population-doc readers #1–#5), not the 2 of 4 an earlier count gave:
  `analyze-logs` (`ARTIFACT_COVERAGE_UNMEASURABLE` inside the message),
  `verify_failure_scope` (typed `unresolved_reason` field), and — the site the earlier count omitted —
  `check-routing-decisions`, which publishes a top-level `footprint_source: unresolved` (`:766`, emitted
  at `:790`) and a per-check `removal_cause: not_evaluated` (`_CAUSE_NOT_EVALUATED`, `:212`) with
  `detail: 'footprint unresolvable'` (`:574-581`). The two that carry no named token are the recall and
  exact-match `inconclusive` returns (`check-artifact-consistency.py:540-551`, `:593-600`): recall
  publishes `footprint_resolved: false` — the *state* — plus prose, and exact-match publishes only the
  `inconclusive` status plus prose, with no state field at all in the block `cmd_run` emits
  (`:909-915`). That is precisely the half-implementation CodeRabbit raised as P2 against the sibling
  site. See **G4**. And the one typed token that does exist is not in its consumer contract (**G3**).

### D3 — fix the recall denominator

- **Required (plan):** read-intent declarations must not count as expected modifications; the consumer
  set must be **derived**, not assumed; *Done when:* a plan declaring read-intent files can reach a
  passing recall, asserted by fixture.
- **Claimed (report):** `extract_modification_intent_files()` is now the denominator; three consumers
  share it, a fourth (`affected_files_count`) is deliberately left unfiltered.
- **Found:**
  - `check-artifact-consistency.py:322-351` — `extract_modification_intent_files`, excluding
    `entry['intent'] != _READ_INTENT` where `_READ_INTENT = STEP_INTENT_READ` imported from
    `tools-file-ops/scripts/constants.py:321`.
  - Consumer 1: `check_affected_files_recall` (`:441`). Consumer 2: `check_affected_files_exact_match`
    via `cmd_run` (`:851`). Consumer 3: `references/request-result-alignment.md:34,37,39,41` — the
    `fulfilled`/`partial` rules read the modification-intent subset while the *scope-creep* rule
    deliberately keeps the full declared list, exactly as reported.
  - Consumer 4 (unfiltered, by design): `affected_files_count` →
    `_manifest_rules.py:328` `_apply_simplify_inactive` / `:343` `_apply_security_class_inactive`,
    called from `manage-execution-manifest.py:1994` / `:2023`. Both symbol names and the file
    attribution in the report are correct.
  - `test_recall_read_intent_denominator.py:73`
    `test_read_heavy_plan_can_reach_passing_recall` is the fixture the *Done when* asks for.
- **Checks run:** `uv run python -m pytest test_recall_read_intent_denominator.py -o addopts=""` → **21
  passed** (21 tests re-counted from the file, matching the report). Mutation: the filter predicate at
  `:350` changed to a token that never matches (i.e. no filtering) → **10 failed, 11 passed**; restored
  from byte snapshot. The denominator guard is not vacuous.
- **Verdict:** CONFIRMED. The reconstruction identity claimed in the report holds on all seven return
  branches of `check_affected_files_recall`: `declared` carries the modification-intent count on every
  branch, `read_intent_excluded` is published on all six details dicts, and the unparseable branch adds
  `declared_unfiltered` (`:466-470`).

### D4 — the composer's decision fails CLOSED

- **Required (plan):** an unresolvable footprint makes every footprint-dependent prune predicate
  INADMISSIBLE, not false; *Done when:* **no composition-time predicate reads the realized footprint**,
  pinned by a test.
- **Claimed (report):** already satisfied — no code change; the code takes the deliverable's *second*
  offered option (state the precondition and skip), so the literal *Done when* is **not** met, and the
  report says so rather than claiming a clean fit.
- **Found:**
  - `manage-execution-manifest.py:817-819` — `footprint = _resolve_footprint(plan_id)` then
    `if footprint is None or not footprint: return phase_5_steps, []`. Quoted line in the report is
    verbatim-correct.
  - `_manifest_rules.py:385` — `if affected_files_count > 0 or live_footprint_count is None or
    live_footprint_count > 0: return phase_6_candidates, []`. Verbatim-correct.
  - `extension_base.py:667` `should_execute_build` — three-valued `unknown` / `not_necessary` /
    `build`; only the positive `not_necessary` drops a gate.
  - `pyproject_build.py:237` — `footprint_resolvable = resolved_footprint is not None`, and `:244-245`
    forces `divergence_possible=True, recommended_target=None` when unresolvable.
- **Checks run:** `pytest test_canonical_verify_inactive.py test_security_class_gate_regression.py` →
  **31 passed**. The three adversarial tests the report names exist:
  `test_unresolvable_footprint_keeps_the_step` (`test_security_class_gate_regression.py:332`),
  `test_unresolvable_and_resolvable_empty_footprints_diverge` (`:358`),
  `test_unresolvable_footprint_is_a_noop_every_canonical_survives`
  (`test_canonical_verify_inactive.py:156`).
- **Verdict:** CONFIRMED with the deviation the report itself declares. The composer *does* read the
  realized footprint at compose time; what it never does is treat an unresolvable read as false. The
  asymmetry the plan asks to be stated explicitly is stated (population doc § "The one line, repeated").
  P7 (CodeRabbit's `WorktreeResolutionError` escape claim) was re-checked and the rejection is correct:
  `resolve_plan_context(plan_id, ensure=False)` (`file_ops.py:1155-1191`) performs a path computation
  and constructs `PlanContext`; the raising members are the lazy `has_worktree` / `worktree_path`
  properties, both inside the `try` at `manage-execution-manifest.py:683-688`.

### D5 — blast radius on the archived corpus

- **Required (plan):** determine whether archived plans are affected and report the count; report
  affected-count **separately** from examined-count; report **blocked** rather than estimating if the
  corpus is unreachable; do not search for it.
- **Claimed (report):** BLOCKED. Two counts reported separately for the population that *was* reachable:
  11 examined, 4 affected. Two bounds recorded for a future run.
- **Found / checks run:** `ls .plan/archived-plans` → *No such file or directory* (a single
  non-recursive existence check, as the report describes). Both bounds re-verified in the tree:
  `plan-retrospective/SKILL.md` frontmatter carries `default_on: false`, `presets: [full]`,
  `lane.class: prunable`, `order: 995`; and the archived fixture
  `test/plan-marshall/plan-retrospective/fixtures/archived-plan/solution_outline.md:41-43,60-61` carries
  bare bullets with no intent markers.
- **Verdict:** CONFIRMED as an honest blocked report. No coverage claim is made about archived plans and
  the two numbers are not conflated.

### D6 — tests verified to FAIL pre-fix

- **Required (plan):** (a) coverage run with source absent yields the unknown state; (b) composition run
  before any file is written emits no footprint-empty omission; (c) a read-intent declaration does not
  depress recall — each verified red pre-fix.
- **Claimed (report):** (a) yes; (b) **no, and it could not be** — the composer fix landed in a sibling
  plan before this branch, so red-before-green is unreachable; (c) yes — 21 tests, 18 failed / 3 passed
  against merge-base `5edca5a`, with a measured 4 `AttributeError` / 4 `KeyError` / 2 `AssertionError`
  split for the verification-added subset.
- **Checks run:** merge-base reproduction. `git show 5edca5a:…/check-artifact-consistency.py` written
  over the current source (byte snapshot taken first), current test module run, source restored:
  **19 failed, 2 passed**. The one-test delta from the report's 18/3 is fully explained by `63943f5`
  (#1295), which changed `test_no_declaration_keeps_its_distinct_skip_reason` to assert the new skip
  message — the test that passed at merge-base then fails at merge-base now. Direction and magnitude
  corroborate the report; nothing refutes it.
- **Verdict:** CONFIRMED with the exception the report discloses. (b)'s unreachability is a property of
  the branch point, not a gap in the tree: the coverage exists and passes.

## Correctness review

Read in full: `check-artifact-consistency.py` (949 lines), `verify_failure_scope.py` (253),
`analyze-logs.py` §§ `resolve_footprint` and the ARTIFACT floor, `_footprint_resolver.py`,
`_manifest_rules.py` §§ 300-395, `manage-execution-manifest.py` §§ 645-830 and 1985-2030,
`_manifest_validation.check_build_verdict_consistent`, `file_ops.PlanContext` §§ 1040-1192,
`_references_core.resolve_live_worktree` / `compute_plan_branch_diff`, `extension_base` §§ 655-720,
`pyproject_build.cmd_resolve_test_scope`.

**Defect 1 — high. `verify_failure_scope._resolve_declared_footprint` still returns a foreign
checkout's diff as the plan's footprint** (`verify_failure_scope.py:94`).

```python
worktree = Path(resolve_plan_context(plan_id, ensure=False).worktree_path)
```

`PlanContext.worktree_path` is documented (`file_ops.py:1097-1120`) to fall back to
`cwd_checkout_root()` for the `pending` and `disabled` worktree states — it raises
`WorktreeResolutionError` only when the `get-worktree-path` channel itself fails. The PR-review fix (P1)
removed the `Path.cwd()` fallback but left the read on the path face, so the same wrong answer is still
reachable through the state face. Both peer sites gate on `has_worktree` instead and document exactly
this hazard: `_references_core.resolve_live_worktree:188-194` and
`manage-execution-manifest._resolve_footprint:673-681`.

Reproduced with `_query_worktree_path` stubbed to `('pending', '')`:

```text
worktree_state = pending
has_worktree   = False
worktree_path  = /home/user/plan-marshall
_resolve_declared_footprint(...) -> set of 310 paths   # this repository's own diff
```

Consequence: for a plan whose worktree is opted-in but not yet materialized, every error path is
classified against an unrelated tree. When that tree is clean against its base — the ordinary case in a
consumer project — `compute_plan_branch_diff` returns an empty **resolved** set, every error path lands
out-of-scope, `exclusively_out_of_scope` becomes `true`, and phase-5-execute Step 11 offers *"Stash
foreign files and re-verify"* as the **default** remedy on no evidence. That is the exact harm the
module docstring (`:30-36`) and `classify_failure_scope` (`:117-128`) say the change removed. See **G1**.

**Defect 2 — medium. The same function's docstring still describes the removed behaviour**
(`verify_failure_scope.py:79-81`): *"An unresolvable worktree degrades to the current working directory,
preserving the previous non-fatal behaviour for archived plans and test seams."* This contradicts the
function's own summary line (`:62`, *"``None`` if unmeasurable"*) and the comment fifteen lines below
(`:96-104`). It also reads as sanction for Defect 1. See **G2**.

**No other logic defect found.** Specifically checked and found sound:

- the two intent regexes (`:118`, `:128`, `:134`) — `head` is `.+?`, so an all-parenthetical bare bullet
  keeps its text rather than reducing to an empty path; a marker is honoured only when its token is in
  `VALID_STEP_INTENTS`; a bare bullet with trailing prose after the annotation keeps the whole body as
  the path, which is pre-branch behaviour, unchanged;
- `read_intent_excluded = len(all_declared) - len(declared)` (`:442`) — `declared ⊆ all_declared`, so
  the cardinality difference equals the set difference; a path declared twice contributes one, and a
  path declared under both intents contributes none, as documented;
- the `recall` division at `:522` needs no zero guard — the `not declared` case returned `skip` above;
- `summarize_checks` (`:634-654`) reconciles: every emitted status buckets, so an `inconclusive` verdict
  cannot vanish from the summary;
- `check_metrics_generated` (`:716-767`) resolves both orders from discovery and reports `inconclusive`
  when either is unresolvable — the same three-state discipline, applied to a different input;
- `_apply_security_class_inactive` (`_manifest_rules.py:385`) — `None` short-circuits before any
  comparison, so no `None > 0` can be reached.

**One documented behavioural divergence, safe in direction, noted rather than charged as a defect.**
`_footprint_resolver.resolve_footprint:218-221` returns `FOOTPRINT_UNRESOLVED` when the tier-1 git diff
raises, discarding tiers 2-4; `analyze-logs.resolve_footprint:286-289` falls through to them. For a live
plan with a broken worktree diff but a valid `realized_footprint` capture, the recall check reports
`inconclusive` while the ARTIFACT floor resolves. The direction fails safe (a measurable footprint
reported unmeasurable, never the reverse), and `analyze-logs` documents the deviation at `:263-267`.
See **G7**.

## Test adequacy

| Deliverable | Covering tests | Non-vacuity evidence |
|---|---|---|
| D2 (reader, analyze-logs) | `test_analyze_logs_behavior.py::test_unresolvable_footprint_reports_unmeasurable_not_silence`, `::test_resolved_empty_footprint_stays_a_measured_zero`; `test_analyze_logs.py::test_unresolvable_when_no_tier_answers`, `::test_present_but_empty_key_is_a_resolved_empty_footprint` | Mutation `if footprint is FOOTPRINT_UNRESOLVED:` → `if False:` ⇒ 1 failed, 137 passed |
| D2 (reader, verify_failure_scope) | `test_verify_failure_scope.py::test_unmeasurable_footprint_does_not_attribute_failures_as_foreign`, `::test_measured_empty_footprint_still_classifies_as_foreign`, `::test_unresolvable_worktree_does_not_classify_against_the_current_directory`, `::test_footprint_resolver_never_diffs_the_current_directory` | Mutation `return None` → `return set()` on the unresolvable path ⇒ 2 failed, 11 passed |
| D2 (reader, recall/exact-match) | `test_check_artifact_consistency.py::test_resolved_but_empty_footprint_still_yields_a_measured_verdict` and the paired unresolvable case above it (asserts exactly 2 warning findings, one per peer) | Both directions present; the negative control is explicit about why it exists |
| D3 | `test_recall_read_intent_denominator.py` — 21 tests | Mutation disabling the intent filter ⇒ 10 failed, 11 passed |
| D4 | `test_security_class_gate_regression.py::test_unresolvable_footprint_keeps_the_step`, `::test_unresolvable_and_resolvable_empty_footprints_diverge`, `test_canonical_verify_inactive.py::test_unresolvable_footprint_is_a_noop_every_canonical_survives` | 31 passed; the adversarial direction (assert the gate is KEPT) is the asserted one |

Every mutated file was restored from a byte snapshot under `/tmp/verify-250-mutsweep/` and
`git status --porcelain` was confirmed clean for each afterwards. No `git checkout`/`restore`/`stash` was
used, and no file another agent had modified was touched.

**One test gap.** `test_footprint_resolver_never_diffs_the_current_directory` is named for a property
broader than it tests: it stubs `_query_worktree_path` to *raise*, covering only the
`WorktreeResolutionError` route. The `pending` route — the one that still diffs the wrong tree — has no
test, and the test immediately above it (`:300-313`) actually *pins* main-checkout diffing for the
`NO_PLAN` sentinel, which makes the absence easy to miss. See **G6**.

## Report accuracy

Every re-derivable claim in `report-01.md` held. Checked and confirmed:

- *"**9 Python files** (4 sources, 5 test modules) of **19** changed files"* — `git diff --name-status
  d34f2b8^1 d34f2b8` yields exactly 19 entries; the `-- '*.py'` filter yields exactly the 9 quoted
  paths, in the quoted order.
- *"`test_recall_read_intent_denominator.py` holds **21** tests"* — re-counted: 21.
- *"**13** files carry a footprint derivation; **5** are providers"*, *"**11** … across **seven**
  skills … all within the single `plan-marshall` bundle"* — independently re-derived; matches.
- *"11 sites examined, 4 affected"* — internally consistent with the population table and reported as
  two separate numbers, as D5 requires.
- *"the hypothesised shared footprint-derivation helper **exists** (`_footprint_resolver.py`)"* — it
  does, at `plan-retrospective/scripts/_footprint_resolver.py`, carrying `FOOTPRINT_UNRESOLVED` (`:57`)
  and `footprint_resolved` (`:114`).
- *"`constants.py:316` still named two importers"* (V8) — now names three (`constants.py:316-319`).
- *"Six obligations follow"* (W3) — `artifact-consistency.md:75` says "Six"; the list at `:77-82` has
  six bullets.
- P5's fixture fix — `fixtures/archived-plan/work/fragment-artifact-consistency.toon` declares
  `checks[6]`, `passed: 6`, and carries `read_intent_excluded: 0` (N10).
- P7's rejection — verified correct against `file_ops.py:1155-1191`; the `None` contract holds.
- Reviewer population M = 3 — derived the same way the report says it did: the `author_login` of each
  `automatic-review/standards/{bot_kind}.md` → `coderabbitai`, `sourcery-ai`, `cuioss-review-bot`.
- The cause-1 discharge claims — `branch-cleanup` frontmatter is `order: 70` with `destroys: [worktree]`;
  `plan-retrospective` is `order: 995`, i.e. the 925-unit gap the report and P8 cite; the
  capture-while-true call is at `branch-cleanup.md:1417-1430`, in the step immediately before worktree
  removal, exactly as described.

Claims that could **not** be checked here, with the reason:

- *"`./pw verify` … 20299 passed, 14 skipped in 418.71s"* and the per-commit quality-gate record —
  UNVERIFIABLE. Running the full suite is outside this audit's remit, and the branch was squash-merged
  (`d34f2b8` has the single parent `8a11858`), so per-commit history is gone from `main`.
- *"14 commits, each carrying the `Co-Authored-By` trailer"* — UNVERIFIABLE for the same reason.
- The round-1..5 finding narratives and the ≈194k/≈214k sub-agent token figures — historical, not
  observable in the tree.
- Round 5's `20298 passed` versus the build-gate section's `20299` is **not** an inconsistency: the
  report states the extra test came from the post-round-5 CodeRabbit fix, and the ordering of the two
  measurements supports that.

No false, stale, or overstated claim was found in `report-01.md` or in
`footprint-read-population.md`. Their one shared incompleteness is D1's population (**G5**), which is an
omission rather than a misstatement.

## Declared residue — current status

| Residue item (from report) | Still open? | Evidence |
|---|---|---|
| **R2-D1** — the phantom `Files expected to mutate:` / `Files to survey:` contract | **Closed by a later plan** | `63943f5` (#1295, plan 350) implemented the two-field form: `check-artifact-consistency.py:185-189` `_DECLARATION_HEADINGS` reads all three headings; `manage-solution-outline.py:344-367` now accepts the pair; `_plan_parsing.py:359-360` owns the constants |
| **R2-D2** — `plan-retrospective`'s undeclared `reads: [worktree]` | **Open** | `plan-retrospective/SKILL.md` frontmatter carries `order: 995`, `post_run_review: true`, no `reads:` key. The ordering defect remains structurally unenforceable |
| **D5 unassessed** (archived corpus unreachable) | **Open** | `.plan/archived-plans` still absent in this clone; a local run is still required |
| **D6(b) red-before-green** not re-checkable | **Open and permanently so** | The composer fix predates the branch point; nothing in the tree can change that |
| **P9** — Step 11 classification has no orchestrator consumer | **Open** | `grep -rln "exclusively_out_of_scope" marketplace/` returns only `phase-5-execute/SKILL.md` and `verify_failure_scope.py` (+ its `.pyc`). `workflow/execution.md` and `workflow/verification-feedback.md` contain neither `footprint_resolved` nor `exclusively_out_of_scope` |
| **R2-D3** — no worked `details:` example in the TOON fragment block | **Open** | `artifact-consistency.md:17-44` — the fragment block still shows `checks`, `findings`, `summary` and no `details:` |
| **Prose-count residue** ("assume this document still contains an uncorrected count") | **Not found** | Every count in the report that is re-derivable from the tree was re-derived and held; the enumeration lead-ins in `artifact-consistency.md` were recounted. The self-flagged risk did not materialise in the checkable subset |
| N9 / V9 — two commit messages with wrong counts, accepted uncorrected | **Open by decision** | Immutable without a force-push; confined to commit messages |

The lane-level lesson the report proposed at Step 9 was accepted and landed separately: `a83fd00` —
*chore(cloud-plan-lane): count enumerations, and define when the verify loop has converged (#1274)*.

## Out-of-scope and collateral

The plan excluded: capturing/persisting the footprint (producer side), rewriting the archived corpus,
posture-driven step drops, and a mis-attribution checker. The commit touches none of them —
`manage-references/**` is unmodified, no archived record is rewritten, and no posture or lane logic is
changed.

Collateral beyond the two fixed scripts, all declared in the report and all coherent with the code:

- `phase-5-execute/SKILL.md:820-833` — the classifier's TOON contract and the "read `footprint_resolved`
  FIRST" consumer obligation. Complete except for the missing `unresolved_reason` row (**G3**).
- `manage-execution-manifest/standards/decision-rules.md:18,21` — both `live_footprint` rows corrected
  from *"empty before the worktree is materialized"* to `None`, so the table is no longer internally
  contradictory (F8 + N6).
- `tools-file-ops/scripts/constants.py:316-319` — comment-only; names the third importer.
- `plan-retrospective/references/{artifact-consistency,logging-gap-analysis,request-result-alignment}.md`
  — all three describe behaviour the code actually has.
- `fixtures/archived-plan/work/fragment-artifact-consistency.toon` — production-shape fixture updated.

No `.plan/` write, no other plan's directory, no bundle outside the two skills the plan named plus
`tools-file-ops` (a comment).

## Method and coverage

- Read `plan.md`, `report-01.md`, `footprint-read-population.md`, and the epic `README.md`; then every
  production file and test file the commit touched, plus the four D4 predicate sites and their peers.
- Re-derived the commit's file set and Python-file set with `git diff --name-status` /
  `git diff --name-only -- '*.py'` against `d34f2b8^1`; confirmed the plan directory itself has not been
  edited since the merge (`git log d34f2b8..HEAD -- <plan dir>` is empty; `63943f5` touched plans 280
  and 350, not this one).
- Re-derived the D1 population independently, by sweeping the three derivation primitives and, as a
  cross-check against a filtered-search false negative, by sweeping the truthiness predicate shapes
  (`if not footprint`, `if footprint`, `footprint or`, `footprint else`). The second sweep is what
  surfaced G5, and it also confirmed the first sweep was not silently empty.
- Ran four targeted test files (76 tests) plus the two composer files (31 tests) with
  `uv run python -m pytest <file> -o addopts=""`; all green.
- Performed four mutations (three defect-injections, one merge-base rollback), each preceded by a byte
  snapshot into `/tmp/verify-250-mutsweep/` and each followed by restoration from that snapshot and a
  `git status --porcelain` check on the file. Two files in the tree were dirty from concurrent audit
  agents (`_freshness_crosscheck.py`, `extract-chat-signal.py`); neither was touched.
- Proved the G1 behaviour by executing `_resolve_declared_footprint` with `_query_worktree_path` stubbed
  to the `pending` state, in a throwaway plan directory under `/tmp`.
- **Not checked:** the full `./pw verify` figure, per-commit gate history, and any claim about the run's
  own process (round narratives, token usage, reviewer surface reads) — these are historical or squashed
  away, and are marked UNVERIFIABLE above rather than assumed.
