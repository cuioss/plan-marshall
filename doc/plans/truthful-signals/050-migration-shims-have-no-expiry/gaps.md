# Gaps — 050-migration-shims-have-no-expiry

**Source:** verification.md (same directory)   **Open items:** 5

## G1 — Stop the shim-rule test from claiming a recall it does not have, and record the measured number

- **Kind:** vacuous-test
- **Severity:** high
- **Where:** `test/pm-plugin-development/plugin-doctor/test_analyze_shim_marker.py:342-350` — `test_real_marketplace_tree_produces_zero_findings`
- **What is wrong:** The test's docstring asserts *"A regression on either side (a new unmarked shim, or an over-broad indicator) turns this red."* Measured: stripping one `# SHIM(A|B):` marker block at a time from each of the 25 marker sites in `marketplace/bundles/*/skills/*/scripts/**/*.py` and re-running `_analyze_shim_marker._scan_file` on the stripped copy produces a finding at **4 sites** (`_cmd_mark_step.py`, `_cmd_assert_step_recorded.py`, `gitignore_setup.py`, `upgrade.py`) and **nothing at the other 21**. So for 21 of the 25 shim shapes the tree actually contains, removing the marker leaves this test green.
- **Why it matters:** This is the epic's own archetype — a green test whose docstring makes a confident claim its mechanism cannot support. A reader (or a later plan) takes "zero findings on the real tree" as evidence that every shim is marked, when it is mostly evidence that the indicator set does not match most shims. The precision-first tradeoff is honestly documented in `_analyze_shim_marker.py`'s module docstring and in `shim-marker-convention.md`; only this test overstates it.
- **Fix:** Reword the docstring to state what the assertion actually proves ("the precision-first indicator set fires on nothing in the current tree") and drop the "a new unmarked shim turns this red" clause. Then add a recall test that measures rather than asserts: for each marker anchor in the real population, strip that block into a temp copy, run `_scan_file`, and assert the detected count equals a checked-in expected number, so a future change to `_INDICATORS` visibly moves it. Publish that number in `references/rule-catalog.md` next to the false-positive-boundary paragraph.
- **Done when:** `test_analyze_shim_marker.py` contains no claim that an unmarked shim necessarily turns the real-tree test red, and a test asserts the measured per-site recall against a stated figure that matches the tree.
- **Module/topic:** `pm-plugin-development:plugin-doctor` — `shim-marker-missing` rule and its tests

## G2 — Wire `analyze_shim_marker` into `plugin-doctor analyze`, or correct the claim that it is

- **Kind:** omission
- **Severity:** medium
- **Where:** `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_runner.py:329-378` — `RuleRunner.run_analyze_marketplace_rules`
- **What is wrong:** `report-01.md` § Deliverables states the rule was "wired build-failing into quality-gate + analyze". It is emitted only from `run_quality_gate` (`_runner.py:206`); `run_analyze_marketplace_rules` lists 29 analyzers and `analyze_shim_marker` is not among them. The landed `_runner.py` hunk in `1296ede1` adds exactly two lines (the import and the quality-gate `emit`), so this was never wired and was not removed by a later commit. The sibling rule this one was mirrored from, `analyze_thinking_directive_in_workflow_docs`, is emitted from both methods.
- **Why it matters:** An author running `plugin-doctor analyze` over a bundle they are editing — the edit-time surface D2 exists to serve — gets no shim finding at all. The defect only surfaces at the quality gate, which is later and coarser.
- **Fix:** Add `issues.extend(analyze_shim_marker(root))` to `run_analyze_marketplace_rules`, positioned next to `analyze_thinking_directive_in_workflow_docs(root)` to match the quality-gate ordering, and extend `test_runner.py`'s analyze-side coverage the way the thinking-directive rule is covered. If a deliberate decision is made to keep it gate-only, correct the report line instead and say why in `references/rule-catalog.md` § Discovery approach, which currently reads "wired into `cmd_quality_gate` (build-failing) and `cmd_analyze`" — also false today.
- **Done when:** `analyze_shim_marker` is reachable from `plugin-doctor analyze`, or `rule-catalog.md:231` no longer claims it is.
- **Module/topic:** `pm-plugin-development:plugin-doctor` — runner dispatch

## G3 — Mark (or explicitly classify out) the `_LEGACY_CI_WAIT` category-B shim the D0 sweep missed

- **Kind:** incomplete-sweep
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/_manifest_decide.py:29-31` — `_LEGACY_CI_WAIT`
- **What is wrong:** The constant is documented as *"The retired phase-6 step id Rules 2 and 5 drop defensively, against project marshal.json files that still list it as a candidate"* and is consumed as a `drop=` set at lines 175 and 221. That is a permanent read-path accommodation of a persisted config shape an older version of this tooling wrote — category B under the convention's own discriminator in `shim-marker-convention.md`. It carries no marker, and it appears neither in report-01.md's 24-row inventory nor in its NOT-A-SHIM negatives list, despite its comment containing `legacy`, one of D0's own sweep terms. No site in the `manage-execution-manifest` bundle appears anywhere in the D0 partition.
- **Why it matters:** D3's completeness claim ("every surviving category-B site is marked") is only as good as D0's enumeration. One demonstrated miss in a bundle the sweep reported zero hits from means the inventory's boundary was never established, which is precisely the "confident signal, hidden caveat" this plan set out to remove.
- **Fix:** Read `_LEGACY_CI_WAIT` and its two call sites by symbol. If it is a shim, add a conforming four-line `# SHIM(B):` block above the constant naming `manage-execution-manifest` as owner, the change that retired the `ci-wait` step id as the floor, and "no project marshal.json lists `ci-wait` as a phase-6 candidate" as the removal trigger. If it is judged out of scope, record it in `shim-marker-convention.md`'s not-a-shim list with the reason. Then re-run the D0 vocabulary sweep over `manage-execution-manifest` and any other bundle the original sweep reported zero hits from, and state the population and hit count separately.
- **Done when:** `_LEGACY_CI_WAIT` either carries a conforming marker or is named in the convention's not-a-shim list, and the re-sweep over the previously zero-hit bundles is recorded with its population size.
- **Module/topic:** `plan-marshall:manage-execution-manifest` — shim inventory

## G4 — Remove the two markers that sit on sites with no shim code to delete

- **Kind:** stale-statement
- **Severity:** low
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_sync_defaults.py:290-293` — `_deep_merge_missing`; and `marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/_invariants.py:747-750` — `_REFERENCES_REQUIRED_KEYS`
- **What is wrong:** `_deep_merge_missing` contains no branch on the legacy `{}` shape. Its own docstring states *"the read path coerces all of {absent, `null`, `{}`, TOON-`''`} to an empty dict, so the two on-disk shapes read identically"*; the tolerance is emergent from `if key not in live`. There is nothing to delete when the marker's `shim-remove-when` condition ("no marshal.json carries a legacy `{}` ownerless-step value") is met. `_invariants.py:747` is the same shape one step weaker: the marker sits on a constant tuple where the tolerance is the *absence* of `modified_files` from it. report-01.md itself labelled these "⚠ borderline" and "⚠ soft".
- **Why it matters:** `shim-marker-convention.md` states that marking a non-shim "is as wrong as leaving a real shim unmarked — it dilutes the signal". A future sweep acting on `shim-remove-when` at these two sites finds no code to remove and learns to distrust the markers.
- **Fix:** For `_cmd_sync_defaults.py:290`, delete the marker block; the docstring paragraph "Ownerless-step interaction" already records the history without claiming a deletable shim. For `_invariants.py:747`, either delete the marker (the prose comment above it already records the retirement) or move it to whichever read path actually tolerates the old shape, if one exists. Confirm `analyze_shim_marker` still reports zero findings afterwards.
- **Done when:** every remaining `# SHIM(A|B):` marker sits on a branch or statement that would be deleted when its `shim-remove-when` condition holds, and the real-tree detector run is still clean.
- **Module/topic:** `plan-marshall:manage-config` / `plan-marshall:plan-marshall` — shim markers

## G5 — Make the examined population readable on a clean run

- **Kind:** doc-drift
- **Severity:** low
- **Where:** `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_shim_marker.py:442-483` — `analyze_shim_marker`
- **What is wrong:** `details.population_size` rides on findings only. On a clean tree the function returns `[]`, and the quality-gate summary line is `{'rule': 'analyze_shim_marker', 'findings': 0}` — the population size appears nowhere. The plan's Verification section says "D2's detector must publish the population size it examined. Run it and read that number." Today that number is only obtainable by calling `enumerate_script_files` yourself (it is 412) or by reading the `>= 100` floor assertion in `test_analyze_shim_marker.py:337`. The empty-population guard covers a population of exactly zero, not a derivation that silently collapses from 412 to 3.
- **Why it matters:** A clean gate result carries no evidence of what it examined, which is the vacuity shape this epic is named for. The same applies to the sibling `analyze_thinking_directive_in_workflow_docs`, so the fix is worth making once for both.
- **Fix:** Have the runner carry the examined population into the rule summary — e.g. extend `emit` to accept an optional `population` and record `{'rule': ..., 'findings': n, 'population_size': m}` — and have `analyze_shim_marker` expose the size it derived (a module-level accessor, or a second return value) so the runner can read it without re-deriving. Assert the summary field in `test_runner.py`.
- **Done when:** a clean `quality-gate` run reports a non-zero examined-population figure for `analyze_shim_marker`, and a test asserts it.
- **Module/topic:** `pm-plugin-development:plugin-doctor` — runner summaries and population-derived rules
