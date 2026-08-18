# Verification — 230-finalize-retriggers-ci-after-it-has-already-gone-green

**Verified against:** commit `ac06e4fc94782328f87d1395472a72b7e7a8559d`   **Landed as:** PR #1194, commit `2dae85c4afd6e4e7e34b2eeeffe56fac5672179c`   **Verdict:** partially-implemented

## Method

Read `plan.md` and `report-01.md` in full. Located the landed commit
(`git log --oneline --all --grep '#1194'` → `2dae85c4`, a squash-merge) and read its complete
diff: `git diff-tree -r -M --name-status 2dae85c4` shows exactly three paths —
`R100` rename of `230-….md` → `230-…/plan.md`, `A` `report-01.md`, `M`
`marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/source-edit-pushability.md`
(+24 lines, no deletions).

Because the report's line citations are dense and the tree has moved since 2026-08-12, every
citation was checked **twice**: against the tree at `2dae85c4` (`git show 2dae85c4:<path>`) and
against HEAD. Files opened at both revisions: `standards/push.md`, `standards/ci-verify.md`,
`standards/source-edit-pushability.md`, `phase-6-finalize/SKILL.md`,
`workflow/pre-submission-self-review.md`, `workflow/lessons-capture.md`, `workflow/create-pr.md`,
`workflow/sonar-roundtrip.md`, `automatic-review/SKILL.md`, `.claude/skills/finalize-step-era-stamp-fill/SKILL.md`,
`scripts/ci_verify.py`, `plan-marshall/scripts/_invariants.py`,
`manage-findings/scripts/_findings_core.py`, `tools-file-ops/scripts/constants.py`,
`.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py`,
`plan-marshall/workflow/verification-feedback.md`,
`test/plan-marshall/phase-6-finalize/test_ci_verify.py`,
`test/plan-marshall/phase-6-finalize/test_finalize_edge_ordering.py`,
`test/pm-plugin-development/ext-self-review-plan-marshall/test_self_review_defect_regression.py`.

Derivations re-computed at verification time rather than trusted:

- The `mutates_source: true` finalize-step population, swept over all step-declaring docs in
  `marketplace/bundles/**` and `.claude/skills/**`: `finalize-step-sync-baseline`(3),
  `finalize-step-lessons-housekeeping`(4), `finalize-step-simplify`(8),
  `finalize-step-security-audit`(9), `finalize-step-era-stamp-fill`(21), `automatic-review`(30),
  `sonar-roundtrip`(40). With `create-pr` at order 20, the **post-PR** subset is exactly three —
  matching the report's D0 figure.
- `_ACTIONABLE_FINDING_TYPES` re-read in full (`_invariants.py:1246-1253` at HEAD, `:1049-1056` at
  the landed commit): six entries, `triage` absent.
- `FINDING_TYPES` re-read (`constants.py:118-131`): `triage` present at `:123`; `query_findings`
  (`_findings_core.py:334`) loads every entry of `FINDING_TYPES`, so an untyped
  `list --resolution pending --include-qgate` does surface ci-verify's findings.
- `QGATE_PHASES` (`constants.py:52`) = the five phases including `6-finalize`.
- The three registry docs under `automatic-review/standards/` (M = 3) re-counted.

Tests executed:

- `uv run python -m pytest test/pm-plugin-development/ext-self-review-plan-marshall/test_self_review_defect_regression.py -o addopts="" -q` → **8 passed** (the D5(d) coverage the report cites).
- `uv run python -m pytest test/plan-marshall/phase-6-finalize/test_ci_verify.py -o addopts="" -q` → **55 passed** (clean baseline).

Mutation check (the D5(c) fail-closed guard, the plan's declared safety test):
`git diff --quiet -- .../scripts/ci_verify.py` → exit 0 (not concurrently modified); file bytes
saved to the scratchpad; both red-path `'step_marked_done': False` returns (`ci_verify.py:691,733`)
flipped to `True`; the suite went **RED** — `test_no_checks_files_single_ci_no_checks_finding` and
`test_failure_files_one_finding_per_check` both failed on `assert True is False`
(`test_ci_verify.py:475`, `:521`). File restored from the saved bytes; `git diff --quiet` → exit 0.
The guard is real, not vacuous.

## Deliverable-by-deliverable

| # | Deliverable | Done-when condition | Implemented? | As documented? | Correct? | Complete? | Evidence (file:line / symbol / command + result) |
|---|---|---|---|---|---|---|---|
| D0 | GATE: attribute excess CI runs to causes; size the token side | attribution split reported with per-plan evidence; token estimate grounded | **No** (declared "could not look") | Yes — the report says so plainly | n/a | No | No archived CI-manifest corpus in `.plan/` (`ls .plan` here → `execute-script.py`, `local/`, `marshal.json`, `project-architecture/`, `temp/`; `ls .plan/local` → `logs/`, `marshall-state.toon`). Mechanism attribution only. |
| D1 | Stop the post-green push where avoidable; verdict per step | every such step has a recorded verdict | **Yes** | Yes | Yes | Partly | `source-edit-pushability.md:120-142` § "Its post-PR CI run is intrinsic, not a defect to relocate"; the other two verdicts live only in `report-01.md` § D1. Post-PR `mutates_source` population re-derived = exactly the three named. |
| D2 | One loop-back barrier across all finding producers | two producers' findings in one finalize yield one loop-back round | **No** (operator-descoped) | Yes — descope recorded | n/a | No | `phase-6-finalize/SKILL.md:1405` item 7b still runs ci-verify's own loop-back; item 7c (`:1491`) still unions only `pr-comment` ∪ `sonar-issue`. |
| D3 | Fix the self-review phase mismatch | examined-nothing distinguishable from found-nothing | **No** — premise verified **refuted** | Yes | Yes (refutation checked at all four sites) | Yes | Writer at `6-finalize` (`pre-submission-self-review.md:378`, `:341-346`); `_query_pending_qgate_count_aggregated` loops `QGATE_PHASES` (`_invariants.py:1103-1164` @ landed); lessons signal gate loops all five phases (`SKILL.md:741-760` @ landed); `query_findings_unified` loops `QGATE_PHASES` (`_findings_core.py:396-408`); `audit.py:3248` globs `*.jsonl` and `_qc_mechanism` (`:3528-3542`) maps any `qgate-*` file to `self-review`. No `5-execute` reference anywhere in the self-review surfaces. |
| D4 | Scope the self-review to what it can usefully check | scope recorded with expected cost + absolute token figure | **No** | Yes — declared undermined by D3 | n/a | No | Nothing landed on the self-review surface. |
| D5 | Four tests, each seen red first | all four pass, each seen red first | **No** — zero tests added | (a) **misdocumented**; (b)(c)(d) as documented | (c) and (d) guards verified real | No | (a) justification cites `test_finalize_edge_ordering.py`, which derives no such invariant (see below); (b) not added; (c) `test_ci_verify.py:475,521` pre-existing, mutation-confirmed RED; (d) `test_self_review_defect_regression.py` pre-existing, 8 passed. |

**D0.** The gate was never passed. The plan made D0 a GATE precisely because D2's benefit and D4's
ratio hang off it; both were subsequently declined partly *because* D0 was unmeasurable. The
non-delivery is honestly labelled ("could not look", not fabricated), which is the correct
truthful-signals behaviour, but the deliverable is unmet and every hypothesis it was to settle
remains open. The report's reachability claim ("`.plan/` contained only `marshal.json` +
`project-architecture/`") describes a cloud clone I cannot inspect; what I *can* confirm is that no
archived-plan corpus exists in this checkout either, so D0 stays un-re-derivable here.

**D1.** Delivered and accurate. Every factual sub-claim of the landed note was checked: the real PR
number is unavailable before `create-pr` (`create-pr.md:7` → `order: 20`; era-stamp `order: 21`,
`.claude/skills/finalize-step-era-stamp-fill/SKILL.md:10`); the step self-commits and self-pushes in
its own Step 3 (`SKILL.md:123-144` @ landed, `:177-190` @ HEAD); the cross-reference the note asserts,
§ "The discover-after-merge rule", exists (`source-edit-pushability.md:86`). The note's corrected
sentence — "the extra CI run is paid whenever a sentinel is present — not only in a sentinel-only
finalize" — is right: the fill pushes at 21, ahead of every loop-back producer (22/30/40), so no
co-occurring commit exists to ride. Incomplete only in that `push.md`, which the plan's Expected
surface named and which carries the stale companion statement, was left untouched (see Report
accuracy and G1).

**D2.** Not implemented; descoped by a recorded operator decision after a verify-first pass. The
three blocking findings were each independently confirmed against the tree: (1) ci-verify files
`--type triage` (`ci_verify.py:377-395`) and `triage ∉ _ACTIONABLE_FINDING_TYPES`
(`_invariants.py:1246-1253`), so its findings do not block the phase boundary; its fail-closed comes
from `step_marked_done: False` on both red paths (`ci_verify.py:691,733`), which my mutation check
proved is genuinely locked. (2) `ci-verify.md:128-136` does argue triage-CI-first and does say
placing it later "would be wrong". (3) The benefit is indeed blocked behind D0. The mechanical
feasibility claims also hold: all three steps declare `requires: [ci-complete]`
(`ci-verify.md:8`, `automatic-review/SKILL.md:11`, `sonar-roundtrip.md:8`), and the
`finalize-feedback` union query is untyped (`verification-feedback.md:162`).

**D3.** The refutation is correct. I treated it as an asserted absence and tried to break it: no
query anywhere under the self-review surfaces mentions `5-execute`; the only hardcoded phase-file
literals are `qgate-6-finalize.jsonl` inside the *writer* doc itself; every read-back site loops the
full `QGATE_PHASES`. The `no_qgate6` flag name does contain a "6" while its computation
(`audit.py:3322-3324`, `total_findings > 0 and self_total == 0`, with `self_total` from
`_qc_mechanism`'s filename-prefix match) carries no phase filter — exactly as reported.

**D5.** No test was added, so "each verified to FAIL pre-fix" is unsatisfied for all four. (c) and
(d) genuinely rest on real pre-existing guards — I ran both, and mutation-broke (c) to confirm it
discriminates. (a)'s stated justification is factually wrong (G2). (b) is honestly deferred with D2.

## Report accuracy

Checked every citation in `report-01.md` against both the landed revision and HEAD. Two
contradictions, plus one systematic non-defect.

1. **"push.md … lists the two finalize-internal `mutates_source: true` steps that commit during
   finalize: `era-stamp-fill` and `lessons-capture`" (report § Directly-verified plan claims,
   marked ✅).** `push.md:59` (landed) / `:63` (HEAD) does say that, but the tree contradicts the
   substance: `workflow/lessons-capture.md` has declared `order: 991` and **`mutates_source: false`**
   since PR #1080 (`e1ae3814`, 2026-08-03) — nine days before this run. The report verified the
   sentence's presence and reported it as a verified *fact*, and it contradicts the report's own D0
   figure ("post-PR source-mutating steps = **exactly three**", which excludes lessons-capture).
   See G1.
2. **"The ordering invariant (era-stamp 21 < ci-verify 22) already holds and is derived by
   `test_finalize_edge_ordering.py`" (report § D5(a)).** False. That module derives exactly two
   gate-relative edge families — `mutates_source: true` ⇒ before `default:branch-cleanup`, and
   `post_run_review: true` ⇒ after it (`test_finalize_edge_ordering.py:12-16, 52-54`) — and states
   in its own prose that "Most finalize steps (push, create-pr, **ci-verify**, …) declare neither
   marker" (`:187`). Its six tests (`:127,136,146,167,184,201`) contain no reference to `ci-verify`
   and no era-stamp/ci-verify order comparison. A tree-wide sweep of `test/` for
   `era-stamp|era_stamp` finds no ordering assertion either. The era-stamp step is covered by that
   module only as `era-stamp(21) < branch-cleanup(70)`. See G2.
3. **Line-number drift is not a report defect.** Nearly every citation is off by 5–200 lines against
   HEAD (e.g. `_invariants.py:1049` → `:1246`; `pre-submission-self-review.md:334-338` → `:341-350`;
   `test_ci_verify.py:489-490,535-536` → `:475,:521`). Re-checked against the tree the run actually
   saw — for `pre-submission-self-review.md`, the revision **before** PR #1189 landed the same day —
   the citations are exact (`:296` = "TWO disjoint verdicts", `:334-338` = the `qgate add` block;
   `_invariants.py:1049` = `_ACTIONABLE_FINDING_TYPES`; `push.md:115` = the post-PR re-push fast
   path; `test_ci_verify.py:489-490,535-536` = the two `step_marked_done is False` asserts). Not a
   contradiction.

Verified with **no** contradiction found: the three-step post-PR `mutates_source` population; the
item-7c unified barrier and its `producer=finalize-feedback` mode (`SKILL.md:1379-1421` @ landed);
the untyped union query (`verification-feedback.md:162`); `triage ∈ FINDING_TYPES` /
`triage ∉ _ACTIONABLE_FINDING_TYPES`; the ci-verify red-path fail-closed returns and their tests;
`ci-verify.md`'s triage-CI-first rationale; all four D3 read-back sites; `audit.py`'s `*.jsonl` glob
and `no_qgate6` computation; the D5(d) regression module's existence, shape (positive-fires /
matched negative controls / cross-class separation) and green result; the era-stamp ordering,
self-commit and self-push; the `requires: [ci-complete]` declaration on all three wait-region steps;
M = 3 reviewer registry docs; and the run's own build-gate claim (the landed diff contains no `*.py`
path, so the `*.py` predicate was correctly false).

## Out-of-scope compliance

Clean. `git diff-tree -r -M --name-status 2dae85c4` returns exactly three paths and no fourth. No
collateral change: the rebase was not moved, the self-review detector set was untouched, the
self-review surfacing layer (sibling plan `100-self-review-surfacing-integrity`) was not entered, and
no test or script changed.

One judgement call worth naming, not a violation: the D1 verdict was recorded in
`marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/source-edit-pushability.md`,
which ships to consumers, while the era-stamp step it discusses is meta-project-only — the boundary
"Consumer-facing changes from D1" guards against. The note changes no consumer behaviour and sits
under that doc's pre-existing `## Reference implementation` section, which already named era-stamp
(`:109-118`), so it inherits an anchor the plan did not create. Recorded as compliant-with-caveat.

A sequencing instruction in the plan's Notes/Out-of-scope ("do not run them concurrently … prefer
this plan FIRST" w.r.t. `100-self-review-surfacing-integrity`) was not honoured: #1189 landed on the
same day, ahead of #1194, and edited the very file the run was citing. The run had no visibility into
that and no lever over scheduling; noted for the record, not charged against the run.

## Residue carried forward

| Residue declared in report-01.md | Still open at HEAD? | Evidence |
|---|---|---|
| D2 dispatcher change (fold ci-verify into the unified triage barrier) | **Open** | `SKILL.md:1405` item 7b still owns ci-verify's own loop-back continuation; item 7c (`:1491`) still describes the union as the two wait-region producers only. |
| D5(b) test (two producers → one loop-back round) | **Open** | No such test exists; there is no consolidated barrier to assert against. |
| D3/D4 self-review half | **Open as scoped**, and correctly reassigned | D3's premise is refuted in today's tree too (re-verified above), so there is nothing to fix. `doc/plans/code-intelligence-substrate/100-self-review-surfacing-integrity/` exists and its work landed as #1189. |
| D0 quantitative attribution + token sizing | **Open** | No archived CI-manifest corpus in this checkout either (`.plan/local` holds only `logs/` and `marshall-state.toon`). |

## What could NOT be verified

- **The report's reachability finding about its own clone** (`.plan/` holding only `marshal.json`
  and `project-architecture/`; `execute-script.py` absent). That is a property of a cloud VM that no
  longer exists. What is checkable — that the archived corpus is not present in this checkout — is
  consistent with it, but does not confirm it.
- **The 58-runs / 36-plans / 61%-overhead / 16-re-ran figures, the 27-of-39 era-stamp incidence, the
  33/22/19/1 marker counts, and the 709,472-token self-review figure.** All are `.plan/`-corpus
  derived; the plan itself labels them unreachable leads. Neither the plan's motivation nor the
  report's refusal to re-derive them can be checked from the tree.
- **The CI/PR-cycle claims** — `verify / conclusion` success on head `22853c4`, `mergeable_state:
  clean`, the reviewer verdicts and rate-limit notices, auto-merge arming. The feature branch and its
  check runs are gone; the squash-merge is the only durable trace, and it carries no check data.
- **Per-commit trailers on the branch commits** ("every commit carries the `Co-Authored-By: Claude`
  trailer"). Squash-merge discarded the individual commits; only the squash message survives, and it
  does carry `Co-authored-by: Claude`.
- **Whether the pre-PR verification sub-agent ran twice and what it returned.** Only the report
  attests to it. Its one MEDIUM finding is corroborated indirectly: the landed note contains the
  *corrected* wording, not the overclaiming wording the report says was fixed.
