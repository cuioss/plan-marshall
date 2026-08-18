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

# plugin-doctor detectors report clean over populations they never examined

**Epic:** truthful-signals
**Branch prefix:** fix — the bulk of the work repairs detectors and guards that emit a wrong signal.

## Problem

The `pm-plugin-development:plugin-doctor` bundle has grown a family of detectors whose job is to
prove that some population was examined and found clean. Several of them cannot do that. They report
`findings: 0` — the shape a green gate takes — in states where nothing was examined at all, where the
wrong thing was examined, or where the guard written to catch exactly that was silently discarded
before it reached the reader. The same shape recurs in the pin-trap detector, which issues `pass` on
a content comparison that walked zero files and `fail` on two samples that demonstrably disagreed.

The mechanisms are distinct and each is readable at a named symbol:

- **The anti-vacuity guard is dropped by the scoped run.** Three rules emit an empty-population
  finding anchored at the *marketplace root* — `EMPTY_POPULATION_TYPE` in
  `_analyze_thinking_directive_in_workflow_docs.py::analyze_thinking_directive_in_workflow_docs` and
  in `_analyze_shim_marker.py::analyze_shim_marker`, and a third in
  `_analyze_incident_reference_in_docs.py::analyze_incident_reference_in_docs`, which anchors the
  same way but carries **no** `EMPTY_POPULATION_TYPE` constant (it emits the rule's ordinary
  `FINDING_TYPE` with `extra.pattern_family='empty_population'`), so a search for the constant name
  finds only the first two. All three reach the `_scoped` closure in
  `doctor-marketplace.py::cmd_quality_gate` — the first two directly, the third through the
  `_suppressed` closure, which calls `_scoped` before the suppression filter — and `_finding_in_scope`
  keeps a finding only when its `file` resolves *to or under* a `--paths` scope dir. The marketplace
  root is a **parent** of every possible scope dir, so under `--paths` the guard's finding is
  unconditionally dropped and the rule reports zero findings over an empty population.
- **The examined population is invisible on a clean run.** `_runner.py`'s `emit()` closure records
  `{'rule': label, 'findings': len(findings)}` and nothing else. `details.population_size` rides on
  findings only, so on a clean tree — the only state a passing gate is ever in — the size the rule
  derived appears nowhere.
- **Documented-invocation analyzers attribute a flag to the wrong scope.**
  `_analyze_argument_naming.py::_entry_from_surface` unions each subcommand's accept set with the
  root parser's flags, justified by a docstring claim about argparse that is false; the union can only
  ever *add* flags, so a root-declared router flag written after the verb can never be reported. The
  mirror defect sits in the same cluster: `_INVOCATION_RE` treats a leading `--flag` as "no
  subcommand", so a *correctly* written router-flag-first invocation is judged against the root flag
  set alone and its verb's own flags are reported as unknown. In
  `_analyze_canonical_enum_drift.py::_enum_sites_in_skill`, the `if block_notation is None:` latch
  records the notation and subcommand path of the *first* executor invocation in a fenced block and
  never updates them, so every enum below the first invocation in a shared fence is scoped to the
  wrong subcommand.
- **The pin-trap oracle passes and fails on axes it did not read.**
  `_plugin_pin_trap.py::compare_pin_content` returns `ContentComparison(0, 0, 0)` for a `source_dir`
  that is missing, empty or unreadable, and `_evaluate_single` tests only `content.diverged > 0`, so
  a zero-file comparison satisfies the content conjunct. The same function enumerates the *source*
  side only, so a pin dir that is a strict superset of source — the retired-file residue the detector
  exists to catch — reads as a complete match. And `_volatile_signature` omits `obs.content`
  entirely, so the double-sample agreement check issues a confident verdict over two samples that
  disagreed on the longest read in the observation.
- **Tests report green over mechanisms they do not exercise.**
  `test_backticked_inline_code_ref_is_exempt`'s fixture carries no incident noun, so it passes
  whether or not the exemption it is named after exists.
  `test_real_marketplace_tree_produces_zero_findings`'s docstring claims that a new unmarked shim
  turns it red — a claim already falsified by a shim that landed unmarked after the guard shipped.

## Goal

Every detector in this plan's scope either publishes the population it examined and can be shown to
fail on the defect it names, or explicitly declares the coverage it does not have. A clean result
from these rules becomes evidence about a stated population rather than evidence that nothing was
looked at, and no verdict — pass or fail — is issued over an axis that was not read.

## Deliverables

Ordered so the highest-severity gaps land first. **D1 is a gate: if its derivation fails, the run
halts and reports, and D2–D8 are not attempted.**

1. **D1 — Root-anchored anti-vacuity findings survive a scoped run** *(GATE)* (closes 040/G6)

   **Derive the population first.** Enumerate, by reading
   `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_runner.py`
   (`RuleRunner.run_quality_gate`), every rule whose findings are routed through the `scoped(...)`
   wrapper **or** through the `suppressed(...)` wrapper — the latter is `_suppressed` in
   `doctor-marketplace.py`, which calls `_scoped` before filtering, so a rule routed that way is
   scope-filtered exactly as a `scoped(...)` rule is. Enumerating `scoped(...)` alone under-derives
   the set. For each, open its analyzer module and determine whether it can emit a finding whose
   `file` is the marketplace root — or any path that is a *parent* of a plausible `--paths` scope dir
   — rather than a file inside the tree. Three members are known at authoring time:
   `_analyze_thinking_directive_in_workflow_docs.py` and `_analyze_shim_marker.py` (both via a
   constant named `EMPTY_POPULATION_TYPE`, both routed through `scoped(...)`), and
   `_analyze_incident_reference_in_docs.py` (routed through `suppressed(...)`, and carrying **no**
   such constant — it emits the rule's ordinary `FINDING_TYPE` with
   `extra.pattern_family='empty_population'`). **Derive by finding anchor, not by constant name, and
   re-derive the set rather than trusting that trio as complete** — a fourth such rule may have
   landed since.

   ⛔ **STOP CONDITION.** If the `scoped(...)` / `suppressed(...)` call sites cannot be enumerated
   from `_runner.py`, or if a routed rule's finding anchor cannot be determined by reading its
   analyzer, **halt the plan**,
   record what was derivable and what was not, and ship nothing from D2–D8. Do **not** fall back to a
   hand-maintained list of exempt finding types: a hand-maintained enumeration of a machine-derivable
   set is the defect class this epic exists to remove, and writing one here would reproduce it inside
   the fix.

   With the set derived, make those findings bypass `_finding_in_scope`. The precedent to mirror is
   in the same method: `validate_extension_contracts`' errors are appended unfiltered with a comment
   stating that a scoped gate must still catch a broken contract. Split each affected rule's result
   so the root-anchored anti-vacuity findings are always appended while the per-file findings keep the
   existing scope filter. Then correct the **Anti-vacuity guard** claim in
   `plugin-doctor/references/rule-catalog.md` for every rule in the derived set — it currently
   asserts that a clean result can never read as a vacuous pass over an unread population, which does
   not hold under `--paths` today.

   *Done when:* a quality-gate run with a non-empty `--paths` scope, over a tree that defines the
   rule's convention document and derives zero population members, reports a **non-zero** `findings`
   count for every rule in the derived set; and a committed test in
   `test/pm-plugin-development/plugin-doctor/` builds that tree, runs the gate scoped to a
   subdirectory, and asserts each such finding is still present.

2. **D2 — The pin-trap oracle stops issuing verdicts over axes it did not read**
   (closes 320/G1, 320/G3, 320/G8, 320/G2, 320/G7)

   All five changes are in
   `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_plugin_pin_trap.py`.

   - **320/G1** — make an empty content comparison unrepresentable as a pass. Either return `None`
     from `compare_pin_content` when `total == 0` (routing to the existing `content is None` →
     `indeterminate` branch) or add a `ContentComparison.usable` predicate required before the `pass`
     arm of `_evaluate_single`. Distinguish the `OSError` case from the genuinely-empty case in the
     reason string.
   - **320/G8** — enumerate `pin_dir.rglob('*')` as well, count every pin-relative path absent from
     the source set into `diverged` and into `total` (so the denominator is the union), and report
     the extra files distinctly in `render()` so a retired-file residue is distinguishable from a
     content edit.
   - **320/G3** — add the content comparison's counts to the tuple returned by `_volatile_signature`
     so a content disagreement between the two samples yields `indeterminate` with the existing
     `read_during_write` reason. If a second content scan is judged too costly to require, the
     exclusion must be stated in the `_volatile_signature` docstring **and** in `Verdict.notes`, so
     the verdict discloses which axes were double-sampled — never left silent.
   - **320/G2** *(vacuous-guard — red-first required)* — `ContentComparison.partial` is currently
     unreachable from the adapter: every source file is counted into either `scanned` or `unreadable`,
     so `scanned + unreadable == total` always holds. Decide and wire the meaning: a file the pin
     simply lacks is a **divergence** (increment `scanned`, count into `diverged`); only an unreadable
     *source* file, or an `OSError` other than not-found, is unscanned and drives `partial`. The
     replacement test must drive `compare_pin_content` itself — not the dataclass constructor — into
     a partial state.
   - **320/G7** — return a result distinguishing `unreadable` / `no_anchor` / `split(versions)` from
     `read_executor_anchored_version`, and route `split` onto the divergence axis with the conflicting
     versions named, leaving the other two on the `unreadable` list.

   *Done when:* `evaluate` over an observation whose `content` has `total == 0` returns
   `indeterminate`, not `pass`; `evaluate` over an otherwise-agreeing observation whose pin holds one
   file source does not have returns `fail`; `evaluate` over two observations differing only in
   `content` returns `indeterminate` (or the exclusion is present in both the docstring and the
   published notes); `evaluate` over an observation built from a version-split executor returns
   `fail` naming the conflicting versions while an unreadable executor still returns `indeterminate`;
   and a test drives `compare_pin_content` into `partial == True` with `PARTIAL scan` in `render()`.
   For **320/G2** specifically, the run must record that the new partial-scan test was **seen RED**
   against the current adapter (which cannot produce a partial state) before the adapter change
   landed — a guard whose red has not been observed is not closed.

3. **D3 — Documented-invocation analyzers attribute flags and enums to the scope that owns them**
   (closes 100/G10, 060/G6, 060/G7)

   - **100/G10** — in `_analyze_canonical_enum_drift.py::_enum_sites_in_skill`, replace the
     `if block_notation is None:` latch with an unconditional notation search on every line, updating
     `block_notation` / `block_path` whenever a line matches and keeping the previous values for
     continuation lines that carry no notation. The comment asserting that the notation is always the
     block's first line goes with it.
   - **060/G6** — add a placement-aware rule to the `ARGUMENT_NAMING_*` cluster in
     `_analyze_argument_naming.py`: when a documented invocation carries a subcommand and a flag that
     is in `root_flags` but **not** in that subcommand's own subtree flags, report it with a fix
     naming the pre-verb position. Keep the existing union for the unknown-flag rule so no new false
     positives appear there, and correct `_entry_from_surface`'s docstring — the union's real
     justification is over-approximation to avoid false findings, not an argparse behaviour that does
     not exist.
   - **060/G7** — in the invocation extractor, skip leading `--flag [VALUE]` pairs when locating the
     subcommand token, so a router-flag-first invocation resolves to the same `(subcommand, rest)`
     pair as the flag-last form, while the router flags stay in `rest` for the flag scan.

   **Read this before running anything against the real tree.** `analyze_argument_naming` resolves
   its ground truth through `.plan/execute-script.py`, and returns `[]` — a silent no-op — when that
   file is absent. **`.plan/` is git-ignored and does not exist in this clone. Do not go looking for
   it, and do not read an empty result from the real tree as evidence of anything.** The supported
   path is the cluster's own fixture helpers reachable from
   `test/pm-plugin-development/plugin-doctor/test_analyze.py` — `_build_fixture_root`,
   `_write_fake_script` and `_write_skill_md` are defined in that file, and
   `write_dispatching_executor` is imported into it from the sibling module
   `test/pm-plugin-development/plugin-doctor/_plugin_doctor_dispatching_executor.py` — which build a
   synthetic executor; re-derive their names and their defining modules from that file's imports
   rather than trusting this list. If a whole-tree
   confirmation of 060/G7's live incidence is attempted and cannot be produced for this reason,
   **record the coverage gap in the run report** rather than reporting the tree clean.

   *Done when:* (a) a synthetic two-skill tree whose single fenced block documents two invocations,
   each correctly, yields **0** findings from `analyze_canonical_enum_drift`, and `derive_population`
   over the real tree reports, for a site below a second invocation in a shared fence, the subcommand
   path the invocation line above it actually names — with `analyze_canonical_enum_drift` still
   returning 0 findings over the real tree; (b) the cluster returns a router-flag-misplaced finding
   for a SKILL.md documenting a root-declared flag written *after* the verb, and returns none for the
   same document written with the flag *before* the verb; (c) a doc writing the flag before the verb
   produces no unknown-flag finding for a flag the named subcommand declares. All three are pinned by
   committed tests beside the cluster's existing positive controls.

4. **D4 — Two tests that pass over the mechanism they name are replaced by tests seen RED**
   (closes 130/G5, 050/G1)

   Both gaps are `vacuous-test`. **Neither is closed by a test that has not been observed failing
   against the defect it names.** The run records, per test, the mutation applied and the observed
   red.

   - **130/G5** — in `test/pm-plugin-development/plugin-doctor/test_analyze_incident_reference_in_docs.py`,
     `test_backticked_inline_code_ref_is_exempt`'s fixture contains no incident noun, so no narration
     family matches it with or without the backticks. Replace the fixture with a line that a narration
     family **would** match if unquoted, keeping the `== []` assertion, and add a paired positive test
     asserting the same sentence without backticks yields exactly one `incident_reference` finding
     from the term-of-art family. The pair is the control.
   - **050/G1** — in `test/pm-plugin-development/plugin-doctor/test_analyze_shim_marker.py`,
     `test_real_marketplace_tree_produces_zero_findings`'s docstring claims that a regression on
     either side turns it red and that every shim in the tree carries a conforming marker. Replace
     both sentences with what the assertion actually proves: the precision-first indicator set fires
     on nothing in the current tree. Then add a test that **measures** recall rather than asserting
     it: for each marker anchor in the real population, strip that block into a temporary copy, run
     the file scanner, and assert the detected count equals a checked-in expected number, so a change
     to the indicator set visibly moves it. Publish that measured number in
     `plugin-doctor/references/rule-catalog.md` beside the false-positive-boundary paragraph.
     **Re-derive the number at the moment of the change** — a figure recorded elsewhere in this epic
     describes a tree that may have moved.

   *Done when:* with the inline-code-span skip in the incident-reference scanner disabled, the
   back-tick exemption test **fails**, and with it restored both it and the new positive test pass;
   `test_analyze_shim_marker.py` contains no claim that an unmarked shim necessarily turns the
   real-tree test red and no claim that every shim in the tree is marked; the recall test asserts a
   measured per-site figure that matches the tree; and the run report names the mutation used to see
   each new guard red.

5. **D5 — The runner publishes the examined population, and the shim rule is reachable where its
   catalogue says it is** (closes 040/G1, 050/G5, 050/G2)

   - **040/G1 + 050/G5** — give `_runner.py`'s `emit()` closure an optional population figure and
     record `{'rule': …, 'findings': n, 'population_size': m}` in `rule_summaries`, and have the two
     population-derived rules expose the size they derived so the runner can read it without
     re-deriving. The two gaps are one fix applied to two rules; make it once.
   - **050/G2** — `analyze_shim_marker` is emitted only from `run_quality_gate`;
     `run_analyze_marketplace_rules` does not list it, while `rule-catalog.md` § Discovery approach
     states it is wired into both. Either add it to the analyze pass next to the sibling
     thinking-directive rule and extend the runner's analyze-side coverage the way that rule is
     covered, **or** correct the catalogue sentence. The plan's preference is to wire it, because the
     edit-time surface is the one the rule was built to serve — but either resolves the gap, and
     whichever is chosen must leave no surface claiming a reachability the code does not have.

   *Done when:* a clean quality-gate run reports a non-zero examined-population figure for both
   population-derived rules in its rule summaries; a committed test asserts the figure is present for
   a **clean, non-empty** population (not only for the finding-bearing case); and either
   `analyze_shim_marker` is reachable from the analyze pass with a test covering it, or no surface
   claims that it is.

6. **D6 — Router-flag placement guidance reaches the surface it is about, and names an invocation a
   caller may run** (closes 060/G3, 060/G5, 060/G2)

   - **060/G5** — `_augment_misplaced_router_flag` in
     `marketplace/bundles/plan-marshall/skills/tools-input-validation/scripts/input_validation.py`
     builds its worked example as `{prog} {flag} VALUE <subcommand> ...`, where `prog` is the root
     parser's `parser.prog`. Most marketplace scripts leave `prog=` unset, so that value is the bare
     script filename; the scripts that do set it (`orchestrator.py`, `marshalld.py`, the
     `marshall-steward` scripts, `platform_runtime.py`, `_ci_barrier.py`) set it to a bare program
     name. **Re-derive which spelling the CI surface's own root parser yields** — either way the
     rendered example is an invocation form the repository's script-execution convention forbids,
     because none of these spellings is the `python3 .plan/execute-script.py {bundle}:{skill}:{script}`
     notation a caller may run — and `<subcommand>` is a placeholder where the caller's own
     verb was available in the failing argv. Build the example from the caller's actual argv instead:
     render the verb tokens that preceded the misplaced flag, and prefer an explicitly supplied
     notation over `parser.prog`, falling back to `prog` only when none is supplied.
   - **060/G3** — the note gates on flags declared on the **root parser**, and the `ci` front-ends
     strip `--plan-id` / `--project-dir` with `extract_routing_args` before the parser is built, so
     the root router-flag set is empty and the note never fires on the surface the residue item was
     about. Close it by declaring the two flags on the `ci` root parser in `ci_base.build_parser`, or
     by giving the parse helper an explicit extra-router-flags parameter that the `ci` front-ends
     supply. Add a test beside `test/plan-marshall/tools-input-validation/test_router_flag_placement.py`
     that drives the **real** CI parser rather than a synthetic one.
   - **060/G2** — add a fifth recurrence signature to § "Never invent script subcommands" in
     `marketplace/bundles/plan-marshall/skills/persona-plan-marshall-agent/standards/agent-behavior-rules.md`:
     a router-scoped flag placed *after* the verb on the CI surface, whose worked example moves the
     flag ahead of the verb. State explicitly that this is the **mirror** of the existing
     verb-scoped-flag signature, whose worked example prescribes the opposite move, so a reader cannot
     collapse the two into one. The section's lead-in sentence states a literal signature count
     ("these four canonical argparse-rejection signatures"); re-derive it from the numbered list at
     the moment of the change and correct it in the same edit — an enumeration lead-in left standing
     above a list of a different length is the same defect class this epic exists to remove. Fix
     060/G5 before or with this, or the guidance points at a note that names an uninvocable path.

   *Done when:* running the CI parser with a subcommand followed by `--plan-id X` produces stderr
   naming the flag and stating that it belongs before the subcommand, pinned by a test against the
   real CI parser; the emitted example names the caller's real verb rather than a placeholder and
   names no bare `*.py` filename, pinned by a test; and the standards document contains a signature
   whose worked example moves a router flag from after the verb to before it, with the section's
   stated signature count equal to the number of numbered entries the section lists.

7. **D7 — The pin-trap detector's loader model, shape table, remedy and sampling API say what they do**
   (closes 320/G6, 360/G3, 320/G5, 320/G4, 320/G9, 320/G10)

   **320/G6 and 360/G3 are the same symbol and must land together** — they are two records of one
   defect in `loader_selected_version`, filed against two plans.

   - **320/G6 + 360/G3** — the body computes a retention-pin / live-set / degraded-fallback selection
     whose result is unconditionally the numerically-newest dir, and the docstring describes a
     marker-aware selector that no longer exists. Reduce the body to the newest-eligible maximum
     (keeping the empty guard) and rewrite the docstring to state the current contract: newest
     eligible wins, the marker is never consulted. Do **not** write "newest-eligible" over a body
     that computes newest-overall — if the eligibility parameter from 320/G5 is not wired, the
     docstring must name the approximation and the case in which it diverges. Rewrite the derived
     unmarked-set note so the marker claim is scoped to the foreign garbage collector and to the
     GC-exposure axis. Re-rank the saturation shape: keep it as a reportable GC-exposure observation
     but take it out of the load-safety failure conjunct and out of the repair-urgently tier, since
     the loader no longer reads the field. Rename the two stale tests in
     `test/pm-plugin-development/plugin-doctor/test_plugin_pin_trap.py` to describe
     marker-insensitivity; their assertions and fixtures stay as they are.
   - **320/G5** — give `loader_selected_version` an optional eligibility parameter restricting the
     pool, defaulting to all dirs, and have the observing adapter populate it from the cache dirs that
     actually carry the subpath under test. Document the divergence case by naming the *per-request*
     predicate in `script-shared/scripts/marketplace_bundles.py`'s bundle-path resolver — the
     mechanism by which a resolution goes **backward**, which is the incident the detector was built
     for — and distinguish it from the directory-existence predicate the directory collector uses.
     No surface may still claim the divergence case is practically unreachable.
   - **320/G4** — the implemented shape-3 condition can only fire when a non-pin dir sorts *higher*
     than the pin, so the literal tree the plan's shape 3 names (an older stale unmarked dir beside a
     correct newest pin) passes. **Do not decide whether the reinterpretation is right.** Record it:
     rename the shape constant to describe what the code evaluates, state in the module docstring that
     the literal tree is a pass under newest-wins selection and why, and add a test asserting the
     literal tree's verdict so the behaviour is pinned. Write the broaden-the-condition alternative
     into the run report as a **proposal for the operator**, not as a change.
   - **320/G9** — the operator remedy's third step is the bare phrase "regenerate the executor" while
     steps (1) and (2) each name an invocable surface. Name the executor-regeneration surface in the
     same form, and extend the remedy test to assert it appears in the verdict's remedy.
   - **320/G10** — the double-sample conjunct has no producer: the observing adapter returns one
     observation and nothing exports a paired variant, so passing the same observation twice satisfies
     the guard. Add a paired observer beside it that samples twice with a delay, taking the sleep
     function as a parameter so a test can drive it without wall-clock cost, export it, and state in
     the evaluator's docstring that passing the same observation twice defeats the guard and that the
     paired observer is the supported producer.

   *Done when:* no docstring in the pin-trap module claims that this repository's version selection
   consults the orphan marker, and `loader_selected_version` contains no branch whose outcome is
   independent of the marker; the function returns an older dir when the newest is excluded by the
   supplied eligibility set, asserted by a test; the literal older-stale-beside-newest-pin tree has an
   asserted verdict and the shape constant's name matches the condition evaluated; the saturation
   shape no longer appears in the load-safety failure conjunct; the operator remedy names an invocable
   surface for all three steps, asserted by the remedy test; the paired observer exists, is exported,
   and is covered by a test injecting a fake sleep and a mutating fixture so the two observations
   differ and the evaluator returns `indeterminate`; and `test_plugin_pin_trap.py` passes.

8. **D8 — Rule coverage widened where it is cheap, declared where it is not, and the stale
   documentation corrected** (closes 100/G7, 130/G3, 130/G2, 100/G6, 040/G2, 460/G5)

   - **100/G7** — in `_analyze_canonical_enum_drift.py`, extend the enum-token pattern to accept the
     brace-less pipe form (`--flag a|b|c`), requiring at least one pipe and rejecting a member list in
     which any member begins with `--`, so the mutually-exclusive-group form is not misread; and teach
     the authority resolver the declarative dict-spec form (`{'flags': [...], 'choices': [...]}`),
     which is a same-file parse. The import-hop half of the gap's fix is **out of scope** (see below);
     in its place, **publish the unresolved-notation fraction as a named field on the analyzer's
     output and record the structural causes in the module docstring's fail-closed list**, so the
     coverage gap is declared rather than silent. The gap names counts for the brace-less sites and
     the unresolved fraction — **re-derive both from `derive_population` at the moment of the change;
     do not carry the recorded figures forward.**
   - **130/G3** — extend the incident-reference rule to the narration forms its own brief named and
     its matcher misses: an incident noun immediately *followed* by an optionally back-ticked
     reference (the reverse of the shipped term-of-art form), and a dated / version-pinned narration
     family. Add one positive test per new form and one negative keeping a legitimate version
     constraint unflagged, and extend the rule catalogue and provenance entries. **The real-tree
     zero-findings test will go red on at least one live site** — the dated lead-in line
     `As of 2025-10-27:` opening the universal-access bullets in
     `marketplace/bundles/plan-marshall/skills/tools-permission-doctor/standards/permission-architecture.md`.
     Remove that date, letting the bullets below it stand as the present-tense statement they already
     are; this is the minimum edit required to keep the rule's real-tree anchor green, and it is
     independently required by the repository's documentation standards. **Re-run the anchor after
     the matcher lands and re-derive the full live-site set from the pattern actually written** — a
     family widened beyond the gap's proposed regex surfaces further sites (see the Claim labels row
     for 130/G3), and each one must be disposed of or the widening narrowed before the anchor is
     green.
   - **130/G2** — a back-ticked incident reference is exempt from every narration family whatever the
     surrounding prose, so a removed reference can be reinstated by adding two backticks and the gate
     stays green. **Do not narrow the exemption in this run.** It is a deliberate, documented,
     project-wide convention published in the rule catalogue, the provenance table, a named test, and
     a sibling rule that states the same posture — narrowing it is an amendment to a stated
     convention, not a defect repair, and this run has no operator to approve one. Instead, **record
     a proposal** in the run report: the narrowing the gap describes (suspend the inline-code skip
     when an incident noun stands within a short window on either side of the match, or when the line
     is a heading), the two live sites the narrowing would newly surface, and the reason a suppression
     entry is the wrong remedy (the rule shipped unconditional by explicit design). Name it as a
     proposal, not a decision taken.
   - **100/G6** — the rule catalogue's manually-maintained-mirror section states a literal rule count
     and enumerates four rules, while two further rules are registered in the rule registry and in
     both runner passes. Add a subsection for each missing rule following the shape of the existing
     entries, correct the literal count, and add both rule ids to the mirror-drift bullets in the
     plugin-doctor SKILL.md. **Re-derive the count from the registry at the moment of the change** —
     writing a second stale literal here would reproduce the defect the section is about.
   - **040/G2** — the run report of the inert-thinking-directives plan states a test count for the
     thinking-directive test file that is short of what the file collects. Replace it with the
     collected count, re-derived by collecting the file. **If that plan's directory is no longer
     present** — a landed plan directory is removed when the epic ingests it — record the gap as
     already collected in the run report and move on; do not recreate the directory.
   - **460/G5** — two docstrings in `test/plan-marshall/plan-retrospective/` describe the
     retrospective reader's context-load cell as a three-way, per-column read. It has read four ways
     since the provenance gate landed, and the fourth verdict is decided **per row**, so the headline
     claim is false about the mechanism, not merely out of date. Rewrite both docstrings to state what
     the tests actually pin. Docstrings only — no assertion or test-name changes, so no behaviour
     moves.

   *Done when:* the brace-less enum sites are collected by `derive_population` and the dict-spec
   authority form resolves, with the unresolved fraction and its structural causes published on the
   analyzer's output and in its module docstring; the incident-reference rule fires on the reversed
   term-of-art form and on the dated narration form, does not fire on a legitimate version
   constraint, and its real-tree zero-findings anchor passes with no suppression entry registered;
   the rule catalogue names both previously-unlisted rules and its stated count equals the number of
   rule subsections the section enumerates; the two retrospective test docstrings no longer describe
   a three-way or per-column read; and the run report carries the 130/G2 narrowing as a labelled
   **proposal** with its two live sites named.

## Out of scope

Each exclusion carries its reason, because with no operator watching, the written boundary is the
only thing that stops mid-run drift.

- **Narrowing the back-tick exemption in the incident-reference rule (130/G2).** It is an amendment
  to a convention published across four surfaces and implemented by a sibling rule; a run with no
  operator cannot approve a contract change. D8 records the proposal instead.
- **Broadening the pin-trap shape-3 condition to report two unmarked dirs (320/G4).** The same
  reason: whether an older unmarked dir beside a correct pin is a finding or a benign post-sync
  window is a policy call. D7 pins the current behaviour and records the alternative as a proposal.
- **Following the import hop in the canonical-enum authority resolver (100/G7).** The gap itself
  offers publishing the unresolved fraction as the alternative when the hop is judged too costly. A
  cross-module parser walk is a substantially larger change than the rest of this plan and would
  couple its verification to the shared parser-building modules; declaring the gap is the honest and
  bounded remedy, and it is what D8 ships.
- **The gaps in the source plans' `gaps.md` files that this plan does not name.** Each source
  document carries more findings than this plan's assigned set; the unnamed ones belong to other
  plans in this epic and picking them up here would collide with a concurrent run over the same files.
- **Regenerating or synchronising any plugin cache.** The cache lives outside git and is a
  machine-local developer concern; the merged bundle source is authoritative and this run neither
  performs a sync nor records one as owed.
- **Wiring the pin-trap detector into a live gate.** It ships as a library with adapters by its own
  plan's declared residue; D2 and D7 repair the oracle's correctness, and gating on it is a separate
  decision with its own blast radius.

## Expected surface

Under `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/`:

- `scripts/_runner.py` — the `emit()` closure (D5) and the analyze-pass registration (D5).
- `scripts/doctor-marketplace.py` — `cmd_quality_gate`'s `_scoped` routing and `_finding_in_scope`
  (D1).
- `scripts/_analyze_thinking_directive_in_workflow_docs.py`,
  `scripts/_analyze_shim_marker.py` — the root-anchored empty-population findings (D1) and the
  population figure the runner reads (D5).
- `scripts/_analyze_argument_naming.py` — `_entry_from_surface`, the invocation extractor, and the
  new placement rule (D3).
- `scripts/_analyze_canonical_enum_drift.py` — `_enum_sites_in_skill` (D3), the enum-token pattern
  and the authority resolver (D8).
- `scripts/_analyze_incident_reference_in_docs.py` — the root-anchored empty-population finding
  (D1) and the narration pattern set (D8).
- `scripts/_plugin_pin_trap.py` — the content comparison, the volatile signature, the executor
  adapter, the loader model, the shape table, the remedy text and the paired observer (D2, D7).
- `references/rule-catalog.md`, `references/rule-provenance.md`, `SKILL.md` — the anti-vacuity claim
  (D1), the measured recall figure (D4), the reachability claim (D5), the new narration forms and the
  mirror-drift enumeration (D8).

Under `marketplace/bundles/plan-marshall/`:

- `skills/tools-input-validation/scripts/input_validation.py` — the router-flag note (D6).
- `skills/tools-integration-ci/scripts/ci_base.py` — the CI root parser or the extra-router-flags
  hand-off (D6).
- `skills/persona-plan-marshall-agent/standards/agent-behavior-rules.md` — the fifth recurrence
  signature (D6).
- `skills/tools-permission-doctor/standards/permission-architecture.md` — the dated section heading
  (D8).
- `skills/script-shared/scripts/marketplace_bundles.py` — **read only**, cited in a docstring (D7).

Under `test/`:

- `test/pm-plugin-development/plugin-doctor/` — `test_runner.py`, `test_analyze.py`,
  `test_analyze_shim_marker.py`, `test_analyze_incident_reference_in_docs.py`,
  `test_analyze_thinking_directive_in_workflow_docs.py`, `test_analyze_canonical_enum_drift.py`,
  `test_plugin_pin_trap.py`. Re-derive the exact file names from the directory; this list is a lead.
- `test/plan-marshall/tools-input-validation/test_router_flag_placement.py` (D6).
- `test/plan-marshall/plan-retrospective/test_analyze_logs.py`,
  `test_analyze_logs_behavior.py` — docstrings only (D8).

Under `doc/plans/truthful-signals/`:

- `040-inert-thinking-directives-in-dispatched-docs/report-01.md` — one count (D8), if the directory
  is still present.

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| 040/G6 reproduces: the empty-population finding is anchored at the marketplace root and `_finding_in_scope` keeps a finding only when its path is the scope dir or under it, so a parent path can never match | OBSERVED | `_analyze_thinking_directive_in_workflow_docs.py` (`EMPTY_POPULATION_TYPE`, `file=str(marketplace_root)`) and `doctor-marketplace.py::_finding_in_scope`; the rule is routed through `scoped(...)` in `_runner.py::run_quality_gate` |
| The same defect exists in `analyze_shim_marker` — its empty-population finding is also root-anchored and also routed through `scoped(...)` | OBSERVED | `_analyze_shim_marker.py` (`EMPTY_POPULATION_TYPE`) and the `emit('analyze_shim_marker', scoped(...))` call in `_runner.py::run_quality_gate` |
| A third member exists — `analyze_incident_reference_in_docs` anchors its empty-population finding at the marketplace root too, reaches `_scoped` through `suppressed(...)`, and carries no `EMPTY_POPULATION_TYPE` constant, so a constant-name search misses it | OBSERVED | `_analyze_incident_reference_in_docs.py` (the `if not targets:` branch returning a `Finding` with `file=str(marketplace_root)` and `extra.pattern_family='empty_population'`), the `emit('analyze_incident_reference_in_docs', suppressed(...))` call in `_runner.py::run_quality_gate`, and `_suppressed` in `doctor-marketplace.py::cmd_quality_gate`, which calls `_scoped` before filtering |
| 050/G1 reproduces: the real-tree shim test's docstring claims a regression on either side turns it red and that every shim carries a marker | OBSERVED | `test/pm-plugin-development/plugin-doctor/test_analyze_shim_marker.py::test_real_marketplace_tree_produces_zero_findings` docstring |
| The measured per-site recall figure quoted in 050/G1 | HYPOTHESIS | The recall harness D4 adds — re-derive by mutation over the real population; do not carry the recorded figure forward |
| 060/G6 reproduces: `_entry_from_surface` unions root flags into every subcommand's accept set, so a root-declared flag can never be reported as misplaced, and its docstring justifies the union with a false claim about argparse | OBSERVED | `_analyze_argument_naming.py::_entry_from_surface` (docstring and the `root_flags \| child_flags` assignment) |
| 060/G7 reproduces: the invocation pattern's subcommand group requires a non-hyphen first token, so a router-flag-first invocation parses with no subcommand and is judged against the root flag set alone | OBSERVED | `_analyze_argument_naming.py` — `_INVOCATION_RE` and the `inv.subcommand is None` branch of `scan_flag` |
| 060/G7's live incidence in the real tree | HYPOTHESIS | Cannot be settled in this clone: `analyze_argument_naming` returns `[]` when `.plan/execute-script.py` is absent, and it is absent. Settled instead by the fixture-level controls in `test_analyze.py`; the whole-tree gap is recorded, not asserted clean |
| 100/G10 reproduces: `_enum_sites_in_skill` latches the block notation on the first invocation and never updates it | OBSERVED | `_analyze_canonical_enum_drift.py::_enum_sites_in_skill` — the `if block_notation is None:` guard and the comment stating the notation is always the block's first line |
| 130/G5 reproduces: the back-tick exemption test's fixture carries no incident noun, so the assertion is satisfied by the absence of a matching pattern | OBSERVED | `test_analyze_incident_reference_in_docs.py::test_backticked_inline_code_ref_is_exempt` fixture, read against `_TERM_OF_ART_RE` and `_PATTERNS` in `_analyze_incident_reference_in_docs.py` |
| 320/G1 reproduces: an unreadable, missing or empty `source_dir` yields a zero-file comparison and `_evaluate_single` tests only `content.diverged > 0` | OBSERVED | `_plugin_pin_trap.py::compare_pin_content` (the `except OSError` return and the `total = len(source_files)` path) and the outcome ladder in `_evaluate_single` |
| 320/G3 reproduces: `_volatile_signature` omits `obs.content` | OBSERVED | `_plugin_pin_trap.py::_volatile_signature` — the returned tuple |
| 320/G8 reproduces: only the source side is enumerated, so a pin superset reads as a complete match | OBSERVED | `_plugin_pin_trap.py::compare_pin_content` — `source_files = sorted(p for p in source_dir.rglob('*') …)` |
| 320/G2 reproduces: `scanned + unreadable == total` always holds, so `ContentComparison.partial` is unreachable from the adapter | OBSERVED | `_plugin_pin_trap.py` — the `scanned` argument built by `compare_pin_content` against `ContentComparison.partial` |
| 320/G6 and 360/G3 reproduce, and are the same symbol | OBSERVED | `_plugin_pin_trap.py::loader_selected_version` — the docstring describing a retention pin, live set and degraded fallback over a body whose `pinned` is by construction the maximum of `pool` |
| 320/G10 reproduces: no paired observer exists | OBSERVED (asserted absence, verified) | `_plugin_pin_trap.py`'s `__all__` lists the single observer and no paired variant |
| 050/G2 reproduces: `analyze_shim_marker` is emitted from the quality-gate pass only, while the catalogue claims both passes | OBSERVED (asserted absence, verified) | The only `analyze_shim_marker` call site in `_runner.py` is inside `run_quality_gate`; `references/rule-catalog.md` § Discovery approach for that rule claims `cmd_quality_gate` **and** `cmd_analyze` |
| 100/G6 reproduces: neither new rule id appears in the catalogue or the plugin-doctor SKILL.md | OBSERVED (asserted absence, verified) | Both rule ids occur zero times in `references/rule-catalog.md` and `SKILL.md`; the mirror-drift section states a literal count of four |
| 100/G7's site and notation counts | HYPOTHESIS | `derive_population` over the real tree — re-derive at the moment of the change; the recorded figures describe an earlier tree |
| 130/G3's live dated-narration site still exists | OBSERVED | `marketplace/bundles/plan-marshall/skills/tools-permission-doctor/standards/permission-architecture.md` — the dated lead-in line `As of 2025-10-27:` standing directly above the universal-access bullets, under the `## Universal Access Pattern` heading (it is a prose line, not a markdown heading); it is the only match for the gap's `(?:as of\|since\|before\|after)\s+(?:20\d{2}(?:-\d{2})?\|\d+\.\d+\.\d+)` family under `marketplace/bundles` outside Javadoc/JSDoc examples — a family widened beyond that pattern (e.g. to a spelled-out month) also matches `pm-dev-frontend-cui/skills/cui-javascript-project/standards/project-structure.md`'s "current active LTS as of October 2025", so re-derive the live-site set against the pattern actually written |
| 130/G3's real-tree anchor goes red unless that site is edited | HYPOTHESIS | The new dated-narration pattern run against the real tree once D8's matcher lands |
| 460/G5 reproduces: two retrospective test docstrings describe a three-way, per-column read | OBSERVED | `test/plan-marshall/plan-retrospective/test_analyze_logs.py` and `test_analyze_logs_behavior.py` — the two docstrings; a third match in `test_chat_provenance.py` is about chat provenance and is out of family |
| The expected surface above is the set of files this plan touches | HYPOTHESIS | The run's own diff, checked against the section at verification time; a file touched and not listed is collateral change to be justified in the report |
| Every gap named in the Deliverables reproduces at HEAD — none was already closed | OBSERVED | Each gap's own `Where` clause was opened at the named file and symbol while this plan was authored; the source documents are git-tracked at `doc/plans/truthful-signals/{040,050,060,100,130,320,360,460}-*/gaps.md` |

An asserted **absence** is verified exactly as an asserted presence, and is the higher-risk half.
The three absences above are each marked as verified.

## Verification

Beyond the per-deliverable *done when* conditions:

**The build gate.** This plan changes Python under `marketplace/bundles/` and `test/`, so the lane's
conditional build gate applies and the full verify must pass. The contract owns the mechanics.

**Red-first, recorded.** D2's partial-scan test and both of D4's tests are vacuous-guard closures.
For each, the run applies the mutation that reproduces the defect, observes the test **fail**, then
lands the fix and observes it pass, and records both observations in the run report naming the
mutation. A guard whose red was not observed is reported as **not closed**, whatever the diff shows.

**Cold reads.** Four deliverables produce text whose whole value is what a later reader *does* with
it. Dispatch the pre-PR verification sub-agent to read each **cold** — without this plan, without the
gap documents, and without the diff's intent — and report which reading it took. A wrong reading is a
wording failure however complete the text looks.

1. **The router-flag error note (D6).** Give the reader the emitted stderr for a real failing
   invocation and one question: *what is the working command?* The correct answer is the exact
   invocation with the flag moved ahead of the verb, expressed through the repository's
   script-execution convention. If the reader produces a bare `*.py` path, or cannot supply the verb,
   the message failed.
2. **The fifth recurrence signature (D6).** Give the reader the § "Never invent script subcommands"
   signature list and ask where `--plan-id` goes for a CI-surface call and for a
   `manage-architecture` call. Two different answers are the correct outcome; one answer applied to
   both means the mirror signatures collapsed and the wording failed.
3. **The pin-trap operator remedy (D7).** Give the reader a `fail` verdict and ask what they run for
   each of the three repair steps. A step for which they cannot name a command has not been closed.
4. **The declared coverage statement (D8, 100/G7) and the anti-vacuity claim (D1).** Give the reader
   the analyzer's published output and its module docstring, and ask: *over what population is this
   clean result evidence, and what did it not look at?* If the reader cannot name the excluded set,
   the declaration is decorative and the wording failed.

**Coverage check against the gap documents.** Every gap id this plan names is git-reachable at
`doc/plans/truthful-signals/{source-plan}/gaps.md`. Before the PR, re-read each named entry's
*Done when* and state, per gap id, met / not met / deliberately recorded-as-proposal. A gap left open
is reported open — an overstated outcome is collected as done and never picked up again, which is
strictly worse than an understated one.

**Counts.** Every figure this plan writes about the tree is a lead. Re-derive at the moment of the
claim: the population sizes the runner publishes, the measured shim recall, the enum site and
unresolved-notation counts, the mirror-drift rule count, and the thinking-directive test count. None
of them is authoritative here.

## Notes

**Where this plan came from.** It closes twenty-nine gaps recorded by adversarial review against
eight already-landed plans in this epic. The source documents are git-tracked and are the only
evidence surface this run needs:
`doc/plans/truthful-signals/040-inert-thinking-directives-in-dispatched-docs/gaps.md` (G1, G2, G6),
`050-migration-shims-have-no-expiry/gaps.md` (G1, G2, G5),
`060-invented-plan-scoping-flags-are-an-overgeneralized-convention/gaps.md` (G2, G3, G5, G6, G7),
`100-canonical-block-diverges-from-argparse-choices/gaps.md` (G6, G7, G10),
`130-skills-carry-incident-history-as-normative-prose/gaps.md` (G2, G3, G5),
`320-sync-plugin-cache-updates-the-cache-and-executor-and-never-the-registry/gaps.md` (G1–G10),
`360-collapse-the-version-selection-machinery/gaps.md` (G3), and
`460-audit-ledger-reader-reads-undatable-zero-as-measured/gaps.md` (G5). Each file's
§ *Refuted during adversarial review* records corrections applied in place; where that section and a
gap body disagree, the section wins. No gap assigned to this plan was refuted, and none was found
already closed at HEAD.

**`.plan/` is invisible here.** The orchestrator ledger, the plan specs and the generated
`.plan/execute-script.py` are git-ignored and absent from this clone. **Do not go looking for any of
them.** This matters twice in practice: the argument-naming cluster silently returns no findings
without the executor (D3), and the repository's ordinary script-execution convention — every
marketplace script invoked through that executor — is unavailable, so the lane's own direct
invocations are the path. The contract owns that.

**Two gaps are the same defect filed twice.** `320/G6` and `360/G3` both target
`loader_selected_version`. They are grouped into D7 deliberately: fixing one without the other leaves
a docstring describing a body that no longer matches it. Neither source plan's run can be assumed to
have touched the symbol.

**Two deliverables deliberately do not decide.** D8's back-tick exemption item and D7's shape-3 item
each present a fork whose resolution is a change to a stated convention or a policy call about what
counts as a finding. Both are authored to **record a proposal** in the run report rather than to make
the call, because this run has no operator to approve one. Shipping either decision would be the run
approving an amendment to a contract it is governed by.

**One collateral edit is required, not optional.** D8's dated-narration family will redden the
incident-reference rule's real-tree anchor unless the live dated site in the permission architecture
standard is corrected in the same commit. That site is separately the subject of a gap assigned
elsewhere in this epic; the edit made here is the one-line date removal that keeps the anchor green
and is independently required by the repository's documentation standards. Nothing else in that file
changes. It is the only site the gap's proposed regex matches — but the live-site set is a function
of the pattern the run actually writes, so re-derive it after the matcher lands rather than assuming
this one edit suffices.

**Sequencing.** D1 gates everything: if the root-anchored population cannot be derived, the run halts
and D2–D8 are not attempted. Within D3 and D6 the two items on `_analyze_argument_naming.py` and the
two on the router-flag note are order-sensitive — the gap documents record that adding a positive
control for the misplaced-router-flag signature before the placement rule exists pins nothing, and
that pointing readers at the router-flag note before its worked example is fixed sends them to an
invocation they must not run.
