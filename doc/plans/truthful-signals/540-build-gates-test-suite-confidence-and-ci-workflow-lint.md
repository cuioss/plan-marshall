> ⛔ **FIRST INSTRUCTION — do not skip, do not delete, do not move below the title.**
>
> Before reading the rest of this plan and before any other action, load the working contract that
> governs this run:
>
> ```text
> Skill: cloud-plan-lane
> ```
>
> It owns the branch/PR/review-comment cycle, the build gate, the pre-PR verification sub-agent, the
> run report, and the closing self-check. **Nothing in this plan overrides it** — where this plan and
> the contract disagree, the contract wins, and the disagreement is reported.
>
> If the skill cannot be loaded, **stop and report the run blocked**. Do not reconstruct the workflow
> from this file: the parts that matter most — the merge gate, the verification dispatch, the report
> — are not in here.
>
> This block is part of the plan, not part of the template. It survives into every copy.

# Build gates, test-suite confidence and CI workflow lint report what they actually checked

**Epic:** truthful-signals
**Branch prefix:** fix — the substance is defective guards and false published signals, not new capability

## Problem

Seven guards in this repository publish a confident verdict over a population they did not examine,
or over a quantity they did not measure. Each was landed as the *fix* for an earlier instance of the
same defect, and each carries the defect one layer down:

- **The `.plan/` exemption predicate** decides trackedness with `git ls-files` (the index) while
  observing dirtiness with un-`-z` porcelain (C-quoted, octal-escaped). The two never speak one
  encoding, and the index cannot see a staged deletion — so a `git rm`'d tracked `.plan/` descriptor,
  and any tracked `.plan/` path git chooses to quote, are silently reported as untracked plan state at
  the guard sites that exist to catch exactly that leak.
- **`tests_run`** is documented as "the executed-test count" and is computed as
  `passed + failed + skipped`. A green build that executed nothing but skips therefore clears a true,
  already-recorded `test-failure` finding and publishes a non-zero execution count for it.
- **The marker-write guard** reports that no production source writes `.orphaned_at`, while its
  detector recognises exactly one AST shape out of at least six, over a glob that misses whole script
  packages, with no floor that would make an empty population fail.
- **The freshness backstop** is calibrated at 2000 files/s — 6× above the throughput band of the
  cache-answered incident it was built to catch — and both of its guards clear the constant by orders
  of magnitude, so a recalibration-shaped regression ships green.
- **The coverage verdict** renders `COMPLETE` over zero dimensions, drops a mypy scope that was
  attempted-and-empty, and asserts in its own honesty output that the gate "never performs" checks it
  routinely performs.
- **The workflow-lint guard** — the sole automated control over the repository's template-injection
  surface — scans neither a wide-dash `run:` step nor a multi-line plain scalar, and asserts a
  `permissions:` block exists rather than that it is read-only.
- **The multi-target generator** guards one of two corrupt-JSON classes, one of two emitters, and one
  of two prune directions.

The mechanism is the same in every case and is stated file-by-file in the gap documents this plan
draws from — see § Notes for the paths. It is: **the population, the vocabulary, or the shape set the
check ranges over is asserted rather than derived**, so the check's green answers a question narrower
than the one its message claims.

## Goal

Every guard named above either enforces the guarantee it reports, or states honestly what it does not
cover. Where a fix requires a policy call this run cannot make, the plan records a proposal for the
operator rather than making it — and removes the false statement that made the unarmed state look
armed.

## Deliverables

Ordered so the five `high` gaps land in D0–D4. **D0 is a stop condition:** if any population below
cannot be derived by the command stated, record which one and **halt the plan** — do not substitute a
hand-maintained list, because a hand-maintained population is the defect class this plan closes.

1. **D0 — Derive the five populations this plan's scopes rest on, or halt** *(closes no gap; gates
   D1, D2, D3, D5, D6)*
   Derive each population and record the command and the result in the run report. Every count below
   is a **lead, not a fact — re-derive it at the moment you use it**; the tree the run clones is not
   guaranteed to match the tree this plan was authored against.
   - **(a) D1's guard-site set** — every consumer of `partition_plan_state_exemption` and of
     `git_dirty_files`, from `grep -rn 'partition_plan_state_exemption\|git_dirty_files'
     --include=*.py marketplace/ test/`. The two sites this plan expects are
     `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/post_run_source_guard.py` and
     `marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/_invariants.py`; a third consumer
     is in D1's scope and is reported.
   - **(b) D2's status vocabulary** — every `STATUS_*` constant in
     `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_result.py` that
     names a *result* status (lead: five — `success`, `error`, `timeout`, `killed`, `indeterminate`).
   - **(c) D3's production-source population** — the file count of
     `marketplace/bundles/**/skills/**/scripts/**/*.py` excluding `__pycache__`, and the count of the
     narrower `**/skills/**/scripts/*.py` the test uses today (leads: 412 and 386).
   - **(d) D5's workflow set** — every file under `.github/workflows/`, and for each, its top-level
     `permissions:` scopes (lead: 7 workflows, all read-only-by-default except `pr-agent.yml`).
   - **(e) D6's targets module set** — every non-`__init__` `.py` module under `marketplace/targets/`,
     `marketplace/targets/claude/`, `marketplace/targets/opencode/` and `marketplace/targets/pr_agent/`.
   *Done when:* the run report names each of the five populations, the exact command that produced it,
   and the derived count — or names the population that could not be derived and states the plan
   halted there.

2. **D1 — One trackedness oracle, one path encoding** *(closes 330/G2, 330/G5 — both `high`)*
   `_plan_state_exemption.tracked_plan_paths`
   (`marketplace/bundles/plan-marshall/skills/script-shared/scripts/_plan_state_exemption.py`) asks
   only the index, so a staged deletion of a tracked `.plan/` file is exempted at both guard sites;
   `git_dirty_files`
   (`marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/_git_helpers.py`) observes with
   un-`-z` porcelain and strips the surrounding quotes without unescaping, so a quoted tracked
   `.plan/` path never matches the tracked set. Fix both:
   - Widen `tracked_plan_paths` so "tracked" means *in the index **or** at HEAD* — union the existing
     `git ls-files -z -- .plan/` result with `git ls-tree -r -z --name-only HEAD -- .plan/`, returning
     `None` only when the `ls-files` observation itself fails, so the fail-closed contract is unchanged
     and a repository with no commits still falls back to the index answer.
   - Make both observations speak one encoding: either switch `git_dirty_files` to
     `git status --porcelain -z` decoded through the `parse_porcelain_z` logic that already exists in
     `phase-6-finalize/scripts/post_run_source_guard.py` (extract it to `script-shared` so the two
     sites share one implementation — this is D1's own "one predicate, not two copies" principle), or
     run both git calls under `-c core.quotePath=false`. Pick one, and say in the run report which and
     why.
   - Add regression tests beside `test_partition_retains_tracked_plan_file` in
     `test/plan-marshall/script-shared/test_plan_state_exemption.py`: a `git rm`'d tracked `.plan/`
     path is **retained**; an untracked `.plan/` path in the same repository is still **exempted**; and
     a committed-then-dirtied tracked `.plan/` path whose name git quotes is **retained**. Add the
     matching layer-D test beside `test_capture_main_dirty_files_reports_tracked_plan_state`.
   - **Filesystem contingency, decided in advance so the run never stalls:** the quoting probe wants a
     non-ASCII filename (`.plan/ünï.json`). If the runner's filesystem or locale refuses to create it,
     use a path containing a **space** instead — git quotes that too under the default
     `core.quotePath` — and record in the report which probe was used. Do not skip the test.
   *Done when:* in a throwaway repository where a committed `.plan/marshal.json` has been `git rm`'d,
   `post_run_source_guard._observe_dirty_source` returns `clean=False` with that path in
   `offending_paths` and **absent** from `exempted_paths`, and `partition_plan_state_exemption` retains
   it; and with a committed-then-dirtied quoted tracked `.plan/` path, `_capture_main_dirty_files`
   returns it spelled as `git ls-files` spells it. Each new test is **seen RED against today's
   `tracked_plan_paths` / `git_dirty_files`** before the fix lands, and the red output is quoted in the
   run report.

3. **D2 — Published build counts and vocabularies mean what they say**
   *(closes 380/G1 `high`, 380/G7, 430/G2, 430/G3)*
   Two published contracts in
   `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/` are wrong in the same way —
   a field's definition does not match its computation, and the test asserting totality samples rather
   than derives.
   - **Executed-test count (380/G1, 380/G7).** Add an `executed` property (`passed + failed`) to
     `UnitTestSummary` in `_build_parse.py` and use it at **both** emission sites:
     `_build_shared.py` `cmd_run_common` (today `tests_run = test_summary.total`) and
     `_build_shared.py` `cmd_parse_common` (today `metrics.tests_run = test_summary.total`). Update
     the three places that state the definition: `_reconcile_pending_build_findings`'s docstring, the
     `tests_run` paragraph of `_build_format.py`'s `EXTRA_FIELDS` docstring, and
     `marketplace/bundles/plan-marshall/skills/extension-api/standards/build-api-reference.md`.
   - **Wire-vocabulary totality (430/G2, 430/G3).** `_build_server_protocol._RESULT_STATUS_TO_WIRE`
     has no row for `indeterminate`, so `wire_status_from_result('indeterminate')` returns a
     non-terminal string through the pass-through fallback and a waiting client re-polls forever.
     **The choice is made here, not by the run:** add an explicit `indeterminate` row mapping onto the
     existing terminal failure wire status, and make `wire_status_from_result` **raise** on a status
     with no row rather than pass it through. Adding a fifth *wire* status is deliberately not taken —
     see Out of scope. Update the three sites in that module that still enumerate a four-value
     `_build_result` vocabulary (the table comment, `wire_status_from_result`'s `Args`, and
     `LogVerdict.status`'s docstring).
   - **Derive the totality population (430/G3).** `TestVocabularyTranslationIsTotal` in
     `test/plan-marshall/script-shared/test_non_finish_discrimination.py` parametrises a literal
     four-tuple, so it is blind to the one omission that exists. Derive the population from
     `_build_result` — D0(b)'s set, read from the module at test time, not copied into the test — and
     assert for each member both that it has an explicit row and that its translation is in
     `TERMINAL_STATUSES`. Keep the explicit expected-mapping table as a *separate* assertion so a wrong
     mapping still fails; stop letting the table define the population.
   *Done when:* a green build whose summary is skips-only leaves a pending `test-failure` finding
   pending and publishes `tests_run: 0`; a green build reporting `2 passed, 9 skipped` publishes
   `tests_run: 2`; `run` and `parse` return the same `tests_run` for the same log; and — **verified by
   mutation, red-first** — adding a new `STATUS_*` constant to `_build_result.py` without a
   `_RESULT_STATUS_TO_WIRE` row makes `TestVocabularyTranslationIsTotal` **fail**, with the mutation's
   red output quoted in the run report and the mutation reverted afterwards.

4. **D3 — The marker-write guard enforces the guarantee it reports**
   *(closes 360/G1 `high`, 360/G6, 360/G4, 360/G2)*
   In `test/plan-marshall/tools-script-executor/test_marker_free_resolution.py`:
   - **Widen `_writes_marker` (360/G1).** Today it flags only
     `(version_dir / '.orphaned_at').write_text(...)` — the literal must sit inside the call's own
     target expression. Add: (1) alias resolution, so a `.orphaned_at` path bound to a `Name` and then
     written through `write_text`/`write_bytes`/`touch`/`open(..., 'w')` in the same scope is a hit;
     (2) module-level string-constant resolution, so `ORPHAN_MARKER_NAME`- and `_MARKER_NAME`-style
     indirection is covered; (3) a template descent — for each module-level `Assign` whose value is a
     string constant containing `.orphaned_at`, `ast.parse` that string and re-run the detector over
     it, labelling hits with the enclosing constant's name. Items (1) and (3) may be ported from the
     retired `test_orphan_marker_existence_only.py` (recoverable with
     `git show d01edfdf^:test/plan-marshall/script-shared/test_orphan_marker_existence_only.py` —
     `_assigned_alias`, `_check_alias_uses`, `_embedded_code_tree`, `_template_label`); the
     named-constant and `.touch()` shapes were missed by that module too and must be **written new**.
     If the host module's own marker fixtures stay spelled via `_MARKER_NAME`, exclude the test tree
     from the production sweep **explicitly** rather than relying on the detector's blindness to it.
   - **Restore the non-vacuity floor (360/G6).** The sweep asserts `not offenders` over a population
     nothing constrains; with the glob pointed at a non-existent directory the whole module still
     passes. Bind the population, then assert before the offender check: a floor on its size (set it
     comfortably under D0(c)'s derived recursive count so ordinary bundle churn does not trip it); that
     the file-name set is a superset of the modules that mention the marker today; and include the
     population size in the offender assertion message.
   - **Widen the sweep glob (360/G4).** `_SOURCE_GLOB` is `'**/skills/**/scripts/*.py'`, which reaches
     only files directly inside a `scripts/` directory while the docstring claims coverage of "any
     production script under `marketplace/bundles/**/scripts`". Change it to
     `'**/skills/**/scripts/**/*.py'` and filter `__pycache__` in the loop. Assert the swept count
     against D0(c)'s recursive count **re-derived at runtime**, never hard-coded.
   - **Retire the deleted mechanism's prose (360/G2).** In
     `test/plan-marshall/tools-script-executor/test_executor_version_split_regression.py`, three
     statements assert a `_retention_pinned_versions` mechanism that no longer exists anywhere in
     `marketplace/` or `test/`: a docstring ("fall back to the retention-pinned NEWEST dir"), a case
     banner, and a test name plus its docstring. Rewrite all three to state what the code does — the
     marker is never consulted, so selection is eligibility plus version ordering alone. Assertions and
     fixtures stay as they are.
   *Done when:* a unit test over synthetic source asserts `_writes_marker` returns a hit for each of
   the alias-bound, named-constant, `open()`, `.touch()` and template-embedded shapes;
   `test_no_production_source_writes_the_shared_marker` still passes over the real tree with the
   recursive glob; **and — red-first, this is a vacuous-guard closure —** pointing `_SOURCE_GLOB` at a
   pattern matching zero files makes the module **FAIL**, demonstrated by a mutation whose red output
   is quoted in the run report and which is reverted afterwards (confirm the file is byte-clean via
   `git diff --quiet` before and after); and
   `grep -n -i 'retention.pin' test/plan-marshall/tools-script-executor/test_executor_version_split_regression.py`
   returns nothing while that file's tests still pass.

5. **D4 — Build-gate coverage verdicts stop overstating**
   *(closes 160/G1 `high`, 160/G8, 160/G10, 160/G6, 160/G5, 160/G3)*
   **Do 160/G1 first within this deliverable — it is the `high`, and a run that stops here must have
   shipped it.** All sites are `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_gate_coverage.py`
   and root `build.py` unless stated.
   - **(G1) Recalibrate the freshness backstop.** `MAX_ANALYSIS_THROUGHPUT` is `2000.0` files/s. The
     incident it exists to catch is 660 files in 2–5 s — 132–330 files/s — which the constant rates
     `plausible`. Lower it to a value in the low hundreds that separates cache-answered throughput from
     cold-analysis throughput, and **record in the constant's own comment the measured cold throughput
     the ceiling was derived from, re-measuring it on this tree during the run** (lead, do not trust
     it: `uv run python build.py compile` reported ~414 files in ~11.35 s, ~37 files/s — re-derive and
     write the figure you actually observe). Add a unit test pinning
     `classify_check_duration(660, 3.0).plausible is False`, and re-key
     `test_quality_gate_fails_closed_when_whole_tree_mypy_reports_implausibly_fast`
     (`test/default/test_build_verify.py`) off the zero-elapsed degenerate case onto a non-zero elapsed
     inside the incident band so the integration guard also bites. Confirm the existing negative guards
     survive: `classify_check_duration(414, 11.35).plausible` must still be `True`, and
     `test_large_scope_with_real_elapsed_is_not_flagged` and
     `test_throughput_boundary_is_the_discriminator`
     (`test/plan-marshall/build-pyproject/test_gate_coverage.py`) must still pass.
   - **(G10) An empty boundary must not render COMPLETE.** `CoverageBoundary.complete` is
     `not self.degraded`, so a boundary that recorded nothing is `complete=True` and
     `render_coverage_summary` emits `COMPLETE … checked over full scope: (nothing)` — a fail-open in
     the module whose docstring claims it fails closed on empty state. Make `complete` require an
     affirmative signal (`bool(self.checked) and not self.degraded`) and render the empty boundary as a
     distinct third verdict that certifies nothing.
   - **(G8) Make a skipped mypy scope visible.** `build.py`'s `cmd_compile` module arm and
     `cmd_test_compile` return 0 from `_skip_empty_mypy_scope` before reaching `_run_mypy`, so the
     dimension is recorded neither as checked nor as degraded and vanishes from the verdict. In both
     branches, when a `boundary` is supplied, record the dimension with its empty scope stated.
   - **(G6) Fix the false not-run clause.** `_render_structural_limits` derives its `not_run` line from
     the whole limits registry as though it were a statement about the command, so a module-scoped
     `quality-gate` prints that the gate "never performs" `plugin-doctor` and `mypy(production)` —
     both false for that invocation. Have the caller pass the dimensions the invocation *could* have
     run at its scope, and render three distinct clauses: **not performed at this scope**, **not
     performed by this gate at all**, and — using G8's records — **attempted, nothing in scope**.
   - **(G5) Record the dimensions no gate covers on either side.** `ruff` runs over
     `[marketplace/bundles, test, .claude]` and mypy over `[marketplace/bundles]` (plus `.claude` when
     collectable); neither list contains `build.py` or `marketplace/targets`, which reach only the SPDX
     check. Add two rows to `parity_population()` with a note stating the coverage is equal **and
     zero**, and record a follow-up item — in the run report, not as a code change — for widening the
     ruff/mypy path lists, naming why the widening is out of this plan's scope (see Out of scope).
   - **(G3) Reconcile the cache guidance.**
     `marketplace/bundles/plan-marshall/skills/build-pyproject/standards/pyproject-impl.md`, in
     § "Verification-Target Trust", still tells the reader to delete `.mypy_cache` before trusting a
     local pass, describing the hazard as an unmitigated manual practice. `build.py`'s `_run_mypy`
     passes `--no-incremental` unconditionally, so the project's own gates are cold by construction.
     Rewrite the bullet to state that, and scope the remaining advice to mypy invocations made
     **outside** `build.py`. Cross-reference
     `phase-6-finalize/standards/pre-push-quality-gate.md` § "Coverage parity with CI, freshness, and
     honest coverage" rather than restating it.
   *Done when:* `classify_check_duration(660, 3.0).plausible` is `False` with a unit test asserting it;
   the `MAX_ANALYSIS_THROUGHPUT` comment names a cold-throughput figure measured during this run;
   `render_coverage_summary(CoverageBoundary())` contains neither `COMPLETE` nor `(nothing)`, pinned by
   a test; a module-scoped `quality-gate` over a bundle whose mypy scope is empty prints a verdict
   naming that dimension with its zero scope and prints **no** line asserting the gate never performs
   `plugin-doctor` or `mypy(production)`, pinned by a test over that invocation's output; the two
   shared-blind cells are present in `parity_population()`; and `pyproject-impl.md` no longer implies
   the project's own mypy gates run warm and names `--no-incremental` as the mechanism. G1 and G10 are
   `vacuous-test` closures: **each new test is seen RED against the pre-change constant / pre-change
   `complete` property**, and the red output is quoted in the run report.

6. **D5 — The workflow-lint guard covers the shapes its docstring claims**
   *(closes 390/G2, 390/G4, 390/G5, 390/G1)*
   All in `test/default/test_workflow_lint.py` unless stated. This module is the **only** automated
   control over this repository's template-injection surface.
   - **(G2) Wide step dashes.** `_RUN_LINE`'s `(?P<dash>- )?` matches only the exact two-character
     `- `, so `-   run: …` matches no branch and its body is never scanned. Broaden the pattern to
     accept any dash-plus-whitespace run and compute `key_col` from the **matched dash width**, not the
     hard-coded `2`.
   - **(G4) Multi-line plain scalars.** The non-block branch inspects only the text after `run:` and
     advances one line, so a YAML plain scalar continued on the following indented line escapes
     entirely — regardless of dash width, so G2's regex fix alone does not close it. Give that branch
     the same body walk the block branch performs (collect following lines that are blank or indented
     deeper than `key_col`, stopping at the first dedent to or past `key_col`), and report a violation
     when `${{` appears in the `after` text **or** anywhere in that body. Advance `i` past the walked
     body only for the block-scalar case, so a sibling `run:` is not skipped.
   - **(G5) Read-only permissions, not merely present.** `_has_top_level_permissions` is a
     `startswith` presence check: it returns `True` for `permissions: write-all`. Parse each workflow's
     top-level `permissions:` block and assert every scope is `read` or `none`, with an explicit
     allowlist keyed by workflow filename for deliberate exceptions — derived from D0(d), and carrying
     the justification for each allowlisted scope **in the allowlist entry's comment**, so widening a
     scope requires editing the allowlist rather than only the workflow.
   - **(G1) Guard the concurrency key.** `.github/workflows/python-verify.yml`'s `concurrency.group`
     includes `github.event_name` at HEAD, but nothing asserts it; the earlier key without it put the
     push run and the `pull_request` run for one branch in the same cancelling group, which cancelled a
     `gate` job mid-decision and planted a red **required** `verify / conclusion` check that returned
     `405 Repository rule violations found` on merge. Add a test asserting the group value contains
     `github.event_name` — and, positively, that the resolved group differs between a `push` and a
     `pull_request` event for the same branch — plus an assertion that `cancel-in-progress` stays
     scoped to `pull_request`. **Put the reason in the assertion message**, naming the cancelled-gate
     failure mode, so the next editor reads *why* before deleting the "redundant" key component.
   *Done when:* `_run_block_context_violations` returns a non-empty list for the wide-dash inline
   shape, the wide-dash block-scalar shape and the plain-scalar continuation shape; returns `[]` for
   the negative control where a sibling `env:`/`with:` mapping at the **same** indent as `run:` carries
   `${{ … }}`; every pre-existing test in the module still passes; and
   `test_workflows_have_no_context_expression_in_run_blocks` still passes over the unmodified
   `.github/workflows/` (count re-derived per D0(d), not assumed). For G5 and G1, the closure is
   red-first by mutation, each reverted after and each red output quoted in the run report: changing
   `.github/workflows/opencode-generate-check.yml`'s top-level block to `contents: write` makes the
   permissions test **fail**, `pr-agent.yml`'s declared write scopes pass **via the allowlist** rather
   than by the check being skipped, and deleting `-${{ github.event_name }}` from the concurrency group
   makes the named concurrency test **fail with the explanatory message**.

7. **D6 — Multi-target generator: both emitters, both corrupt-input classes, both prune directions**
   *(closes 370/G6, 370/G7, 370/G1, 370/G2, 370/G3, 370/G5)*
   - **(G6) The valid-JSON-but-not-an-object case.** `claude/equality_check.py`'s
     `_read_emitted_plugin_json` catches only `json.JSONDecodeError`, so an emitted `plugin.json`
     holding `[]`, `"x"`, `null` or `3` parses and then crashes in `check_bundle` on `.get`. Its
     sibling `_check_marketplace_json` guards **both** halves — decode error *and*
     `isinstance(..., dict)`. Add the `isinstance` half, widening
     `CorruptEmittedPluginJsonError.__init__` to accept a reason string so the non-object case can
     raise it. Add a parametrised test over `'[]'`, `'"x"'`, `'null'`, `'3'`.
   - **(G7) The Claude emitter never prunes a removed bundle.** `claude/target.py`'s `generate` (emit
     mode) iterates **source** bundles, so an output bundle directory with no surviving source is never
     visited and never removed — and `generate.py`'s version stamp walks the *output* tree, so it
     reports a bundle count above the source count. After the per-bundle loop and before the equality
     check, remove every immediate child directory of `output_dir` that is neither `.claude-plugin` nor
     the name of a source bundle, going through `fs_safety.safe_rmtree(child, output_dir)` so D1's
     containment invariant is not bypassed. Gate it on the unscoped case exactly as the OpenCode
     emitter does, since a scoped `--bundles` emit legitimately leaves other bundles in place.
   - **(G3) The OpenCode emitter lacks the Claude emitter's source-tree refusal.**
     `opencode/emitter.py`'s `emit_bundles` has no equivalent of `emit_bundle_verbatim`'s refusal when
     the destination resolves inside the source tree, and `_prune_stale_outputs` gives it a destructive
     path. Refuse before any write when `output_dir` resolves inside `marketplace_dir`, reusing
     `fs_safety.is_within` and raising the same shape of error.
   - **(G1) Name the corrupt outcome honestly.** `run_equality_check`'s docstring enumerates only
     "missing or drifts" and omits the corrupt case D4 added, and corrupt bundles are returned inside
     `missing_target_bundles` — a field whose name asserts absence for a file that is present. Extend
     the docstring to name the corrupt case, **rename the field to `unusable_target_bundles`** (the
     choice is made here, not by the run) at its declaration and both construction sites and in its
     test assertions, and sort the combined list once rather than concatenating two sorted halves.
   - **(G2) Anchor the third frontmatter reader.** `body_transform_engine._frontmatter_field` opens on
     `content.startswith('---')` and closes on `content.find('\n---', 3)`, so it closes on any line
     *beginning* with `---`. Bring it to the sibling readers' newline-delimited anchor (`'---\n'` open,
     `content.find('\n---\n', 4)` close) with the same end-of-file tolerance, and add a test asserting a
     field following a `---`-leading value line is still read.
   - **(G5) Complete the architecture tree.** `marketplace/targets/README.md`'s "## Architecture" tree
     omits `fs_safety.py` — the module that exists specifically to be found and reused instead of
     re-implemented — and seven others. Make the tree exhaustive against D0(e)'s derived module set.
   *Done when:* `run_equality_check` returns the documented re-run-emit diagnostic — not an exception —
   for an emitted `plugin.json` of `[]`, `"x"`, `null` or `3`; a full unscoped Claude emit over an
   unchanged source tree removes an injected `<output>/zz-removed/` directory and the post-emit stamp
   line reports the **source** bundle count, while a scoped emit leaves a second bundle's directory
   untouched; `emit_bundles(marketplace_dir, marketplace_dir, config_dir)` raises before writing or
   unlinking anything and a legitimate output directory still emits and prunes; the equality result's
   field name matches what it contains and a test asserts the corrupt bundle is reported under it; all
   three frontmatter readers under `marketplace/targets/` use the `\n---\n` anchor with a test pinning
   `_frontmatter_field`; and every module in D0(e)'s derived set appears in the README tree.

8. **D7 — Pollution-guard scope, sandbox ownership, and the zero-skip gate proposal**
   *(closes 380/G2, 380/G3, 380/G4, 380/G6, 380/G8)*
   - **(G2) Broaden the `touches_real_state` predicate.** `test/conftest.py`'s
     `pytest_collection_modifyitems` marks a test only when it requests the `plan_context` fixture,
     while the docstring beside it states that a state-driving test without that fixture "opts in by
     carrying the marker explicitly" — a half with **zero** users tree-wide. Broaden the predicate so a
     test is marked when it requests `plan_context` **or** its module references
     `PlanContext` / `BuildContext` / `EmptyPlanContext` or assigns `PLAN_BASE_DIR`; or mark those
     modules explicitly. Either way, delete or honour the "opts in explicitly" sentence so the
     docstring names only mechanisms that have users. Add a collection-time test asserting the named
     files yield marked items.
   - **(G3) Finish retiring the manual `PLAN_BASE_DIR` save/restore.** Replace each manual
     `os.environ['PLAN_BASE_DIR'] = …` / `del os.environ[…]` pair and each raw
     `_config_core.PLAN_BASE_DIR = …` / `_config_core.MARSHAL_PATH = …` assignment under `test/` with
     `monkeypatch` (already requested by the affected tests), so one mechanism owns those globals.
     Re-derive the site list rather than trusting one: the files at authoring time were
     `test/plan-marshall/manage-logging/test_logging.py`,
     `test/plan-marshall/manage-providers/test_list_providers.py`,
     `test/plan-marshall/build-maven/test_maven_run.py`,
     `test/plan-marshall/build-npm/test_npm_run.py` and
     `test/plan-marshall/script-shared/test_build_parse.py` — confirm by grep before editing. **This
     is an ownership defect, not a leak:** the autouse sandbox already repairs these at teardown, so
     do not report it as a leak in the run report.
   - **(G4) Delete the two stale stub comments.** `test/conftest.py` carries two comments describing
     `sys.modules.setdefault(…, MagicMock(…))` as a pattern test modules currently use; those stubs
     were deleted and the two comments are now the only occurrences of the phrase under `test/`.
     Rewrite the pre-import comment to state the ordering guarantee without asserting current stub
     usage, and rewrite the namespace-helper comment to justify its `isinstance` check on its own terms
     (it filters non-dict namespaces).
   - **(G6) Refresh or drop the stale suite count.** `pyproject.toml`'s `filterwarnings` rationale
     claims a whole-tree run "of all 14794 tests" emits zero warnings; the collected count is now far
     larger (lead only — re-derive with `pytest --collect-only -q -o addopts=""`). Either re-run the
     suite under those flags, confirm zero warnings and write the freshly derived number, or state the
     zero-warnings property **without** a population figure. Do not copy the lead.
   - **(G8) The zero-skip gate — record a proposal, do not make the call.** `_STRICT_NO_SKIP_ENV`
     (`PLAN_MARSHALL_STRICT_NO_SKIP`) occurs on three lines, all inside `test/conftest.py`; no
     workflow, no `pyproject.toml` entry and no build target sets it, so `pytest_sessionfinish` returns
     at its first line on every run this project performs — while the comment above the flag asserts
     "CI on the reference platform sets it to `1`". **Arming it would change CI behaviour and require
     reconciling the skips the suite currently reports; deleting it would remove a gate. Both are
     operator decisions and this run makes neither.** What this run does: replace the false sentence
     with a statement of the observed fact — that the gate is armed by no producer in this repository,
     re-derived by the sweep at the moment of the edit — and record both options, with their costs, in
     the run report's findings as a proposal for the operator.
   *Done when:* `pytest --collect-only -m touches_real_state` over the modules that enter
   `PlanContext`/`BuildContext` or assign `PLAN_BASE_DIR` returns their full collected count and the
   conftest docstring names only mechanisms that have users; a tree-wide grep for
   `os.environ['PLAN_BASE_DIR'] =`, `del os.environ['PLAN_BASE_DIR']`, `_config_core.PLAN_BASE_DIR =`
   and `_config_core.MARSHAL_PATH =` under `test/` returns zero and the suite is still green;
   `grep -rn "sys.modules.setdefault" test/` returns zero and no comment under `test/` asserts that
   test modules install `MagicMock` stand-ins; `pyproject.toml`'s comment either names a count matching
   a re-derivation made during this run or states the property without a count; and `test/conftest.py`
   no longer claims CI arms the zero-skip gate, with the arm-or-delete proposal recorded in the run
   report.

## Out of scope

Each exclusion carries its reason, because with no operator watching the written boundary is the only
thing standing between this run and mid-run drift.

- **Widening the `ruff` / `mypy` path lists to `build.py` and `marketplace/targets/**`.** D4(G5)
  *records* that both dimensions are uncovered on both sides; actually widening them changes what CI
  checks as well as what the local gate checks, which needs its own authorization and its own
  green-tree reconciliation. The follow-up item is the deliverable; the widening is not.
- **Arming or deleting the zero-skip gate (380/G8).** Arming it makes the whole-suite CI job fail on
  the skips the suite legitimately reports today; deleting it removes a control. Choosing between them
  is a policy call, and this run has no operator to make it. D7 records a proposal and removes the
  false "CI arms it" claim — nothing more.
- **Adding a fifth *wire* status to the daemon protocol (430/G2 option (a)).** A new wire status must
  be recognised by the daemon's terminalization, its supervisor's terminal-payload arms and the
  client's wait loop — an amendment to a contract that spans three components. D2 takes the bounded
  option instead and records the widening as the alternative not taken.
- **Relabelling `parity_population()` as derived rather than recorded (160/G2).** That gap is not in
  this plan's set; D4(G5) only adds two rows to the artifact as it stands and does not touch its
  "derived" framing either way.
- **A `plugin-doctor` `test-conventions` rule rejecting raw `PLAN_BASE_DIR` mutation (the second half
  of 380/G3's Fix).** A new doctor rule changes plugin-doctor's whole-tree scope and gate behaviour for
  every bundle; the migration alone meets G3's stated done-when, and a new gate rule deserves its own
  review.
- **Retro-editing any `report-NN.md` under `doc/plans/`.** A run report is a dated record of one
  execution, not documentation of current state. Where a report holds a wrong figure, the correction of
  record is the gap entry, not an edit to the report.
- **Refreshing the plugin cache or the generated executor.** Both are machine-local build steps over
  git-ignored trees that a cloud clone does not have. Merged bundle source is authoritative; this run
  neither performs a sync nor records one as owed.

## Expected surface

Production sources:

- `marketplace/bundles/plan-marshall/skills/script-shared/scripts/_plan_state_exemption.py` — D1
  trackedness oracle
- `marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/_git_helpers.py` — D1 porcelain
  encoding
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/post_run_source_guard.py` — D1,
  only if the shared `parse_porcelain_z` is extracted to `script-shared`
- `marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/_invariants.py` — D1 layer-D capture,
  if the encoding change surfaces there
- `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_shared.py`,
  `_build_parse.py`, `_build_format.py` — D2 executed-test count
- `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_server_protocol.py`,
  `_build_result.py` — D2 wire vocabulary
- `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_gate_coverage.py` — D4
  freshness, verdict, parity rows
- `build.py` — D4 skipped-scope recording and the not-run clause's scope argument
- `marketplace/targets/claude/equality_check.py`, `claude/target.py`, `opencode/emitter.py`,
  `body_transform_engine.py`, `README.md` — D6
- `pyproject.toml` — D7 filterwarnings comment

Standards and documentation:

- `marketplace/bundles/plan-marshall/skills/extension-api/standards/build-api-reference.md` — D2
- `marketplace/bundles/plan-marshall/skills/build-pyproject/standards/pyproject-impl.md` — D4(G3)

Tests:

- `test/plan-marshall/script-shared/test_plan_state_exemption.py`, and the layer-D capture test — D1
- `test/plan-marshall/build-pyproject/test_build_findings_store.py`,
  `test/plan-marshall/script-shared/test_non_finish_discrimination.py`, plus the two suites that drive
  `cmd_parse_common` (`test/plan-marshall/build-maven/test_maven_cmd_parse.py`,
  `test/plan-marshall/build-operations/test_truthful_status_guard.py`) — D2
- `test/plan-marshall/tools-script-executor/test_marker_free_resolution.py`,
  `test_executor_version_split_regression.py` — D3
- `test/plan-marshall/build-pyproject/test_gate_coverage.py`, `test/default/test_build_verify.py` — D4
- `test/default/test_workflow_lint.py` — D5
- `test/marketplace/targets/claude/test_equality_check.py`, `test/marketplace/targets/claude/`
  emitter/target tests, `test/marketplace/targets/opencode/test_emitter.py`, and a new
  `body_transform_engine` test — D6
- `test/conftest.py`, `test/plan-marshall/manage-logging/test_logging.py`,
  `test/plan-marshall/manage-providers/test_list_providers.py`,
  `test/plan-marshall/build-maven/test_maven_run.py`,
  `test/plan-marshall/build-npm/test_npm_run.py`,
  `test/plan-marshall/script-shared/test_build_parse.py` — D7

Not expected: `.github/workflows/**` is **read** by D5's new assertions and must not be **edited** by
this plan except as a reverted mutation probe; any workflow edit surviving into the diff is collateral
change and is reported.

## Claim labels

Every count in this table is a lead. Re-derive it at the moment you use it.

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| 330/G2 reproduces: `git_dirty_files` runs `git status --porcelain` without `-z` and strips quotes without unescaping | OBSERVED (read at HEAD) | `marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/_git_helpers.py` — `git_dirty_files`, the `subprocess.run(['git','status','--porcelain'])` call and the `rest.startswith('"')` strip |
| 330/G5 reproduces: `tracked_plan_paths` asks only the index | OBSERVED (read at HEAD) | `marketplace/bundles/plan-marshall/skills/script-shared/scripts/_plan_state_exemption.py` — `tracked_plan_paths`, its single `git ls-files -z -- .plan/` observation |
| 380/G1 reproduces: `tests_run` is `test_summary.total` | OBSERVED (read at HEAD) | `.../script-shared/scripts/build/_build_shared.py` — `cmd_run_common` (`tests_run = test_summary.total …`) and `_reconcile_pending_build_findings`'s "executed-test count" docstring |
| 360/G1 reproduces: `_writes_marker` recognises only the inline attribute-call shape | OBSERVED (read at HEAD) | `test/plan-marshall/tools-script-executor/test_marker_free_resolution.py` — `_writes_marker`, whose only hit condition is an `ast.Call` on `write_text`/`write_bytes` whose `func.value` mentions the literal |
| 160/G1 reproduces: `MAX_ANALYSIS_THROUGHPUT` is 2000.0 files/s, above the recorded incident band | OBSERVED (read at HEAD) | `.../script-shared/scripts/build/_gate_coverage.py` — `MAX_ANALYSIS_THROUGHPUT` and `classify_check_duration` |
| Each remaining gap in D2–D7 reproduces at HEAD | OBSERVED (read at HEAD) | The file and symbol each gap entry names, under `doc/plans/truthful-signals/{160,330,360,370,380,390,430}-*/gaps.md` — all git-tracked and readable from the clone |
| No gap in this plan's set was already closed by a later commit | OBSERVED | Every one of the 31 was opened at the file and symbol it names and the defect was present; nothing is carried as already-closed |
| The five populations in D0 are derivable from the tree by the commands D0 names | HYPOTHESIS | D0 itself settles it: each command is run and its result recorded, and the plan HALTS on any that cannot be derived |
| The four D0 counts stated as leads (412 / 386 recursive-vs-narrow scripts, 5 result statuses, 7 workflows) match the clone | HYPOTHESIS | Re-derivation in D0; a mismatch is recorded and the derived value used |
| The expected surface above is the set this plan touches | HYPOTHESIS | The PR diff at verification time — any file outside it is collateral change and is reported |
| `.plan/` holds nothing this plan needs | OBSERVED | `.plan/` is git-ignored and **absent from the clone**. Do not go looking for it, do not invoke `.plan/execute-script.py`, and do not treat its absence as a blocker. Every path this plan names is git-tracked |

An asserted **absence** is verified exactly as an asserted presence. Three absences this plan relies
on, each of which the run must re-check rather than trust: no test anywhere under `test/` asserts
anything about `python-verify.yml`'s `concurrency:` block (D5/G1); `PLAN_MARSHALL_STRICT_NO_SKIP` has
no producer outside `test/conftest.py` (D7/G8); and `_retention_pinned_versions` appears nowhere under
`marketplace/` or `test/` (D3/G2).

## Verification

Beyond each deliverable's *Done when*:

1. **Red-first evidence for every vacuous-guard closure.** Four gaps are `vacuous-test` kind — 160/G1,
   160/G10, 360/G6, 430/G3 — and two more (390/G1, 390/G5) have mutation-shaped done-whens. For each,
   the run **sees the new test RED against the defect it names before the fix lands**, quotes the red
   output in the run report, reverts the mutation where one was used, and confirms the file is
   byte-clean afterwards (`git diff --quiet`). A green-only demonstration does not close any of these
   six; a deliverable whose red-first check was not performed is reported as **partial**, not done.
2. **Cold reads of the text whose value is what a later reader does with it.** Dispatch the pre-PR
   verification sub-agent to read each of the following **cold** — without this plan, without the gap
   documents — and report *which reading it took*. A wrong reading means the wording failed, however
   complete the change looks:
   - the three rendered clauses from D4's `_render_structural_limits`: does the reader distinguish
     "not performed at this scope" from "not performed by this gate at all" from "attempted, nothing
     in scope", and can they say which remedy each implies?
   - D4's rewritten `pyproject-impl.md` bullet: does the reader conclude that this project's own mypy
     gates are cold by construction, and that the manual cache advice applies only to invocations made
     outside `build.py`?
   - D5's concurrency-test assertion message: does the reader understand *why* removing
     `github.event_name` is unsafe, without opening the git history?
   - D5's permissions allowlist comments: does the reader conclude that widening a scope requires
     editing the allowlist?
   - D7's rewritten conftest text for the zero-skip gate: does the reader conclude the gate is
     **unarmed in this repository** — and not that it was deleted, and not that CI arms it?
3. **Whole-suite green.** The Python change footprint is large and crosses `build.py`, so run the full
   build gate, not a scoped one. Read the result's `status` / `errors[]` — the wrapper exits 0 even on
   failure.
4. **Collateral-change check.** Diff the PR's touched-file set against § Expected surface and report
   every file outside it, with why it was touched. `.github/workflows/**` appearing in the final diff
   is a defect: D5 reads those files and mutates them only as reverted probes.
5. **Coverage check against the gap set.** The run report states, per gap id, whether it was closed,
   partially closed, or not reached — all 31 ids, none omitted. A gap that turned out not to
   reproduce is recorded as such with the evidence, not silently dropped.

## Notes

- **Where the gaps come from.** Every gap id in this plan is an entry in a git-tracked document you can
  open from the clone: `doc/plans/truthful-signals/{source-plan}/gaps.md`, where `{source-plan}` is one
  of `160-build-gate-coverage-parity`, `330-post-run-guard-exempts-every-tracked-plan-file`,
  `360-collapse-the-version-selection-machinery`, `370-multi-target-generator-edge-paths`,
  `380-test-suite-false-confidence`, `390-ci-and-supply-chain-hardening`, and
  `430-a-timeout-is-not-a-red-test-and-a-kill-is-not-a-timeout`. Each entry carries Kind, Severity,
  Where, What is wrong, Why it matters, Fix and Done when, and the sibling `verification.md` carries an
  `## Adversarial review` section recording what was upheld, refuted or re-severitied. **Where a gap
  body and that section disagree, the adversarial-review section wins.** Read the full entry before
  implementing its deliverable — this plan states the mechanism and the boundary, not every file:line
  the entries carry.
- **Refutations already folded in.** Three narrower claims were refuted during adversarial review and
  must not be re-implemented: 330/G2's original claim that the encoding mismatch also affects
  non-`.plan/` source paths (it does not — both sides of that comparison carry the same spelling);
  360/G5's instruction to correct `manage-config/standards/data-model.md` (already post-fix correct);
  and 380/G3's claim that the raw `PLAN_BASE_DIR` assignments leak across tests (the autouse sandbox
  repairs them at teardown — the defect is ownership, not restoration).
- **`.plan/` is invisible here.** This plan executes in the standalone lane: there is no
  `.plan/execute-script.py`, no orchestrator ledger, no plan state. Use `./pw verify` directly for the
  build gate as `cloud-plan-lane` specifies, and `$TMPDIR` for every temporary file and throwaway git
  repository — never the repository, never `.plan/`.
- **Sequencing.** D0 gates D1, D2, D3, D5 and D6 and runs first. D1–D4 carry the five `high` gaps and
  are ordered ahead of everything else; within D4, the freshness recalibration (160/G1) is done first.
  D5, D6 and D7 touch disjoint surfaces from each other and from D1–D4, so a run that reaches them can
  take them in any order.
- **Do not self-approve a contract change.** D2's wire-vocabulary row and D7's conftest correction both
  sit next to contracts this run does not own. Where a change would amend a governing contract rather
  than fix a defect against it, record the proposal — the lane forbids self-approval, and this plan has
  already taken the bounded option in both places so the run does not have to choose.
