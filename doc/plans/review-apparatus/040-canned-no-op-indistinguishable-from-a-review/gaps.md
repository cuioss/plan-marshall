# Gaps — 040-canned-no-op-indistinguishable-from-a-review

Actionable follow-up derived from `verification.md`. Each entry is a task a later plan can pick up
without re-deriving the analysis.

Ordered by severity: majors G1–G4, then minors G5–G12.

## G1 — Give the deficit signal a verdict for "no required reviewer reviewed", instead of rendering `clean`

- **Severity:** major
- **Kind:** bug
- **Where:** `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py:691`
  (`verdict = DEFICIT_DEFICIT if deficit_reviewers else DEFICIT_CLEAN`), the verdict constants at `:283-285`,
  the emitter's `if required_reviewed:` guard at `:1145-1149`, and the contract wording at
  `marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md:551-553`
- **Evidence:** Executed against the library function (no file modified):
  `rc.assess_deficit([{'bot_kind':'pr-agent','reviewed':False,'finding_count':0}, {'bot_kind':'coderabbit','reviewed':True,'finding_count':4}], required_bots=['pr-agent'])`
  returns `{'verdict': 'clean', 'baseline_max': 4, 'baseline_reviewers': ['coderabbit'], 'required_reviewed': [], 'deficit_reviewers': []}`.
  `rc._emit_deficit_toon` on that payload prints `verdict: clean` / `baseline_max: 4` /
  `baseline_reviewers[1]: - coderabbit` and **no `required_reviewed` line at all**, because the emitter
  suppresses empty lists. `deficit_reviewers` is built only over reviewers filtered on `r.get('reviewed')`
  (`:678-681`), so a required reviewer that refused contributes nothing and the else-branch fires.
- **Impact:** A run in which the required reviewer refused outright and a baseline reviewer found four
  defects is reported to a reader as `clean`, with the required reviewer represented by no row. That is
  the plan's own vacuous-set archetype ("deriving rows from the responding set makes the detector's
  population a strict subset of its own domain") reproduced inside the signal built to close it — a false
  green in the one place the epic exists to remove one. The `check_deficit` CLI path partially rescues it
  by appending `reviewers[]`, but the `verdict` field — the value a consumer reads — still says `clean`.
- **Task:** Add a fourth verdict to the vocabulary alongside `DEFICIT_DEFICIT` / `DEFICIT_CLEAN` /
  `DEFICIT_UNASSESSABLE` — the required-side companion of `unassessable` (a name such as
  `DEFICIT_REQUIRED_ABSENT`) — and return it from `assess_deficit` when `baseline` is non-empty and
  `required_reviewed` is empty. Order the branches so the baseline check still wins (no baseline stays
  `unassessable`). Make `_emit_deficit_toon` print `required_reviewed` unconditionally, as an explicit
  empty list rather than an omitted line, so the absent population is visible instead of inferred.
  Update `bot-participation-contract.md` § "The comparative deficit signal" and
  `automatic-review/SKILL.md` § "Canonical invocations → review_completeness — deficit" to enumerate the
  new member.
- **Done when:** `assess_deficit` with a reviewing baseline and zero reviewing required reviewers returns
  the new verdict (never `clean`), the rendered TOON shows the required population explicitly in that case,
  and a test pins both — asserting the verdict is not `DEFICIT_CLEAN`.
- **Suggested grouping:** automatic-review / review_completeness — deficit signal

## G2 — Make the retrospective's per-row `participation` distinguish reviewed-clean from never-ran

- **Severity:** major
- **Kind:** incomplete
- **Where:** `.claude/skills/finalize-step-review-retrospective/scripts/review_retrospective.py:331`
  (`participation = 'measured' if raw_total > 0 else 'unmeasurable'`), the legend at `:380-383`, the
  docstring at `:245-257`, and the SKILL.md restatement at
  `.claude/skills/finalize-step-review-retrospective/SKILL.md` § Step 2
- **Evidence:** The row classifier reads only `raw_total`. A reviewer that reviewed and found nothing files
  no `pr-comment` records, so it renders `participation: unmeasurable` — the identical string a reviewer
  that never ran renders. The landing's own test says so:
  `test/plan-marshall/finalize-step-review-retrospective/test_review_retrospective.py`,
  `test_enabled_reviewer_with_no_findings_gets_an_unmeasurable_row`: *"'produced nothing', 'never ran', and
  'enabled-invoked-refused' all leave no record; without a row they render identically."* The plan's D3
  *Done when* is "no surface renders 'nobody reviewed' and 'reviewed clean' as the same string, proven by a
  test per surface"; surface 1 has such a test
  (`test_nobody_reviewed_and_reviewed_clean_render_differently`), surface 2 has none.
- **Impact:** The second D3 surface still collapses the exact distinction the plan is named after. A reader
  of a retrospective cannot tell a reviewer that did its pass and found nothing from one that never ran.
  #1170 (`b286928c`) closed this at the **aggregate** level by adding `_grade_comparison`
  (`clean` vs `indeterminate`, `:107-155`); the per-row field was not revisited, even though the signal it
  needs is now a parameter of the same `aggregate()` call.
- **Task:** Thread `reviewed_reviewers` (already a parameter, `:216-217`) into the row loop. Classify each
  row over at least three values rather than two: `measured` (records exist), a positively-substantiated
  reviewed-but-silent value (the author is in `reviewed_reviewers` — a legitimate no-op, never scored), and
  `unmeasurable` (enabled, no record, no reviewed-at-all signal). Update the `participation_states` legend
  so it is keyed off the constants rather than string literals, matching the `comparison_states` pattern at
  `:387-392`. Update the SKILL.md participation table so the LLM pass reads the three-way field.
- **Done when:** `aggregate([], enabled_reviewers=['a','b'], reviewed_reviewers=['a'])` gives `a` and `b`
  different `participation` values, and a test asserts the two differ — the surface-2 counterpart of
  `test_nobody_reviewed_and_reviewed_clean_render_differently`.
- **Suggested grouping:** finalize-step-review-retrospective — participation rendering

## G3 — Wire the `deficit` subcommand into a workflow, or record explicitly that it is a manual surface

- **Severity:** major
- **Kind:** omission
- **Where:** `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md:999-1028` (the only
  mention, inside § "Canonical invocations"); no caller anywhere
- **Evidence:** `grep -rn "deficit" marketplace/ .claude/ doc/ -l` (excluding `doc/plans`) returns four
  files: `tools-script-executor/SKILL.md` (an unrelated use of the word), `automatic-review/SKILL.md`,
  `bot-participation-contract.md`, and `review_completeness.py`. `grep -rn
  "check_deficit\|assess_deficit\|cmd_deficit" --include=*.py marketplace/ test/ .claude/` finds no
  non-test caller outside `review_completeness.py` itself. `bot-participation-contract.md:662` lists the
  command in § "Consumers", but that table describes what each command *reads*, not who runs it.
- **Impact:** D2's opening sentence is "A required reviewer returning materially fewer findings than a
  reviewer that actually reviewed the same diff **is reported**". In the tree, nothing reports it, because
  nothing calls it. The deliverable is a capability with no surface, and the observability the plan set out
  to add is not observable.
- **Task:** Add a step that runs it. The natural site is the `automatic-review` step's participation-guard
  block (`automatic-review/SKILL.md` § "Mark Step Complete"), immediately after the `check` call whose
  observation sets it already shares — forwarding the same flags including `--refused-causes` and
  `--refusal-size-caps`, as § "Canonical invocations → deficit" already mandates. Record the verdict as an
  INFO `decision` line (never as a gate, never in `display_detail`'s pass/fail sense) so the non-gating
  ceiling stays intact. If a workflow call is judged too costly, state that decision in
  `bot-participation-contract.md` § "The comparative deficit signal" — naming `deficit` an operator-invoked
  diagnostic — so the absence is a recorded choice rather than an unclosed deliverable.
- **Done when:** either a workflow document invokes `review_completeness deficit` and dispositions its
  verdict, or the contract states in as many words that the command is manual-only and why.
- **Suggested grouping:** automatic-review / review_completeness — deficit signal

## G4 — Bring the composed `display_detail` back inside the ≤80-character, plain-ASCII contract

- **Severity:** major
- **Kind:** bug
- **Where:** `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md:797`, `:800`, `:805`,
  `:850` (the em-dash template), and its own restatement of the rule at `:856`
- **Evidence:** The governing contract is
  `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/output-template.md:341-343` —
  "**Max 80 characters** (softer limits encouraged; the renderer does not truncate)" and "**Plain ASCII** —
  no unicode glyphs" — repeated at
  `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/external-step-contract.md:55`, with
  `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md:1707` requiring
  the length be checked "against its placeholders' **worst-case expansion**, never its literal form".
  Measured: `len('0 comment(s) found — 1 empty, 1 refused, 1 refused-structural (unified triage pending)')`
  is **86**, and `isascii()` is **False**. A three-bucket distribution including `refused-structural` and
  `not-triggered` measures **98**. The 86-character case is ordinary for this repository's configured
  roster (`.plan/marshal.json:117-118`: `required_bots: pr-agent`, `optional_bots: coderabbit,sourcery`) —
  pr-agent reviews clean, coderabbit rate-limits, sourcery size-refuses.
- **Impact:** The step emits a `display_detail` the renderer does not truncate and the contract forbids, in
  the ordinary three-reviewer case. `automatic-review/SKILL.md:856` restates the ≤80/ASCII rule inside the
  same section whose template breaks it, so the skill contradicts itself on the page.
- **Task:** Replace the em dash with an ASCII separator (`-`) at all four sites, and shorten the composed
  form so the worst-case expansion fits 80 characters — for example drop the `(unified triage pending)`
  tail when the summary segment is present (the summary already tells the reader more than the tail does),
  or shorten the longest bucket labels in `_STATE_SUMMARY_BUCKETS`
  (`review_completeness.py:294-311`) — `refused-structural` at 18 characters and `not-triggered` at 13 are
  the two that blow the budget. Then measure the worst-case expansion in the document, as
  `branch-cleanup.md:1707` requires, and state the measured figure.
- **Done when:** every rendered form of the Branch A `display_detail` is ASCII-only and its worst-case
  expansion over the full bucket vocabulary is ≤80 characters, with the measurement stated in the skill.
- **Suggested grouping:** automatic-review — display_detail composition

## G5 — Guard that every taxonomy member has a display bucket

- **Severity:** minor
- **Kind:** missing-test
- **Where:** `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py:294-311`
  (`_STATE_SUMMARY_BUCKETS`) and `:601-611` (`compose_review_state_summary`)
- **Evidence:** `compose_review_state_summary` tallies every state into `counts` (`:602-604`) but emits only
  the states enumerated in `_STATE_SUMMARY_BUCKETS` (`:607-610`); an unbucketed state is silently dropped.
  `grep -rn "_STATE_SUMMARY_BUCKETS" test/ marketplace/` finds no test referencing the constant, and no
  test asserts that the bucket union covers the taxonomy.
- **Impact:** A taxonomy member added without a bucket vanishes from `review_state_summary`, so the tally
  stops summing to the roster size and a reader sees "2 refused" for a three-reviewer roster with no
  indication a reviewer is unaccounted for — an under-report of exactly the kind this plan exists to
  prevent. The hazard is live: the taxonomy gained `refused_structural` in #1167 and the bucket list was
  updated by hand, not by a failing test. The sibling drift guard for the taxonomy prose already exists
  (`test/plan-marshall/automatic-review/test_bot_participation_contract.py` reads the contract's prose
  count back as an integer), so the pattern to copy is in the same directory.
- **Task:** Add a test asserting that the union of the state tuples in `_STATE_SUMMARY_BUCKETS` equals the
  full member set (`_UNPROVEN_STATES | {STATE_PARTICIPATED, STATE_PARTICIPATED_BUT_EMPTY}`), and a second
  asserting that `sum` of the bucket counts equals `len(bot_states)` for a roster containing one bot in
  every member.
- **Done when:** adding a `STATE_*` constant to the taxonomy without adding it to `_STATE_SUMMARY_BUCKETS`
  fails a test.
- **Suggested grouping:** automatic-review / review_completeness — display buckets

## G6 — Make the empty-roster `display_detail` fallback state that no reviewer was configured

- **Severity:** minor
- **Kind:** incomplete
- **Where:** `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md:798` (the fallback form)
  and `review_completeness.py:610-611` (`compose_review_state_summary` returning `''`)
- **Evidence:** With an empty roster the summary is `''`, and `SKILL.md:798` prescribes falling back to
  `"{N} comment(s) found (unified triage pending)"` — character-for-character the string the plan's Problem
  section quotes as the defect. `automatic-review/SKILL.md:648` states that `required_bots` and
  `optional_bots` "both default EMPTY", so an unconfigured consumer project takes this path always.
- **Impact:** In the documented default configuration the fix is inert and the collapsed string returns.
  Returning `''` from the composer is defensible (inventing a bucket for reviewers that were never
  configured would be a claim about nothing), but the *display string* still reads to a cold reader as "a
  review happened and found nothing".
- **Task:** Give the empty-roster case its own honest rendering at the composition site rather than at the
  composer — e.g. `"{N} comment(s) found - no reviewers configured"` — leaving
  `compose_review_state_summary`'s `''` return and its rationale unchanged. Keep it ASCII and within the
  80-character bound (see G4).
- **Done when:** a run with an empty reviewer roster renders a `display_detail` that differs from the one a
  reviewed-clean run renders, and a test pins the difference.
- **Suggested grouping:** automatic-review — display_detail composition

## G7 — Correct the Branch A illustration that describes an unreachable state

- **Severity:** minor
- **Kind:** stale-doc
- **Where:** `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md:800`
- **Evidence:** The sentence reads "So a run where three **required** reviewers all refused renders `"0
  comment(s) found — 3 refused (unified triage pending)"`". But every refusal member is in
  `_UNPROVEN_STATES` (`review_completeness.py:252-268`), `participation_complete = not required_unproven`
  (`:864`), and `SKILL.md:788` states Branch A is "entered only after the participation guard above returns
  `participation_complete: true`, or a force-done WARNING was recorded". Three refusing *required*
  reviewers therefore route to Branch C (loop-back), not Branch A.
- **Impact:** The deliverable's headline example describes a path its own branch cannot normally take, so a
  reader calibrating on it mis-models when the new string appears. The ordinary case for "3 refused" is
  three refusing *optional* reviewers, or a force-done.
- **Task:** Rewrite the sentence to use refusing **optional** reviewers (or a required set satisfied
  alongside refusing optional ones), and note the force-done hatch as the only way a refusing required set
  reaches Branch A.
- **Done when:** the illustration names a configuration that reaches Branch A under the guard stated twelve
  lines above it.
- **Suggested grouping:** automatic-review — SKILL.md accuracy

## G8 — Test the required-reviewer-did-not-review case of the deficit signal

- **Severity:** minor
- **Kind:** missing-test
- **Where:** `test/plan-marshall/automatic-review/test_review_completeness.py`, class `TestDeficitSignal`
- **Evidence:** `grep -n "required_reviewed" test/plan-marshall/automatic-review/*.py` returns nothing. Of
  the nine deficit tests, none constructs a required reviewer with `reviewed: False` alongside a
  *reviewing* baseline; `test_rows_c_and_d_unassessable_when_every_baseline_refused` sets `reviewed=False`
  on the required reviewer but also on both baselines, so the `not baseline` branch short-circuits at
  `review_completeness.py:682` before the gap can be observed.
- **Impact:** The blind spot in G1 is untested in either direction, so a fix for G1 has no regression net
  and the current false-clean has nothing pinning it as intentional.
- **Task:** Add a test for the mixed shape (baseline reviewed with N > 0, required reviewer `reviewed:
  False`) asserting the verdict is not `DEFICIT_CLEAN`, and a companion asserting `required_reviewed`
  appears in the rendered TOON even when empty. Land it together with G1.
- **Done when:** the mixed shape is covered and the test fails against the current
  `verdict = DEFICIT_DEFICIT if deficit_reviewers else DEFICIT_CLEAN`.
- **Suggested grouping:** automatic-review / review_completeness — deficit signal

## G9 — Restate the refusal pre-filter positively, or record it as open residue

- **Severity:** minor
- **Kind:** omission
- **Where:** `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py:155-187`
  (`_is_refusal_notice`), and its consumer
  `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py` `fetch_findings`
- **Evidence:** `_is_refusal_notice` returns True when the body matches one of the bot's registry
  `refusal_patterns` **or** the structural `_is_rate_limit_notice` shape — an enumeration of known refusal
  phrasings, with no positive test of what a review body must contain. The plan's Claim-labels table
  records the leak as OBSERVED ("three sibling refusal bodies filtered, a fourth stored as a pending
  finding") and its Notes carry the remedy: "restate it **positively** — a stored `pr-comment` finding must
  positively look like review feedback". `report-01.md`'s Claim re-derivation row defers this with "see
  'Out of this plan (split)'" — a section that does not exist in the report (its sections are: Skills
  loaded, Claim re-derivation, Scoping decision, Deliverables, Build gate, Findings, Reviewer
  participation, Cost, Contract check, What have we learned, Residue) — and § Residue does not list it.
- **Impact:** A deferred item with a dangling cross-reference and no residue entry is a deferral nothing
  carries forward. The enumeration-versus-positive-validation defect is live in the tree and unrecorded, so
  no follow-up plan will pick it up from the report.
- **Task:** Either implement the positive restatement — require a stored `pr-comment` finding to match a
  bot's declared `actionable_content_markers` (or an equivalent positive predicate) rather than merely
  failing to match a refusal list — or, if that is judged too wide, open a spec for it in the
  `review-apparatus` epic so the deferral is recorded somewhere a planner reads.
- **Done when:** either `_is_refusal_notice`'s consumer applies a positive review-feedback predicate before
  filing a finding, or an epic spec exists naming the remedy and its trigger.
- **Suggested grouping:** workflow-integration-github — refusal pre-filter

## G10 — Record the owed architecture insight about participation artifacts

- **Severity:** minor
- **Kind:** omission
- **Where:** `marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md`
  (the natural home — § "Participation is not review quality" or § "Evidence taxonomy")
- **Evidence:** The plan's Notes state an insight this plan "should record": *a review bot's persistent
  summary card and its trigger acknowledgement are participation artifacts, not diff-derived claims —
  dispose of them as accepted without opening a fix task, and never read their presence as evidence the bot
  reviewed the current HEAD; check for a review object stamped with the live reviewed-commit SHA instead.*
  `grep -rn "summary card\|already reviewed\|trigger acknowledg\|Review finished" --include=*.md` over
  `automatic-review/` and `workflow-integration-github/` returns no output. `report-01.md` does not claim
  to have recorded it, so this is an omission rather than a false claim.
- **Impact:** The mechanical half of the insight is already enforced — the currency rule
  (`bot-participation-contract.md:207`) and `STATE_DECLINED` (`:249`) both key on the reviewed-commit SHA,
  and the `contentless_review_markers` conditional drop (`:459`) keeps a clean card from consuming a triage
  decision — but the *reasoning* is nowhere, so the next reader has to re-derive why a summary card is not
  review evidence, and the disposition guidance ("accepted, no fix task, no reply") is not written down for
  a triage agent to follow.
- **Task:** Add a short subsection to `bot-participation-contract.md` § "Participation is not review
  quality" stating the insight and cross-referencing the currency rule and the `contentless_review_markers`
  drop rather than restating their mechanics.
- **Done when:** the contract states that a persistent summary card and a trigger acknowledgement are
  participation artifacts to be disposed of as accepted without a fix task, and that their presence is
  never evidence the bot reviewed the current HEAD.
- **Suggested grouping:** automatic-review — bot-participation-contract

## G11 — Reconsider the `min_deficit` default of 1

- **Severity:** minor
- **Kind:** bug
- **Where:** `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py:616`
  and its docstring at `:641-644`; restated at `automatic-review/SKILL.md:1010` and
  `bot-participation-contract.md:548-550`
- **Evidence:** `min_deficit: int = 1`, documented as "a required reviewer that reviewed yet produced
  strictly fewer findings than a baseline reviewer that reviewed the same diff". The plan's D2 says
  "**materially** fewer findings". `test_min_deficit_threshold_is_honoured` confirms a 1-vs-2 split reports
  `DEFICIT_DEFICIT` at the default.
- **Impact:** A one-finding gap between two reviewers on the same diff is ordinary variance, not a
  reviewer-quality bug. At the default the signal will fire routinely, which is how an observability signal
  becomes noise and stops being read — the failure mode the plan's own ⛔ on cases (b) and (c) warns about,
  arriving through the threshold instead of through the baseline.
- **Task:** Either raise the default to a genuinely material gap (2 or a proportional rule) with the
  reasoning recorded in the docstring and the contract, or state explicitly why 1 is the right floor for
  this signal. The threshold is already a parameter, so only the default and its justification change.
- **Done when:** the default is either changed or defended in `bot-participation-contract.md` §
  "The comparative deficit signal", and the test pins whichever value is chosen.
- **Suggested grouping:** automatic-review / review_completeness — deficit signal

## G12 — Close D0's corpus partition, or restate the obligation as satisfied by derivability

- **Severity:** minor
- **Kind:** incomplete
- **Where:** the plan's D0 *Done when* ("the contract is written with each population published, and the
  absence corpus is **partitioned by cause**") against
  `marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md`
  § "Two axes: awaitability and CAUSE" (`:365-407`)
- **Evidence:** At the landing the contract said (`git show fd292004:…/bot-participation-contract.md:344-351`)
  "The cause partition is therefore **derivable from the tree**" and the cause member is "deliberately
  **not wired** here". No corpus was partitioned and no diff size was recovered from a merge commit, though
  the plan stated "Diff sizes are recoverable from merge commits, so this is cheaply derivable" and made
  the deliverable a HALT gate. `report-01.md` argues the HALT does not trigger because the *mechanism*
  exists — a different proposition from the one the clause states.
- **Impact:** Low today: the wiring landed in #1167 (`6ba4dace`), so the partition is now a computed signal
  and the contract at `:404-406` says so ("The partition is a computed signal, not merely a documented
  possibility"). What is still absent is any measured partition of the historical absence corpus, which is
  the input a later plan would need before reporting a per-reviewer participation rate — and the contract's
  invariant forbids reporting one until it exists.
- **Task:** Either derive the partition over a real corpus (recover each PR's diff size from its merge
  commit, attribute each observed absence to `size` or `quota`, publish both population sizes), or record
  in the contract that no historical partition has been computed and that the invariant therefore still
  blocks any participation rate.
- **Done when:** either a measured cause partition with published population sizes exists, or the contract
  states in as many words that none does and what that blocks.
- **Suggested grouping:** automatic-review — bot-participation-contract
