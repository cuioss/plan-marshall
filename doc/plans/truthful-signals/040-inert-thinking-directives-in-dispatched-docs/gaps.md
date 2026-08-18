# Gaps — inert-thinking-directives-in-dispatched-docs

**Source:** verification.md (same directory)   **Open items:** 5

The plan's three deliverables all landed and all hold up under execution: the pre-fix tree produces exactly the 5 reported hits, HEAD produces 0, the derived population is 33 by two independent derivations, and a mutation that reintroduces a removed directive turns the plan's own anchor test RED. The items below are one partial miss against an explicit Verification requirement, three stale statements in `report-01.md`, and one still-open residue item.

## G1 — Publish the examined population size on a clean run, not only inside findings

- **Kind:** incomplete-sweep
- **Severity:** medium
- **Where:** `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_thinking_directive_in_workflow_docs.py` — `analyze_thinking_directive_in_workflow_docs`; consumed at `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_runner.py:203-205` (the `emit()` closure defined at `_runner.py:143-145`)
- **What is wrong:** `plan.md` § Verification requires *"D3's detector must publish the population size it examined **in its own output**. Verify by running it and reading that number."* The size is published only as `details.population_size` on a finding. On the real tree the rule is clean, so it emits zero findings and the runner records `{'rule': 'analyze_thinking_directive_in_workflow_docs', 'findings': 0}` — the population size appears nowhere. Running the rule and reading the number is impossible on a clean tree, which is the only state the gate ever passes in. Confirmed by executing `analyze_thinking_directive_in_workflow_docs(marketplace/bundles)` at HEAD (returns `[]`, population 33) and by reading `emit()` in `_runner.py`, which records only a label and a count.
- **Why it matters:** the mechanism the plan asked for is the one that survives a *degraded* population, not just an empty one. The committed guards cover the zero case (the `empty_population` finding) and a hard floor (`test_real_marketplace_population_is_non_empty` asserts `>= 20`), but a derivation that silently shrinks the population from 33 to, say, 21 still reports `findings: 0` with no number visible to the reader of the gate output. That is the "a zero reads as coverage" shape the epic is named for.
- **Fix:** have the analyzer surface the population size on every run, not only on findings. Either (a) return a clean-run informational record the runner can render (e.g. an entry whose `severity` is informational and which `_scoped`/exit-code accounting ignores), or (b) give the rule a summary hook so `_runner.py`'s `emit()` can record `{'rule': …, 'findings': 0, 'population_size': 33}` in `rule_summaries`. Add a test asserting the size is present in the emitted output for a **clean, non-empty** population — the current `test_population_size_published_in_finding` only covers the finding-bearing case.
- **Done when:** running the plugin-doctor quality gate against a clean tree shows the examined population size for `analyze_thinking_directive_in_workflow_docs` in its output, and a test asserts that on a clean non-empty population.
- **Module/topic:** `pm-plugin-development:plugin-doctor` — rule `thinking-directive-in-workflow-doc`

## G2 — Correct the test count in report-01.md (39 → 46)

- **Kind:** stale-statement
- **Severity:** low
- **Where:** `doc/plans/truthful-signals/040-inert-thinking-directives-in-dispatched-docs/report-01.md` — § Deliverables → D3, the bullet reading "`test/pm-plugin-development/plugin-doctor/test_analyze_thinking_directive_in_workflow_docs.py` (39 tests)"
- **What is wrong:** the landed test file collects and passes **46** tests (`uv run python -m pytest … --collect-only` → `46 tests collected`; full run → `46 passed`). The file has one commit in its history (`94eb7521`), so 46 is what landed. The 39 figure describes the branch before the review-fix commit `de61276` — which was squashed into the same landed commit — added the mixed-content, tilde-fence, four-backtick, and descriptive-negative cases. The report was amended twice after merge (#1144, #1146) without re-deriving this number.
- **Why it matters:** the report is the audit record for this plan. A count that is wrong by seven against the very commit the report documents makes every other unverifiable count in it less trustworthy.
- **Fix:** change "(39 tests)" to "(46 tests)" in the D3 bullet of `report-01.md`.
- **Done when:** the number in `report-01.md` § D3 equals the collected test count of `test/pm-plugin-development/plugin-doctor/test_analyze_thinking_directive_in_workflow_docs.py`.
- **Module/topic:** `doc/plans/truthful-signals/040-…` run report

## G3 — Retract the "sole consumers are the phase-6-finalize tests" claim about `_dispatch_roster.py`

- **Kind:** stale-statement
- **Severity:** medium
- **Where:** `doc/plans/truthful-signals/040-inert-thinking-directives-in-dispatched-docs/report-01.md` — § Deliverables → D2, first paragraph: "It is a generic Markdown-section parser (`section_lines` / `parse_roster`) **whose sole consumers are the phase-6-finalize tests**"
- **What is wrong:** false at the moment it was written. `git grep -ln 'from _dispatch_roster import' 94eb7521 -- test/` lists three importers outside `test/plan-marshall/phase-6-finalize/`: `test/plan-marshall/manage-lessons/test_lesson_store_resolution_population.py`, `test/plan-marshall/phase-5-execute/test_execute_phase_markers.py`, and `test/plan-marshall/ref-workflow-architecture/test_citations_only_conformance.py`. The set has grown since. The conclusion the sentence supports — that the module is a heading-bounded Markdown-section/roster-row parser, not the execution-context workflow roster — is independently correct and is not in question.
- **Why it matters:** this sentence is the evidence given for the STOP CONDITION that re-scoped D2, and it is the same sentence the § Residue and Step-9 notes reuse when advising future plan authors about `_dispatch_roster.py`. A reader acting on "sole consumers are the phase-6-finalize tests" would mis-scope any change to that shared module and miss three suites.
- **Fix:** replace the clause with what is verifiable — e.g. "a generic heading-bounded Markdown-section and roster-row parser (`section_lines`, `parse_roster_rows`, `parse_roster`) whose docstring scopes it to `dispatch-inline-split.md`'s `## Dispatched steps` / `## Inline steps` sections, and which is imported by suites across phase-5-execute, phase-6-finalize, manage-lessons and ref-workflow-architecture". Keep the conclusion; drop the consumer claim.
- **Done when:** `report-01.md` § D2 no longer asserts an importer set that `git grep 'from _dispatch_roster import'` contradicts.
- **Module/topic:** `doc/plans/truthful-signals/040-…` run report

## G4 — Correct or attribute the "10 positive / 10 negative" boundary-harness figure

- **Kind:** stale-statement
- **Severity:** low
- **Where:** `doc/plans/truthful-signals/040-inert-thinking-directives-in-dispatched-docs/report-01.md` — § Deliverables → D3, "Verified by a boundary harness (10 positive / 10 negative) and by the negative parametrized tests"
- **What is wrong:** the committed negative parametrization (`TestNegativeBoundary::test_procedural_prose_does_not_fire`) has **13** cases, not 10; the positive family parametrization has 10. The separate "boundary harness" is not in the tree, so the 10/10 figure cannot be re-derived from any committed artifact.
- **Why it matters:** the false-positive boundary is the load-bearing half of D3, and this is the only number the report offers for it. An uncheckable figure sitting next to a checkable-and-different one invites a reader to trust the wrong count.
- **Fix:** state the committed counts (10 positive family cases, 5 removed-D1 regression cases, 13 negative boundary cases) and mark the ad-hoc harness explicitly as an uncommitted run-time artifact, or drop the harness figure.
- **Done when:** every count in the D3 bullet is re-derivable from the committed test file.
- **Module/topic:** `doc/plans/truthful-signals/040-…` run report

## G5 — Land the plan-authoring note that population-derived detectors derive from ext-point frontmatter

- **Kind:** omission
- **Severity:** low
- **Where:** `.claude/skills/author-cloud-plan/SKILL.md` (no occurrence of `population-derived`, `_dispatch_roster`, or `implements:`); the mis-pointer still stands at `doc/plans/truthful-signals/050-migration-shims-have-no-expiry/plan.md:84` ("copy the pattern from `test/_shared/_dispatch_roster.py`")
- **What is wrong:** `report-01.md` § Residue and § Step 9 both flag that two plans in this epic named `test/_shared/_dispatch_roster.py` as the pattern for a population-derived detector, and that this is the wrong mechanism. Nothing durable was written down. Plan 050 has since run and its report rediscovered the same mis-pointer from scratch (`050/report-01.md:169,261`) — the cost was paid twice.
- **Why it matters:** the shape this plan established (derive the population from the ext-point `implements:` frontmatter, publish the size, guard the empty case) is reusable and is now implemented twice; without it recorded, the next plan author reaches for `_dispatch_roster.py` again.
- **Fix:** add a short paragraph to `.claude/skills/author-cloud-plan/SKILL.md` stating that a plan calling for a population-derived detector must name the derivation mechanism, that the mechanism for dispatched-doc populations is the ext-point `implements:` frontmatter (or `extension_discovery.find_implementors` where the surface matches), and that `test/_shared/_dispatch_roster.py` is a Markdown-section parser for finalize step rosters and not a population source. Cite `_analyze_thinking_directive_in_workflow_docs.py::enumerate_execution_context_workflow_docs` as the reference implementation.
- **Done when:** `.claude/skills/author-cloud-plan/SKILL.md` names the frontmatter-derivation mechanism for population-derived detectors and explicitly rules out `_dispatch_roster.py`.
- **Module/topic:** `.claude/skills/author-cloud-plan` — plan-authoring guidance
