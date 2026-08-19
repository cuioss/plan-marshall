# Verification — 050-coverage-shortfall-disclosed-against-the-roster-not-the-required-set

**Landed as:** PR #1170, squash commit `b286928c`
**Verdict:** verified-with-gaps

Every deliverable produced the outcome its *Outcome* clause names, and out-of-scope compliance is
clean. One published figure in the run report is wrong (a stale suite count, see claim 11); no claim
about what the run created is false. But the one piece of code the plan actually shipped reproduces
the plan's own archetype in four places: its `measured` grade is satisfiable by META records alone,
its discriminating input has no producer anywhere in the tree so `clean` is unreachable in
production, its `clean` branch is roster-denominated rather than required-denominated, and its
`vacuous` grade asserts *"no reviewer roster configured"* from an input the caller may simply have
omitted.

## Method

Read in full: `plan.md`, `report-01.md`, the landed diff (`git show b286928c --name-status
--find-renames`), and the current tree.

**Tree state.** The source tree is byte-identical to `61a43e53`: `git diff --name-status
61a43e53..HEAD` returns only additions under `doc/plans/review-apparatus/*/`. Every line citation
below resolves against HEAD.

Files read in the current tree:

- `.claude/skills/finalize-step-review-retrospective/scripts/review_retrospective.py` (all 490 lines)
- `.claude/skills/finalize-step-review-retrospective/SKILL.md` (§ Step 1, Step 2, Step 3, Step 4,
  Step 5, Error Handling, Canonical invocations)
- `test/plan-marshall/finalize-step-review-retrospective/test_review_retrospective.py`
  (module docstring `:4-34`; `:760-914` — the whole `comparison` section, banner to EOF)
- `.claude/skills/cloud-plan-lane/SKILL.md` (§ Step 7 participation record `:1182-1260`, § Step 8
  condition 5 `:1436-1452`, § Report Reviewer participation `:1736-1750`)
- `marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md`
  (§ The counting rule `:508-535`, § the delta's published populations `:627`, Consumers table
  `:660-668`)
- `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py`
  (module docstring `:105-112`, `compose_review_state_summary` `:586-611`, the required-subset gating
  `:851-865`, the `check_completeness` return `:902-925`)
- `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_gate_delta.py`
  (`assess` `:300-350`)
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md`
  (the barrier's config read `:721-737`, the predicate `:860-871`, the clean path `:982`)
- `.gitignore` `:45-47`, `.plan/marshal.json`
  (`plan.phase-6-finalize.steps["plan-marshall:automatic-review"]`)

Searches run (each cited at the finding it backs):

- `git log --oneline b286928c..HEAD -- <path>` on the aggregator (**1** commit, `622f4484` / #1239),
  on the whole `finalize-step-review-retrospective/` directory (**1**, the same), on the test module
  (**2**, `6514cf24` / #1290 and `622f4484`), and on `cloud-plan-lane/SKILL.md` (**27**, none on this
  axis); `git log --oneline -S'unreadable'` / `-S'Reopens?'` on that last file
- `grep -rn "nothing to compare"` across `*.md`/`*.py`/`*.json` excluding `doc/` and `.git`
- `grep -rln "review_retrospective\|review-retrospective"` repo-wide (consumer sweep)
- `grep -rn "reviewed_reviewers\|reviewed-reviewers"` repo-wide (producer sweep)
- `grep -rn "bot_lists_provenance"` across `marketplace/`, `.claude/`, `test/`, `.plan/marshal.json`
- `grep -rn "N-of-M\|Review coverage\|reviewer_coverage"` across `.claude/` and `marketplace/`
  (reviewer-coverage emitter sweep — the bare `"N of M"` pattern alone does **not** find the
  `:1442` worked example, so it is not sufficient on its own)
- `grep -n "required_bots\|optional_bots\|marshal.json"` on `cloud-plan-lane/SKILL.md`
- `grep -n "rr.main\|main(\[\|argv\|sys.argv"` in the test module (CLI-level test sweep — no matches)
- `grep -n "reviewed_author_logins\|enabled_author_logins"` in the retrospective SKILL
- `grep -c "^def test_"` on the test file at `b286928c^`, `b286928c`, and HEAD (30 / 40 / 43), plus a
  name-level `diff` of the three lists

Executed (no repository file left modified):

- `uv run python -m pytest test/plan-marshall/finalize-step-review-retrospective/test_review_retrospective.py
  -o addopts="" -q` → **43 passed**
- The pre-fix module extracted to a scratchpad (`git show b286928c^:…/review_retrospective.py`) and
  probed: `hasattr(rr,'_grade_comparison')` False, `hasattr(rr,'COMPARISON_MEASURED')` False,
  `'comparison' in aggregate([])` False, and `aggregate(..., reviewed_reviewers=[...])` raises
  `TypeError: aggregate() got an unexpected keyword argument 'reviewed_reviewers'`. This
  independently substantiates D4's fail-pre-fix claim, which the report established only by reasoning.
- A META-only store probed against the current module:
  `aggregate([{'author':'coderabbitai','kind':'issue_comment'}], enabled_reviewers=[…],
  reviewed_reviewers=[])` → `comparison: measured`, `total_findings: 1`, every reviewer
  `actionable_count: 0`.
- The pure helper probed directly: `_grade_comparison(0, {'req','opt'}, {'opt'})` → `clean`;
  `_grade_comparison(0, set(), {'x'})` → `vacuous`; `_grade_comparison(0, {'a'}, set())` →
  `indeterminate`; `aggregate([], enabled_reviewers=None)` → `vacuous`.
- **A mutation run against the legend test** (source snapshotted to `$TMPDIR/adv-050-mutsweep/` and
  restored from that snapshot in a `finally`, never by `git checkout`): a fifth constant
  `COMPARISON_FIFTH` plus a fifth `_grade_comparison` return branch, with **no** legend entry added.
  The whole module suite still reported **43 passed**. See G11.

## Deliverables

| # | *Outcome* (plan) | Report claim | Ground truth in the tree | Verdict |
|---|---|---|---|---|
| D1 | "a **proposal** with the exact replacement text for the shortfall condition and the participation-record section" | Proposals D1a (Step 7 record) and D1b (Step 8 cond 4) recorded with exact replacement text; `cloud-plan-lane/SKILL.md` not edited | Both proposals present in `report-01.md`; `cloud-plan-lane/SKILL.md` untouched by `b286928c`. **But the D1a replacement span has since acquired two subsections** the proposal does not carry | met, anchors now stale |
| D2 (lane half) | "proposal text for the lane surfaces" | D2a: every ratio names its population; absence-of-siblings verified whole-repo | The absence claim's load-bearing half re-verified true today (3 lane ratio sites, all in `cloud-plan-lane`). Exact replacement text exists for 2 of the 3 sites; the report template is described, not replaced | partially met |
| D2 (instrument) | "a real code change for the instrument"; grade `indeterminate`, "never `done` with a benign summary" | `comparison` grade + `_grade_comparison` + `--reviewed-reviewers` landed | All symbols present at HEAD and unchanged by the one later commit touching the file. **The grade is unreachable at `clean`, satisfiable by META at `measured`, benign-by-default at `vacuous`, and absent from the non-zero-findings display-detail and the persisted artifact** | landed, materially incomplete |
| D3 | "the read mechanism named and settled, plus proposal text" | Executor-free read via git-tracked `.plan/marshal.json`; vacuous rendering proposed | `.gitignore:45-47` negation confirmed, `git check-ignore` exits 1, values are exactly as reported. Proposal text present | met |
| D4 | "tests, each verified to FAIL pre-fix, each proving discrimination by mutation" — four named cases | 8 grade tests + 2 regression tests landed; four lane cases staged as cold-read scenarios | 10 tests present and passing; all 10 provably fail pre-fix (probe above). The four *lane* cases are a 4-row scenario table, not tests — permitted by the plan's ⚠ carve-out | met, with a weak legend test |

### D1 — the verdict distinguishes required from optional

**Proposal recorded, correctly, and the file was not edited.** `git show b286928c --name-status`
lists six paths, none of them `.claude/skills/cloud-plan-lane/SKILL.md`. The plan's ⛔ PROPOSAL-ONLY
constraint is honoured. CONFIRMED.

The defect the proposal targets is **still live at HEAD**, exactly as D1 describes:

- `.claude/skills/cloud-plan-lane/SKILL.md:1206` — the `reviewed` verdict still folds in
  "(or an explicit "nothing to report" over the diff)", i.e. `participated_but_empty` still reads as
  `reviewed`.
- `:1439` — "When **any** expected reviewer's verdict is not `reviewed`, state the shortfall" —
  roster-wide, no `required_bots`/`optional_bots` anywhere in the condition.
- `:1442` — the worked example is still the bare `"Review coverage: 1 of 3 …"`.
- And the contract reads neither list **anywhere**: `grep -n "required_bots\|optional_bots\|marshal.json"`
  over the whole of `cloud-plan-lane/SKILL.md` returns exactly one hit, `:1591`, which is a statement
  about what `.plan/` contained on one run — not a config read.

CONFIRMED. This is the intended state (proposal, not edit), not a regression.

**Anchor staleness — CONFIRMED and material.** D1a instructs: *"Replace from '**Record a verdict per
reviewer, derived from the stored comment bodies**' through '…not merely unmentioned.'"* Both anchors
still exist — the opening at `:1199`, the closing at `:1259` — but the span between them has grown
two subsections that landed after `b286928c`:

- the `unreadable` verdict row (`:1209`) plus its ⛔ block (`:1211`) and the merge-gate paragraph at
  `:1226` (`git log -S'unreadable'` → `b814d2fd`, PR #1281);
- the whole `Reopens?` subsection with its table at `:1241-1243` (`git log -S'Reopens?'` →
  `dc188529`, PR #1244).

The D1a replacement text carries a four-row verdict table (`reviewed` / `reviewed-empty` /
`rate-limited` / `silent`) with no `unreadable` row and no `Reopens?` column. Applied verbatim today
it would **delete** both later landings. See G4.

### D2 — every emitted coverage ratio names its denominator; the instrument grades `indeterminate`

**The absence claim, re-derived and split in two.** The report asserts two things at once:
`cloud-plan-lane/SKILL.md` is (a) the sole emitter whose denominator is the full registry roster, and
(b) "the **only** emitter of an 'N of M' reviewer-coverage ratio at all".

- **(a) holds.** `grep -rn "N-of-M\|Review coverage\|reviewer_coverage"` over `.claude/` and
  `marketplace/` returns three lane ratio sites — `:1258`, `:1442`, `:1746` — and no other
  roster-denominated one. CONFIRMED at HEAD.
- **(b) does not.** `review_gate_delta.assess` emits `reviewer_coverage` as
  `f'{len(covered)}/{len(roster)}'` (`review_gate_delta.py:313`, payload key at `:345`) — literally an
  N-of-M reviewer-coverage ratio. It is **not** a sibling defect: it publishes `enabled_bots` and
  `reviewed_bots` beside the figure (`:346-347`), which `bot-participation-contract.md:627` states as
  a rule ("Every figure publishes `reviewer_coverage`, `enabled_bots`, `reviewed_bots`"), so its
  denominator is named and D2's requirement is met there. The report's *finding* survives; its
  universal phrasing does not. See claim 6.

**Only two of the three lane sites get replacement text.** D1a covers `:1258` (it ends inside the
replaced span) and D1b covers `:1439-1444`. The third — the § Report **Reviewer participation**
template at `:1736-1746`, whose closing line is *"State the coverage as N-of-M"* — is addressed by one
clause of prose ("gains the required/optional column and the two-ratio coverage line") with no column
layout and no replacement text. See G5.

**The instrument change is real and survives.** `_grade_comparison` (`review_retrospective.py:108-153`),
the four `COMPARISON_*` constants (`:102-105`), the `comparison` / `reviewed_reviewers` /
`comparison_states` payload keys (`:360-391`), and the `--reviewed-reviewers` flag (`:449-465`) are all
present at HEAD. Exactly **one** commit has touched that file since `b286928c` (`622f4484`, #1239);
`git diff b286928c HEAD -- <that file> | grep "comparison\|grade"` yields a single line, and it is a
hunk header — no line of the grade changed. CONFIRMED.

**Four defects in it.** See § Correctness review — G1 (`measured` from META alone), G2 (`clean`
unreachable), G3 (`clean` roster-denominated), G8 (`vacuous` from an unsupplied roster).

**`--outcome` stays `done`.** `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_mark_step.py:81`
— `VALID_OUTCOMES = ('done', 'skipped', 'loop_back', 'failed')`. The report's justification is
CONFIRMED and the plan's "never `done` with a benign summary" is satisfied *on the zero-record path*
only; on the records-but-no-actionable path the benign summary survives (G1).

### D3 — the config read is resolved, not assumed

**Settled, and the finding is correct.** `.gitignore:45-47`:

```gitignore
.plan/*
!.plan/marshal.json
!.plan/project-architecture/
```

`git check-ignore -v .plan/marshal.json` exits 1; `git ls-files .plan/` lists `marshal.json`. Reading
`plan.phase-6-finalize.steps["plan-marshall:automatic-review"]` gives `required_bots: "pr-agent"`,
`optional_bots: "coderabbit,sourcery"`, `bot_lists_provenance: "answered"` — exactly the values the
report publishes. CONFIRMED.

**The vacuous rendering is proposed for the lane and absent from the code.**
`review_retrospective.py` never reads `bot_lists_provenance`. The repo-wide sweep returns
`.plan/marshal.json` itself, `manage-config` (SKILL + `standards/data-model.md`), `marshall-steward`
(SKILL + `scripts/upgrade.py`), `tools-integration-ci/scripts/ci_base.py:1410`,
`phase-6-finalize/workflow/create-pr.md:253-257`, and four test modules — and **nothing** in the
retrospective or in `review_completeness.py`. So an empty roster grades `vacuous` — "nothing was
expected to compare" — whether the operator answered *none* or was never asked. D3's ⛔ requires those
two be distinct and the second treated as **unestablished**. See G7.

The distinction is not novel here: `create-pr.md:256-257` already splits exactly this pair, applying
`skip-bot-review` on an empty-plus-`answered`/`migrated` posture and refusing to on an empty-plus-
`never_asked` one ("**A never-asked posture does NOT mean 'skip review'** … Fail toward being
reviewed"). The house pattern exists; the retrospective does not consume it.

**And the in-lifecycle site was not swept.**
`review_completeness.py:110-112` states in as many words: *"An EMPTY `required_bots` is a valid
configured state — the quorum is vacuously satisfied and `participation_complete` is `true`."* The
returned envelope (`:902-925`) carries no vacuous marker and no provenance. `review_state_summary`
does not cover the case: `compose_review_state_summary` returns `''` only when `bot_states` is
**wholly** empty (`:597-600`), and `bot_states` spans required ∪ optional — so an empty
`required_bots` beside a populated `optional_bots` yields a non-empty summary *and* a vacuously true
`participation_complete`. `branch-cleanup.md:982` gates the clean path on that boolean. That is the
vacuous-authority archetype in the in-lifecycle mechanism the report describes as "correct on this
axis". See G13.

### D4 — tests

**All ten exist, all pass, all provably fail pre-fix.** Present at
`test/plan-marshall/finalize-step-review-retrospective/test_review_retrospective.py`:
`test_comparison_measured_when_findings_exist` (:775),
`test_comparison_clean_when_a_reviewer_reviewed_and_found_nothing` (:785),
`test_comparison_indeterminate_when_no_reviewer_produced_content` (:798),
`test_comparison_vacuous_when_no_roster_configured` (:814),
`test_comparison_fails_closed_to_indeterminate_without_the_reviewed_signal` (:822),
`test_comparison_clean_vs_indeterminate_discriminate_on_identical_zero_store` (:835),
`test_comparison_states_legend_matches_the_four_graded_constants` (:862),
`test_grade_comparison_helper_is_directly_unit_testable` (:878),
`test_comparison_clean_requires_an_ENABLED_reviewer_not_any_reviewer` (:886),
`test_comparison_empty_roster_is_vacuous_even_with_an_off_roster_reviewer` (:905).
No named test is missing. CONFIRMED by grep, by a name-level `diff` of the pre-fix and post-fix test
lists (exactly these ten added, nothing removed), and by a passing run (43 passed).

Pre-fix failure independently CONFIRMED by probing the extracted `b286928c^` module: the kwarg raises
`TypeError`, and `comparison` / `reviewed_reviewers` / `COMPARISON_*` / `_grade_comparison` do not
exist. Every assertion in the ten tests touches at least one of those.

The discrimination test at `:835` is a genuine mutation proof: it asserts `clean != indeterminate` over
an identical empty store and identical roster, so any constant-returning mutant fails. CONFIRMED by
reading the assertions.

The legend test at `:862` is not — proved by mutation, see G11. And
`test_comparison_vacuous_when_no_roster_configured` (`:814`) *pins the conflation* rather than
guarding against it: it passes `enabled_reviewers=[]` and calls that "no roster configured", which is
the same argument value an omitted flag produces. See G8.

## Report-claim audit

| # | Claim in `report-01.md` | Verdict | Evidence |
|---|---|---|---|
| 1 | "the two `cloud-plan-lane/SKILL.md` deliverables are `proposal recorded`… `cloud-plan-lane/SKILL.md` was NOT edited" | **ACCURATE** | `git show b286928c --name-status` lists six paths, none of them that file |
| 2 | Roster is 3 reviewers; required = `{pr-agent}`, optional = `{coderabbit, sourcery}`, provenance `answered` | **ACCURATE** | `.plan/marshal.json` read directly — the three values match verbatim |
| 3 | "`.plan/marshal.json` is **git-tracked**… `git check-ignore` exits 1; `git ls-files` lists it" | **ACCURATE** | Both re-run; `.gitignore:45-47` carries the negation |
| 4 | "the counting rule already **landed** — `bot-participation-contract.md` § 'The counting rule' (lines 446-472), owned by plan 040's D0" | **ACCURATE** | `git show b286928c:…/bot-participation-contract.md \| grep -n "^## The counting rule"` → 446. At HEAD it is line 508 (the section moved, not the content) |
| 5 | "`mark-step-done`'s `VALID_OUTCOMES = ('done','skipped','loop_back','failed')` has **no `indeterminate`** member" | **ACCURATE** | `_cmd_mark_step.py:81` |
| 6 | "`cloud-plan-lane`'s disclosure is the **only** emitter of a roster-denominated reviewer-coverage figure, and the **only** emitter of an 'N of M' reviewer-coverage ratio at all" | **ACCURATE in its first clause; OVERSTATED in its second** | The roster-denominated half re-verified true at HEAD (3 sites, all in that file). The universal half is refuted: `review_gate_delta.py:313,345` emits `reviewer_coverage` as `covered/roster`. It publishes its populations beside it (`:346-347`, the rule at `bot-participation-contract.md:627`), so it is **not** a defect and owes no gap — but the report's absence claim reaches further than its evidence |
| 7 | "the only '0 pr-comment findings — nothing to compare' production surfaces were the aggregator and its SKILL.md, both rewritten" | **ACCURATE** | `grep -rn "nothing to compare"` — no production surface carries the retrospective's old string; remaining hits are unrelated domains (`marshall-steward`, `manage-metrics`, `plan-retrospective`, …) and the new tests' own comments |
| 8 | "`--reviewed-reviewers` is passed **bare**… the zero-findings grade **fails closed to `indeterminate`**" | **ACCURATE** | `SKILL.md:155`, `:225-231`; `_grade_comparison:151-153` |
| 9 | "the aggregator now emits… `_grade_comparison(total_findings, enabled, reviewed)`" with the four-grade table | **ACCURATE but incomplete** | The table's `measured` row says "≥1 finding"; the code passes `len(records)`, which counts META records — the table never says *actionable* and the code does not filter (G1) |
| 10 | "Every assertion on `comparison` **fails pre-fix**… confirmed by direct reasoning" | **ACCURATE, and now independently confirmed** | Pre-fix module probe: `TypeError` on the kwarg; none of the symbols exist |
| 11 | "the `finalize-step-review-retrospective` suite is **38 passed** — including all 8 new `comparison`-grade tests" | **INACCURATE — stale, not invented** | `grep -c "^def test_"` → 30 at `b286928c^`, **40** at `b286928c`; a name-level `diff` shows exactly **ten** tests added, all `comparison`-grade. 38/eight is the pre-review-fix measurement carried forward; the report itself names the two extra regression tests in § Findings (G16) |
| 12 | "The in-lifecycle mechanism… is **correct** on this axis — it reads `required_bots`/`optional_bots`, gates `participation_complete` on the **required set only**" | **ACCURATE as scoped, OVERSTATED as read** | `check_completeness:851-865` does gate on the required subset. But on D3's vacuous axis the same function returns `participation_complete: true` for an empty `required_bots` with no marker (`review_completeness.py:110-112`) — the archetype D3 names, left unrecorded (G13) |
| 13 | CodeRabbit finding #1 "**CONFIRMED real bug. Fixed** — `_grade_comparison` now checks `not enabled_reviewers → vacuous` first, then `enabled ∩ reviewed → clean`" | **ACCURATE** | `review_retrospective.py:149-152` in that exact order; two named regression tests at `:886` and `:905` |
| 14 | CodeRabbit finding #2 "the legend now keys off the constants" | **ACCURATE** | `:386-391` uses `COMPARISON_*` as dict keys. Side effect: it weakened the legend test (G11) |
| 15 | CodeRabbit finding #3 resolution: "the SKILL.md now states plainly that no persisted handoff exists" | **ACCURATE** | `SKILL.md:151-164` says exactly that |
| 16 | "the counting-rule Consumers table now names both inputs and the `comparison` grade" | **ACCURATE** | `bot-participation-contract.md:664` names `--enabled-reviewers`, `--reviewed-reviewers`, and the four grades |
| 17 | "`./pw verify` → `=== verify: SUCCESS ===`, `19052 passed, 14 skipped`" | **UNVERIFIABLE** | No CI record reachable from this checkout; the module suite does pass (43) |
| 18 | "CI: all required checks green on head `677c1c2`… `mergeStateStatus: clean`"; "3 fixed in `18f7814`" | **UNVERIFIABLE** | Squash-merged; the branch's intermediate commits are not in this repository's history |
| 19 | "`cuioss-review-bot` posted… 'No major issues detected' with zero findings"; "`sourcery-ai` returned only a refusal" | **UNVERIFIABLE** | PR comment bodies are not readable from the checkout. Note a mild internal tension: the CI list records `Sourcery review` as *skipped*, while the participation table records a posted rate-limit notice |
| 20 | "the emission-site sweep read 14 files closely and grepped 100+" | **UNVERIFIABLE** | A sub-agent's activity leaves no artifact in the tree. Its *conclusion* is re-derived above (claim 6); the effort figures are not checkable, and "100+" is a floor rather than a count |
| 21 | "Four recomputed landings each met required quorum at 1 of 1 — **Not corroborable here**" | **ACCURATE** (a correctly-refused inheritance) | The plan's ⛔ forbade inheriting it; the report declines and says why |
| 22 | "The disclosure has fired a false shortfall on a real run — **No instance found**… this run carries **no** incident count" | **ACCURATE** | Stated exactly as the plan's UNSETTLED label demands |
| 23 | Contract check row "6 Verification sub-agent — **Done** — one finding… ran the plan's central cold read" | **OVERSTATED** | The plan's ⭐ demands three answers *reported verbatim*. The report gives a paraphrase of Q2 and of the empty-`required_bots` read; Q1 ("was the diff reviewed?") and Q3 ("how many reviewers were required, and how do I know?") have no reported answers at all (`grep -in "cold read\|cold-read\|verbatim"` over the report — 8 hits, none carrying a verbatim answer) (G12) |

**One claim in `report-01.md` is inaccurate** — the suite figure at claim 11, stale rather than
invented — and two are overstated (claims 6 and 12) at the level of reach rather than substance.
Every named symbol, test, flag, and doc section the report claims to have created exists in the tree
at HEAD.

## Correctness review

### `measured` is satisfiable by META records alone — and that run also skips the graded exit

CONFIRMED by execution, and the sharpest defect in what landed.

`review_retrospective.py:360-364` grades on the **raw store size**:

```python
comparison = _grade_comparison(
    len(records),
    set(enabled_reviewers or []),
    set(reviewed_reviewers or []),
)
```

`_grade_comparison:147-148` returns `measured` — *"findings exist — the review-quality comparison was
performed"* (`:387`) — on `total_findings > 0`. But the module's own contract is that META records
"never inflate `actionable_count`" (`:234-237`) and "cannot dilute the ratio" (`:41-42`). A store
holding only CodeRabbit's walkthrough `issue_comment` and its status-summary `review_body` is a store
with **zero actionable findings** and every reviewer's `pct_resolved_as_fixed` at `None` — nothing to
compare — and it grades `measured`. Executed:

```
aggregate([{'author':'coderabbitai','kind':'issue_comment'}], enabled_reviewers=[…], reviewed_reviewers=[])
→ comparison: measured, total_findings: 1, actionable per reviewer: [('coderabbitai',0,1), ('cuioss-review-bot',0,0)]
```

That shape is not hypothetical — the test module's own docstring (`:32-33`) pins "the full CodeRabbit
review shape (5 inline + 1 status-summary `review_body` + 1 walkthrough `issue_comment`)", so META
records demonstrably reach the store.

It compounds: `SKILL.md:134` gates the graded exit on `filtered_count is 0`, so a META-only store takes
the ordinary path and lands at `SKILL.md:443`, whose `--display-detail` is still the unchanged bare
`"{N} reviewers compared, {M} actionable comments"` — a benign no-op summary, ungraded, with no
population named. The plan's ⛔ *"It must not mark itself complete on a comparison it could not
perform"* is enforced on the empty store and not on its nearest neighbour. See G1.

### `clean` is unreachable in production

CONFIRMED. `grep -rn "reviewed_reviewers\|reviewed-reviewers"` over the whole repo returns hits
**only** in: the aggregator, its SKILL, its test, the contract's Consumers row (`:664`), two
`__pycache__` artefacts, the git-ignored generated executor's flag-surface cache
(`.plan/execute-script.py:382`), and a plugin-doctor help cache. **No producer exists** — nothing
computes or writes the set. `SKILL.md:151-164` states this outright and instructs the flag be passed
bare, and `SKILL.md:225-231` repeats it for Step 2.

Consequence: at every real invocation `reviewed_reviewers` is empty, so `_grade_comparison:151` can
never be true and `clean` can never be emitted. The deployed grade is a three-valued function of
`(len(records), roster)`. D2's requirement — *"it must distinguish reviewers ran and found nothing from
no reviewer produced content"* — is met by the pure function and **not** met by the shipped pipeline:
in production those two facts still render identically, as `indeterminate`. The report records this as
residue, so it is disclosed rather than hidden; it is nevertheless the deliverable's substance. See G2.

Second-order, stated precisely: `indeterminate` fires on *every* zero-record run with a configured
roster, including genuinely reviewed-clean ones. That is **not** a false alarm — `indeterminate` says
"could not be established", which is true when no substantiating input exists, and fail-closed is the
right default. It is an **information-content** problem: a grade that takes one value over the whole
population it is computed on distinguishes nothing, so the discrimination D2 bought exists only in the
unit tests. The remedy is the missing producer (G2), not a looser default.

### `clean` is roster-denominated, not required-denominated

CONFIRMED as a property of the code, **latent** as a production defect. `SKILL.md:209-212` derives
`--enabled-reviewers` from `required_bots ∪ optional_bots`, and `_grade_comparison:151` earns `clean`
on **any** member of that union intersecting the reviewed set. Executed:
`_grade_comparison(0, {'req','opt'}, {'opt'})` → `clean`. So a run where the *required* reviewer
produced nothing and an *optional* reviewer reviewed-and-found-nothing grades `clean` — "reviewers ran
and found nothing" — hiding the required-side collapse. That is the plan's own false-clean scenario
("the required reviewer resolved to `participated_but_empty` while an optional reviewer produced 16
records") reproduced inside the only code the plan shipped.

**The unstated precondition:** this cannot occur today, because `reviewed_reviewers` is always empty
(G2) and `clean` is therefore unreachable. It becomes live the moment the producer G2 asks for is
built — which is exactly why the two must be fixed in one change rather than in sequence. See G3.

The counter-argument is legible: the instrument's domain is review *quality* over the enabled roster,
not the merge quorum, and it does publish both populations (`enabled_reviewers`, `reviewed_reviewers`)
so the grade is auditable. But D2 explicitly extends the required-vs-optional counting rule "to the
review-quality instrument itself", and the grade collapses the distinction the rule exists to keep.

### `vacuous` is asserted from an input that may simply be absent

CONFIRMED by execution, and neither the report nor the run's own review named it.

`_grade_comparison:149-150` returns `vacuous` whenever `enabled_reviewers` is empty, and the emitted
legend glosses that as *"0 findings and **no reviewer roster configured** — nothing was expected to
compare"* (`:389`); `SKILL.md:191` renders it to the operator as `"no reviewer roster configured —
nothing to compare"`. But `--enabled-reviewers` is `nargs='?', const='', default=''`
(`review_retrospective.py:434-438`), so **flag omitted**, **flag bare**, and **flag with an empty
value** all reach `aggregate` as the same empty list — and the SKILL sanctions the bare form in as many
words (`:482-483`: "It may be supplied bare (no value), which reads as the empty roster"). Executed:
`aggregate([], enabled_reviewers=None)` → `vacuous`; `aggregate([], enabled_reviewers=[])` → `vacuous`.

So the instrument asserts a **configuration fact it never read**, in the most benign of its four
grades, on the path where the caller supplied nothing. This is the same archetype the plan is about —
a predicate satisfiable without the thing it exists to establish — one argument to the left of where
the fix was placed. The test at `:814` pins the conflation rather than catching it: it passes
`enabled_reviewers=[]` and names that case "no roster configured". See G8.

### The `vacuous` grade ignores provenance

CONFIRMED. Even where the roster *is* read, `vacuous` is returned for any empty roster. D3 requires
`answered`-empty (*"quorum vacuously satisfied"*) and `never_asked`-empty (*"the question has not been
put"*, treated as **unestablished**) be rendered differently, and names `never_asked` as the
reachable-by-default case. The provenance sweep confirms the retrospective never reads
`bot_lists_provenance`, while `create-pr.md:256-257` already splits the same pair for the
skip-bot-review label. See G7.

### The `{reviewed_author_logins}` placeholder is undefined and contradicts its own prose

CONFIRMED. `grep -n "reviewed_author_logins\|enabled_author_logins"` over the retrospective SKILL
returns exactly four lines — `:168`, `:169`, `:234`, `:235`, the two invocation blocks. Both blocks
pass `--reviewed-reviewers "{reviewed_author_logins}"`, while the prose at `:155` orders the flag
passed **bare** and `:225-231` repeats it. `{enabled_author_logins}` is in the same shape but has a
derivation instruction behind it (`:209-218`, "derive the enabled reviewer roster… never transcribe a
reviewer list here"); `{reviewed_author_logins}` has none anywhere in the file. An agent following the
block literally passes the token itself, which the CSV split at `:472` turns into a single bogus
`author_login` that is echoed back in `reviewed_reviewers` — the field the payload publishes "so the
population behind the `comparison` grade is visible" (`:371-372`). See G9.

### The `comparison` grade does not reach the persisted artifact

CONFIRMED, and the SKILL contradicts itself about it. `SKILL.md:196-197` asserts the grade "lives in
the `--display-detail` and **the persisted artifact**". Step 4 (`:388-425`) enumerates exactly what the
artifact carries — the metrics table, the `## Review-versus-Gate Delta` section with its named fields,
`## Qualitative Quality Assessment`, `## Comparative Verdict` — and never names `comparison` or
`comparison_states`. `grep -n "comparison"` over the whole SKILL returns ten lines (`:136`, `:143`,
`:172`, `:173`, `:188`, `:192`, `:241`, `:244`, `:460`, `:488`) — none inside Step 4. See G6.

## Completeness review

**Consumers of the changed contract, swept by kind:**

| Consumer kind | Swept | Result |
|---|---|---|
| Production code emitting the old string | `grep -rn "nothing to compare"` repo-wide | Clean — no stale production surface |
| Other skills/docs referencing the step | `grep -rln "review_retrospective\|review-retrospective"` repo-wide | Non-test hits: `ext-point-finalize-step.md:249`, `ext-point-lane-element.md:200,221`, `dispatch-inline-split.md:29`, `github_pr.py:588`, `bot-participation-contract.md` — all describe ordering/lane/role. Eight further test modules match; a follow-up grep for `comparison`/`nothing to compare` in them finds only incidental uses of the English word. Clean |
| Contract standards | `bot-participation-contract.md` Consumers table | Updated at `:664`. Clean |
| The step's own SKILL | Step 1, 2, 4, 5, Error Handling, Canonical invocations | Steps 1, 2, Error-Handling row and Canonical invocations updated. **Step 4 (artifact) and Step 5 (display-detail) not updated** — see G1, G6 |
| Test fixtures / module docstring | The test module's own `Coverage:` list (`:19-33`) | **Not updated** — it enumerates every other measured property and omits the `comparison` grade (G15) |
| CLI / argparse `help=` prose | `review_retrospective.py:434-465` | Accurate on both flags, including the bare form — but the accuracy is what exposes G8: the help documents an empty roster as a legitimate input while the legend calls it "configured" |
| Callers of the new flag | `grep -rn "reviewed-reviewers"` repo-wide | **No producer exists** (G2) |
| CLI-level tests | `grep -n "rr.main\|main(\[\|argv\|sys.argv"` in the test module | **No match — the argparse path is untested** (G10) |
| Sibling site resolving the same config | `review_completeness.py`, `branch-cleanup.md` | **Not swept by the run** — vacuous quorum renders as met (G13) |

**Sites the plan named that received no exact replacement text:** the § Report Reviewer-participation
template (`cloud-plan-lane/SKILL.md:1736-1746`) — one of the three emission sites D2 enumerates (G5).

**Verification demands not discharged:** the ⭐ cold read's three answers, required verbatim (G12);
the Notes' "surface it" for the un-awaited recoverable refusal — the repo's live
`review_rate_window_await: false` is never named in the report, only the general awaitable-vs-hard
distinction inside the D1a proposal text (G14).

## Out-of-scope compliance

Clean on every item. CONFIRMED.

- **Editing `cloud-plan-lane/SKILL.md`** — not touched; `git show b286928c --name-status` lists six
  paths and that is not one of them.
- **Dropping, demoting, or re-ranking any reviewer** — nothing in the diff or the proposals changes
  `required_bots`/`optional_bots` or any registry `bot_kind`; D1b carries an explicit ⛔ restating the
  prohibition.
- **Deriving a per-reviewer participation rate from the cited instances** — the report's only ratios
  are this PR's own participation record, which the lane requires; no pooled rate is computed.
- **Auditing other repositories** — explicitly declared a lead in D3's scope caveat, not a finding.
- **The absence-cause partition** — the convergence question is answered in § Residue as the plan's
  Sequencing note demands ("denominator vs cause… not shipping two mechanisms").
- **Bridge writes** — `--name-status` shows the only `doc/plans/` changes are the plan's own directory:
  `R100` moving `050-….md` → `050-…/plan.md`, and `A` for `report-01.md`.

## Residue status

| Residue item recorded by the report | Status at HEAD |
|---|---|
| "The cloud-lane fix is a proposal, not a landed change… an operator or a non-cloud-lane run must apply them" | **STILL OPEN.** `cloud-plan-lane/SKILL.md:1206, 1258, 1439, 1442, 1746` are unchanged on this axis. 27 commits have touched that file since `b286928c` (`git log --oneline b286928c..HEAD -- …`); none applied D1a/D1b/D2a/D3. **And the proposals have gone stale in the interim** (G4) |
| "A persisted reviewed-at-all handoff to the retrospective does not exist… `--reviewed-reviewers` is passed bare" | **STILL OPEN.** Producer sweep finds no writer of the reviewed-at-all set anywhere (G2) |
| "Consumer-project config absence (D3 scope caveat) is a lead" | **STILL OPEN** — out of scope by the plan's own declaration; no action owed here |
| "Convergence with the absence-cause plan… reported per the plan's Sequencing note" | **CLOSED as an obligation** — the report states the axes and the verdict; nothing further was owed |

## Summary

**Counts by severity:** 4 major, 12 minor, 0 blockers — 16 gaps.

Plan 050 did what its deliverables told it to do: the two contract-touching deliverables produced exact
replacement text without editing the contract, the executor-free config read was settled correctly and
is verifiably true today, the roster-denominator absence claim still holds where it matters, and the
ten `comparison` tests exist, pass, and provably fail pre-fix. Out-of-scope compliance is clean and the
report is honest about what it could not corroborate; its one wrong figure is a stale suite count, and
two of its absence claims reach slightly further than their evidence.

The gaps are concentrated in the one piece of code that landed. Its `measured` grade is earned by META
records alone, so the benign-no-op condition survives one step to the left of where the fix was placed.
Its `clean` grade has no producer anywhere in the tree, so the discrimination D2 exists to create is
unreachable outside the unit tests and every zero-record run grades `indeterminate` — honest, but
carrying no information. Where `clean` *is* reachable in principle it is earned by an optional reviewer
while the required one stays silent — the plan's own false-clean, latent inside the plan's own fix and
armed by the very handoff that would repair the previous defect. And its `vacuous` grade announces "no
reviewer roster configured" on an argument the caller may simply have omitted, with a test that pins
the conflation rather than catching it.

Separately, the proposals the plan's main deliverables consist of have been overtaken by two later
landings in the exact span they say to replace, so the highest-value follow-up is to re-anchor them
before anyone applies them.

## Adversarial review

This document and `gaps.md` were re-derived end-to-end by a second reviewer with no prior context,
against the tree described in § Method. Every load-bearing citation was reopened, every count
recomputed, and every claim about executable behaviour settled by running it rather than by reading it.

**Method, precisely enough to re-run.**

1. `git show b286928c --name-status --find-renames`, and `git diff --name-status 61a43e53..HEAD` to
   establish the source tree is unchanged since the first verification pass.
2. Every `path:line` citation in both documents opened with `sed -n` and matched against the quoted
   text.
3. Every count recomputed: `grep -c "^def test_"` at `b286928c^` / `b286928c` / HEAD (30 / 40 / 43),
   a name-level `diff` of the three test lists, `git log --oneline b286928c..HEAD -- <path>` for each
   of the four touched paths, and the enumerations behind the four repo-wide sweeps.
4. The pure grader and `aggregate` called directly under `uv run python -c`, including the META-only
   store, the roster-vs-required pair, and the omitted-roster case.
5. One mutation run: a fifth grade constant plus a fifth `_grade_comparison` return branch, with no
   legend entry. Source bytes snapshotted to `$TMPDIR/adv-050-mutsweep/` first and restored from that
   snapshot in a `finally` — never via `git checkout`/`restore`/`stash`; `git status --porcelain`
   re-checked afterwards and showed no modification to any tracked file.

**Outcome.** Fourteen findings re-derived independently and **upheld** (G1, G2, G4, G5, G6, G7, G9,
G10, G11, G13, G14, G15, G16, and the D1/D3/D4 deliverable verdicts). Three **overstated** and
corrected here: G3's impact was stated as live when it is latent behind G2 (severity kept at major,
with the precondition now stated, because fixing G2 alone arms it); the "clean is unreachable"
second-order paragraph called the always-`indeterminate` path a "false-alarm generator", which
`indeterminate` is not — it is honest and uninformative, and the paragraph now says so; and G13's task
asserted that the barrier's caller "already reads" the provenance. One claim **refuted**: `grep -c
"bot_lists_provenance"` over `branch-cleanup.md` returns 0 — the barrier reads `required_bots` and
`optional_bots` (`:721-728`) and never the provenance, so G13's task now names the read it must add.
The report's own absence claim was likewise split (claim 6): its roster-denominated half holds, its
"only N-of-M emitter at all" half is refuted by `review_gate_delta.py:313,345` — which owes no gap,
because it publishes its populations. Five items remain **unverifiable** from the clone and are marked
as such rather than as passes (claims 17-20 and the PR comment bodies): CI records, intermediate
commits of a squashed branch, PR comment text, and a sub-agent's effort figures.

**Added.** One gap the first pass missed — G8, the `vacuous` grade asserted from an unsupplied roster,
found by reading the argparse defaults against the legend string and confirmed by calling `aggregate`
with the flag omitted. One traceability repair: G9 (the `{reviewed_author_logins}` placeholder) was an
actionable gap with no supporting finding in this document, and now has one. Several citations were
repaired (`cloud-plan-lane/SKILL.md:1198` → `:1199`; the "cannot dilute the ratio" quote attributed to
`:234-242` when it lives at `:41-42`; the test module's `comparison` section `:762-919` → `:760-914`,
which overran EOF; `review_completeness.py:110-113` → `:110-112`; "two later commits" on the aggregator
→ one), and two search descriptions were corrected to name searches that actually return the results
claimed for them.

**Verdict unchanged: `verified-with-gaps`.** Nothing found here is a blocker, and nothing found here
rehabilitates the shipped grade: the added gap deepens the same pattern the first pass identified
rather than contradicting it.
