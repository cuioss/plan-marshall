# Gaps — 050-migration-shims-have-no-expiry

**Source:** verification.md (same directory)   **Open items:** 7

## G1 — Stop the shim-rule test from claiming a recall it does not have, and record the measured number

- **Kind:** vacuous-test
- **Severity:** high
- **Where:** `test/pm-plugin-development/plugin-doctor/test_analyze_shim_marker.py:342-350` — `test_real_marketplace_tree_produces_zero_findings` (the two overstating sentences are in the docstring at lines 343-349)
- **What is wrong:** The docstring makes two claims the mechanism does not support. (a) *"A regression on either side (a new unmarked shim, or an over-broad indicator) turns this red."* Measured: stripping one `# SHIM(A|B):` marker block at a time from each of the 25 marker sites in `marketplace/bundles/*/skills/*/scripts/**/*.py` and re-running `_analyze_shim_marker._scan_file` on the stripped copy produces a finding at **4 sites** (`_cmd_mark_step.py:355`, `_cmd_assert_step_recorded.py:125`, `gitignore_setup.py:196`, `upgrade.py:239`) and **nothing at the other 21**. So for 21 of the 25 shim shapes the tree actually contains, removing the marker leaves this test green. (b) *"Every migration/back-compat shim in the tree carries a conforming marker"* — false as stated: see G3 (`_LEGACY_CI_WAIT`, unmarked since before this plan) and G6 (`posture_cutoff_legacy_aggregate`, unmarked and landed after it).
- **Why it matters:** This is the epic's own archetype — a green test whose docstring makes a confident claim its mechanism cannot support. A reader (or a later plan) takes "zero findings on the real tree" as evidence that every shim is marked, when it is mostly evidence that the indicator set does not match most shims. The precision-first tradeoff is honestly documented in `_analyze_shim_marker.py`'s module docstring and in `shim-marker-convention.md`; only this test overstates it. **The overstatement is not hypothetical:** commit `7951ada9` (#1276, 2026-08-17) landed a new, unmarked category-B shim — `check-routing-decisions.py:170` `posture_cutoff_legacy_aggregate`, a permanent read path for a retired decision-log shape — one week after this guard shipped, and this test stayed green through it (G6). The claim "a new unmarked shim turns this red" has already been falsified on the tree it guards.
- **Fix:** In the docstring, replace both sentences: state what the assertion actually proves ("the precision-first indicator set fires on nothing in the current tree"), and drop both the "every shim carries a marker" and the "a new unmarked shim turns this red" clauses. Then add a recall test that measures rather than asserts: for each marker anchor in the real population, strip that block into a temp copy, run `_scan_file`, and assert the detected count equals a checked-in expected number (4 of 25 today), so a future change to `_INDICATORS` visibly moves it. Publish that number in `references/rule-catalog.md` next to the false-positive-boundary paragraph.
- **Done when:** `test_analyze_shim_marker.py` contains no claim that an unmarked shim necessarily turns the real-tree test red and no claim that every shim in the tree is marked, and a test asserts the measured per-site recall against a stated figure that matches the tree.
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
- **What is wrong:** The constant is documented as *"The retired phase-6 step id Rules 2 and 5 drop defensively, against project marshal.json files that still list it as a candidate"* (comment at lines 29-30, constant at line 31) and is consumed as a `drop=` set at lines 175 and 221. That is a permanent read-path accommodation of a persisted config shape an older version of this tooling wrote — category B under the convention's own discriminator in `shim-marker-convention.md`. `ci-wait` is confirmed retired as a phase-6 step id by `manage-execution-manifest/standards/decision-rules.md:628` (*"CI completion is now a dispatcher-resolved precondition … not a sibling step"*); the drop is silent accommodation, not a refusal, so the "breaking refusal" negative class does not apply. It carries no marker, and it appears neither in report-01.md's 24-row inventory nor in its NOT-A-SHIM negatives list, despite its comment containing `legacy`, one of D0's own sweep terms. No site in the `manage-execution-manifest` bundle appears anywhere in the D0 partition. **It is a genuine D0 miss, not a later regression:** `git log -S '_LEGACY_CI_WAIT'` dates the constant to `d04ac98e` (#1066, 2026-07-30), eleven days before this plan landed as `1296ede1` (2026-08-10).
- **Why it matters:** D3's completeness claim ("every surviving category-B site is marked") is only as good as D0's enumeration. One demonstrated miss in a bundle the sweep reported zero hits from means the inventory's boundary was never established, which is precisely the "confident signal, hidden caveat" this plan set out to remove.
- **Fix:** Read `_LEGACY_CI_WAIT` and its two call sites by symbol. If it is a shim, add a conforming four-line `# SHIM(B):` block above the constant naming `manage-execution-manifest` as owner, the change that retired the `ci-wait` step id as the floor, and "no project marshal.json lists `ci-wait` as a phase-6 candidate" as the removal trigger. If it is judged out of scope, record it in `shim-marker-convention.md`'s not-a-shim list with the reason. Then re-run the D0 vocabulary sweep over `manage-execution-manifest` and any other bundle the original sweep reported zero hits from, and state the population and hit count separately.
- **Done when:** `_LEGACY_CI_WAIT` either carries a conforming marker or is named in the convention's not-a-shim list, and the re-sweep over the previously zero-hit bundles is recorded with its population size.
- **Module/topic:** `plan-marshall:manage-execution-manifest` — shim inventory

## G4 — Remove the `_deep_merge_missing` marker: it sits on a site with no shim code to delete

- **Kind:** stale-statement
- **Severity:** low
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_sync_defaults.py:290-293` — the `# SHIM(B):` block above `_deep_merge_missing`'s merge loop
- **What is wrong:** `_deep_merge_missing` contains no branch on the legacy `{}` shape. Its body is `if key not in live: … elif isinstance(default_value, dict) and isinstance(live[key], dict): …` — nothing tests for `{}`. Its own docstring states *"the read path coerces all of {absent, `null`, `{}`, TOON-`''`} to an empty dict, so the two on-disk shapes read identically"*; the tolerance is emergent from `if key not in live`. There is nothing to delete when the marker's `shim-remove-when` condition ("no marshal.json carries a legacy `{}` ownerless-step value") is met. report-01.md itself labelled this site "⚠ borderline".
- **Why it matters:** `shim-marker-convention.md:29-30` states that marking a non-shim "is as wrong as leaving a real shim unmarked — it dilutes the signal". A future sweep acting on `shim-remove-when` here finds no code to remove and learns to distrust the markers.
- **Fix:** Delete the four-line marker block at `_cmd_sync_defaults.py:290-293`; the docstring paragraph "Ownerless-step interaction" already records the history without claiming a deletable shim. Re-run `analyze_shim_marker` over `marketplace/bundles` and confirm it still returns `[]`.
- **Done when:** `_cmd_sync_defaults.py` carries no `# SHIM(B):` block above `_deep_merge_missing`, and the real-tree detector run is still clean.
- **Module/topic:** `plan-marshall:manage-config` — shim markers

## G5 — Make the examined population readable on a clean run

- **Kind:** doc-drift
- **Severity:** low
- **Where:** `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_shim_marker.py:442-483` — `analyze_shim_marker`
- **What is wrong:** `details.population_size` rides on findings only. On a clean tree the function returns `[]`, and the quality-gate summary line is `{'rule': 'analyze_shim_marker', 'findings': 0}` — the population size appears nowhere. The plan's Verification section says "D2's detector must publish the population size it examined. Run it and read that number." Today that number is only obtainable by calling `enumerate_script_files` yourself (it is 412) or by reading the `>= 100` floor assertion in `test_analyze_shim_marker.py:337`. The empty-population guard covers a population of exactly zero, not a derivation that silently collapses from 412 to 3.
- **Why it matters:** A clean gate result carries no evidence of what it examined, which is the vacuity shape this epic is named for. The same applies to the sibling `analyze_thinking_directive_in_workflow_docs`, so the fix is worth making once for both.
- **Fix:** Have the runner carry the examined population into the rule summary — e.g. extend `emit` to accept an optional `population` and record `{'rule': ..., 'findings': n, 'population_size': m}` — and have `analyze_shim_marker` expose the size it derived (a module-level accessor, or a second return value) so the runner can read it without re-deriving. Assert the summary field in `test_runner.py`.
- **Done when:** a clean `quality-gate` run reports a non-zero examined-population figure for `analyze_shim_marker`, and a test asserts it.
- **Module/topic:** `pm-plugin-development:plugin-doctor` — runner summaries and population-derived rules

## G6 — Mark the `posture_cutoff_legacy_aggregate` category-B shim that landed after the guard shipped

- **Kind:** omission
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/check-routing-decisions.py:170-183` — the `posture_cutoff_legacy_aggregate` entry of `_REMOVAL_CAUSE_PATTERNS`
- **What is wrong:** The entry's own comment reads *"LEGACY — the RETIRED aggregate `lane_resolution` shape, kept for ARCHIVED decision logs only. The composer stopped emitting this when it moved to one line per dropped step … It is retained because this script reads archived plans … and an archived log is immutable history."* That is a textbook category-B shim under the convention's discriminator: a permanent read path accommodating a shape this project's own composer once wrote and no longer writes. It carries no `# SHIM(B):` marker, no owner, no floor, and no removal trigger, even though the comment states the extinction condition in prose.
- **Why it matters:** This shim landed in commit `7951ada9` (#1276, 2026-08-17) — a week *after* the `shim-marker-missing` guard shipped in `1296ede1` (2026-08-10) — and the build-failing quality gate passed. D2 exists so "the next shim cannot land unmarked"; the next shim landed unmarked. It also sits in `plan-retrospective`, a bundle D0 *did* sweep (B7–B10), so this is a live recall failure of the guard rather than a bundle the sweep never reached. It is the empirical counterpart to G1's mutation measurement, and it shows the convention is otherwise being used — `#1181` and `#1287` each added a conforming marker to a new shim in the same period.
- **Fix:** Add a conforming four-line `# SHIM(B):` block immediately above the `'posture_cutoff_legacy_aggregate'` tuple entry: `shim-owner: plan-retrospective`; `shim-floor:` the composer change that replaced the aggregate `lane_resolution` line with one line per dropped step; `shim-remove-when: no archived plan's decision log carries the aggregate lane_resolution line shape`. Then re-run `analyze_shim_marker` over `marketplace/bundles` and confirm it still returns `[]`.
- **Done when:** `check-routing-decisions.py`'s `posture_cutoff_legacy_aggregate` entry carries a conforming `# SHIM(B):` marker with all three non-empty fields, and `analyze_shim_marker(marketplace/bundles)` returns `[]`.
- **Module/topic:** `plan-marshall:plan-retrospective` — shim inventory

## G7 — Remove or relocate the `_REFERENCES_REQUIRED_KEYS` marker: the tolerance is a key's absence, not code

- **Kind:** stale-statement
- **Severity:** low
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/_invariants.py:747-750` — the `# SHIM(B):` block above `_REFERENCES_REQUIRED_KEYS` (the constant is at line 751)
- **What is wrong:** The marker sits on `_REFERENCES_REQUIRED_KEYS: tuple[str, ...] = ('base_branch', 'branch')`. The tolerance it names is the *absence* of `modified_files` from that tuple — there is no branch, no fallback, and no statement that would be deleted when `shim-remove-when` ("no in-flight plan's references.json predates the key retirement") holds; the tuple stays exactly as it is either way. The prose comment at lines 739-746 already records the retirement in full. report-01.md itself labelled this site "⚠ soft".
- **Why it matters:** Same dilution as G4 — `shim-marker-convention.md:29-30` forbids marking a non-shim. A marker whose removal trigger can never cause a removal teaches the next sweep that `shim-remove-when` is decorative.
- **Fix:** Delete the four-line marker block at `_invariants.py:747-750`, keeping the prose comment at 739-746 that already records the retirement. If a real tolerate-branch for a pre-retirement `references.json` exists elsewhere (check `_capture_references_valid` and its callers), move the marker onto that branch instead of deleting it. Re-run `analyze_shim_marker` over `marketplace/bundles` and confirm it still returns `[]`.
- **Done when:** `_invariants.py` carries no `# SHIM(B):` block on `_REFERENCES_REQUIRED_KEYS` (or carries one on an actual tolerate-branch), and the real-tree detector run is still clean.
- **Module/topic:** `plan-marshall:plan-marshall` — shim markers


## Refuted during adversarial review

**No gap in G1–G5 was refuted.** Each was re-derived first-party by an independent agent that did not
write this document: the recall figure (4 of 25) was reproduced with a separately written mutation
script, not by re-reading the original; every file:line, symbol, and quotation was opened at HEAD;
and each severity was re-tested against the rubric. G4 was **split** (its second site is now G7)
because a finding is recorded per instance. Two gaps were **added** (G6, G7).

Recorded so they are not re-litigated — candidate shim sites surfaced by an independent, deliberately
broader vocabulary sweep (412 scripts, comment tokens only, 181 hits across 78 files) and then
**rejected** by reading the symbol:

- `check-manifest-consistency.py:81` `_CANONICAL_VERIFY_PREFIX` — *"archived manifests predating the
  canonical-verify step id carry bare names too. Both forms are accepted."* **Not a shim:** the
  discriminator requires a shape the current writer no longer produces, and
  `normalize_verification_step`'s own docstring (lines 386-390) records that the `--phase-5-steps`
  CSV fallback still forwards the bare form verbatim today. A live input shape, not a legacy one.
- `_manifest_core.py:61` `DEFAULT_ENVELOPE_COUNT` — *"a manifest composed before this field existed
  simply has no `phase_5.envelope_count` key."* **Not a shim:** an honest default for an absent key,
  with no branch on an old shape — the same class as the `_stamp_value_scope` negative D0 already
  recorded.
- `claude_runtime.py:129` `_TOOL_BUCKETS` — *"the retired `Task` spelling coexisting with its `Agent`
  rename."* **Not a shim:** the tolerated shape is written by the Claude Code harness's transcripts,
  an *external* system — D0's declared external-variance negative.
- `ci_base.py:632` — *"Fall back to the legacy single-flag behaviour when the helper is not on the
  import path."* **Not a shim:** an import-path fallback, not a read path over persisted state.
- `_cmd_quality_phases.py:516` — the `legacy plan.phase-5-execute.steps` key. **Not a shim:** prose
  in a `remove-field` verb describing what the verb deletes; no tolerate-branch.
