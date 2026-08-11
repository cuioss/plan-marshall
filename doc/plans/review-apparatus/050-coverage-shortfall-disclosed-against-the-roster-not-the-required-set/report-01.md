# Run report — 050-coverage-shortfall-disclosed-against-the-roster-not-the-required-set (run 01)

**Date (UTC):** 2026-08-11    **Branch:** `claude/coverage-shortfall-disclosure-u3w0pt` (harness-assigned; kept as-is per lane § Step 2)    **PR:** [#1170](https://github.com/cuioss/plan-marshall/pull/1170)    **Outcome:** completed — the two `cloud-plan-lane/SKILL.md` deliverables are `proposal recorded` (a complete result, not a partial one, per the plan's own § "READ THIS BEFORE THE DELIVERABLES"); the review-retrospective instrument change (D2) is a landed code change.

> **Reading note on populations.** This is a plan about unstated denominators, so every ratio below
> names its population. The roster for this repository is **3** reviewers — `cuioss-review-bot`
> (bot_kind `pr-agent`), `coderabbitai` (`coderabbit`), `sourcery-ai` (`sourcery`). The configured
> split (read from `.plan/marshal.json`, see D3) is **required = {`pr-agent`}** (1), **optional =
> {`coderabbit`, `sourcery`}** (2), **provenance = `answered`**.

## Skills loaded

- `cloud-plan-lane` (first action, the governing contract) — via `Skill:` load.
- `plan-marshall:ref-code-quality` — read at `marketplace/bundles/plan-marshall/skills/ref-code-quality/SKILL.md`.
- `pm-plugin-development:plugin-script-architecture` — read at its bundle path.
- `pm-dev-python:python-core` — Python production code (the aggregator change).
- `pm-dev-python:pytest-testing` — Python tests (the aggregator tests).

The plugin was not assumed installed; skills were read by bundle path (the always-works route). No
skill was un-loadable by both routes.

## Summary of what this run establishes

The defect is a **hand-written prose reimplementation** in `cloud-plan-lane/SKILL.md` (Step 7's
per-reviewer participation record and Step 8 condition 4's shortfall disclosure) that derives the
expected-reviewer population from the **full registry roster** and fires a shortfall whenever **any**
roster member's verdict is not `reviewed`. It never reads `required_bots` / `optional_bots`. This
produces two opposite defects on the same mechanism:

1. **False alarm** — on a PR whose required quorum (`pr-agent`) is satisfied, an **optional** bot
   (`coderabbit` or `sourcery`) being silent still trips the "shortfall".
2. **False clean (worse)** — the current `reviewed` verdict folds in "an explicit 'nothing to report'
   over the diff", i.e. `participated_but_empty`. So a required bot that participated-but-filed-nothing
   reads as `reviewed`, the shortfall stays silent, and the run reports full coverage on a diff nothing
   substantively reviewed.

The in-lifecycle mechanism (`branch-cleanup.md` Pre-Merge Review-Completeness Barrier →
`review_completeness.py`) is **correct** on this axis — it reads `required_bots`/`optional_bots`, gates
`participation_complete` on the **required set only**, and already emits `review_state_summary` to tell
reviewed-clean from nobody-reviewed. The cloud-lane prose is the sole surface that regressed the
distinction, because it is a manual mirror that never consumed the config.

Because `cloud-plan-lane/SKILL.md` is the contract governing this very run, the lane forbids
self-approving a change to it (plan § top-block). **D1 and the D2/D3 lane-surface halves are recorded
as proposals with exact replacement text below.** The review-retrospective instrument (ordinary source,
`.claude/skills/finalize-step-review-retrospective/`) is changed for real.

---

## Deliverables

### D1 — the verdict distinguishes required from optional; the record still ranges over the roster

**Outcome: proposal recorded.** (Touches `cloud-plan-lane/SKILL.md` — PROPOSAL ONLY.)

**What is wrong (confirmed):** the VERDICT computed over the population, not the population read.
Current Step 7 (`cloud-plan-lane/SKILL.md:549-575`) derives the population from *every* registry
`author_login` (correct — keep it) but its three verdicts (`reviewed` / `rate-limited` / `silent`)
(a) fold `participated_but_empty` into `reviewed` (line 565: "*or an explicit 'nothing to report' over
the diff*"), and (b) carry no required/optional classification. Current Step 8 condition 4
(`SKILL.md:652-658`) fires the shortfall when "**any** expected reviewer's verdict is not `reviewed`" —
roster-wide, so an optional silence trips it.

**The fix keeps the roster-wide record and changes only the verdict + the shortfall predicate.** It does
not narrow the population (that would trade a false alarm for a blind spot) and drops/demotes/re-ranks
no reviewer.

#### PROPOSAL D1a — replace the Step 7 verdict table and its surrounding two paragraphs (`cloud-plan-lane/SKILL.md`, the block at lines 558-575)

Replace from "**Record a verdict per reviewer, derived from the stored comment bodies**" through
"…not merely unmentioned." with:

> **Classify each roster reviewer as required, optional, or unclassified.** Read `required_bots` and
> `optional_bots` from the resolved step config — in this repository, the git-tracked
> `.plan/marshal.json`, at `plan.phase-6-finalize.steps["plan-marshall:automatic-review"]` (see § "Read
> the required/optional split", added by D3). A reviewer whose `bot_kind` is in `required_bots` is
> **required**; in `optional_bots`, **optional**; in neither, **unclassified** (its comments still count,
> but its absence is expected of nothing).
>
> **Record a verdict per reviewer, derived from the stored comment bodies** — never from a check state,
> a review summary, an absence of complaint, or this contract's prose. For each `author_login` in the
> population, read that author's actual comment/review bodies on the PR (both surfaces above) and assign
> exactly one verdict:
>
> | Verdict | Body evidence |
> |---|---|
> | `reviewed` | The author published a review artifact **carrying findings** against the diff — an inline thread comment, or a review/issue-comment body with findings. |
> | `reviewed-empty` | The author published a review artifact against the diff that **carried no findings** — an explicit "nothing to report", or a persistent summary card ("no major issues") with nothing actionable. This is `participated_but_empty`: a review happened, but it substantiates no finding. It is **not** the same as `reviewed`, and a required quorum resting entirely on it is a quorum met by empty participation — surface it as such. |
> | `rate-limited` | The author published **only a refusal/quota notice** in place of a review (e.g. "Review limit reached", "reached your weekly rate limit of … diff characters"). It engaged but did not review this diff. State whether the limit is an **awaitable window** (reopens on its own — the review is re-requestable) or a **hard quota / size ceiling** (does not reopen usefully); an awaitable refusal that was never awaited is a discarded review, not a dead end. |
> | `silent` | The author published **nothing at all** — no review, no notice. State the reason when one is known (a mid-review push aborted it; the PR carries `skip-bot-review`; the reviewer is disabled); an unexplained silence is recorded as such. |
>
> A check-run state is never a verdict: a green check can conclude having published nothing, and a
> reviewer that posts no check at all would read as absent on every run. The verdict comes from the
> bodies or it is not evidence.
>
> Record the population, each reviewer's **required/optional classification**, its verdict, and the body
> evidence in the report's **Reviewer participation** table (§ Report). State coverage as **two named
> ratios, never one bare ratio**: the **required** quorum (`k of |required_bots|`, and whether it is met
> **by empty participation**) and the **optional/roster** coverage (`j of |optional_bots|` reviewed,
> with each silence's cause). A reviewer that never spoke is then *visibly* `silent` and *visibly*
> optional-or-required in the record, not merely unmentioned.

Rationale: surfaces the four facts the plan's Goal names — required quorum met; required quorum met by
empty participation; an optional reviewer accountably absent; and (via D3) no required reviewers
configured — that the current three-verdict, roster-flat record cannot tell apart. Tests it would need:
the four D4 cold-read scenarios below (staged against this proposal, since the surface is prose).

#### PROPOSAL D1b — replace Step 8 condition 4's opening (`cloud-plan-lane/SKILL.md:652-658`)

Replace "From the per-reviewer participation record (§ Step 7), read the verdict of every expected
reviewer. When **any** expected reviewer's verdict is not `reviewed`, state the shortfall …" with:

> From the per-reviewer participation record (§ Step 7), read each reviewer's classification and verdict.
> **The shortfall predicate is over the REQUIRED set, mirroring the in-lifecycle
> `review_completeness` quorum** — it is not roster-wide. State the coverage as two named ratios, and
> disclose in this order:
>
> - **Required quorum.** A **required** reviewer whose verdict is `rate-limited`, `silent`, or
>   `reviewed-empty` **is the shortfall to state** — e.g. "Required quorum NOT substantively met: 0 of 1
>   — `cuioss-review-bot` participated but produced no findings (`reviewed-empty`)." A required quorum
>   met by `reviewed` is stated as met: "Required quorum met: 1 of 1 — `cuioss-review-bot` reviewed."
>   A required quorum met **only by `reviewed-empty`** is stated as *"met by empty participation"*, never
>   as a plain "met".
> - **Optional coverage.** An **optional** reviewer that did not review is **disclosed, never framed as a
>   shortfall** — "Optional coverage: 0 of 2 — `coderabbitai` rate-limited (awaitable window),
>   `sourcery-ai` rate-limited (weekly quota)." Its absence changes what the run *says*, never whether it
>   merges, exactly as the block below already requires.
> - **Vacuous case (D3).** When `required_bots` is empty, do not state "required quorum met". State it
>   as *"no required reviewers configured — quorum vacuously satisfied"* (provenance `answered`) or
>   *"reviewer requirements not configured — the question has not been put"* (provenance `never_asked`).
>
> An example line the run must be able to produce: **"Required quorum met by empty participation (1 of 1:
> `cuioss-review-bot` reviewed-empty); optional 1 of 2 reviewed (`coderabbitai`: 16 findings;
> `sourcery-ai` size-capped)."** A run that merges on a required quorum met only by empty participation
> must _say_ so.

The existing "⛔ This is a disclosure requirement, and it is NOT a block" paragraph below is kept
verbatim — the shortfall still changes only what the run says, never whether it merges. The report's
**Reviewer participation** template (§ Report) gains the required/optional column and the two-ratio
coverage line.

> ⛔ **Not in this proposal:** dropping, demoting, or re-ranking any reviewer, or reassigning which is
> `required`. Two reporters said so unprompted and the plan repeats it; this only makes the existing
> verdict legible.

---

### D2 — every emitted coverage ratio NAMES its denominator; and the instrument grades `indeterminate`

**Outcome: proposal recorded for the lane surfaces; landed code change for the instrument.**

#### The counting rule is consumed, not re-derived

The epic's counting rule already **landed** — it is `automatic-review/standards/bot-participation-contract.md`
§ "The counting rule" (lines 446-472), owned by plan 040's D0. It names three populations, each
published: the **required set** (`required_bots`), the **optional set** (`optional_bots`), and the
**enabled roster** (`required ∪ optional`). This plan **consumes** it; it does not restate a fourth. The
epic still has exactly one owner. (Handback: nothing to hand back — the rule is landed and consumed.)

Note the full-registry **roster** the cloud-lane record ranges over is *deliberately wider* than the
enabled roster the counting rule names, and that is correct for a *record* (it catches a reviewer added
to the registry but not yet configured). What must be named per ratio is the **denominator of each
emitted rate** — and those denominators are the counting rule's three, never the bare roster.

#### PROPOSAL D2a — name the denominator at every lane emission site

- **Step 7 record / report Reviewer-participation table / run-report coverage line:** every ratio states
  its population. Never a bare "N of M". Emit the pair: `required k of |required_bots|` and `optional j
  of |optional_bots|` (and, for the record's own breadth, `roster r of |roster|`). This is the
  D1a/D1b replacement text above; D2a is the standing "publish-your-population" rule that governs all
  three sites at once.
- **Absence-of-siblings, verified.** A background sweep (14 files read closely, 100+ grepped — see
  § Findings) confirms the **HYPOTHESIS**: `cloud-plan-lane`'s disclosure is the **only** emitter of a
  roster-denominated reviewer-coverage figure, and the only emitter of an "N of M" reviewer-coverage
  ratio at all. Every in-lifecycle emitter (`review_completeness`, `review_retrospective`, the
  merge-gate barrier) already reads `required_bots`, the enabled roster, or a per-reviewer quality
  denominator. So this fix corrects the one emitter; there are no siblings publishing the wrong
  denominator. **Scope searched: the whole repo; sole roster-denominated site: `cloud-plan-lane/SKILL.md`
  (Step 7, Step 8 cond 4, and the report template).**

#### The instrument — a landed code change (`.claude/skills/finalize-step-review-retrospective/`)

The review-retrospective instrument, on a zero-`pr-comment`-findings run, previously recorded
`--outcome done --display-detail "0 pr-comment findings — nothing to compare"` unconditionally. Zero
findings is **ambiguous**: a `participated_but_empty` reviewer files zero findings just like a silent
one, so that string renders a coverage collapse identically to a clean review — a benign no-op reported
in exactly the condition the instrument exists to detect.

**Change (`review_retrospective.py`):** the aggregator now emits a top-level **`comparison`** grade,
computed by the pure helper `_grade_comparison(total_findings, enabled, reviewed)`:

| `comparison` | condition | meaning |
|---|---|---|
| `measured` | ≥1 finding | there was content to compare |
| `clean` | 0 findings, ≥1 reviewer positively substantiated as reviewed | reviewers ran, found nothing — a legitimate no-op |
| `vacuous` | 0 findings, no roster configured | nothing was ever expected — the honest empty |
| `indeterminate` | 0 findings, roster configured, **no** reviewer substantiated | **no reviewer produced content — the comparison could NOT be performed** |

The reviewed-at-all signal is supplied as `reviewed_reviewers` (the `participated` /
`participated_but_empty` set from `review_completeness`, `author_login`s), via a new
`--reviewed-reviewers` flag. **Absent that signal against a non-empty roster the grade fails closed to
`indeterminate`** — an unsubstantiated review is never credited as a clean one. The instrument now emits
`comparison`, `reviewed_reviewers`, and a `comparison_states` legend.

**Why `--outcome` stays `done`.** `mark-step-done`'s `VALID_OUTCOMES = ('done', 'skipped', 'loop_back',
'failed')` has **no `indeterminate` member**, and the step is declared non-fatal ("finalize must never
abort because the review retrospective hit a snag"). So `indeterminate` is carried by the instrument's
own **grade** (`comparison`) and its `--display-detail`, never by the lifecycle `--outcome` — the grade
is the instrument assessing its own work; the `done` outcome only says the step ran. The SKILL.md Step 1
zero-findings exit and the Error-Handling row are rewritten to run the aggregator on the empty store and
choose the display-detail from the grade — never the flat "nothing to compare".

Commit: see § Deliverables commit map. Tests: § D4.

---

### D3 — the config read is resolved, not assumed; the vacuous case rendered as vacuous

**Outcome: read mechanism named and settled (positive answer for this repo); proposal recorded for the
vacuous rendering.**

#### The executor-free read path — SETTLED

The plan's caveat is that "the cloud lane runs WITHOUT the generated executor; a fix that reaches the
config through the executor-mediated config script would be inert." **Settled finding:** in this
repository an executor-free read path **does exist**, because `.plan/marshal.json` is **git-tracked**,
not git-ignored. The `.gitignore` rule is:

```gitignore
.plan/*
!.plan/marshal.json
!.plan/project-architecture/
```

`git check-ignore .plan/marshal.json` exits 1 (not ignored); `git ls-files` lists it; it is a committed
blob at `origin/main`. So the cloud clone **has** it, and the lane can read it with the plain `Read`
tool — no executor, no config script:

> **Read the required/optional split (executor-free).** `Read .plan/marshal.json`, parse JSON, and take
> `plan.phase-6-finalize.steps["plan-marshall:automatic-review"]`. The three fields are `required_bots`
> (CSV of `bot_kind`), `optional_bots` (CSV), and `bot_lists_provenance` (`never_asked` / `migrated` /
> `answered`). This is the same nested step-param the in-lifecycle barrier reads via the executor
> (`branch-cleanup.md` § "Read the barrier knob and the bot participation lists"); the git-tracked file
> is the executor-free equivalent. Everything else under `.plan/` is git-ignored and absent from the
> clone — only `marshal.json` and `project-architecture/` are tracked.

**Current values in this repo (the population behind every ratio in this report):** `required_bots =
"pr-agent"`, `optional_bots = "coderabbit,sourcery"`, `bot_lists_provenance = "answered"`.

**Scope caveat (a lead, not a finding).** This path holds because *this* repository un-ignores
`marshal.json`. A **consumer project** of plan-marshall would need the same `.gitignore` negation for
its cloud clone to carry the config; without it, the config is absent and there is **no executor-free
read path** — in which case the disclosure must fall back to "reviewer requirements unknown
(configuration absent from the clone)" and render the required quorum as **unestablished**, never as
met. Auditing whether other repos carry the negation is explicitly out of scope (the plan's own
Out-of-scope); D3 makes the vacuous/unknown case *visible* where it occurs.

#### PROPOSAL D3 — render the vacuous case as vacuous, honouring provenance

The disclosure must distinguish, using the read above:

- **`required_bots` non-empty** → the D1b required-quorum path.
- **`required_bots` empty, provenance `answered`** → the quorum is **vacuously satisfied** (a deliberate
  operator answer of none). State *"no required reviewers configured — quorum vacuously satisfied"*.
  **Never render this as "required quorum met".**
- **`required_bots` empty, provenance `never_asked` (or `migrated`)** → the question has not been
  answered. State *"reviewer requirements not configured — the question has not been put"*, and treat
  the required quorum as **unestablished**, not satisfied. This is the vacuous-authority archetype and
  it is the DEFAULT for any project that has not run the wizard.
- **Config absent from the clone** (consumer project without the `.gitignore` negation) → *"reviewer
  requirements unknown — configuration absent"*; required quorum **unestablished**.

This is a distinct rendering for each of "met", "met-by-empty" (D1), "vacuously satisfied",
"not-configured", and "unknown" — five states the current single "coverage N of M" collapses.

---

### D4 — tests, each verified to FAIL pre-fix, each proving discrimination by mutation

**Outcome: real discriminating tests landed for the instrument; the four cloud-lane cases staged as
cold-read scenarios against the proposal (the surface is prose, not code).**

#### Landed real tests — the instrument's `comparison` grade

`test/plan-marshall/finalize-step-review-retrospective/test_review_retrospective.py`, new section
"D2 (plan 050) — the `comparison` grade". Every assertion on `comparison` **fails pre-fix** because the
field did not exist. The discriminating pair maps directly onto the plan's `participated_but_empty`-vs-
nobody-reviewed axis:

- `test_comparison_measured_when_findings_exist` — findings → `measured`.
- `test_comparison_clean_when_a_reviewer_reviewed_and_found_nothing` — 0 findings, a reviewer reviewed →
  `clean` (the `participated_but_empty` = reviewed-empty case: **visible as a review, not a collapse**).
- `test_comparison_indeterminate_when_no_reviewer_produced_content` — 0 findings, roster, none reviewed →
  `indeterminate` (**the collapse the instrument exists to detect**).
- `test_comparison_vacuous_when_no_roster_configured` — 0 findings, no roster → `vacuous`.
- `test_comparison_fails_closed_to_indeterminate_without_the_reviewed_signal` — the fail-closed default.
- `test_comparison_clean_vs_indeterminate_discriminate_on_identical_zero_store` — **the mutation proof**:
  two runs with an identical empty store and identical roster, differing only in whether a reviewer is
  substantiated, produce `clean` vs `indeterminate`. A mutant that hard-codes the grade (the pre-fix
  "always a benign done") cannot satisfy both assertions — so the test discriminates rather than
  decorates.
- `test_comparison_states_legend_matches_the_four_graded_constants` and
  `test_grade_comparison_helper_is_directly_unit_testable` — legend/constant integrity and the pure
  helper.

Pre-fix verification: confirmed by direct reasoning — the `comparison`, `reviewed_reviewers`, and
`comparison_states` keys are new, so every assertion referencing them raises `KeyError`/`AttributeError`
against the pre-change module; the `clean`-vs-`indeterminate` pair was **byte-identical** pre-fix (both
produced the same all-`unmeasurable` zero-findings payload with no grade).

#### Staged cold-read scenarios — the four cloud-lane cases (against the D1/D3 proposal)

Because `cloud-plan-lane/SKILL.md` may not be edited, its D4 cases are staged as the cold-read scenarios
the plan's Verification section mandates. Each is written so a naive roster-flat detector behaves
identically on the discriminating pair, proving discrimination:

| Case | Input | Proposed disclosure must say | A roster-flat detector says (the bug) |
|---|---|---|---|
| required-bot silent | `pr-agent` silent, optionals reviewed | **shortfall fires**: required 0 of 1 | fires (agrees — non-discriminating alone) |
| optional-bot silent, required met | `pr-agent` reviewed, `coderabbit` silent | **NO shortfall**; optional 1 of 2 disclosed | **fires a false shortfall** ← discriminates |
| required `participated_but_empty` | `pr-agent` reviewed-empty, `coderabbit` 16 findings | **required quorum met by empty participation** (visible) | reads "required met", full coverage ← discriminates |
| empty `required_bots` | `required_bots=""`, provenance `answered` | **"no required reviewers configured — vacuously satisfied"** | "required quorum met" ← discriminates |

The middle two are the discriminating cases the plan flags; a detector that behaves identically on them
and on a real shortfall has not been fixed.

---

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` → the aggregator
(`.claude/skills/finalize-step-review-retrospective/scripts/review_retrospective.py`) and its test
carry `*.py`, so the build ran. **`./pw verify` → `=== verify: SUCCESS ===`, `19052 passed, 14 skipped`
(read from the output, not the exit code).** The instrument's own suite, run targeted
(`./pw module-tests plan-marshall/finalize-step-review-retrospective`), is **38 passed** — including all
8 new `comparison`-grade tests. The later `bot-participation-contract.md` edit (Findings, below) is
docs-only (`*.md`), so it triggers no additional local build; the merge queue's `merge_group` run
verifies docs.

## Findings

- **Emission-site sweep (HYPOTHESIS → CONFIRMED).** A read-only sub-agent swept the repo for
  reviewer-coverage emitters: 14 files read closely, 100+ grepped. `cloud-plan-lane/SKILL.md` is the
  **sole** emitter whose denominator is the full registry roster, and the **only** emitter of an "N of M"
  reviewer-coverage ratio at all. All in-lifecycle emitters read `required_bots`, the enabled roster, or
  a per-reviewer quality denominator. Disposition: corroborates D2a's absence claim with a published
  scope; the fix corrects one emitter with no siblings left publishing the wrong denominator.
- **Verification sub-agent (Step 6) — one finding, ACCEPTED and fixed.** The independent sub-agent
  verified the D2 code (executed `_grade_comparison`/`aggregate` directly — all four grades correct, the
  fail-closed default correct, backward-compatible), confirmed `VALID_OUTCOMES` has no `indeterminate`
  member (so `--outcome done` + graded display-detail is the only valid choice), independently
  re-verified the D3 read mechanism (`.gitignore` negation + `git ls-files` + the marshal.json values),
  confirmed the D1/D3 proposal anchors match the current `cloud-plan-lane/SKILL.md` verbatim, and ran
  the plan's central cold read on the D1b proposal (Q2 "gap or accounted-for absence?" **is** answerable;
  the empty-`required_bots` rendering answers "was a required review performed?" as "no required
  reviewers configured — vacuously satisfied", not "yes"). **Finding:** the counting-rule Consumers
  table in `bot-participation-contract.md:516` described the `review_retrospective` consumer as reading
  only `--enabled-reviewers`; post-change it also consumes the reviewed-at-all predicate via
  `--reviewed-reviewers` (the counting rule's second named quantity) — incomplete, not false.
  **Disposition: fixed** — the table row now names both inputs and the `comparison` grade. No other
  stale claim was found (the only "0 pr-comment findings — nothing to compare" production surfaces were
  the aggregator and its SKILL.md, both rewritten). Two items the sub-agent explicitly could not
  mechanically verify — the correctness of the prose proposals (a judgment call; its cold read supports
  them) and the "four landings" claim (records absent) — are recorded as such, not as passes.
- **CI:** all required checks green on head `677c1c2` — `verify / conclusion` success, `review / review`
  success, `dependency-review` success; `Sourcery review` skipped (optional); `mergeStateStatus: clean`.
  (Re-verified after the review-fix push below.)
- **PR review — CodeRabbit (`coderabbitai`, optional) posted 4 inline findings; all handled.** Reading
  both surfaces (conversation + inline review threads) was load-bearing: the conversation view showed
  only a benign "Actionable comments posted: 4" summary, while the *inline* threads carried the real
  findings — the exact green-check-hides-review failure the lane warns about.
  1. `review_retrospective.py:149` (🟠 Major, functional correctness) — `clean` accepted *any* reviewed
     reviewer, not just enabled ones, and empty-roster + non-empty-reviewed wrongly returned `clean`
     instead of `vacuous`. **CONFIRMED real bug. Fixed** — `_grade_comparison` now checks
     `not enabled_reviewers → vacuous` first, then `enabled_reviewers ∩ reviewed_reviewers → clean`; two
     regression tests added (`test_comparison_clean_requires_an_ENABLED_reviewer_not_any_reviewer`,
     `test_comparison_empty_roster_is_vacuous_even_with_an_off_roster_reviewer`).
  2. `review_retrospective.py:378` (🟡 Minor, maintainability) — `comparison_states` legend used string
     literals that mirror the `COMPARISON_*` constants. **Fixed** — the legend now keys off the constants.
  3. `SKILL.md:157` (🟠 Major, data integrity) — the `--reviewed-reviewers` classification is not
     persisted anywhere the retrospective can read at `order: 990`. **ACCEPTED the point. Resolution:**
     the SKILL.md now states plainly that no persisted handoff exists, so `--reviewed-reviewers` is
     passed **bare** and the zero-findings grade **fails closed to `indeterminate`** — the correct safe
     behaviour (an unsubstantiated review is never credited `clean`). Building the persisted handoff is a
     larger cross-step change beyond this plan's surface; recorded as residue, not built.
  4. `report-01.md:233` (🟡 Minor, lint) — MD040 missing fence language. **Fixed** — the `.gitignore`
     fence is now tagged `gitignore`.
- **PR review — `cuioss-review-bot` (pr-agent, REQUIRED)** posted its "PR Reviewer Guide": *"No major
  issues detected"* with zero findings — `participated_but_empty` / `reviewed-empty`. Nothing to handle
  (it filed no finding); recorded in Reviewer participation as the empty-participation quorum.
- **PR review — `sourcery-ai` (sourcery, OPTIONAL)** returned only a refusal: *"reached your weekly rate
  limit of 500000 diff characters"* — `rate-limited` (hard_quota, weekly). Nothing to handle; disclosed
  as an optional absence.

## Claim-label verification

| Claim | Plan label | This run's verdict |
|---|---|---|
| Expected-reviewer population is roster-derived | OBSERVED | **Confirmed** — `SKILL.md:553-554` ("that set **is** the expected reviewer population"). |
| Disclosure fires on ANY roster member | OBSERVED | **Confirmed** — `SKILL.md:654` ("When **any** expected reviewer's verdict is not `reviewed`"). No `required_bots`/`optional_bots` in it. |
| An optional bot's absence never blocks | OBSERVED | **Confirmed** — `bot-participation-contract.md:16,104`; the in-lifecycle barrier gates on required only (`review_completeness.check_completeness`). |
| `rate_limited` is in the shipped taxonomy, not collapsed | OBSERVED | **Confirmed** — three refusal states split by `rate_limit_class` (`review_completeness._refusal_state`). **Residual:** the cloud-lane `rate-limited` verdict *collapses* awaitable/hard/unknown; D1a restores the awaitable-vs-hard distinction the disclosure should consume. |
| No other emitter reads the roster as its denominator | HYPOTHESIS | **Confirmed** — emission-site sweep (scope: whole repo; 14 read, 100+ grepped; sole site: `cloud-plan-lane`). |
| Four recomputed landings each met required quorum at 1 of 1 | HYPOTHESIS | **Not corroborable here** — the per-PR landing records live under git-ignored `.plan/` (inbox/landing state), absent from the clone. What *is* confirmed from `marshal.json`: the required set is exactly `{pr-agent}`, so "1 of 1 required" is the correct denominator; the specific four landings cannot be re-derived. Not inherited. |
| The disclosure has fired a false shortfall on a real run | UNSETTLED | **No instance found**, and that does **not** refute the finding — the code path is OBSERVED. Stated plainly: this run carries **no** incident count; absence of a found instance is not evidence of zero impact. |

## Reviewer participation

Population **derived from configuration** (not transcribed): the roster is the three `author_login`s in
the registry; the required/optional split is read from `.plan/marshal.json` (D3): required =
{`pr-agent`}, optional = {`coderabbit`, `sourcery`}. Verdicts are from the stored comment bodies on
PR #1170 (both surfaces), classified per the D1a proposal's four-verdict scheme.

| Reviewer (`author_login`) | Class | Verdict | Body evidence |
|---|---|---|---|
| `cuioss-review-bot` (pr-agent) | **required** | `reviewed-empty` | Posted its "PR Reviewer Guide 🔍": *"No major issues detected"*, "No security concerns", "PR contains tests" — its declared `issue_comment` publish shape, but **zero findings**. Participated; produced nothing actionable = `participated_but_empty`. |
| `coderabbitai` (coderabbit) | optional | `reviewed` | Published a review with **4 actionable inline findings** (2 Major, 2 Minor) against the diff — one a real correctness bug in the graded code. |
| `sourcery-ai` (sourcery) | optional | `rate-limited` | Published only a refusal: *"reached your weekly rate limit of 500000 diff characters"* — `hard_quota` (weekly). |

**Coverage, with populations named:**
- **Required quorum: 1 of 1 — met by EMPTY participation.** The sole required reviewer (`pr-agent`)
  participated but produced no findings; its Guide asserts "no major issues" on a diff where the
  *optional* CodeRabbit found two Majors.
- **Optional coverage: 1 of 2 reviewed** — `coderabbitai` reviewed (4 findings); `sourcery-ai`
  rate-limited (weekly quota).
- **Roster: 2 of 3 participated** (`coderabbitai` reviewed; `pr-agent` reviewed-empty; `sourcery-ai`
  rate-limited).

⭐ **This run is itself a live instance of the plan's false-clean defect.** The required quorum reads
"met" while the substantive review came entirely from an *optional* reviewer, and the *required*
reviewer's "no major issues" card would — under the current cloud-lane roster-flat disclosure and its
`reviewed`-folds-in-empty verdict — have rendered as full coverage. Under the D1 proposal this discloses
as **"required quorum met by empty participation (1 of 1: `cuioss-review-bot` reviewed-empty); optional
1 of 2 reviewed (`coderabbitai`: 4 findings incl. 2 Major; `sourcery-ai` rate-limited, weekly quota)."**

**Step 8 shortfall disclosure — FIRED** (see § Merge gate below): stated to the operator before arming
auto-merge, exactly as the two-ratio line above. Under the current *shipped* cloud-lane text this would
also have "fired" — but as a bare "2 of 3" roster shortfall that conflates the empty required quorum
with two optional absences; the disclosure recorded here is the corrected required-vs-optional form the
D1 proposal specifies.

## Cost

- **Tokens:** not reliably available to the agent in this session; stated plainly rather than guessed.
- **Wall-clock:** run start ≈ report Date; end recorded at Step 8.
- **Population:** this single Claude Code cloud session's usage. ⛔ **Not comparable** to a
  plan-marshall `metrics.toon` total — that counts the orchestrator-plus-agent dispatch tree under
  plan-marshall's per-task billing boundary, which a single interactive cloud session does not share.

## Contract check (Step 9)

| Step | Verdict |
|---|---|
| 1 Skills loaded | **Done** — cloud-plan-lane + ref-code-quality + plugin-script-architecture + python-core + pytest-testing, read by bundle path (plugin not assumed installed). Named in § Skills loaded. |
| 2 Branch | **Done** — harness-assigned `claude/coverage-shortfall-disclosure-u3w0pt`, kept as-is; published to `origin` before any edit. Branch form: **harness-assigned**. |
| 3 Plan directory | **Done** — `doc/plans/review-apparatus/050-.../plan.md` exists and opens with the first-instruction block (present on receipt; not repaired). |
| 4 Implement | **Done** — commits carry the `Co-Authored-By: Claude` trailer, no "Generated with" footer. |
| 4 Per-commit gate | **Done** — every `*.py`-touching commit was preceded by a green build (`./pw verify` = SUCCESS, `total_issues`/failures 0). |
| 4 Pushed | **Done** — every commit pushed; no unpushed commit remains at merge time. |
| 5 Build gate | **Done** — Python changed → `./pw verify` run (twice: initial + after the review-fix push), both `=== verify: SUCCESS ===`. |
| 6 Verification sub-agent | **Done** — one finding (counting-rule Consumers table), fixed and re-verified clean; dispositions in § Findings. |
| 7 PR cycle | **Done** — PR #1170; all 4 CodeRabbit inline comments dispositioned (3 fixed, 1 accepted-and-resolved-by-fail-closed); both comment surfaces read. |
| 8 Merge gate | Conditions 1–3 met; auto-merge armed (see § Merge gate). Landing delegated to the orchestrator collect if the session cannot self-confirm; the merge commit is reported to the operator, not embedded here. |
| 8 Bridge | **Clean** — no status/bookkeeping write landed under `doc/plans/` outside this plan's own directory. The `bot-participation-contract.md` edit is a declared collateral fix (ordinary source), not a bridge write; `cloud-plan-lane/SKILL.md` was NOT edited. |
| 9 This check | Appended here. |
| 9 What have we learned | Below. |

**GitHub access path:** the **GitHub MCP server** (cloud path). **`/sync-plugin-cache`:** not owed — a cloud run neither performs nor records it.

## What have we learned (Step 9)

**No new cloud-lane contract change is proposed for self-approval** — and that is the correct outcome,
because the changes this run *would* make to `cloud-plan-lane/SKILL.md` (D1/D2/D3) are the plan's own
deliverables, recorded as proposals precisely because a run may not self-approve a change to its
governing contract. They are presented to the operator in this report, not shipped here.

Three genuine observations this run produced:

1. **The run empirically reproduced the plan's thesis.** The required reviewer (`pr-agent`) produced a
   "no major issues" card with zero findings while the *optional* CodeRabbit caught a real Major
   correctness bug in the graded code. This is exactly the false-clean the plan describes, observed live
   on the plan's own PR — strengthening the evidence for D1 rather than resting on the cited incidents.
2. **The lane's two-surface rule proved load-bearing here.** CodeRabbit's real findings were only in the
   *inline review-thread* surface; the conversation view carried a benign "Actionable comments posted: 4"
   summary. Reading only the conversation view would have merged with 2 Majors unaddressed. No change —
   this validates the existing § Step 7 rule.
3. **All self-wake tools were absent, not merely gated, in this session** — `subscribe_pr_activity`
   (harness and MCP) and `send_later` (MCP) all returned "No such tool available". The lane's
   **manual-read-polling** fallback (§ Step 8) carried the run to a self-confirmed state, so no contract
   change is warranted; but the lane's wording ("may be approval-gated") understates the case where the
   tools are wholly absent — the manual-read-polling path is then not an alternative but the *only* path,
   and it worked. Recorded as a data point, not a proposed edit.

## Residue

- **The cloud-lane fix is a proposal, not a landed change** (by design — the run may not self-approve a
  change to its governing contract). D1a/D1b/D2a/D3 carry exact replacement text; an operator or a
  non-cloud-lane run must apply them to `cloud-plan-lane/SKILL.md`.
- **A persisted reviewed-at-all handoff to the retrospective** (CodeRabbit finding #3) does not exist:
  `review_completeness`'s `{bot_kind, state}` classification is not written anywhere the `order: 990`
  retrospective can read it, so `--reviewed-reviewers` is passed bare and a zero-findings run grades
  `indeterminate` (fail-closed, correct). Upgrading a genuinely reviewed-clean run to `clean` needs that
  handoff built — a cross-step change beyond this plan's surface. Follow-up, not built here.
- **Consumer-project config absence** (D3 scope caveat) is a lead: whether other repos carry the
  `!.plan/marshal.json` negation is unverified and out of scope.
- **Convergence with the absence-cause plan.** This plan owns the **denominator** (whose absence
  counts); the sibling absence-cause plan owns **why** a bot is absent. The two converge on *reading
  `required_bots`/`optional_bots`* but the disclosure logic is distinct (denominator vs cause), so this
  is not shipping two mechanisms — reported per the plan's Sequencing note.
