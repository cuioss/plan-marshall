# Verification — 130-review-bots-catch-what-in-house-gates-cannot

**Landed as:** PR #1239, squash commit `622f4484`
**Verdict:** verified-with-gaps

Every artifact the report names exists in the tree today, and the three deliverables it calls "done"
are really implemented. The metric D2 ships, however, **can** produce the inversion the plan says
must not ship — by a route the plan's own inversion test does not cover — and three further
correctness defects sit in the landed code. The report is accurate on substance and inaccurate on two
counts (test/file tallies).

## Method

Read in full: `plan.md`, `report-01.md`.

Landed diff: `git show --stat 622f4484`, `git show --stat --name-only 622f4484`, and per-path
`git show 622f4484 -- <path>` for `_gate_coverage.py`.

Later landings over the same files: `git log --oneline 622f4484..HEAD -- <the six production
scripts>` → exactly one, `9e9e9880` (PR #1241, the `refused_structural` taxonomy member). Its diff
was read for collisions with this plan's surfaces.

Current-tree ground truth (`git rev-parse HEAD` = `61a43e53`). Files read end-to-end:

- `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_gate_delta.py`
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/review_commitments.py`
- `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_gate_coverage.py`
- `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/self_review.py`
  (§ `_format_structural_limit`, § `_cmd_surface` payload)
- `.claude/skills/finalize-step-review-retrospective/scripts/review_retrospective.py` (§ `_is_actionable`)
- `build.py` (§ `_run_mypy`, `cmd_compile`, `cmd_test_compile`, `cmd_quality_gate`, `cmd_verify`)
- `marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md`
  §§ "The counting rule", "The review-versus-gate delta", Consumers table
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/pre-push-quality-gate.md`
  §§ "A gate states what its green does not evaluate", "Verdict-input surface — deliberately undeclared"
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/finalize-step-simplify.md` § Step 3b
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md`
  § "A clean verdict carries the structural limit of the analysis"
- `.claude/skills/finalize-step-review-retrospective/SKILL.md` §§ Step 3b, Step 4
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md` Step 3 item 1, § "Special case
  — HEAD-dependent steps", § Canonical invocations
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/verdict_currency.py` § `classify`
- `marketplace/bundles/plan-marshall/skills/workflow-integration-gitlab/scripts/gitlab_pr.py` (the
  `add_finding` call site)
- `marketplace/bundles/plan-marshall/skills/manage-findings/scripts/_findings_core.py` § `add_finding`,
  `_findings_ingest.py` § `ingest_findings`
- the four registry docs (`coderabbit.md`, `sourcery.md`, `pr-agent.md`, `bot_registry.py`)
- all eight touched test files (names enumerated by grep; bodies read for the delta, the commitments,
  the gate-coverage and the parity suites)

Searches run (each stated where an absence is asserted):

- `grep -rn "review_gate_delta"` over `--include=*.py --include=*.md --include=*.json --include=*.toon`,
  excluding `doc/plans` and `target` — used for the consumer-count claim.
- `grep -rn "structural_limit"` over `marketplace/ test/ .claude/`.
- `grep -rn "_gate_coverage\|gate_coverage"` over the repo excluding `target/` and `doc/plans/` —
  used to establish `build.py` is the only production consumer.
- `grep -rn "record_checked\|record_degraded\|CoverageBoundary\|render_coverage_summary"` over
  `marketplace/ --include=*.py` (non-test) — same purpose.
- `grep -n "resolution" review_gate_delta.py` → **exit 1, no match** (backs the "no resolution filter"
  finding).
- `grep -rn "gate escape\|gate_escape\|review-versus-gate\|escaped the gate"` over `marketplace/ .claude/`
  → only this plan's own surfaces plus one unrelated hit in `emit-landing.md` (backs the plan's
  HYPOTHESIS that no pre-existing metric captures the delta).
- `find marketplace/bundles -maxdepth 3 -type d -name "ext-self-review*"` → one implementor.
- `grep -o` over the generated `.plan/execute-script.py` probe for both new script ids → both registered.

Executed:

- `uv run python -m pytest test/plan-marshall/automatic-review/test_review_gate_delta.py
  test/plan-marshall/phase-6-finalize/test_review_commitments.py
  test/plan-marshall/build-pyproject/test_gate_coverage.py
  test/plan-marshall/automatic-review/test_counting_rule_parity.py -o addopts="" -q`
  → **86 passed**.
- A scratch probe driving `assess_delta` directly (roster shrink, GitLab-shaped record, all-addressable
  partition, a `resolution: rejected` finding) — outputs quoted inline below. No repository file was
  modified; the probe lives in the session scratchpad.
- A scratch probe of `toon_parser.serialize_toon` to confirm `None` renders `null` and `0.0` renders
  `0.0` (the unmeasured-vs-genuine-zero question).

## Deliverables

| # | *Done when* (plan) | Report claim | Ground truth in the tree | Verdict |
|---|---|---|---|---|
| D0 | "each gate's verdict carries its own scope limit, derived from what the gate actually analyses" | Two gates changed, one already compliant; three gates named as an unclosed boundary | Build gate: real, derived, rendered. Self-review: field exists but rides the *surfacer's* TOON, not the step's verdict. Participation guard: compliant. Three gates still bare. Two reachable render paths carry no block at all | **partially implemented** |
| D1 | "a committed line survives a later simplify pass, or the removal is surfaced as a conflict rather than performed silently — proven by a test" | `review_commitments.py` + `finalize-step-simplify.md` Step 3b | Both exist; 29 tests, all passing; fail-closed states implemented as described | **verified** |
| D2 | "the metric excludes refusal-PRs by construction and publishes its population and provenance — or the stop condition fires and is reported" | Instrument ships; no rate; empirical half reported blocked | Instrument exists and publishes population + provenance. **The by-construction exclusion is defeated by a roster shrink** (probe-confirmed `structural_share: 100.0` at `1/1`), and the published provenance mis-states which PRs are measurable | **partially implemented** |
| D3 | "tests, each verified to FAIL pre-fix, plus retirement of the two lessons" | 100 tests / six files; one labelled regression pin; both lessons verified-closed, retirement not performed | 91 new `def test_` across **eight** files; the regression pin exists and is labelled; mutation evidence covers ~11 of 91 | **verified-with-gaps** |

### D0 — each gate states what its green does not evaluate

**Build gate — implemented, and correctly derived.**
`_gate_coverage.py:187-260` defines `AnalysisLimit` and `_ANALYSIS_LIMITS` keyed by six analysis
stems; `dimension_stem` (`:262-276`) strips the per-run bracket suffix; `structural_limits`
(`:289-313`) derives the pairs from `boundary.checked` in first-appearance order;
`_render_structural_limits` (`:315-360`) renders them on both verdict forms and appends the derived
`not run in this gate at all: …` line. `render_coverage_summary` (`:362-408`) calls it on the
COMPLETE branch (`:393`) and the PARTIAL branch (`:407`).

The registry keys match what `build.py` actually records — verified against the six record sites
(`build.py:319` `mypy(production)`/`mypy(test)` via `_run_mypy(dimension=…)`, `:468` `ruff`, `:484`
`SPDX headers`, `:499` `plugin-doctor`, `:570` `module-tests`). `test_every_dimension_build_py_records_has_a_registered_limit`
(`test_gate_coverage.py:205`) pins the same population.

Two reachable paths render **nothing**, and both are the absence-read-as-coverage shape D0 exists to
close:

1. `_render_structural_limits` early-returns `[]` when `boundary.checked` is empty
   (`_gate_coverage.py:322-324`). `cmd_quality_gate` runs `cmd_compile` **first**
   (`build.py:442`), so the most reachable PARTIAL — a freshness-suspect mypy — produces
   `checked == []` and `degraded == [('mypy(production)', …)]`. That PARTIAL verdict therefore
   carries no per-analysis limit and no un-run line. The test that claims to cover this case
   (`test_gate_coverage.py:285 test_partial_verdict_also_states_the_structural_limit`) seeds a
   boundary with `record_checked('ruff …')`, so it does not exercise the reachable shape.
2. `CoverageBoundary.complete` is `not self.degraded` (`_gate_coverage.py:181-184`), so a boundary
   that checked nothing and degraded nothing renders
   `>>> coverage: COMPLETE over the dimensions below — checked over full scope: (nothing)`, with no
   limit block and no un-run line. `test_empty_boundary_does_not_claim_a_limit_block_it_cannot_populate`
   (`test_gate_coverage.py:372`) pins exactly that behaviour as intended.

A third, narrower inaccuracy: `_skip_empty_mypy_scope` returns 0 **without recording either checked
or degraded** (`build.py:344-346`, `:365-367`), so an analysis that was attempted and found nothing
to check lands in the un-run list, whose wording is *"absent from the list above because this gate
never performs them"* (`_gate_coverage.py:353-357`) — false for that case.

**Self-review — the field exists; the *verdict* does not carry it.**
`self_review.py:139-171` defines `_format_structural_limit`, and `:409` emits `structural_limit` on
the `surface` payload unconditionally (only one emit site for `scope_statement` exists, at `:402`, so
the two are genuinely paired on every surface). Four tests pin it
(`test_self_review.py:3855-3907`). But `pre-submission-self-review.md:270` states plainly that
*"the `--display-detail` budget … carries neither, and the dispatched-envelope schema below has no
field for either"*, and `:272` concludes *"it is published, not discharged"*. So the step's recorded
verdict — the artefact a downstream reader sees — carries no limit; only the helper's TOON, read by
the dispatched agent, does. Against the plan's *Done when* ("each gate's **verdict** carries its own
scope limit") that is a partial discharge, and it is asymmetric with the build gate, whose limit is
on the rendered verdict itself.

**Participation guard — confirmed already compliant, read-only.** `proves: participation_only` is
required by `bot-participation-contract.md` § "Participation is not review quality" and the guard was
not touched by the diff.

**Gate-set completeness — the report's own disclosure is accurate and still open.** `ci-verify.md`,
`sonar-roundtrip.md` and `.claude/skills/finalize-step-plugin-doctor/SKILL.md` were grepped for
`structural limit` / `does NOT evaluate` / `cannot evaluate`: the first two have no match at all;
plugin-doctor's two matches (`:23`, `:167`) are a **scope** statement about scoped-vs-whole-tree mode,
cured by widening — the very thing the standard says a structural limit must not be.

**Cold read.** The report claims three cold reads, all answering "No". No artifact persists them, so
this is UNVERIFIABLE. The wording itself reads as intended on inspection.

### D1 — same-run reconciliation between a review commitment and the simplify step

Implemented as described and, as far as I can establish, correct.

- `review_commitments.py:96-104` — `COMMITTED_RESOLUTIONS` / `RELEASED_RESOLUTIONS`, disjoint and
  pinned by `test_the_two_resolution_sets_are_disjoint`.
- `derive_commitments` (`:145-176`) — `pending` and any unrecognised resolution fall to
  `BASIS_UNDECIDED` and still bind; a finding with no `file_path` binds nothing and is counted by
  `count_unanchored` (`:179-190`).
- `_binds` (`:297-311`) — an anchor-less commitment binds its whole file; an anchored one binds only
  a deletion range containing it. Both directions tested (`test_review_commitments.py:288`, `:320`).
- `parse_deletions` (`:203-287`) — old-side numbering, contiguous runs collapsed, `\ No newline`
  neither advances the counter nor flushes a run, `--- ` disambiguated by `in_hunk` position,
  `+++ /dev/null` attributed to the pre-image path. Each of those is separately tested (`:191`,
  `:199`, `:224`, `:248`).
- `reconcile` (`:311-355`) — `proves: removal_conflict_only`, `gates_merge: false`, populations
  published, every conflicting pair reported.
- `cmd_reconcile` (`:388-410`) — an unreadable diff or an unreadable store emits an error TOON with
  **no** `verdict` field, so a crash cannot read as clear.
- The workflow side exists: `finalize-step-simplify.md:180-213` (Step 3b, the `.plan/temp/` diff
  path with the `.git/`-is-a-pointer-file warning, the three-way verdict branch, the revert
  disposition), `:249-253` (`reverted_count` emitted unconditionally), `:262` (the `status: error`
  row in Error Handling). The canonical invocation block is at `phase-6-finalize/SKILL.md:1868`, and
  the script id `plan-marshall:phase-6-finalize:review_commitments` is present in the generated
  executor's `SCRIPTS` map.

The premise holds against the dispatcher: `finalize-step-simplify.md:8` declares `order: 8` and
`:10` `head_dependent: true`; `automatic-review/SKILL.md:10` declares `order: 30`; the re-entry check
at `phase-6-finalize/SKILL.md:677-696` re-fires a head-dependent step whose `head_at_completion`
diverges from live HEAD. On a first forward pass there are no `pr-comment` findings yet and
`read_jsonl_merge` skips missing files silently (`jsonl_store.py:100-102`), so the step reports
`clear` with `commitments_considered: 0` rather than an error — checked, and correct.

The one imprecision worth recording is disclosed in the module's own docstring (`:56-72`): the
finding's stored `line` is GitHub's line at review time and is never re-anchored (pre-filter 5,
`github_pr.py:1094-1104`), so a loop-back fix commit can shift the file between the two coordinate
systems. The docstring states the consequence and the direction of the risk.

### D2 — the review-versus-gate delta as a measured signal

The instrument exists, is registered
(`plan-marshall:automatic-review:review_gate_delta` is in the executor's `SCRIPTS` map), has a
canonical invocation block (`automatic-review/SKILL.md:1055`), a governing contract section
(`bot-participation-contract.md:569-651`), a consumer (`.claude/skills/finalize-step-review-retrospective/SKILL.md:326-386`
Step 3b) and a persistence step (`:388-410` Step 4). Population and provenance are published on every
verdict (`review_gate_delta.py:342-368`). The partition withholds rather than defaults
(`:317-322`, `:419`). No rate was emitted.

Three defects, all confirmed by execution:

**1. The no-inversion guarantee is not structural.** `_share_withheld_reason:417` withholds when
`len(covered) < len(roster)` — a comparison against a **caller-supplied** roster. Shrink the roster
and full coverage is restored:

```
roster=['coderabbit'] reviewed=['coderabbit'] gates green, SHAs equal,
2 escapes both gate_structural
  -> verdict=measured  structural_share=100.0  reviewer_coverage=1/1  share_withheld=None
```

That is verbatim the number the contract calls the failure mode
(`bot-participation-contract.md:606-611`: *"a naive share reports 100% — 'the gates are perfectly
configured' — when the only thing that changed is who spoke"*), reached without the guard firing.
The route is live, not hypothetical: `bot-participation-contract.md:62` gives `refused_structural`'s
remedy set as *"split, accept the gap, or **disable this reviewer for this PR**"*. Disabling the
size-capped reviewer removes it from `required_bots ∪ optional_bots` and the metric resumes reporting
— better. The plan's inversion test
(`test_review_gate_delta.py:142 test_collapsing_coverage_withholds_the_share_it_never_improves_it`)
holds `enabled_bots=_ROSTER` fixed on both arms, so this axis is untested.

**2. Findings the run rejected as wrong are counted as gate escapes.** `grep -n "resolution"
review_gate_delta.py` returns nothing. Probe:

```
one finding, resolution='rejected', partition=gate_structural
  -> escapes_total=1  structural_share=100.0
```

A bot false positive is not something the gates missed — the gates were right. The counting rule
(`bot-participation-contract.md:513-521`) defines the *filed* count and is silent on resolution, so
the module follows the rule; but the delta's own definition of an escape ("something the gates ran
over and did not report") does not survive it, and the partition taxonomy has no member for "not a
defect", so such a finding must be mislabelled or withhold the whole share.

**3. The published selection effect mis-states which PRs are measurable.** `_PROVENANCE:160-172` and
the contract's `⛔` paragraph (`bot-participation-contract.md:640-646`) both assert that *"the ONLY
measurable PRs are those where **neither** step committed anything"*. But `pre-push-quality-gate.md:315`
states the gate *"declares **no** `verdict_inputs` … so the dispatcher's verdict-currency classifier
never narrows its re-fire: **every HEAD advance re-runs it**"*, and `verdict_currency.py:434-438`
confirms it (`REASON_UNDECLARED` → `VERDICT_INVALIDATED` → RE-FIRE per
`phase-6-finalize/SKILL.md:686`). So on any loop-back re-entry the gate re-fires and re-stamps
`head_at_completion` at the then-current HEAD; if simplify and security-audit commit nothing on that
final pass, the two SHAs agree and the PR is measurable. The measurable set is *"PRs whose final pass
had no post-gate commit"*, which is biased **toward** PRs that looped back — that is, toward PRs
where review found something. The published provenance names neither the mechanism nor that bias
direction.

**Metric-precision boundary analysis** (the plan's Verification asks for it):

- `structural_share = round(100.0 * structural / len(escapes), 1)` (`:373`).
- **Divide by zero** — guarded: `WITHHELD_NO_ESCAPES` fires at `total == 0` (`:420-425`), so the
  division is unreachable at an empty population.
- **Unmeasured vs genuine zero** — distinguishable. `serialize_toon` renders `None` as `null` and
  `0.0` as `0.0` (executed). A genuine `0.0` (full coverage, everything partitioned, every escape
  `gate_addressable`) was produced by probe; an unmeasured PR carries `structural_share: null` plus a
  non-null `share_withheld`, and an excluded one additionally carries `verdict: excluded` and
  `exclusion_reason`. The consumer restates the rule (`SKILL.md:377`: *"`structural_share: null` is
  never `0`"*).
- **One unit below rounding granularity** — a non-zero share rounds to `0.0` only when
  `100/N < 0.05`, i.e. `N > 2000` escapes on one PR. Unreachable in practice, and `by_partition` ships
  the raw counts beside the share anyway, so the collision is recoverable even there. No defect.
- **Smallest value the producing format can express** — one escape of one is `100.0`; two of three is
  `66.7` (pinned at `test_review_gate_delta.py:151`). The rounding never crosses a decision boundary,
  because nothing consumes the share as a threshold.
- **Empty population** — an empty roster is `EXCLUSION_NO_ROSTER` rather than vacuous completeness
  (`:407-410`, tested at `:212`); an empty reviewed set is `EXCLUSION_NO_REVIEWER` (`:411-412`,
  tested at `:121`).

The stop condition: the plan permits either a metric or a reported stop. The run reports the
empirical half blocked and assembled no corpus. That is an admissible reading of a deliverable whose
*Done when* is disjunctive, and the report is explicit about the split.

### D3 — tests, each verified to FAIL pre-fix

`git show 622f4484 -- 'test/**' | grep -c "^+.*def test_"` → **91**; per file: 4 / 3 / 4 / 32 / 11 /
4 / 29 / 4 across **eight** files. `grep -c "^+.*parametrize"` → **0**, so no parametrisation
inflates the count toward 100.

`TestAbsentVersusInProgressDistinction` exists at `test_review_completeness.py:2228` with the four
methods the report implies, is explicitly labelled as retirement evidence for a shipped mechanism,
and survived PR #1241's heavy rewrite of `review_completeness.py`.

The plan asks for **every** D3 test proven discriminating by mutation. The report supplies six
mutations covering, by its own attribution, eleven tests. The remaining eighty are asserted
red-first, which is a different (and weaker) claim than mutation-discrimination. The report does not
overclaim here — it presents exactly what it did — but the plan's demand is not met in full.

All 86 tests in the four suites I ran pass on the current tree.

## Report-claim audit

| Claim | Verdict | Evidence |
|---|---|---|
| "Commit `1b3cfa6`, refined in `61dd515`" (and the six other branch SHAs) | **UNVERIFIABLE** | The PR was squash-merged and the branch deleted; `git log --oneline -1 <sha>` returns "unknown revision" for all seven. Not evidence of falsehood |
| D0: build gate gained `AnalysisLimit`, `dimension_stem`, `structural_limits`, rendered on COMPLETE and PARTIAL, UNKNOWN for uncharacterised dimensions | **ACCURATE** | `_gate_coverage.py:187-408`; four tests at `test_gate_coverage.py:191-386` |
| D0: "An uncharacterised dimension renders UNKNOWN rather than being omitted" | **ACCURATE** | `:326-332`; `test_unregistered_dimension_is_reported_unknown_not_omitted:245` |
| D0: self-review gained `structural_limit` "beside the existing `scope_statement`" | **ACCURATE but incomplete** | `self_review.py:409`; the field rides the surfacer payload only, and `pre-submission-self-review.md:272` says so ("published, not discharged"). The report does not note that the step's verdict still carries neither |
| D0: "The block now closes with a derived `not run in this gate at all: …` line" | **ACCURATE** | `_gate_coverage.py:344-357`; tests at `:326`, `:344`, `:357` |
| D0: "Gate-set completeness is not claimed … three carry no structural limit and were not changed" | **ACCURATE** | Grep over the three docs: no structural-limit text; plugin-doctor's two hits are scope statements |
| D1: "`review_commitments.py` (new, `phase-6-finalize/scripts/`) derives … parses … reports the intersection" | **ACCURATE** | File present, 456 lines, functions as described |
| D1: "Two undetermined states fail closed to a conflict" | **ACCURATE** | `derive_commitments:167` (`BASIS_UNDECIDED`), `_binds:307-309` (file-wide); tested at `test_review_commitments.py:82`, `:96`, `:122`, `:320`, `:331` |
| D1: "The seam reports and never decides … An error return carries no `verdict` field" | **ACCURATE** | `reconcile:340-343`; `cmd_reconcile:398,404`; tested at `:393`, `:424` |
| D2: "`review_gate_delta.py` (new) … Consumer wired at `finalize-step-review-retrospective` Step 3b, persisted by Step 4" | **ACCURATE** | `SKILL.md:326`, `:354`, `:388-402` |
| D2: "The share is emitted only at full reviewer coverage, so a collapse can only move the metric from a number to no number, never to a better one" | **OVERSTATED** | True for a fixed roster; false for a roster shrink. Probe: `roster=['coderabbit'], reviewed=['coderabbit']` → `structural_share=100.0` at `1/1`. The same overstatement is in `review_gate_delta.py:52-60` and `bot-participation-contract.md:601-611` |
| D2: "on the current step ordering the only measurable PRs are those where **neither** post-gate mutating step committed anything" | **OVERSTATED** | The gate declares no `verdict_inputs` (`pre-push-quality-gate.md:315`), so every HEAD advance re-fires it (`verdict_currency.py:434-438`; dispatcher `SKILL.md:686`). After a loop-back the SHAs can agree |
| D2: "**Population and provenance**, published on every verdict" | **ACCURATE** | `review_gate_delta.py:342-368`; tested at `test_review_gate_delta.py:97` |
| D2: "every escape is `gate_addressable`, `gate_structural`, or `unpartitioned`. An unpartitioned escape **withholds** the share" | **ACCURATE** | `:317-322`, `:419`; tested at `:237`, `:247`, `:260` |
| Finding #10/#18: the carve-out now "matches the promoted top-level `body`" and is begins-with | **ACCURATE** | `_BODY_FIELDS = ('body', 'message')` (`:136`), `opening.startswith` (`:241-246`); the promotion is real (`_findings_ingest.ingest_findings:80-133`, schema field `body` at `validate_struct.py:96`), and over-long bodies are **clamped**, not rejected (`validate_struct.py:15-16`), so the prefix survives |
| Finding #12: "`_SUMMARY_AUTHOR = 'coderabbitai'` hard-coded … fixed — new registry field `review_body_summary_patterns`" | **ACCURATE** | `bot_registry.py:406-441`, `:600-602`; `coderabbit.md:52`; no `_SUMMARY_AUTHOR` remains (grep over the retro skill returns nothing) |
| Finding #13: "'must land in both' was an obligation with no mechanism — fixed — `test_counting_rule_parity.py`" | **ACCURATE as to the file; the obligation it enforces is now stale** | The file exists (201 lines, 3 tests, all passing). But `review_retrospective._is_status_summary:160-174` now **delegates** to `review_gate_delta.is_status_summary`, so on that axis the two are one implementation and the parity assertion is vacuous. `bot-participation-contract.md:663` still says "the two implement the same rule **independently**" |
| Finding #19: "`review_retrospective` … keyed on `author` while the sibling keyed on `bot_kind` → divergence on **every GitLab finding** — fixed — `resolve_bot_kind` reads either key" | **FALSE as to the GitLab rationale** | `gitlab_pr.py:274-280` calls `add_finding` with `plan_id, finding_type, title, detail, file_path, line, raw_input` — and **no** `author=`, `kind=` or `bot_kind=`. So neither selector is present on a GitLab record and `resolve_bot_kind` returns `''` there. Probe with a record carrying only `author` shows the fallback works — but that record shape is one the GitLab producer never emits. The rationale in `review_gate_delta.py:181-184` and the corpus case at `test_counting_rule_parity.py:150-153` both encode it |
| Finding #24 recorded as accepted-not-resolved | **ACCURATE** | One shared predicate still drives both counters |
| D3: "100 tests added across six files" | **OVERSTATED** | 91 added `def test_` across eight test files; zero `parametrize` |
| Build gate: "5 production scripts, 7 test files" | **OVERSTATED** | Six production `.py` (`review_retrospective`, `bot_registry`, `review_gate_delta`, `review_commitments`, `_gate_coverage`, `self_review`) and eight test files, per `git show --stat --name-only 622f4484` |
| Build gate: "Final `./pw verify`: **19748 passed**" | **INCONSISTENT, UNVERIFIABLE** | The squash commit message on the same run says **19752 passed**. Neither can be re-derived without a full build, which is out of scope here |
| Lesson 1 "CLOSED — re-derived against current main": `STATE_ABSENT` / `STATE_IN_PROGRESS` distinct, `not_triggered` refines further | **ACCURATE** | `review_completeness.py:194`, `:195`, `:243`; `TestAbsentVersusInProgressDistinction` exercises all three |
| Lesson 2 "CLOSED by D1" | **ACCURATE** | `review_commitments.py` + Step 3b exist |
| "Neither retirement could be performed — the corpus is `.plan/`-local" | **UNVERIFIABLE, plausible** | `.plan/` is git-ignored; no lessons corpus in the clone |
| Cost figures (232k/317k/376k/423k, 1.35M) | **UNVERIFIABLE** | Arithmetic is self-consistent (232+317+376+423 = 1348k) |
| Reviewer participation table, coverage 1 of 3, the two refusal bodies | **UNVERIFIABLE** | Provider-side state; the refusal shapes it quotes match `coderabbit.md`'s `refusal_patterns` and `sourcery.md`'s `refusal_size_patterns`, which is consistent |
| Residue: "The sibling epic's zero-scoped-modules / null-test-scope branch was NOT reached" | **ACCURATE as to that branch; incomplete** | No `pyproject.toml` and no gate-footprint file in the diff. But the same archetype *is* present in `_gate_coverage.CoverageBoundary.complete` — code this plan edited — and the plan's Note asked the run to say so if it reached the branch. It is not mentioned |

## Correctness review

**C1 — the coverage guard compares against a mutable denominator.** `review_gate_delta.py:417`
withholds the share when `len(covered) < len(roster)`, where `roster` is whatever the caller passed as
`--enabled-bots`. Nothing anchors the roster to a stable configuration, and the taxonomy's own remedy
for a size-capped reviewer is to disable it for the PR. The metric therefore *can* report improving
parity as real reviewer coverage collapses — the plan's named prohibition. CONFIRMED by execution.

**C2 — no resolution filter on the escape set.** A `rejected` finding (the reviewer was wrong) is
counted as a gate escape and can drive `structural_share` to 100.0. CONFIRMED by execution and by
`grep -n "resolution" review_gate_delta.py` returning nothing.

**C3 — the GitLab fallback cannot fire on the path it names.** `resolve_bot_kind`'s docstring
(`:178-186`) justifies the `author` fallback with *"the GitLab producer (`gitlab_pr`) never sets
[`bot_kind`] at all"*. `gitlab_pr.py:274-280` sets neither `bot_kind` nor `author` nor `kind`.
Consequences on GitLab: `_is_actionable` (`:250-258`) sees no `kind` and returns `False` for every
record, so `escapes_total` is always 0; `resolve_bot_kind` returns `''`, so no summary pattern ever
applies; and no `reviewed_commit_sha` is stored, so `EXCLUSION_GATE_TREE_UNKNOWN` fires on every
GitLab PR. The instrument is inert there, and the stated rationale for the fallback is false.
CONFIRMED by reading both call sites.

**C4 — the published selection effect is wrong about the measurable set.** See D2 above. The
conclusion drawn from it in the report ("few or no measurements will accumulate until the finalize
ordering changes") does not follow, and the actual bias direction — toward PRs that looped back, i.e.
toward PRs where review found escapes — is the opposite of the misreading the disclosure guards
against. CONFIRMED against `pre-push-quality-gate.md:313-321` and `verdict_currency.py:410-448`.

**C5 — a PARTIAL verdict on the most reachable degradation path renders no structural-limit block.**
See D0. The suppression is deliberate for "checked nothing" but conflates it with "attempted nothing":
a boundary with one degraded dimension and no checked one *did* attempt an analysis, and the un-run
line — the very thing that would tell the reader what this gate does not do — is suppressed with it.
CONFIRMED by reading `_gate_coverage.py:322-324` against `build.py:442-450`.

**C6 — an empty boundary reports COMPLETE.** `complete = not self.degraded`
(`_gate_coverage.py:181-184`). "No dimension was analysed" and "every dimension passed" produce the
same verdict word. This is the one-signal-two-meanings archetype the plan's Notes call out as living
in at least three places; it is now demonstrably in a fourth, inside the function D0 rewrote.
CONFIRMED by reading, and pinned as intended by `test_gate_coverage.py:372`.

**C7 — the un-run line's wording is false for an attempted-but-empty scope.** `build.py:344-346` /
`:365-367` return 0 without recording, and `_gate_coverage.py:353-357` then prints *"absent from the
list above because this gate never performs them, NOT because they passed"*. For a module-scoped run
whose mypy scope collapsed to nothing, the gate does perform that analysis; it found nothing to
analyse. CONFIRMED by reading.

**C8 — the published per-escape `bot_kind` is degraded relative to the module's own resolver.**
`:317` uses `record.get('bot_kind')` raw while `resolve_bot_kind` exists two functions above for
exactly the records that lack it. Probe with `{'author': 'coderabbitai', …}` yields
`escapes[0]['bot_kind'] == ''`. The population field a reader uses to attribute escapes is blank
precisely where the resolver would have filled it. CONFIRMED by execution.

**C9 — error-handling asymmetry between the two new CLIs.** `review_gate_delta.cmd_assess:469`
catches `(OSError, ValueError)` around `query_findings(...)['findings']`;
`review_commitments.cmd_reconcile:404` catches `(OSError, ValueError, KeyError)` around the identical
expression. A malformed store that produces a payload without a `findings` key would traceback out of
the delta and be rendered as an error TOON by the sibling. CONFIRMED by reading; low likelihood.

**Checked and found sound.** The diff parser's edge cases (whole-file removal, `\ No newline`,
content lines opening `--`, contiguous-run collapsing, multi-file reset on `diff --git`); the
fail-closed exclusion ladder and its strength ordering (`_exclusion_reason:378-414`); the
`0/0`-is-not-full-coverage rule; the off-roster-reviewer intersection; the begins-with status-summary
predicate on both realistic shapes and its documented residual; both-sides normalisation of the
registry comparison (`:238-246`, tested at `:479`, `:498`); the ingest clamp preserving the body
prefix; the `not_run` derivation excluding degraded dimensions; and `structural_limit` /
`scope_statement` being genuinely distinct strings.

## Completeness review

**Consumers.** `review_gate_delta` is invoked from exactly one place —
`.claude/skills/finalize-step-review-retrospective/SKILL.md:354` — which is a **project-local** skill
under `.claude/skills/`. The grep over `--include=*.py --include=*.md --include=*.json
--include=*.toon`, excluding `doc/plans` and `target`, found no bundle-level consumer. The
instrument, its contract and its counting rule ship to every consuming project; the step that would
run it does not. D2's "recurring measured signal" is therefore a meta-project-only signal.

**Doc restatements swept.** For `review_body_summary_patterns` (the field this plan added), all
registry-field enumerations carry it: `automatic-review/SKILL.md:132` and `:140`, `coderabbit.md:19`,
`sourcery.md:17`, `pr-agent.md:50`, `bot_registry.py:36` and `:57`. Both bots that do not declare it
state the empty default and its fail-closed direction in prose. That sweep is complete.

**One stale restatement survives**, and it is load-bearing:
`bot-participation-contract.md:663` — *"the two implement the same rule independently because they
live in different bundles, so a change to the rule must land in both"* — is no longer true of the
status-summary half, which `review_retrospective.py:172` imports from `review_gate_delta`. The
sentence is the stated motivation for `test_counting_rule_parity.py`, whose
`test_both_implementations_agree_on_every_corpus_record` is now partly tautological.

**Test-fixture shapes.** `test_counting_rule_parity.py:150-153` encodes
`{'author': 'coderabbitai', 'kind': 'review_body', 'body': …}` under the label *"summary identified
from the author login with no bot_kind"*, justified in the comment at `:148` by "`gitlab_pr` never
sets it at all". No producer emits that shape: `github_pr` always sets both `author` and `bot_kind`
(when classified) plus `kind`; `gitlab_pr` sets none of the three. This is the same class the run's
own § "What have we learned" proposes a contract bullet for — a fixture asserting a shape production
never emits, making a predicate look verified.

**Untested reachable shapes.** No test seeds a `CoverageBoundary` with an empty `checked` and a
non-empty `degraded` (the reachable PARTIAL) — searched `test_gate_coverage.py` for every
`record_degraded` call site: `:288` and `:365`, both paired with a `record_checked`. No test varies
`enabled_bots` between two arms of a coverage-collapse comparison — searched
`test_review_gate_delta.py` for `enabled_bots=`; every occurrence in the collapse tests passes
`_ROSTER`. No test drives either counter with a `resolution` field.

**Prose-bearing string literals in production code.** Swept the two new scripts' `argparse`
`help=` / `description=` strings against the implemented behaviour: `--enabled-bots`'
"0/0 is not full coverage", `--reviewed-bots`' "never a clean zero", `--gate-head-sha`'s "an absent
SHA is not evidence of sameness" and `--partitions`' "withholds the structural share" all match the
code. `_PROVENANCE` is the exception — see C4.

**Plan-mandated verification not evidenced.** The plan's claim-label table required the asserted
absence ("no existing metric already captures the review-versus-gate delta") to be checked against
`manage-metrics` and the retrospective checks, warning that an unverified absence would duplicate a
shipped check. The report records no such check. I ran it — `grep -rn "gate escape\|gate_escape\|
review-versus-gate\|escaped the gate"` over `marketplace/` and `.claude/` returns only this plan's own
surfaces plus one unrelated hit — so the absence holds. The obligation to demonstrate it was not
discharged in the report.

## Out-of-scope compliance

**Compliant.** The plan forbade touching `pyproject.toml`'s `select=` list and the gate footprint
logic (both returned to a sibling epic). `git show --stat --name-only 622f4484` lists neither
`pyproject.toml` nor any footprint-scoping file. Nothing in the diff adds a self-review detector
(`self_review.py`'s change is the `structural_limit` formatter and its payload field — no new
`CANDIDATE_LISTS` member). No file under `doc/plans/` outside this plan's own directory was written.
D2 ships without a parity claim attached, as the plan's Out-of-scope requires
(`bot-participation-contract.md:649-651`).

One boundary was crossed only in the sense the plan invited: the plan's Notes ask the run to *say so*
if it reached the zero-scope / one-signal-two-meanings branch. It reached an instance of that
archetype in `CoverageBoundary.complete` and did not say so. That is an unmet reporting obligation,
not a scope violation.

## Residue status

| Residue item recorded by the report | Status today | Evidence |
|---|---|---|
| Finding #24 — the two consumers' opposite loss functions; one shared predicate errs toward counting | **OPEN** | `review_retrospective._is_status_summary:172` still delegates to the single shared predicate; no second predicate exists |
| The finalize step ordering is the real unblocker for D2 | **OPEN, and its statement needs correction** | Orders unchanged: `pre-push-quality-gate.md:7` = 5, `pre-submission-self-review.md:7` = 7, `finalize-step-simplify.md:8` = 8, `finalize-step-security-audit.md:9` = 9, `automatic-review/SKILL.md:10` = 30. But see C4 — the loop-back re-entry already re-gates, so the item overstates its own blocking effect |
| The residual status-summary misclassification (a body opening with the status line and carrying same-line substance) | **OPEN, pinned** | `test_review_gate_delta.py:457 test_the_known_residual_is_pinned_rather_than_hidden`; the narrowing mechanism (`contentless_review_markers` / `actionable_content_markers`) is still undeclared by `coderabbit.md` |
| Three gates carry no structural limit — `default:ci-verify`, `finalize-step-plugin-doctor`'s step verdict, `sonar-roundtrip` | **OPEN** | Greps over all three docs for `structural limit` / `does NOT evaluate` / `cannot evaluate`: no hits in `ci-verify.md` or `sonar-roundtrip.md`; plugin-doctor's hits at `:23` and `:167` are scope statements |
| The sibling epic's zero-scoped-modules / null-test-scope branch was NOT reached | **ACCURATE for that branch** | No `pyproject.toml`, no footprint file in the diff. See Out-of-scope for the adjacent archetype the report does not mention |
| Both lesson retirements recorded, not performed | **UNVERIFIABLE** | The corpus is `.plan/`-local and absent from the clone |

No later landing closed any of these. The only commit touching this plan's production files after the
squash is `9e9e9880` (PR #1241), which added the `refused_structural` taxonomy member; it left
`_REVIEWED_STATES` (`review_completeness.py:279`) at `participated` / `participated_but_empty`, so
D2's reviewed-at-all predicate is unaffected — and it introduced the `disable this reviewer for this
PR` remedy that makes C1 reachable.

## Summary

**Gaps by severity: 1 blocker, 7 major, 8 minor (16 total).**

Everything the report claims to have built exists in the tree today and works as described; three of
four deliverables are genuinely implemented, the test suites pass, the out-of-scope boundary was
respected, and the report's disclosures — the dropped deliverable, the named gate-set boundary, the
labelled regression pin, the un-emitted rate — are honest and mostly accurate. The plan's central
prohibition is nonetheless violated: `structural_share` reaches `100.0` at `1/1` coverage the moment
the reviewer roster shrinks, which is exactly the "the gates are perfectly configured" inversion the
plan says must not ship, reached by a route (disable-a-size-capped-reviewer) that a sibling PR made a
first-class remedy two hours later — and the plan's own inversion test holds the roster fixed, so
nothing catches it. Alongside it sit a metric that counts rejected bot false positives as gate
escapes, a documented GitLab fallback that cannot fire because the GitLab producer stores none of the
fields it reads, a published provenance that mis-states the measurable population, and two gate-verdict
render paths that carry no scope limit at all — including one where an empty boundary still prints
COMPLETE. None of these is a regression; all of them are things a second pass over the same surfaces
should now close.
