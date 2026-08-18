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
  dict 2517–2540, the argparse block 3215–3231); `scripts/_manifest_decide.py`
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
| D2 | Name the two scopes apart wherever both appear (rename, not alias) | the names differ | yes | yes | yes | yes | Flag renamed `--change-type` → `--plan-change-type` at `manage-execution-manifest.py:3223-3231`, subparser built with `allow_abbrev=False` (3215; the root parser too, 3212) so the old spelling cannot resolve as an abbreviation — a genuine rename, pinned by `test_old_change_type_flag_is_rejected`. Tree sweep for `--change-type` re-run at HEAD over `marketplace/`, `test/` and `.claude/`: 4 hits (`SKILL.md:111`, `manage-execution-manifest.py:3220`, `test_compose_change_type_reconciliation.py:191,219`), all prose, a historical comment or the rejection test — **no live old-spelling invocation**. Distinct locals in `cmd_compose`; scopes named apart at all four sites where both appear — `SKILL.md:111,167,537`, `decision-rules.md:34-49`, `phase-4-plan/SKILL.md:684` — each re-read at HEAD. **Complete: yes** (corrected from `partly` in adversarial review — D2's condition is "wherever **both** appear", and it holds at every such site). **Gap G3** is residue beyond D2, not a shortfall against it: the surfaces that author *one* scope each still spell the field bare |
| D3 | The narrowing decision records which scope it used | the decision carries its input | yes | yes | yes | **partly** | `manage-execution-manifest.py:1873-1881` computes `effective_change_type` / `change_type_scope` and emits a `decision.log` line naming both candidates; `effective_change_type` is what reaches `_apply_simplify_inactive` (1995) and `_decide` (2095) — after the reconciliation block no decision consumes `args.change_type` (its only reads are the enum check at 1812/1817 and the capture at 1848). Result fields at 2527-2530. Documented at `SKILL.md:167` and `decision-rules.md:47`. **Gap G4** (adversarial review): the `change_type_scope_conflict` **refusal** returns at 1851-1867, *before* the emission at 1875, so a refused compose writes no `decision.log` line at all — executed and confirmed (`_emit_decision_log` captured zero calls on the conflict path) — while `decision-rules.md:47` claims the narrowing "can be audited afterward" with no carve-out |
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

**D2 (completeness).** The rename is genuine and the confusion site is fixed. D2's condition is
"wherever **both** appear", and at all four such sites the names now differ — so D2 is **complete**
(this column was corrected from `partly` during adversarial review). Residual, beyond the deliverable:
the two scopes still share the bare spelling in the surfaces that *author* one each —
`phase-3-outline/SKILL.md:437`, `manage-solution-outline/templates/deliverable-template.md:11,59` and
`standards/solution-outline-standard.md:297,462` present the deliverable-scoped field as plain
`change_type`, and `manage-status/SKILL.md:73` plus `standards/status-lifecycle.md:102` present the
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
  (`manage-execution-manifest.py:3226`). Note the by-design residue this leaves — on a plan with **no**
  settled classification the caller still forwards the first deliverable's kind and compose accepts it
  (`change_type_scope: supplied`). That is precisely what D4(c) mandated. **Correction (adversarial
  review): recipe-derived plans are NOT that population.** This document originally named them as the
  live population on the reasoning that they skip phase-3-outline Steps 4–11 and therefore never settle
  a plan-level classification. They do skip those steps (`phase-3-outline/SKILL.md:233`), but the recipe
  branch settles the classification on its own path: `phase-3-outline/standards/outline-workflow-detail.md`
  Step 3 (lines 148-154) runs `manage-status metadata --set --field change_type --value {default_change_type}`
  before jumping to Step 12. A recipe plan therefore reaches compose **with** a settled classification and
  takes the `settled` path. The actual live population for `change_type_scope: supplied` is narrower —
  plans where the heuristic was ambiguous and so self-skipped its persist
  (`_cmd_change_type_heuristic.py:223`) and the LLM `detect-change-type` fallback did not run. The
  narrowing is at least now recorded in `decision.log` on that path — though **not** on the refusal
  path, which is G4.

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

## Adversarial review

**Reviewed by:** an independent agent that did not write this document.

**Checked.** Every `high` gap, every clean-pass deliverable row, and every "swept, clean" claim, plus
each stated figure. Concretely:

- **Re-derived figures.** `git show --stat -M 6f7f9c76` → 14 paths, 698 insertions / 44 deletions,
  including the `R100` plan-directory rename (exact). `pytest test_compose_change_type_reconciliation.py`
  → **9 passed**; `pytest test/plan-marshall/manage-execution-manifest/` → **869 passed** (both exact).
  Both commit SHAs (`5cea6604`, `6f7f9c76`) resolve. The "22 test-namespace files" re-derivation was
  itself re-run: `git grep -l 'change_type=' 6f7f9c76 -- test/plan-marshall/manage-execution-manifest/`
  = **20**, the same query at HEAD = **22** — this document's characterisation of that figure is correct.
- **Executed, not read (G1).** `cmd_compose` was driven against a real `plan_context` with
  `status.metadata.change_type = 'feature_breaking'`, iterating the **whole** input domain — all six
  members of `VALID_CHANGE_TYPES` plus `feature_breaking`. Result: 6/6 `change_type_scope_conflict`,
  `feature_breaking` → `invalid_change_type`. The original entry sampled two of those seven inputs.
- **Executed, not read (G4, new).** `_emit_decision_log` was captured across a conflicting compose;
  the refusal path produced **zero** log lines.
- **Mutation, twice.** `git diff --quiet` on the compose script → exit 0 before starting; bytes copied
  to `$TMPDIR`; (1) minimal mutation pinning `change_type_scope = 'supplied'` at line 1874 → **2 failed
  / 7 passed**, `test_reconciliation_emits_auditable_decision_log_line` green; (2) full pre-fix shape
  (refusal disabled, `effective_change_type` pinned) → **3 failed / 6 passed**, the same test still
  green. Restored from the saved bytes (never `git checkout`/`restore`/`stash`); md5
  `02171cf521815cb7565e74c00a22e1a7` before and after, `git diff --quiet` exit 0 at the end.
- **Sweeps re-run with broader patterns than the originals.** `--change-type` across `marketplace/`,
  `test/` and `.claude/` → the same 4 benign hits. A *semantic* sweep the original did not run —
  `first deliverable|first-deliverable|deliverable's change_type|deliverable's local|deliverable[0]`
  intersected with change-type context — returned 10 hits, every one either the new corrected prose or
  an explicitly past-tense historical note. The `security_class_inactive` staleness sweep was re-run and
  all four sites confirmed, including `manage-execution-manifest.py:1998-2008` where the phrase is split
  across two lines and a naive single-line grep misses it. A **producer** sweep the original did not run
  (`default_change_type` across every in-tree `provides_recipes()`, the heuristic `_KEYWORDS` map, and the
  LLM fallback vocabulary) established that no automated producer can write a non-canonical value —
  recorded in G1 as the reachability counter-evidence.
- **Citations re-derived at the commit each claim is about.** At HEAD: 1812, 1848-1867, 1873-1881, 1995,
  2095, 2527-2530, 3212/3215/3223-3231; `_manifest_decide.py:340-376`; `_manifest_core.py:65-72`;
  `_status_query.py:51-65` and `cmd_metadata:271-319`; `_cmd_planning_lane.py:104,785`;
  `_cmd_classification_validate.py:277`; `_cmd_change_type_heuristic.py:223,230`;
  `plan-efficiency.md:142,144`; `decision-rules.md:34-49`; `SKILL.md:111,167,537`;
  `phase-4-plan/SKILL.md:684`; `phase-3-outline/SKILL.md:437`; `manage-status/SKILL.md:73,957`;
  `status-lifecycle.md:102`; `check-manifest-consistency.py:141-163`; `check-routing-decisions.py:199`.
  At `6f7f9c76^`: argparse `2707`, `_decide` `1974`, simplify pre-filter `1873-1875`,
  FIRST-DELIVERABLE-WINS comment `1879-1882`, `manage-solution-outline.py:201,206-217`.
- **The "exactly one live caller" claim** was independently checked at the source rather than at the
  sweep: `phase-1-init` references `manage-execution-manifest` exactly twice (`SKILL.md:903` `lanes
  preview`, `:945` prose) and never invokes `compose`. Upheld.

**Not re-checked.** The `./pw verify` figures (mypy 398/734, plugin-doctor 36 rules, 19613/14) — not
re-run, as before. All PR #1221 metadata. Every `.plan/`-sourced claim. Whether any real plan has ever
carried a non-canonical `status.metadata.change_type` (G1's precondition remains unobserved; its
reachability argument is now stated explicitly in G1 rather than left implicit). The Method section's
approximate block ranges (`1955-2010`, `343-370`, Step 7b `670-760`) were not line-checked — they are
navigational, not load-bearing.

| Item | Original claim | Verdict | Evidence |
|---|---|---|---|
| G1 | `high` — a settled value outside `VALID_CHANGE_TYPES` has no accepting compose input | **upheld, evidence strengthened** | Re-executed over the full seven-value input domain (6/6 conflict + 1 invalid), not the two-value sample originally cited. Severity challenged on reachability — no automated in-tree producer emits a non-canonical value (three sweeps) — and upheld at `high` because `manage-status/SKILL.md:957` documents `feature_breaking` as live at exactly the blocked key. Both the sweep and the counter-argument are now recorded in G1 |
| G2 | `medium` — the decision-log test cannot distinguish the two scopes | **upheld** | Reproduced independently with a *minimal* single-line mutation (2 failed / 7 passed, the named test green) as well as the full pre-fix shape (3 failed / 6 passed, still green). Severity re-argued: the rubric's "a guard that passes against the defect it names" points at `high`, but `test_narrowing_decision_records_its_scope_and_input` genuinely covers D4(d) and went red under **both** mutations, so no false coverage signal escapes this one test name. `medium` stands. Line range tightened to 172-186 |
| G3 | `low` — five authoring surfaces spell both scopes bare | **upheld, re-scoped** | All five citations re-derived exactly at HEAD. But D2's condition is "wherever **both** appear", and it holds at all four such sites — so this is residue beyond the deliverable, not a shortfall against it. The D2 **Complete** column is corrected from `partly` to `yes`; the gap itself stands at `low` |
| G4 | — (newly found) | **added, `medium`** | The `change_type_scope_conflict` refusal returns at 1851-1867, before the `_emit_decision_log` call at 1875. Executed: zero decision-log lines on the conflict path. `decision-rules.md:47` and `SKILL.md:167` both claim the narrowing "can be audited afterward" with no carve-out, and `check-manifest-consistency.py:141-163` harvests exactly those lines — so the refusal is invisible to the retrospective auditor |
| D0 row | clean pass | **upheld** | Every symbol in the published population re-confirmed at HEAD or at `6f7f9c76^`. A `--include=*.py` sweep for readers/writers of `change_type` returned exactly the sites the report classified, in both directions |
| D3 row | clean pass | **downgraded to `partly` (complete)** | The accepting paths do carry their input, but the refusal path records nothing — G4 |
| "no live `--change-type` invocation" | swept, clean | **upheld** | Sweep re-run over a wider path set; same 4 benign hits. A broader *semantic* sweep for restatements of first-deliverable forwarding also came back clean |
| "staleness sweep, 4 sites" | swept, clean | **upheld** | All four confirmed, including the one a single-line grep misses |
| "recipe-derived plans never settle a classification" (Residue) | stated as fact | **refuted** | `outline-workflow-detail.md:148-154` — the recipe branch runs `metadata --set --field change_type --value {default_change_type}` before jumping to Step 12. Recipe plans reach compose *with* a settled classification |
| "`args.change_type` is read exactly once, at 1848" | stated as fact | **corrected** | It is also read at 1812 and 1817 by the enum check. The intended claim — that no *decision* consumes it after 1848 — is true and is now what the row says |
| Verdict `implemented-with-gaps` | headline | **upheld** | All five deliverables are implemented; three carry correctness/completeness gaps. Nothing is unimplemented, so `partially-implemented` would be wrong |

**Documents corrected.** *gaps.md*: G1 gained a whole-domain execution result and an explicit
reachability sweep (with the counter-evidence, so the severity can be re-opened on evidence);
G2's line range tightened and its mutation evidence replaced with an independently re-run pair;
G3 re-scoped from "D2 incomplete" to "residue beyond D2" with all five citations re-derived; **G4
added**; open items 3 → 4; a `## Refuted during adversarial review` section records that nothing was
refuted and why G3's reconsideration changed a framing rather than a verdict. *verification.md*: the
D2 row's **Complete** corrected `partly` → `yes`; the D3 row's **Complete** corrected `yes` →
`partly` for G4; the false "recipe-derived plans never settle" claim in Residue replaced with the
re-derived mechanism and the corrected live population; the "read exactly once" claim corrected;
argparse line numbers corrected (3222-3230 → 3223-3231, 3214 → 3215, 3225 → 3226, result-dict range
2521-2534 → 2517-2540); the D2 sweep row given its concrete hit list.

**Residual doubt.** Three things a third reviewer should open first. (1) **G1's severity turns entirely
on a reachability argument, not on an instance** — if a real plan is ever found carrying a
non-canonical `status.metadata.change_type`, G1 is unambiguously `high` and urgent; if the
`feature_breaking` documentation at `manage-status/SKILL.md:957` and `_cmd_planning_lane.py:104` is
itself stale (the router scores a value the canonical vocabulary does not define — a discrepancy
`plan-efficiency.md:144` names and explicitly leaves unowned), then the right fix may be to retire
`feature_breaking` rather than to soften compose. That vocabulary split is unowned by any plan and is
the largest loose thread here. (2) **`phase-4-plan/SKILL.md`'s "Idempotent firm-signal re-compose"
paragraph states that "phase-1-init runs the FIRST, provisional compose"**, which is false at HEAD —
phase-1-init runs `lanes preview`, never `compose`. It predates this plan and is out of its scope, but
it is a live stale mechanism claim in a file this plan edited. (3) **`manage-solution-outline.py:286-296`
validates a *deliverable's* `change_type` against the same six canonical values**, so
`breaking-refactor-task-split.md:13,25` — which keys its rule on a deliverable whose `change_type` is
`feature_breaking` — describes a state the outline validator rejects. Also unowned.
