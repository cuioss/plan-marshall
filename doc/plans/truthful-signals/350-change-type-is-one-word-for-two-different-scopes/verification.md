# Verification — 350-change-type-is-one-word-for-two-different-scopes

**Verified against:** commit `5cea6604a2a934fd6b7567bf44e4118ead017a5a`   **Landed as:** PR #1221, commit `6f7f9c76c9e44dc7d4687d0f074874de2bed84c4`   **Verdict:** implemented-with-gaps

## Method

What was actually done, in order:

- Read `plan.md` and `report-01.md` in full.
- Located the landed commit: `git log --oneline --all --grep '#1221'` → `6f7f9c76` (squash merge; the
  per-commit SHAs the report names — `ba766bf`, `c638b26`, `2abb824`, head `879ce52` — do not exist in
  `main` history, as expected for a squash-merged PR). `git show --stat -M 6f7f9c76` → 14 paths,
  698 insertions / 44 deletions, including an `R100` rename of
  `doc/plans/truthful-signals/350-….md` → `…/350-…/plan.md`.
- Opened at HEAD: `manage-execution-manifest/scripts/manage-execution-manifest.py`
  (`cmd_compose` lines 1795–1885, the `_decide` call at 2095, the pre-filter block 1955–2010, the result
  dict 2521–2534, the argparse block 3214–3231); `scripts/_manifest_decide.py`
  (`_read_settled_change_type`, 340–376); `scripts/_manifest_rules.py`
  (`_apply_security_class_inactive`, 343–370); `scripts/_manifest_core.py` (`VALID_CHANGE_TYPES`, 65–72);
  `manage-execution-manifest/SKILL.md`; `manage-execution-manifest/standards/decision-rules.md`;
  `phase-4-plan/SKILL.md` Step 7b (670–760); `phase-6-finalize/standards/finalize-step-security-audit.md`;
  `manage-status/scripts/_status_query.py::cmd_metadata`;
  `manage-status/scripts/_cmd_planning_lane.py`; `manage-status/scripts/_cmd_classification_validate.py`;
  `manage-solution-outline/scripts/manage-solution-outline.py`;
  `plan-retrospective/scripts/check-manifest-consistency.py` and `check-routing-decisions.py`;
  `test/plan-marshall/manage-execution-manifest/test_compose_change_type_reconciliation.py` and
  `test_security_class_gate_regression.py`.
- Tree-wide sweeps: `--change-type` (hyphenated flag), `first deliverable` (spaced),
  `first-deliverable` / `FIRST-DELIVERABLE-WINS` (hyphenated — the spaced sweep does **not** catch this
  form, so both were run), `_read_settled_change_type` / `settled_change_type` / `supplied_change_type` /
  `effective_change_type` / `change_type_scope` / `plan-change-type`, `feature_breaking`,
  `Rule .* fired`, and all `compose` invocation blocks in `marketplace/bundles/**`.
- Ran tests: `uv run python -m pytest test/plan-marshall/manage-execution-manifest/test_compose_change_type_reconciliation.py -o addopts="" -q`
  → **9 passed**; the whole directory → **869 passed in 28.18s**.
- Executed the code on real input rather than reading it: a throwaway probe test (written into the test
  dir, run, then deleted — `git status --porcelain` clean afterwards) seeded
  `status.metadata.change_type = 'feature_breaking'` and called `cmd_compose` twice. Result:
  `--plan-change-type feature` → `change_type_scope_conflict`; `--plan-change-type feature_breaking` →
  `invalid_change_type`. That is the evidence for G1.
- **Mutation check** (highest-risk guard). `git diff --quiet -- .../manage-execution-manifest.py` → exit
  0 (not concurrently modified), file bytes copied to the scratchpad, then two edits applied that restore
  the pre-fix shape: the refusal condition forced to `if False:` and
  `effective_change_type`/`change_type_scope` pinned to the supplied value. The plan's own test file went
  **3 failed / 6 passed** — `test_settled_vs_deliverable_change_type_is_refused_naming_both`,
  `test_matching_change_type_composes_and_records_settled_scope` and
  `test_narrowing_decision_records_its_scope_and_input` all RED. File restored by copying the saved bytes
  back (md5 `02171cf521815cb7565e74c00a22e1a7` before and after; `git diff --quiet` exit 0). No
  `git checkout`/`restore`/`stash` was used, and no file this verification did not write was touched.
- The same mutation run is what exposed G2: `test_reconciliation_emits_auditable_decision_log_line`
  stayed **green** against the mutant.

## Deliverable-by-deliverable

| # | Deliverable | Done-when condition | Implemented? | As documented? | Correct? | Complete? | Evidence (file:line / symbol / command + result) |
|---|---|---|---|---|---|---|---|
| D0 | GATE: derive both scopes + every producer/consumer, both directions | every site classified as PLAN or DELIVERABLE scope, population stated | yes | yes | yes | yes | report-01.md § D0 publishes Scope A (producers: `_cmd_change_type_heuristic.py::cmd_change_type_heuristic` writes `status['metadata']['change_type']` at line 230 — confirmed at HEAD; manual `metadata --set`; the LLM `detect-change-type` fallback / consumers: `_cmd_planning_lane.py:785`, `_cmd_classification_validate.py:277`, phase-6-finalize), Scope B (producers: phase-3-outline per deliverable, validated by `manage-solution-outline.py` `valid_change_types`; recipe `default_change_type` at `change-types.md:103` — confirmed / consumers: phase-4-plan Step 7b, `breaking-refactor-task-split.md:13,25`) and Scope C (the flag). Pre-fix line citations spot-checked at `6f7f9c76^`: argparse `2707` exact, `_decide` call `1974` exact, simplify pre-filter `1874` exact, first-deliverable comment `1879-1882` exact, `change-types.md:103` exact, `manage-solution-outline.py:201,206-217` exact. Two citations off by 3 (see Report accuracy) |
| D1 | Composition reconciles against the settled classification; contradiction refused naming both | contradiction refused, message names both | yes | yes | **partly** | yes | `manage-execution-manifest.py:1848-1867` (`supplied_change_type` / `settled_change_type` / `change_type_scope_conflict`, both values in the message and as fields, `return` before any manifest write); read helper `_manifest_decide.py:340-376`. Mutation → test RED. **Gap G1**: no guard for a settled value outside `VALID_CHANGE_TYPES` — such a plan can never compose |
| D2 | Name the two scopes apart wherever both appear (rename, not alias) | the names differ | yes | yes | yes | **partly** | Flag renamed `--change-type` → `--plan-change-type` at `manage-execution-manifest.py:3222-3230`, subparser built with `allow_abbrev=False` (3214) so the old spelling cannot resolve as an abbreviation — a genuine rename, pinned by `test_old_change_type_flag_is_rejected`. Tree sweep for `--change-type`: 4 hits, all of them the new spelling's prose, a historical comment, or the rejection test — **no live old-spelling invocation**. Distinct locals in `cmd_compose`; scopes named apart in `SKILL.md:111,167,537`, `decision-rules.md:36-49`, `phase-4-plan/SKILL.md:684`. **Gap G3**: the outline-authoring and status-metadata surfaces still spell both scopes bare |
| D3 | The narrowing decision records which scope it used | the decision carries its input | yes | yes | yes | yes | `manage-execution-manifest.py:1873-1881` computes `effective_change_type` / `change_type_scope` and emits a `decision.log` line naming both candidates; `effective_change_type` is what reaches `_apply_simplify_inactive` (1995) and `_decide` (2095) — `args.change_type` is read exactly once, at 1848. Result fields at 2527-2530. Documented at `SKILL.md:167` and `decision-rules.md:47` |
| D4 | Four tests, each verified to FAIL pre-fix | all four pass, each seen red first | yes | yes | **partly** | yes | `test_compose_change_type_reconciliation.py` — 9 tests, `pytest … -q` → **9 passed in 0.78s**. (a) `test_settled_vs_deliverable_change_type_is_refused_naming_both`, (b) `test_matching_change_type_composes_and_records_settled_scope`, (c) `test_no_settled_classification_still_composes` + two variants (`…status_without_change_type_key…`, `…malformed_status_json…`), (d) `test_narrowing_decision_records_its_scope_and_input` + the log-line test + the two rename tests. Mutation drove (a), (b), (d) RED. **Gap G2**: the log-line test's assertions cannot distinguish the two scopes and stayed green against the mutant |

**D1 (correctness).** `cmd_compose` (`manage-execution-manifest.py:1848`) validates the *supplied* value
against `VALID_CHANGE_TYPES` at line 1812 but never validates the *settled* value that
`_read_settled_change_type` returns. `VALID_CHANGE_TYPES` (`_manifest_core.py:65-72`) is the six canonical
values; `status.metadata.change_type` is written through `manage-status metadata --set`, whose
`_coerce_metadata_value` (`_status_query.py:51-65`) coerces booleans only and stores every other value
verbatim — no enum check. The repository itself asserts a plan can carry `feature_breaking` at that key
(`_cmd_planning_lane.py:104` `_DEEP_CHANGE_TYPES`, and `plan-retrospective/references/plan-efficiency.md:144`
in so many words), and `feature_breaking` is not in `VALID_CHANGE_TYPES`. Executed, not inferred: with the
settled value `feature_breaking`, supplying `feature` returns `change_type_scope_conflict` and supplying
`feature_breaking` returns `invalid_change_type` — compose has no accepting input. See G1.

**D2 (completeness).** The rename is genuine and the confusion site is fixed, but the two scopes still
share the bare spelling in the surfaces that *author* each one: `phase-3-outline/SKILL.md:437` and
`manage-solution-outline/standards/solution-outline-standard.md` present the deliverable-scoped field as
plain `change_type`, and `manage-status/SKILL.md:73` plus `standards/status-lifecycle.md:102` present the
plan-scoped field the same way, with neither naming its scope. Nothing crosses scopes at those sites, so
this is doc drift rather than a live defect. See G3.

**D4 (correctness).** `test_reconciliation_emits_auditable_decision_log_line` asserts `'settled' in
recon[0]` and `'bug_fix' in recon[0]`. The emitted message is
`… used {effective!r} from the {scope} scope (supplied --plan-change-type={supplied!r}, settled
status.metadata.change_type={settled!r})` — the literal token `settled` is present in *every* message
regardless of which scope was used, and on this fixture `bug_fix` is present regardless too. Both
assertions therefore hold when the decision used the *supplied* scope, which is exactly the defect D4(d)
exists to catch. Demonstrated: the test stayed green against a mutant that pinned
`change_type_scope = 'supplied'`. The deliverable is still covered by
`test_narrowing_decision_records_its_scope_and_input` (which did go red), so nothing false ships — but the
named guard is vacuous. See G2.

## Report accuracy

Re-derived at HEAD (or at `6f7f9c76^` where the claim is about the pre-fix tree):

- **Confirmed.** `argparse:2707 required=True` (exact at `6f7f9c76^`); `_decide` call at line 1974 and
  `simplify_inactive` pre-filter at line 1874 (both exact); the first-deliverable-wins comment at
  1879-1882 (exact); `_cmd_change_type_heuristic.py:230` writing `status['metadata']['change_type']`;
  `_cmd_planning_lane.py:785`; `_cmd_classification_validate.py:277`;
  `manage-solution-outline.py:201,206-217`; `change-types.md:103`.
- **Confirmed — "no remaining live `--change-type` compose invocation."** Tree sweep for `--change-type`
  returns 4 hits: `SKILL.md:111` (prose naming the old spelling as retired),
  `manage-execution-manifest.py:3220` (a comment), and two lines inside
  `test_old_change_type_flag_is_rejected`. Both compose invocation blocks in the bundles
  (`manage-execution-manifest/SKILL.md:98,565` and `phase-4-plan/SKILL.md:746`) use the new flag, and
  `compose` has exactly **one** live caller — phase-4-plan Step 7b (phase-1-init calls `lanes preview`,
  not `compose`).
- **Confirmed — the retrospective parse is unaffected.** `check-routing-decisions.py:199` matches
  `finalize-step-simplify\s+omitted\s+—\s+change_type=`; the new line does not match it.
  `check-manifest-consistency.py:141-163` collects every line carrying
  `(plan-marshall:manage-execution-manifest:compose)` verbatim for the report renderer, so the new line is
  additionally *reported*, harmlessly. There is no `Rule … fired` regex parse in the retrospective scripts
  at all, so that claim is true but vacuously so.
- **Confirmed — staleness sweep.** The `security_class_inactive` rationale reads as
  "orthogonal to the security surface" at all four sites the report names:
  `manage-execution-manifest.py:1998-2007`, `_manifest_rules.py:351-357`,
  `decision-rules.md:241`, `finalize-step-security-audit.md:38`. The two historical mentions of
  first-deliverable-wins that remain (`manage-execution-manifest.py:1836`,
  `test_security_class_gate_regression.py:15`) are explicitly past-tense and cross-reference plan 350.
- **Confirmed — test count.** D4 says 8 tests, the Findings section adds
  `test_malformed_status_json_degrades_to_no_settled`; the file collects and passes **9**.
- **Minor inaccuracy — two line citations in D0 are off by 3.** The report cites
  `phase-4-plan` SKILL.md:681 for "use the first deliverable's `change_type`" and :734 for the forward.
  At `6f7f9c76^` those texts are at **684** and **737**; line 681 is the "Idempotent firm-signal
  re-compose" paragraph. The quoted text and the symbol-level claim are correct; only the numbers drift.
- **Minor inaccuracy — the "22 test-namespace files" rationale for keeping `dest='change_type'`.**
  Not reproducible under any obvious derivation: at the landed commit,
  `git grep -l 'change_type=' -- test/plan-marshall/manage-execution-manifest/` = **20**,
  `… -- test/` = **35**, and `git grep -l change_type -- test/plan-marshall/manage-execution-manifest/`
  = **20**. Today the first figure is 22. The figure is incidental to the decision it justifies; no
  conclusion depends on it.
- **Contradicted in effect — "all five deliverables IMPLEMENTED-AS-SPECIFIED" (the pre-PR sub-agent
  verdict the report relays).** D1 and D4 carry the defects at G1 and G2. This is recorded as a
  contradiction of the relayed verdict, not of a first-party claim the run made about its own edits.
- **Not re-derivable from this clone** (stated as such, not counted against the report): the `./pw verify`
  figures (mypy 398/734 files, plugin-doctor `total_issues: 0` across 36 rules, `19613 passed, 14
  skipped`); the observed-red-first run; all PR #1221 CI, review and reviewer-participation figures; and
  every `.plan/`-sourced claim about the originating run, which the plan itself declared unreachable.

## Out-of-scope compliance

Clean. The landed diff is 14 paths: the 5 declared-surface bundle files
(`manage-execution-manifest` SKILL.md + 3 scripts + `decision-rules.md`), `phase-4-plan/SKILL.md`, 5 test
files, `phase-6-finalize/standards/finalize-step-security-audit.md`, plus the plan-directory rename and
`report-01.md`. The security-audit standard is outside the plan's "Expected surface" list but is squarely
inside the post-implementation staleness sweep the report declares, and its edit is confined to the
change-type rationale sentence. Nothing touches change-type **detection** (`_cmd_change_type_heuristic.py`
and `phase-3-outline/workflow/detect-change-type.md` are untouched — confirmed by the diff file list), and
nothing touches the manifest cross-check the sibling plan owns
(`plan-retrospective/scripts/check-manifest-consistency.py` is untouched). `manage-status/**` appears in
the Expected surface but was not modified; D0 resolved it to a read-side consumer needing no change, which
is the plan's own "every entry is a HYPOTHESIS until D0 resolves it" rule working as designed. No
undeclared collateral change.

## Residue carried forward

- **Merge landing** (report: auto-merge armed, squash SHA unknown at report time). **Closed** — the PR
  landed as `6f7f9c76` on `main`.
- **Rate-limited reviewers** (`coderabbitai`, `sourcery-ai` did not review the diff). **Still true and
  unremediable from the tree**; nothing in today's tree changes it, and no re-review was warranted.
- **Sibling plan owns the manifest cross-check.** **Still open.**
  `check-manifest-consistency.py` is unmodified by this plan and its bare-versus-canonical token
  behaviour is untouched here — correctly cited, not merged.
- **The ⚠ flag-stays decision.** Shipped as described: `--plan-change-type` is still `required=True`
  (`manage-execution-manifest.py:3225`). Note the by-design residue this leaves — on a plan with **no**
  settled classification the caller still forwards the first deliverable's kind and compose accepts it
  (`change_type_scope: supplied`). That is precisely what D4(c) mandated, and recipe-derived plans (which
  skip phase-3-outline Steps 4–11 and therefore never settle a plan-level classification) are the live
  population for it. The narrowing is at least now recorded in `decision.log`.

## What could NOT be verified

- The report's red-first claim ("all 8 failed for the right reasons" against stashed pre-fix sources).
  The per-commit SHAs are gone with the squash, so the exact pre-fix intermediate state is not
  reconstructible. **Independently substituted**: the mutation check above drove three of the plan's own
  tests red against a hand-restored pre-fix shape, which establishes the guard is load-bearing even
  though it does not reproduce the run's own observation.
- Every `./pw verify` figure the report states (mypy file counts, plugin-doctor rule count, the
  19613/14 module-test totals). Not re-run — out of proportion to this verification. The
  `manage-execution-manifest` directory was run instead: **869 passed**.
- All PR #1221 metadata: check conclusions, `mergeable_state`, comment/review bodies, reviewer coverage
  1-of-3, and the PR/check timestamps. Not reachable from the tree.
- Every `.plan/`-sourced claim — the originating run's decision log, the five-instance corpus cluster,
  the orchestrator spec. The plan declared these unreachable from this clone and the report labelled them
  NOT re-derivable; that labelling is itself correct.
- Whether `feature_breaking` (or any other non-canonical value) has ever actually been written to a real
  plan's `status.metadata.change_type`. G1 rests on the write path being unvalidated and on the
  repository's own documented assertion that a plan can carry the value — not on an observed instance.
