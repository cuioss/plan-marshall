# Gaps — 230-validate-precision

The deliverables landed and their headline measurements re-derive exactly, so what remains is
narrower than the plan: two regression tests that cannot fail against the defects they were written
for (one of them the lock on the run's most dangerous fix), two sentences in the shipped `SKILL.md`
contract that are false or mis-attributed, one live production defect the plan filed rather than
fixed, the untriaged residue the plan deliberately deferred, and a set of one-off figures in
`report-01.md` that are wrong against the tree they describe. Checked to reach this: the full 380-row
D0 partition replayed through the shipped predicates, the merge-commit and HEAD baselines re-measured
in-process, an old-vs-new resolved-edge diff over the same corpus, an 11-mutation sweep over the test
file, and synthetic probes of every excluded shape in both directions.

## G1 — Give the import-retarget guard a test that can fail

- **Kind:** test-gap
- **Severity:** medium
- **Topic:** tests
- **Where:** `test/pm-plugin-development/tools-marketplace-inventory/test_resolve_dependencies.py:1432-1468`
  (`TestRetargetAppliesToWrittenNotationOnly::test_python_import_is_not_retargeted_onto_a_same_named_entry_script`),
  guarding `marketplace/bundles/pm-plugin-development/skills/tools-marketplace-inventory/scripts/_dep_index.py:502-508`
- **Evidence:** replacing the guard `if dep_type is not DependencyType.SCRIPT_NOTATION:` with
  `if False:` leaves all 96 tests in the file green, while the live corpus moves from
  `unresolved 61 / circular 296` to `unresolved 50 / circular 297` — the 11 `extension_base` findings
  silently resolve. The test's probe bundle is named `probe-bundle` while
  `PYTHON_MODULE_MAPPINGS['toon_parser']` targets `plan-marshall:ref-toon-format:toon_parser`, so the
  entry-script lookup misses on the *bundle* segment whether or not the guard exists. No other test
  in the repository references `_entry_script_for_subcommand` or exercises this path.
- **Why it matters:** report-01.md § round 3 lists R‑10 ("the R‑2 fix introduced a false resolution
  … silently resolving 11 genuine findings") as **Fixed — with a regression test**. There is no
  regression test: the next refactor of the retarget can re-introduce R‑10 with a green suite.
- **Action:** rebuild the fixture so the mapped module's target bundle is the fixture bundle — e.g.
  monkeypatch `PYTHON_MODULE_MAPPINGS` to map a module onto `probe-bundle:real-skill:ghost_module`
  where `real-skill` owns a same-named entry script — and assert the import stays
  `resolved is False`.
- **Done when:** flipping the `dep_type is not DependencyType.SCRIPT_NOTATION` guard to a no-op makes
  the single test file fail.
- **Effort:** S
- **Risk if fixed:** none beyond the test file; the production path is unchanged.

## G2 — Cover the self-edge skip

- **Kind:** test-gap
- **Severity:** medium
- **Topic:** tests
- **Where:** `marketplace/bundles/pm-plugin-development/skills/tools-marketplace-inventory/scripts/_dep_index.py:562-567`
- **Evidence:** disabling the self-edge `continue` leaves all 96 tests green while the corpus moves
  from 296 to **297** cycles and gains 24 dependencies. Live instrumentation shows 24 retargets
  currently suppressed by this branch. No test name in the file mentions a self-edge or self-loop.
- **Why it matters:** R‑11 was a real defect found only by re-measuring the corpus — an entry script
  documenting its own verbs manufactured a circular dependency. The fix has no lock, so the same
  regression returns silently and shows up only as a moved `circular_dependencies` count.
- **Action:** add a case to `TestOnlyVerbBearingShapesRetarget` (or a sibling class) building a skill
  whose entry script's own file cites `bundle:skill:{verb}`, asserting the index records no edge from
  that script to itself and that `detect_circular_deps()` returns no cycle containing it.
- **Done when:** removing the `entry.to_notation() == component_id.to_notation()` branch turns the
  single test file red.
- **Effort:** S
- **Risk if fixed:** none.

## G3 — Correct the "cannot hide a real reference" claim in `SKILL.md`

- **Kind:** doc-defect
- **Severity:** medium
- **Topic:** bundle-docs
- **Where:** `marketplace/bundles/pm-plugin-development/skills/tools-marketplace-inventory/SKILL.md:194`
- **Evidence:** the sentence reads "Every exclusion in the table above is conditional, so **none of
  them can hide a real reference**." The index drops an excluded match precisely when it "names no
  component" (`_dep_index.py:569-572`) — which is the definition of a *broken* reference. Probed on a
  synthetic bundle, each of these cites a script that does not exist and produces **no row at all**:
  `Run probe-bundle:real-skill:ghost-script.py now.`;
  `Emitted (probe-bundle:caller:ghost-script) here.`;
  `Coordinate x.probe-bundle:caller:ghost-script here.`. The plain-shape control
  (`Run probe-bundle:caller:ghost-script now.`) is reported unresolved.
- **Why it matters:** this page is the contract a future gate is wired against. A reader who takes
  the sentence at face value will treat a clean `validate` as evidence that no broken reference
  exists in any excluded shape, which is the fail-open the same page rejects two paragraphs later.
- **Action:** scope the sentence to what it actually guarantees — an excluded shape that names an
  existing component is kept as an edge — and state the converse plainly: a reference that names
  nothing *and* wears an excluded shape is dropped unreported, so the gate under-reports exactly
  there.
- **Done when:** `SKILL.md` states both directions, and the § "Precision of `validate`" limits list
  includes broken-reference-in-excluded-shape alongside the two limits already there.
- **Effort:** S
- **Risk if fixed:** none — documentation only.

## G4 — Stop attributing verb-registration enforcement to a rule that cannot see the shape

- **Kind:** doc-defect
- **Severity:** medium
- **Topic:** bundle-docs
- **Where:** `marketplace/bundles/pm-plugin-development/skills/tools-marketplace-inventory/SKILL.md:204`
- **Evidence:** the page says the unchecked verb registration "is enforced separately by the
  `manage-invocation-invalid` plugin-doctor rule". That analyzer extracts invocations with
  `_NOTATION_RE` at
  `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_manage_invocation.py:375`,
  which is anchored on `python3\s+\.plan/execute-script\.py\s+…`. The retarget's whole population is
  decision-log prefixes and prose citations, none of which carry the executor prefix. The live
  instance: `plan-marshall:manage-execution-manifest:classify`
  (`manage-execution-manifest/standards/decision-rules.md:365`) resolves onto the entry script
  although `classify` is a `[STATUS]` label and not among `manage-execution-manifest.py`'s
  `add_parser` verbs.
- **Why it matters:** the page presents a compensating control that does not cover the gap, so the
  disclosed limitation reads as bounded when it is not. `report-01.md` § Residue in turn claims the
  limitation is "stated in `SKILL.md`", which is only half true.
- **Action:** replace the attribution with what holds — `manage-invocation-invalid` covers
  executor-prefixed invocations only — and record that a verb citation in prose or a decision-log
  prefix retargets without any check that the verb is registered, naming `…:classify` as the live
  example.
- **Done when:** the paragraph names the executor-prefix anchor as the rule's scope and no longer
  implies coverage of prose citations.
- **Effort:** S
- **Risk if fixed:** none — documentation only.

## G5 — Fix the two `_BUCKET_B_NOTATIONS` entries that match no script

- **Kind:** bug
- **Severity:** high
- **Topic:** dispatch/finalize
- **Where:** `marketplace/bundles/plan-marshall/skills/execute-task/scripts/inject_project_dir.py:39-50`
- **Evidence:** the frozenset holds `plan-marshall:workflow-integration-git:git` and
  `plan-marshall:workflow-pr-doctor:pr-doctor`. The on-disk scripts are
  `workflow-integration-git/scripts/git-workflow.py` and `workflow-pr-doctor/scripts/pr_doctor.py`,
  and every real invocation uses those spellings — e.g.
  `tools-script-executor/standards/cwd-policy.md:68` calls
  `plan-marshall:workflow-integration-git:git-workflow locate-plan-checkout`, and
  `workflow-pr-doctor/SKILL.md:84` calls `plan-marshall:workflow-pr-doctor:pr_doctor track-attempt`.
  The comparison at `inject_project_dir.py:121` is exact-match on the notation, so it never fires for
  either. Both rows are still unresolved at HEAD.
- **Why it matters:** a Bucket B guard that cannot fire. When a plan runs in an isolated worktree,
  `--plan-id` is never injected into git-workflow or pr-doctor invocations, so those scripts resolve
  against the wrong checkout — silently, because the helper reports "not rewritten" rather than an
  error. This is the highest-value item the plan filed.
- **Action:** replace the two entries with `plan-marshall:workflow-integration-git:git-workflow` and
  `plan-marshall:workflow-pr-doctor:pr_doctor`, after confirming both scripts implement the
  `--plan-id`/`--project-dir` two-state contract; add a test asserting injection fires for each.
- **Done when:** `inject_project_dir` rewrites a `git-workflow` and a `pr_doctor` command, and the
  validator reports zero unresolved rows sourced from `inject_project_dir.py`.
- **Effort:** M
- **Risk if fixed:** injection begins firing on two script families for the first time — if either
  script does not honour `--plan-id`, previously-silent commands start failing loudly.

## G6 — Re-derive the test-count figures in the run report

- **Kind:** report-defect
- **Severity:** low
- **Topic:** measurement/metrics
- **Where:** `doc/plans/code-intelligence-substrate/230-validate-precision/report-01.md:265-267`
- **Evidence:** "**30 new test functions**; the file's collected total is **95** (from 65)". The
  test file is byte-identical between the merge commit `3d96e40` and HEAD (`git diff` empty), and
  today it holds **96** test functions and collects 96; the merge parent holds 65, with 31 added and
  0 removed.
- **Why it matters:** the report's own closing lesson is that a number is a claim; this one was
  carried forward rather than re-derived, in the section that documents the plan's regression lock.
- **Action:** correct to 31 new / 96 collected.
- **Done when:** the figures in § D5 match `grep -c "def test_"` on the file at the merge commit.
- **Effort:** S
- **Risk if fixed:** none.

## G7 — Re-derive the inventory-suite pass count

- **Kind:** report-defect
- **Severity:** low
- **Topic:** measurement/metrics
- **Where:** `report-01.md:266`
- **Evidence:** "the inventory suite is **187 passed**". The directory
  `test/pm-plugin-development/tools-marketplace-inventory/` is unchanged since the merge and yields
  `188 passed` under `uv run python -m pytest … -o addopts=""`.
- **Why it matters:** same class as G6 — an off-by-one in a figure presented as measured.
- **Action:** correct to 188.
- **Done when:** the stated figure matches a run of that directory at the merge commit.
- **Effort:** S
- **Risk if fixed:** none.

## G8 — Reconcile the two whole-suite figures

- **Kind:** report-defect
- **Severity:** low
- **Topic:** measurement/metrics
- **Where:** `report-01.md:320` ("**`20075 passed, 14 skipped`**") vs `report-01.md:563`
  ("20076 passed / 14 skipped")
- **Evidence:** the Build gate section and the Contract check table state different totals for the
  same final `./pw verify` run. Neither is verifiable now — the tree has moved — so the
  contradiction is the whole of the evidence.
- **Why it matters:** the build gate is the report's own evidence that the change is safe; two
  different totals for one run make it impossible to tell which was measured.
- **Action:** state one figure, or state that the two runs differed and which is final.
- **Done when:** a single whole-suite figure appears in the report.
- **Effort:** S
- **Risk if fixed:** none.

## G9 — Correct the commit count

- **Kind:** report-defect
- **Severity:** low
- **Topic:** measurement/metrics
- **Where:** `report-01.md:560` ("Twelve commits"), `:474` (F‑7: "**Fixed** — nine"), `:589`
  ("before each of eight commits")
- **Evidence:** the PR carries **13** commits (GitHub API, `pull_request_read get_commits` on
  cuioss/plan-marshall#1254). The report states three different values, and F‑7 records a correction
  ("nine") that does not match the table it claims to have corrected ("Twelve").
- **Why it matters:** F‑7 is presented as a closed reporting-accuracy finding; it is not.
- **Action:** re-derive from the PR commit list and state one value, or state the two populations
  (commits at report time vs commits at merge) explicitly.
- **Done when:** every commit count in the report agrees with the PR's commit list or names its own
  population.
- **Effort:** S
- **Risk if fixed:** none.

## G10 — Pin `CANONICAL_COMMAND_PREFIXES` to the authority it claims to mirror

- **Kind:** test-gap
- **Severity:** low
- **Topic:** tests
- **Where:** `marketplace/bundles/pm-plugin-development/skills/tools-marketplace-inventory/scripts/_dep_detection.py:164-169`
  and `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_quality_phases.py:68`
- **Evidence:** the constant's docstring states it "mirrors `_CANONICAL_VERIFY_PREFIXES` in
  `plan-marshall:manage-config`", and `SKILL.md:189` repeats the claim. The two tuples are currently
  identical, but no test or import ties them: `grep` for `CANONICAL_COMMAND_PREFIXES` outside the
  defining module returns nothing.
- **Why it matters:** R‑5 was exactly this drift (the mirror carried one of two prefixes). The fix
  restored the value without adding anything that would notice the next drift.
- **Action:** add a test that loads both modules and asserts
  `CANONICAL_COMMAND_PREFIXES == _CANONICAL_VERIFY_PREFIXES`.
- **Done when:** removing one prefix from either module turns a test red.
- **Effort:** S
- **Risk if fixed:** the test couples two bundles at test time; use the existing path-loading helper
  so no import package is implied.

## G11 — Restate round-2 finding 2's disposition: a parenthesised broken reference still escapes

- **Kind:** report-defect
- **Severity:** low
- **Topic:** detectors/auditor
- **Where:** `report-01.md:360` (round-2 finding 2, "**Fixed** — see the provisional change below")
- **Evidence:** the finding as stated is "any parenthesised reference was dropped unconditionally, so
  a genuinely-broken reference written parenthetically escaped the gate". Probe:
  `Emitted (probe-bundle:caller:ghost-script) here.` on a skill with no entry script still produces
  no row — and `TestExclusionsAreConditional::test_parenthesised_prefix_without_an_entry_script_is_dropped`
  codifies that as intended behaviour. What the provisional mechanism fixed is the adjacent case of a
  *valid* reference written parenthetically.
- **Why it matters:** a reader auditing the gate's fail-open surface will believe this hole is
  closed. It is not; it is deliberate, and belongs on the disclosed-limitations list instead.
- **Action:** restate the disposition as "partly fixed — valid references in an excluded shape are
  preserved; a broken one in an excluded shape is still dropped", and cross-reference the
  limitations paragraph fixed under G3.
- **Done when:** the disposition distinguishes the two cases.
- **Effort:** S
- **Risk if fixed:** none.

## G12 — Restate round-2 finding 3's disposition: `…:ghost.py` still escapes

- **Kind:** report-defect
- **Severity:** low
- **Topic:** detectors/auditor
- **Where:** `report-01.md:361` (round-2 finding 3, "`bundle:skill:script.py` was dropped by the
  `.`+word arm — **Fixed**")
- **Evidence:** probe `Run probe-bundle:real-skill:ghost-script.py now.` produces no row. Only the
  resolvable case is rescued, which is what
  `TestExclusionsAreConditional::test_real_reference_with_py_suffix_is_kept` asserts.
- **Why it matters:** recorded as a separate instance from G11 because it is a separate finding with
  its own disposition; both were closed on the same reasoning and both remain half-open.
- **Action:** as G11, for the `.`+word arm.
- **Done when:** the disposition distinguishes the valid and broken cases.
- **Effort:** S
- **Risk if fixed:** none.

## G13 — Re-derive the all-guards-off fixture count

- **Kind:** report-defect
- **Severity:** low
- **Topic:** measurement/metrics
- **Where:** `report-01.md:353-355` ("all-off gives 6, corroborating the red-before-green claim")
- **Evidence:** rebuilding the shipped fixture
  (`test_resolve_dependencies.py:1240-1269`, seven excluded instances after R‑13) with all four
  exclusion arms disabled yields **7** unresolved rows:
  `bundle:skill:script`, `default:verify:quality-gate`, `example:example-lib:compile`,
  `precision-bundle:phase-thing:{ghost-script,planning,qgate,standards}`.
- **Why it matters:** the "6" belongs to the pre-R‑13 fixture; quoting it against the shipped fixture
  makes a stale number look like present-tense corroboration.
- **Action:** re-derive against the shipped fixture and mark the earlier figure as historical.
- **Done when:** the stated all-off count matches the shipped fixture.
- **Effort:** S
- **Risk if fixed:** none.

## G14 — Pin the baseline measurement to a commit

- **Kind:** report-defect
- **Severity:** low
- **Topic:** measurement/metrics
- **Where:** `report-01.md:29-36` (baseline table) and `:199-204` (re-baseline)
- **Evidence:** the pre-change detector over the merge parent `3d96e40^` gives
  `total_dependencies 5332 / resolved 4952`, against the report's `5301 / 4921`; the merged tree gives
  `5058 / 4996` against the report's `5027 / 4965`. `unresolved`, `total_components` and
  `circular_dependencies` match exactly, and every delta the report states reproduces (resolved +44,
  dependencies −274), so this is main moving under the branch before the squash-merge — but the
  report names no commit, so a later reader cannot reproduce either absolute figure.
- **Why it matters:** the report's own standard is that every figure carries its population; these
  two carry a corpus that no longer exists at any named revision.
- **Action:** state the commit each baseline was measured at (or note that the absolutes are only
  comparable to each other and that the deltas are the durable claim).
- **Done when:** both tables name their measurement revision.
- **Effort:** S
- **Risk if fixed:** none.

## G15 — Partition the untriaged unknown-bundle residue

- **Kind:** incomplete
- **Severity:** medium
- **Topic:** detectors/auditor
- **Where:** `marketplace/bundles/pm-plugin-development/skills/tools-marketplace-inventory/scripts/resolve-dependencies.py:268-318`
  (`cmd_validate`) and `SKILL.md:212`
- **Evidence:** 26 of the 61 unresolved rows at HEAD name a first segment that is not an indexed
  bundle (`lint:js:fix` ×9, `lint:style:fix` ×6, `project:core:compile` ×3, `HH:mm:ss`,
  `YYYY-MM-DDTHH:MM:SSZ` ×2, `css:*` ×2, `trivy:ignore:CVE-2024-XXXX`,
  `pm-dev-builder:build-cache:manage-cache`, `phase-6-finalize:default:record-metrics`). The plan's
  residue names the fail-closed way forward — report `unknown-bundle` separately from
  `missing-component` — and the sibling editor-facing plan is explicitly blocked on it.
- **Why it matters:** the 26 rows are 43 % of the current finding set and are the reason `validate`
  is documented as a report rather than a gate. Surfacing them into an editor reproduces this epic's
  own archetype.
- **Action:** add a reason field to each unresolved row (`unknown-bundle` vs `missing-component`)
  rather than suppressing by bundle membership, and update § "Precision of `validate`".
- **Done when:** `validate` output carries a per-row reason and the in-namespace subset can be
  consumed alone without a client-side bundle check.
- **Effort:** M
- **Risk if fixed:** the output contract changes — consumers keying on the current `unresolved` row
  shape (including the architecture materialization in `plan-marshall-plugin`) must be checked.

## G16 — Resolve the `extension_base` mapping and the nested-script coverage decision

- **Kind:** omission
- **Severity:** medium
- **Topic:** detectors/auditor
- **Where:** `marketplace/bundles/pm-plugin-development/skills/tools-marketplace-inventory/scripts/_dep_detection.py:218-225`
  (`PYTHON_MODULE_MAPPINGS['extension_base']`) and `_dep_index.py:290` (`scripts_dir.glob('*.py')`)
- **Evidence:** 11 unresolved rows at HEAD for `plan-marshall:extension-api:extension_base`. The
  module actually lives at `plan-marshall/skills/script-shared/scripts/extension/extension_base.py`,
  and component discovery globs `scripts/*.py` rather than recursing, so no rename alone can make the
  mapping resolve.
- **Why it matters:** the single largest filed finding, and the mechanism behind it (nested modules
  are importable but never components) silently limits every consumer of the graph, including the
  architecture edge materialization.
- **Action:** decide between recursing discovery into `scripts/{subdir}/` (widening the component
  namespace) and correcting the mapping to a component that exists; implement one, with a test.
- **Done when:** the 11 rows either resolve or are re-classified with a stated reason.
- **Effort:** M
- **Risk if fixed:** recursing discovery adds components to a namespace that `deps`/`rdeps`/`tree`
  and the architecture projection all key on.

## G17 — Establish plugin-doctor's real CLI surface in its documentation

- **Kind:** omission
- **Severity:** low
- **Topic:** bundle-docs
- **Where:** documented invocations of `pm-plugin-development:plugin-doctor:{validate,fix,analyze}`
  (6 + 4 + 3 rows at HEAD)
- **Evidence:** `plugin-doctor/scripts/doctor-marketplace.py` registers `list-components`, `analyze`,
  `fix`, `report`, `quality-gate`, `test-conventions`, `contracts` — there is no `validate`, and the
  entry script is not same-named with its skill, so `plugin-doctor:{verb}` notations are not
  executable and are correctly reported.
- **Why it matters:** 13 of the 35 in-namespace findings are documentation that names commands which
  would not run.
- **Action:** rewrite each site as `pm-plugin-development:plugin-doctor:doctor-marketplace {verb}`
  against the registered surface, dropping the `validate` chains that map onto nothing.
- **Done when:** those 13 rows leave the unresolved set.
- **Effort:** M
- **Risk if fixed:** the documented workflows change shape; readers following the old chains must
  find the replacement verbs.

## G18 — Correct `tools-integration-ci`'s Executor Mapping

- **Kind:** doc-defect
- **Severity:** low
- **Topic:** bundle-docs
- **Where:** the two rows `plan-marshall:tools-integration-ci:{github,gitlab}` (1 each at HEAD)
- **Evidence:** the skill's entry script is `tools-integration-ci/scripts/ci.py`
  (`tools-integration-ci/SKILL.md:306` documents its canonical argparse surface); no `github.py` or
  `gitlab.py` exists.
- **Why it matters:** two documented notations that cannot execute, in the abstraction layer the
  repository mandates for all CI operations.
- **Action:** replace with the `ci.py` notation plus whatever verb selects the provider.
- **Done when:** both rows leave the unresolved set.
- **Effort:** S
- **Risk if fixed:** none beyond the doc.

## G19 — Make the pre-existing unconditional drops provisional

- **Kind:** bug
- **Severity:** medium
- **Topic:** detectors/auditor
- **Where:** `marketplace/bundles/pm-plugin-development/skills/tools-marketplace-inventory/scripts/_dep_detection.py:315-333`
- **Evidence:** the comment-line skip, URL-line skip and `http`/digit segment filters discard matches
  outright rather than recording an exclusion. Measured at HEAD, the comment-line skip alone hides
  **9 resolvable** notations (e.g.
  `plugin-architecture/references/goal-based-organization.md:293` →
  `pm-plugin-development:tools-marketplace-inventory:scan-marketplace-inventory`,
  `plugin-task-plan/SKILL.md:185` → `plan-marshall:manage-architecture:architecture`) and 7
  non-resolvable ones, none of which is genuinely broken today. `SKILL.md:198` discloses this.
- **Why it matters:** these are the last fail-open drops in the detector. A broken notation written on
  a markdown heading or beside a URL is invisible to the gate, and the graph under-reports 9 real
  edges.
- **Action:** route these three skips through the same `Exclusion` mechanism so the index decides on
  existence, adding an `Exclusion` member per shape.
- **Done when:** disabling each skip changes no `unresolved` row, and the 9 resolvable notations
  appear as edges.
- **Effort:** M
- **Risk if fixed:** `total_dependencies` and possibly `circular_dependencies` move; every figure the
  skill's own docs quote must be re-measured.

## G20 — Check that a retargeted verb is registered

- **Kind:** incomplete
- **Severity:** medium
- **Topic:** detectors/auditor
- **Where:** `marketplace/bundles/pm-plugin-development/skills/tools-marketplace-inventory/scripts/_dep_index.py:481-529`
- **Evidence:** the retarget asks only whether the *shape* may bear a verb and whether an entry
  script exists; it never asks whether the segment is one the entry script registers. Live instance:
  `plan-marshall:manage-execution-manifest:classify`
  (`manage-execution-manifest/standards/decision-rules.md:365`) resolves although
  `manage-execution-manifest.py` registers `compose`, `read`, `lanes`, `record-step`,
  `refire-report`, `validate`, `reconcile`, `validate-loadable`, `step-params` — not `classify`. Of
  37 live retargets, 36 land on `manage-execution-manifest` and 1 on `manage-status`.
- **Why it matters:** the retarget is the one place this change *adds* resolutions, so it is the one
  place it can manufacture a false clean verdict. Today the false resolution is benign; the mechanism
  is not bounded.
- **Action:** validate the segment against the entry script's argparse surface (the
  `argparse_surface` helper plugin-doctor already uses) and leave the row unresolved when the verb is
  not registered.
- **Done when:** `…:classify` is reported again, and a synthetic unregistered verb on a skill with an
  entry script stays unresolved while a registered one still resolves.
- **Effort:** M
- **Risk if fixed:** parsing argparse surfaces at index time is heavier than the current lookup and
  couples this skill to that helper; some of the 37 live retargets may turn back into findings.
