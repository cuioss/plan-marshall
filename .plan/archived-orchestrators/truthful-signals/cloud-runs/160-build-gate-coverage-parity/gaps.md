# Gaps — 160-build-gate-coverage-parity

**Source:** verification.md (same directory)   **Open items:** 10

## G1 — Recalibrate the freshness duration backstop so it can fire on the incident it was built for

- **Kind:** vacuous-test
- **Severity:** high
- **Where:** `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_gate_coverage.py:86` — `MAX_ANALYSIS_THROUGHPUT`; `:108` — `classify_check_duration`. Two guards ride the same constant and both clear it: `test/plan-marshall/build-pyproject/test_gate_coverage.py:42` — `test_large_scope_reported_in_near_zero_time_is_flagged` (660 files / 0.05 s), and `test/default/test_build_verify.py:470` — `test_quality_gate_fails_closed_when_whole_tree_mypy_reports_implausibly_fast`, which drives the *zero*-elapsed degenerate case (`_ticks(100.0, 100.0)`), not the recorded incident band
- **What is wrong:** The ceiling is 2000 files/s. The plan's own problem statement records the stale-cache incident as "the local test-compile gate **passed in 2–5 seconds**" while CI "checked 660 files" — 132–330 files/s. Executed against the real module: `classify_check_duration(660, 2.0)`, `(660, 3.0)` and `(660, 5.0)` all return `plausible=True`, and `(660, 0.33)` is still `True`; the first `False` appears at `(660, 0.32)` = 2062 files/s. The guard therefore fires only below ~0.33 s for that scope. Neither test reaches the incident band: the unit test uses 13 200 files/s (40× beyond it) and the integration test uses infinite throughput. Both pass against a calibration that cannot detect the defect they name.
- **Why it matters:** D4's done-when is "a stale cache can no longer produce a clean verdict, **and** an implausible duration is surfaced". The first half is closed deterministically by `--no-incremental` (re-confirmed by mutation: removing the flag from `build.py:306` turns 4 tests red). But the backstop that is supposed to survive its removal — or catch any other cached/short-circuited checker wired in later — is inert for the entire throughput band where real cache-answered runs live. `build-pyproject/standards/pyproject-impl.md:118` states the human version of the same heuristic ("a local run that finishes in a couple of seconds over hundreds of files is a red flag"), which the code contradicts.
- **Fix:** Lower `MAX_ANALYSIS_THROUGHPUT` to a value that separates cache-answered throughput from cold-analysis throughput. Cold throughput was measured on this tree during review: `uv run python build.py compile` reports `checked 414 source files` in **11.35 s** wall — ~37 files/s — so a ceiling in the low hundreds keeps roughly 5× headroom over a cold run while catching the recorded incident. Record that measurement in the constant's comment so the number has a stated substrate rather than being asserted. Add a unit test pinning the incident: `classify_check_duration(660, 3.0).plausible is False`. The existing negative guards survive a recalibration to that band unchanged — `test_large_scope_with_real_elapsed_is_not_flagged` uses 660 / 15.0 s = 44 files/s, and `test_throughput_boundary_is_the_discriminator` is expressed relative to the constant — so no false-alarm risk is introduced by the change itself. Re-key `test_quality_gate_fails_closed_when_whole_tree_mypy_reports_implausibly_fast` off zero-elapsed onto a non-degenerate elapsed inside the incident band, so the integration guard also bites.
- **Done when:** `classify_check_duration(660, 3.0).plausible` is `False`; a unit test asserts exactly that; `test_quality_gate_fails_closed_when_whole_tree_mypy_reports_implausibly_fast` drives a non-zero elapsed and still fails closed; `classify_check_duration(414, 11.35).plausible` is still `True`; and the `MAX_ANALYSIS_THROUGHPUT` comment names the measured cold throughput the ceiling was derived from.
- **Module/topic:** `plan-marshall/script-shared/build/_gate_coverage.py` (build gate freshness)

## G2 — Stop calling the parity population "derived" while it is a hand-written literal

- **Kind:** stale-statement
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_gate_coverage.py:434-457` — `parity_population`; `:55` (module docstring); `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/pre-push-quality-gate.md:71`
- **What is wrong:** The doc says the population is "**derived, not hand-listed** (`_gate_coverage.parity_population`)" and the module docstring calls it "the derived set of dimensions". The function returns a literal 9-tuple of `ParityCell`s with hand-written notes; nothing reads `pyproject.toml`, `build.py` or the workflow at run time. Grepping `parity_population`/`ParityCell` across the tree (re-run during adversarial review over `*.py`/`*.md`/`*.toml`/`*.yml`) finds the module, that one doc sentence, three tests, a passing mention in `doc/plans/multiplattform/reference/marketplace-audit.md:198`, and this plan directory — **no production consumer**. `test_parity_population_is_non_empty` asserts `len(...) > 0` over that literal, and `test_parity_cells_carry_a_verdict_and_evidence` checks only that each cell has a non-empty string.
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
- **Where:** `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/pre-push-quality-gate.md:275` (module-tests branch 3, `whole_tree_available == false`) and `:342-346` (Branch A default detail, `--display-detail` at `:344`)
- **What is wrong:** This plan added a DEGRADED detail variant for the whole-tree `quality-gate` honest-degradation path (`:356-369`), because the default Branch A string "…would affirmatively misreport an un-run arm as green". The module-tests gate has a structurally identical branch — branch 3 emits a WARNING that the divergence class is "UN-GATED at finalize for this push" and then routes to **Mark Step Complete (Success)** — and no variant was added for it, so the step record still reads `"{N} bundles + whole-tree quality-gate green, test-compile + module-tests green"` for a run where module-tests never executed. Branch 5 (zero scoped modules) did get a variant at `:348-352` (pre-existing, not added by this plan), which shows the pattern was known.
- **Why it matters:** The same defect the plan fixed on one arm remains on the neighbouring arm, and the step record is what a later reader (and the finalize renderer) treats as the coverage claim.
- **Fix:** Add a third detail variant next to the existing two, e.g. `--display-detail "{N} bundles + whole-tree gates green, module-tests UNAVAILABLE (degraded)"` — measured during review at 73 characters literal / 70 before `{N}` expands, inside the ≤80-character ceiling stated at `phase-6-finalize/standards/external-step-contract.md:52` (**not** at the location `:354` currently points to — see G9) — and reference it from branch 3.
- **Done when:** branch 3 names a detail variant that does not contain the word "green" for the module-tests dimension, and Branch A's default string is documented as inapplicable on that path.
- **Module/topic:** `plan-marshall/phase-6-finalize` — pre-push-quality-gate standard

## G5 — Record the dimensions no gate covers on either side: `build.py` and `marketplace/targets/**`

- **Kind:** omission
- **Severity:** medium
- **Where:** `build.py:463` (ruff path list), `build.py:339-357` (`cmd_compile` mypy path list), `build.py:475` (SPDX-only extension); recorded nowhere in `report-01.md` § D1 or § Residue
- **What is wrong:** `ruff check` runs over `[marketplace/bundles, test, .claude]` and mypy over `[marketplace/bundles]` (plus `.claude` when collectable). Neither list contains `build.py` or `marketplace/targets`; both reach only `check_spdx_headers`. So the file implementing the gate, and the multi-target generator, are lint- and type-check-invisible to the local gate **and** to CI. The report discloses the `marketplace/targets` half in a parenthetical under sampled hole 4 but carries it into neither the D1 table nor § Residue; `build.py` appears in the report only as an SPDX path and as a citation target, never as a lint-/type-check-blind dimension. Confirmed empirically during review: a real `build.py compile` reports `checked 414 source files`, exactly the `_mypy_collect_count(['marketplace/bundles', '.claude'])` figure, so nothing under `marketplace/targets` or `build.py` is reached transitively either.
- **Why it matters:** D1's stated purpose was to derive the population rather than adjudicate the sample, and a cell where both sides check nothing is exactly the kind a sample-driven read misses. A reader of the D1 table concludes `marketplace/targets` is "CLOSED" and that `build.py` was never at issue; in fact a type error introduced into `build.py` by this very plan would have been caught by no static gate.
- **Fix:** Add two rows to the parity table (in `report-01.md` if it is amended, and in `_gate_coverage.parity_population()` if G2 keeps that artifact) with verdict `equal` and a note stating the coverage is equal *and zero*, and open a follow-up item for widening the ruff/mypy path lists to `marketplace/targets` and `build.py`. Note in that item that the widening changes both sides, so it is deliberately outside this plan's "changing what CI checks" boundary and needs its own authorization.
- **Done when:** the shared-blind cells are named in the parity artifact, and a follow-up item exists for widening the path lists.
- **Module/topic:** `plan-marshall/script-shared/build/_gate_coverage.py` + root `build.py` gate scope

## G6 — Fix the "this gate never performs them" claim for a module-scoped run

- **Kind:** stale-statement
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_gate_coverage.py:315` — `_render_structural_limits`, the `not_run` block at `:352-358`
- **What is wrong:** The derived not-run line reads "`not run in this gate at all: … — absent from the list above because this gate never performs them, NOT because they passed`". It is false on a real, routinely-executed command. Running `cmd_quality_gate('pm-code-intelligence')` end-to-end during review printed:
  `not run in this gate at all: mypy(production), mypy(test), plugin-doctor, module-tests — … because this gate never performs them`.
  Two of those four are wrong for that invocation: `cmd_quality_gate` *does* perform plugin-doctor, just only when `module is None` (`build.py:486-499`); and it *did* attempt `mypy(production)` on this very run — `_skip_empty_mypy_scope` printed `skipping mypy for marketplace/bundles/pm-code-intelligence — no file there survives the [tool.mypy] exclude patterns` — so that dimension was attempted-and-empty, not never-performed. The per-bundle `quality-gate {bundle}` sweep is exactly what the finalize gate runs, so this text ships on ordinary runs.
- **Why it matters:** It is a false statement inside the gate's own honesty output — the one place where a reader is entitled to take the wording literally. "Never performs them", "does not perform them at this scope", and "attempted and found nothing to check" have three different remedies, and the last one is a coverage hole the sentence actively conceals (see G8).
- **Fix:** In `_render_structural_limits`, stop deriving `not_run` from the whole `_ANALYSIS_LIMITS` registry as though it were a statement about the command. Have the caller pass the set of dimensions this invocation *could* have run at its scope, and render three distinct clauses: "not performed at this scope", "not performed by this gate at all (run `verify`)", and — once G8 records them — "attempted, nothing in scope". (Introduced by PR #1239 in the file this plan created; grouped here because it is the same output surface.)
- **Done when:** `cmd_quality_gate('pm-code-intelligence')` prints no line asserting that this gate never performs plugin-doctor or `mypy(production)`, and a test pins that output for a module-scoped run.
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
- **Severity:** medium
- **Where:** `build.py:343-345` (`cmd_compile` module arm) and `build.py:364-365` (`cmd_test_compile`) — the `_skip_empty_mypy_scope` early `return 0`
- **What is wrong:** When no file under the scope survives the `[tool.mypy]` excludes, the command returns 0 before reaching `_run_mypy`, so the dimension is recorded neither as checked nor as degraded. Demonstrated by execution during review, twice:
  - `cmd_test_compile('pm-dev-python', boundary=b)` → `rc=0`, `b.checked == []`, `b.degraded == []`, `b.complete is True`, and `render_coverage_summary(b)` returns exactly `>>> coverage: COMPLETE over the dimensions below — checked over full scope: (nothing)` — a COMPLETE verdict over zero dimensions, with even the structural-limit block suppressed.
  - `cmd_quality_gate('pm-code-intelligence')` → `rc=0` and `coverage: COMPLETE` listing only `ruff` and `SPDX headers`; the attempted-and-skipped `mypy(production)` appears nowhere except in the misleading not-run line (G6).

  Grepping `record_degraded` across the tree confirms the freshness path at `build.py:317` is its only production caller, so no other partial-coverage condition can make a verdict PARTIAL.
- **Why it matters:** D5's done-when is that a partially-checked footprint produces a distinguishable verdict. A silently omitted dimension is the absence-read-as-coverage shape the deliverable targets, and the `COMPLETE … (nothing)` form is that shape at full strength — the epic's namesake defect reproduced inside its own fix. PR #1239's not-run line only partially covers it, and mis-describes it (G6).
- **Fix:** In both skip branches, when a `boundary` is supplied, call `boundary.record_checked(f'{dimension} [0 files, nothing collectable]')` (or a dedicated `record_skipped`) so the dimension appears in the verdict with its empty scope stated, rather than vanishing. Add a test driving `cmd_verify` with an empty test scope and asserting the printed summary names the skipped dimension.
- **Done when:** `cmd_quality_gate('pm-code-intelligence')` prints a verdict naming `mypy(production)` with its zero scope, and a test drives a skipped mypy scope and asserts the printed summary names the skipped dimension.
- **Module/topic:** root `build.py` + `plan-marshall/script-shared/build/_gate_coverage.py`

## G9 — Repoint the `display_detail` ceiling cross-reference to the document that states it

- **Kind:** doc-drift
- **Severity:** low
- **Where:** `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/pre-push-quality-gate.md:354` (the sizing paragraph) and `:368-369` (this plan's added sizing sentence, which inherits the pointer)
- **What is wrong:** The sizing paragraph sends the reader to "the `display_detail` length ceiling owned by [`ref-workflow-architecture/standards/agents.md`] (do not restate the number here — read it there)". That document states no ceiling: grepping it for `80` and for `character` returns nothing, and its only `display_detail` mention (`agents.md:162`) points **back** to `phase-6-finalize/standards/external-step-contract.md` § "Required termination", which is where the `≤80 characters` constraint actually lives (`external-step-contract.md:52`). A reader who follows the instruction literally finds no number and lands in a two-hop loop.
- **Why it matters:** This plan's own DEGRADED variant paragraph closes with "Size it the same way as the module-tests variant … and it stays inside the same `display_detail` ceiling", so the new text's only route to the number is the broken pointer. G4's fix asks for a third variant sized against that same ceiling; leaving the pointer dangling makes that instruction unfollowable.
- **Fix:** Change the link target at `:354` from `../../ref-workflow-architecture/standards/agents.md` to `external-step-contract.md` § "Required termination" (a sibling of this file), keeping the "do not restate the number" discipline.
- **Done when:** `pre-push-quality-gate.md:354` links to the document that states the ≤80-character constraint, and no `display_detail`-ceiling reference in that file points at `agents.md`.
- **Module/topic:** `plan-marshall/phase-6-finalize` — pre-push-quality-gate standard

## G10 — An empty coverage boundary must not render COMPLETE

- **Kind:** vacuous-test
- **Severity:** low
- **Where:** `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_gate_coverage.py:181-184` — `CoverageBoundary.complete`; `:362` — `render_coverage_summary`; `:315-324` — `_render_structural_limits`'s empty-boundary early return
- **What is wrong:** `complete` is `not self.degraded`, so a boundary that recorded **nothing at all** is `complete=True`, and `render_coverage_summary` emits `>>> coverage: COMPLETE over the dimensions below — checked over full scope: (nothing)`. `_render_structural_limits` additionally returns `[]` for an empty boundary, so even the "what a green does not evaluate" block is suppressed and the reader gets a bare COMPLETE. Reproduced during review by handing `render_coverage_summary` a boundary that `cmd_test_compile('pm-dev-python', boundary=b)` had left empty. The module's own docstring (`:11-16`) claims it applies rule (b) "fail closed on undetermined / empty state" from `ref-code-quality/standards/error-handling.md:289`; on the empty boundary it fails **open**.
- **Why it matters:** "A parity table derived from nothing looks identical to perfect parity" is the plan's own framing of this exact confusion (plan.md § Verification), and it recurs one level down in the verdict renderer. Recorded as `low` and not higher because today's production callers always record at least one dimension before rendering — `cmd_quality_gate` reaches `ruff` and `SPDX headers`, `cmd_verify` reaches `module-tests` — so the empty form is currently latent rather than shipped. Fixing G8 makes it *less* reachable but does not remove the fail-open.
- **Fix:** Make `complete` require an affirmative signal: `return bool(self.checked) and not self.degraded`. Render a boundary with no checked and no degraded dimensions as a distinct third verdict (e.g. `>>> coverage: NONE — this gate certified nothing`), never as COMPLETE. Add a test asserting `CoverageBoundary().complete is False` and that the rendered text for an empty boundary contains neither `COMPLETE` nor `(nothing)`.
- **Done when:** `render_coverage_summary(CoverageBoundary())` does not contain the string `COMPLETE`, and a test pins that.
- **Module/topic:** `plan-marshall/script-shared/build/_gate_coverage.py`

## Refuted during adversarial review

**None.** Every gap G1–G8 was re-checked independently (see verification.md § "Adversarial review" for the per-item means) and each held. Two were re-severitied upward (G6, G8) on evidence from executing the affected commands rather than reading them; several file:line citations and one over-broad sentence in G5 were corrected. Two gaps (G9, G10) were added.
