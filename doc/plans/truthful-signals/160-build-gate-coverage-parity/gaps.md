# Gaps — 160-build-gate-coverage-parity

**Source:** verification.md (same directory)   **Open items:** 8

## G1 — Recalibrate the freshness duration backstop so it can fire on the incident it was built for

- **Kind:** vacuous-test
- **Severity:** high
- **Where:** `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_gate_coverage.py:86` — `MAX_ANALYSIS_THROUGHPUT`; `:108` — `classify_check_duration`; test at `test/plan-marshall/build-pyproject/test_gate_coverage.py:42` — `test_large_scope_reported_in_near_zero_time_is_flagged`
- **What is wrong:** The ceiling is 2000 files/s. The plan's own problem statement records the stale-cache incident as "the local test-compile gate **passed in 2–5 seconds**" while CI "checked 660 files" — 132–330 files/s. Executed against the real module: `classify_check_duration(660, 2.0)` and `classify_check_duration(660, 5.0)` both return `plausible=True`, and `(660, 0.33)` is still `True`. The guard fires only below ~0.33 s for that scope. The one test asserting the positive direction uses 660 files / 0.05 s = 13 200 files/s, i.e. 40× beyond the observed case, so the test passes against a calibration that cannot detect the defect it names.
- **Why it matters:** D4's done-when is "a stale cache can no longer produce a clean verdict, **and** an implausible duration is surfaced". The first half is closed deterministically by `--no-incremental`, but the backstop that is supposed to survive its removal — or catch any other cached/short-circuited checker wired in later — is inert for the entire throughput band where real cache-answered runs live. `build-pyproject/standards/pyproject-impl.md:118` states the human version of the same heuristic ("a local run that finishes in a couple of seconds over hundreds of files is a red flag"), which the code contradicts.
- **Fix:** Lower `MAX_ANALYSIS_THROUGHPUT` to a value that separates warm-cache throughput from cold-analysis throughput — measure a cold `./pw compile` and a warm one on this tree and set the ceiling between them (a cold whole-tree mypy over ~414 files takes tens of seconds, i.e. well under 100 files/s, so a ceiling in the low hundreds is defensible). Add a test that pins the plan's recorded incident: `classify_check_duration(660, 3.0).plausible is False`. Keep `test_large_scope_with_real_elapsed_is_not_flagged` and add a negative case at realistic cold throughput so the both-directions requirement stays honest.
- **Done when:** `classify_check_duration(660, 3.0).plausible` is `False`, a test asserts exactly that, and a test asserts a cold-run throughput measured on this tree is still `plausible=True`.
- **Module/topic:** `plan-marshall/script-shared/build/_gate_coverage.py` (build gate freshness)

## G2 — Stop calling the parity population "derived" while it is a hand-written literal

- **Kind:** stale-statement
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_gate_coverage.py:434-457` — `parity_population`; `:55` (module docstring); `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/pre-push-quality-gate.md:71`
- **What is wrong:** The doc says the population is "**derived, not hand-listed** (`_gate_coverage.parity_population`)" and the module docstring calls it "the derived set of dimensions". The function returns a literal 9-tuple of `ParityCell`s with hand-written notes; nothing reads `pyproject.toml`, `build.py` or the workflow at run time. Grepping `parity_population` across the tree finds only the module, that one doc sentence, and three tests — there is no production consumer. `test_parity_population_is_non_empty` asserts `len(...) > 0` over that literal, and `test_parity_cells_carry_a_verdict_and_evidence` checks only that each cell has a non-empty string.
- **Why it matters:** The cells assert facts about live configuration (`'ruff-rules', 'equal', 'single [tool.ruff.lint] select shared by both'`, `'spdx-paths', 'equal', 'SPDX over [bundles, test, .claude, targets, build.py] on both'`). If someone adds a CI-only lint step, changes the SPDX path list, or splits the ruff config, every cell keeps claiming `equal` and no test notices. A frozen snapshot labelled "derived" is precisely the confident-but-unsubstantiated signal this epic is about.
- **Fix:** Either (a) make it genuinely derived — have `parity_population()` read the ruff/mypy path lists from `build.py`'s constants and the rule set from `pyproject.toml`, and compute the `equal` verdicts — or (b) relabel it honestly in both places as a *recorded* derivation (naming the commit it was derived at) and add at least one test that re-checks a cell against its substrate, e.g. asserting the `spdx-paths` note matches the actual `spdx_paths` list `cmd_quality_gate` builds for `module=None`.
- **Done when:** no document or docstring calls the population "derived" unless a test fails when the underlying configuration changes and the cell does not.
- **Module/topic:** `plan-marshall/script-shared/build/_gate_coverage.py` + `phase-6-finalize/standards/pre-push-quality-gate.md`

## G3 — Reconcile the pyproject-impl cache guidance with the now-unconditional `--no-incremental`

- **Kind:** doc-drift
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/build-pyproject/standards/pyproject-impl.md:118` — § "Verification-Target Trust", bullet "Validate against a CLEAN mypy cache…"
- **What is wrong:** The bullet still tells the reader to "Delete/ignore `.mypy_cache` (or run in a clean checkout) so the local run re-checks the same file set CI will", describing the cache hazard as an unmitigated manual practice. `build.py:306` now passes `--no-incremental` on the tree's only mypy invocation, so `./pw compile`, `test-compile`, `quality-gate` and `verify` are already cold. It is the one remaining doc in the tree that states the hazard (verified by grepping `incremental` across `*.md`/`*.py`/`*.toml`), and it is in the `build-pyproject` skill — the standards doc a developer wiring a new build gate actually opens.
- **Why it matters:** A reader follows advice the tooling has already implemented, and — worse — will read the surviving "a couple of seconds over hundreds of files is a red flag" sentence as describing what the gate detects, which it does not (see G1).
- **Fix:** Rewrite the bullet to state that `build.py` runs every mypy invocation with `--no-incremental` so the project's own gates are cold by construction, and scope the remaining advice to mypy invocations made *outside* `build.py`. Cross-reference `phase-6-finalize/standards/pre-push-quality-gate.md` § "Coverage parity with CI, freshness, and honest coverage" rather than restating it.
- **Done when:** `pyproject-impl.md` no longer implies the project's own mypy gates run warm, and names `--no-incremental` as the mechanism.
- **Module/topic:** `plan-marshall/build-pyproject` standards

## G4 — Give the module-tests honest-degradation branch its own `--display-detail` variant

- **Kind:** incomplete-sweep
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/pre-push-quality-gate.md:275` (module-tests branch 3, `whole_tree_available == false`) and `:343-347` (Branch A default detail)
- **What is wrong:** This plan added a DEGRADED detail variant for the whole-tree `quality-gate` honest-degradation path (`:355-370`), because the default Branch A string "…would affirmatively misreport an un-run arm as green". The module-tests gate has a structurally identical branch — branch 3 emits a WARNING that the divergence class is "UN-GATED at finalize for this push" and then routes to **Mark Step Complete (Success)** — and no variant was added for it, so the step record still reads `"{N} bundles + whole-tree quality-gate green, test-compile + module-tests green"` for a run where module-tests never executed. Branch 5 (zero scoped modules) did get a variant at `:288`, which shows the pattern was known.
- **Why it matters:** The same defect the plan fixed on one arm remains on the neighbouring arm, and the step record is what a later reader (and the finalize renderer) treats as the coverage claim.
- **Fix:** Add a third detail variant next to the existing two, e.g. `--display-detail "{N} bundles + whole-tree gates green, module-tests UNAVAILABLE (degraded)"`, size it against its worst-case `{N}` expansion against the ≤80-character ceiling in `phase-6-finalize/standards/external-step-contract.md:52`, and reference it from branch 3.
- **Done when:** branch 3 names a detail variant that does not contain the word "green" for the module-tests dimension, and Branch A's default string is documented as inapplicable on that path.
- **Module/topic:** `plan-marshall/phase-6-finalize` — pre-push-quality-gate standard

## G5 — Record the dimensions no gate covers on either side: `build.py` and `marketplace/targets/**`

- **Kind:** omission
- **Severity:** medium
- **Where:** `build.py:463` (ruff path list), `build.py:339-357` (`cmd_compile` mypy path list), `build.py:475` (SPDX-only extension); recorded nowhere in `report-01.md` § D1 or § Residue
- **What is wrong:** `ruff check` runs over `[marketplace/bundles, test, .claude]` and mypy over `[marketplace/bundles]` (plus `.claude` when collectable). Neither list contains `build.py` or `marketplace/targets`; both reach only `check_spdx_headers`. So the file implementing the gate, and the multi-target generator, are lint- and type-check-invisible to the local gate **and** to CI. The report discloses the `marketplace/targets` half in a parenthetical under sampled hole 4 but carries it into neither the D1 table nor § Residue, and never mentions `build.py` at all.
- **Why it matters:** D1's stated purpose was to derive the population rather than adjudicate the sample, and a cell where both sides check nothing is exactly the kind a sample-driven read misses. A reader of the D1 table concludes `marketplace/targets` is "CLOSED" and that `build.py` was never at issue; in fact a type error introduced into `build.py` by this very plan would have been caught by no static gate.
- **Fix:** Add two rows to the parity table (in `report-01.md` if it is amended, and in `_gate_coverage.parity_population()` if G2 keeps that artifact) with verdict `equal` and a note stating the coverage is equal *and zero*, and open a follow-up item for widening the ruff/mypy path lists to `marketplace/targets` and `build.py`. Note in that item that the widening changes both sides, so it is deliberately outside this plan's "changing what CI checks" boundary and needs its own authorization.
- **Done when:** the shared-blind cells are named in the parity artifact, and a follow-up item exists for widening the path lists.
- **Module/topic:** `plan-marshall/script-shared/build/_gate_coverage.py` + root `build.py` gate scope

## G6 — Fix the "this gate never performs them" claim for a module-scoped run

- **Kind:** stale-statement
- **Severity:** low
- **Where:** `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_gate_coverage.py:355` — `_render_structural_limits`
- **What is wrong:** The derived not-run line reads "`not run in this gate at all: … — absent from the list above because this gate never performs them, NOT because they passed`". Rendering it for a module-scoped `quality-gate` boundary (verified by executing `render_coverage_summary` on a boundary carrying only `mypy(production)`, `ruff`, `SPDX headers`) lists `plugin-doctor` among them — but `cmd_quality_gate` *does* perform plugin-doctor, just only when `module is None` (`build.py:485`). The same line mis-describes a `mypy(test)` dimension that `_skip_empty_mypy_scope` skipped rather than never attempted.
- **Why it matters:** It is a false statement inside the gate's own honesty output — the one place where a reader is entitled to take the wording literally. "Never performs them" and "did not perform them on this invocation" have different remedies.
- **Fix:** Reword to "not performed on this invocation" and, where the caller can distinguish them, split "this gate never runs X" from "X was skipped on this scope". (Introduced by PR #1239 in the file this plan created; grouped here because it is the same output surface.)
- **Done when:** the rendered line for a module-scoped boundary no longer asserts that the gate never performs plugin-doctor.
- **Module/topic:** `plan-marshall/script-shared/build/_gate_coverage.py`

## G7 — Remove the duplicate `_pending_` Cost section from report-01.md

- **Kind:** doc-drift
- **Severity:** low
- **Where:** `doc/plans/truthful-signals/160-build-gate-coverage-parity/report-01.md` — the second `## Cost` heading, immediately after the completed one
- **What is wrong:** The report carries two `## Cost` sections; the first is filled in (wall-clock, population caveat) and the second contains only `_pending_`.
- **Why it matters:** A reader scanning headings finds the empty one and reads the run's cost as unrecorded, contradicting the section three lines above it.
- **Fix:** Delete the second `## Cost` heading and its `_pending_` body.
- **Done when:** `report-01.md` contains exactly one `## Cost` section.
- **Module/topic:** `doc/plans/truthful-signals` run reports

## G8 — Make a skipped mypy scope visible in the coverage verdict

- **Kind:** omission
- **Severity:** low
- **Where:** `build.py:343-345` (`cmd_compile` module arm) and `build.py:363-365` (`cmd_test_compile`) — the `_skip_empty_mypy_scope` early `return 0`
- **What is wrong:** When no file under the scope survives the `[tool.mypy]` excludes, the command returns 0 before reaching `_run_mypy`, so the dimension is recorded neither as checked nor as degraded. `cmd_verify`/`cmd_quality_gate` then render `coverage: COMPLETE` over a dimension list that simply omits it. Grepping `record_degraded` confirms the freshness path at `build.py:317` is its only production caller, so no other partial-coverage condition can make a verdict PARTIAL.
- **Why it matters:** D5's done-when is that a partially-checked footprint produces a distinguishable verdict. A silently omitted dimension is the absence-read-as-coverage shape the deliverable targets; PR #1239's not-run line only partially covers it, and mis-describes it (G6).
- **Fix:** In both skip branches, when a `boundary` is supplied, call `boundary.record_checked(f'{dimension} [0 files, nothing collectable]')` (or a dedicated `record_skipped`) so the dimension appears in the verdict with its empty scope stated, rather than vanishing. Add a test driving `cmd_verify` with an empty test scope and asserting the printed summary names the skipped dimension.
- **Done when:** a `verify` run whose mypy scope was skipped prints a verdict that names that dimension and its zero scope.
- **Module/topic:** root `build.py` + `plan-marshall/script-shared/build/_gate_coverage.py`
