# Gaps — 040-canned-no-op-indistinguishable-from-a-review

Actionable follow-up derived from `verification.md`. Each entry is a task a later plan can pick up
without re-deriving the analysis.

Sixteen entries, ordered by severity: majors G1–G3, then minors G4–G16.

## G1 — Persist the reviewed-at-all classification, so the retrospective can tell reviewed-clean from nobody-reviewed

- **Severity:** major
- **Kind:** incomplete
- **Where:** `.claude/skills/finalize-step-review-retrospective/SKILL.md:151-156` (the ⚠ block that
  records the missing handoff and instructs the step to pass the flag bare), repeated at `:225-230`;
  `.claude/skills/finalize-step-review-retrospective/scripts/review_retrospective.py:153`
  (`return COMPARISON_INDETERMINATE`, the fail-closed default); the producer side is
  `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py:911`
  (`'bot_states': bot_states`) and `automatic-review/SKILL.md:700`, where the classification is read
  in-process and then discarded
- **Evidence:** `_grade_comparison` returns `COMPARISON_CLEAN` only when
  `enabled_reviewers & reviewed_reviewers` is non-empty (`review_retrospective.py:151-152`). The step
  never supplies that intersection. Its own SKILL.md says why, in as many words: *"⚠ **No persisted
  handoff of that classification currently reaches this step.** `review_completeness check` emits
  `bot_states` in its immediate TOON during the automatic-review step and the merge-gate barrier, but
  nothing persists it in a form this step can read at `order: 990` (after the merge gate). So **pass
  `--reviewed-reviewers` bare** here, and the zero-findings grade **fails closed to `indeterminate`**."*
  A whole-tree `grep -rn "bot_states" --include=*.md --include=*.py marketplace/ .claude/` returns only
  in-process reads of the classifier's immediate TOON and docstrings about it — no writer, anywhere. The
  proving test supplies the input directly (`test_review_retrospective.py:848`,
  `reviewed_reviewers=['cuioss-review-bot']`), which is why the library passes while the surface does not.
- **Impact:** This is the plan's title condition, still live on the plan's own second surface. Every
  zero-findings run — a reviewer that reviewed and found nothing, and a run where nobody reviewed —
  grades `indeterminate` and renders the single `--display-detail` string at
  `finalize-step-review-retrospective/SKILL.md:192`. D3's *Done when* is "no **surface** renders 'nobody
  reviewed' and 'reviewed clean' as the same string, proven by a test per surface"; surface 2 renders them
  as the same string on every run the workflow can actually produce. The fail-closed direction is correct
  — an unsubstantiated review must never be credited clean — so the defect is the missing handoff, not the
  grading rule.
- **Task:** Persist the reviewed-at-all set where a step ordered after the merge gate can read it. The set
  is `bot_states` filtered to `_REVIEWED_STATES` and mapped `bot_kind → author_login` through the registry
  docs — the mapping `finalize-step-review-retrospective/SKILL.md:145-149` already specifies. Write it at
  the `automatic-review` step (the classification's only producer) into a plan-scoped artifact the
  retrospective can read at `order: 990`, then have the retrospective read it instead of passing the flag
  bare. Replace the ⚠ block with the mechanism, and keep the fail-closed default for the case where the
  artifact is absent — a missing handoff must stay `indeterminate`, never become `clean`.
- **Done when:** a zero-findings run in which an enabled reviewer reviewed and found nothing renders a
  different `--display-detail` from one in which no reviewer produced content, with a test that exercises
  the *step's* path rather than `aggregate()` directly; and the ⚠ block no longer instructs the step to
  pass `--reviewed-reviewers` bare.
- **Suggested grouping:** finalize-step-review-retrospective — reviewed-at-all handoff

## G2 — Give the deficit signal a verdict for "no required reviewer reviewed", instead of rendering `clean`

- **Severity:** major
- **Kind:** bug
- **Where:** `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py:691`
  (`verdict = DEFICIT_DEFICIT if deficit_reviewers else DEFICIT_CLEAN`), the verdict constants at
  `:283-285`, the emitter's `if required_reviewed:` guard at `:1145-1149`, the module docstring's TOON
  shape at `:171` and `:175-176` ("emitted only when non-empty"), and the contract wording at
  `marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md:556-557`
- **Evidence:** Executed against the library function (no file modified):
  `rc.assess_deficit([{'bot_kind':'pr-agent','reviewed':False,'finding_count':0}, {'bot_kind':'coderabbit','reviewed':True,'finding_count':4}], required_bots=['pr-agent'])`
  returns `{'verdict': 'clean', 'baseline_max': 4, 'baseline_reviewers': ['coderabbit'],
  'required_reviewed': [], 'deficit_reviewers': []}`. `rc._emit_deficit_toon` on that payload prints
  `verdict: clean` / `baseline_max: 4` / `baseline_reviewers[1]: - coderabbit` and **no
  `required_reviewed` line at all**, because the emitter suppresses empty lists. On the `unassessable`
  payload it is worse: `baseline_reviewers` is empty too, its guard (`:1140-1144`) drops it as well, and
  the whole block is five lines carrying **no population whatsoever**. `deficit_reviewers` is built only
  over `required_reviewed`, which is filtered on `r.get('reviewed')` (`:675-678`), so a required reviewer
  that refused contributes nothing and the else-branch fires.
- **Impact:** A run in which the required reviewer refused outright and a baseline reviewer found four
  defects is reported to a reader as `clean`, with the required reviewer represented by no row. That is
  the plan's own vacuous-set archetype ("deriving rows from the responding set makes the detector's
  population a strict subset of its own domain") reproduced inside the signal built to close it — a false
  green in the one place the epic exists to remove one. It also inverts the plan's Verification demand
  ("**Publish each population size** the rule computes over, in the artifact itself") at exactly the two
  inputs where the empty population *is* the finding. The `check_deficit` CLI path partially rescues the
  first case by appending `reviewers[]` (`:1008`, printed at `:1155-1160`), but the `verdict` field — the
  value a consumer reads — still says `clean`.
- **Task:** Add a fourth verdict alongside `DEFICIT_DEFICIT` / `DEFICIT_CLEAN` / `DEFICIT_UNASSESSABLE` —
  the required-side companion of `unassessable` (a name such as `DEFICIT_REQUIRED_ABSENT`) — and return it
  from `assess_deficit` when `baseline` is non-empty and `required_reviewed` is empty. Order the branches
  so the baseline check still wins (no baseline stays `unassessable`). Make `_emit_deficit_toon` print
  `baseline_reviewers` and `required_reviewed` unconditionally, as explicit empty lists rather than omitted
  lines, so an absent population is visible instead of inferred. Then update **every** restatement of the
  three-member vocabulary in lock-step — `review_completeness.py:171` (TOON shape), `:175-176` (the
  emitted-only-when-non-empty annotations, which the fix invalidates), `:283-285`, `:646-647`
  (`assess_deficit`'s Returns), `bot-participation-contract.md:554-559`, and
  `automatic-review/SKILL.md:1021-1024` — and land the guard from G8 in the same change so the next
  widening cannot drift them apart by hand.
- **Done when:** `assess_deficit` with a reviewing baseline and zero reviewing required reviewers returns
  the new verdict (never `clean`), the rendered TOON shows both populations explicitly in that case and on
  `unassessable`, a test pins both (see G12), and all five restatements name the new member.
- **Suggested grouping:** automatic-review / review_completeness — deficit signal

## G3 — Wire the `deficit` subcommand into a workflow, or record explicitly that it is a manual surface

- **Severity:** major
- **Kind:** omission
- **Where:** `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md:999-1028` (the only
  mention, inside § "Canonical invocations"); no caller anywhere
- **Evidence:** `grep -rln "deficit" marketplace/ .claude/ doc/` (excluding `doc/plans`) returns four
  files: `tools-script-executor/SKILL.md` (an unrelated use of the word), `automatic-review/SKILL.md`,
  `bot-participation-contract.md`, and `review_completeness.py`. `grep -rn
  "check_deficit\|assess_deficit\|cmd_deficit" --include=*.py marketplace/ test/ .claude/` finds no
  non-test caller outside `review_completeness.py` itself. `bot-participation-contract.md:662` lists the
  command in § "Consumers", but that table describes what each command *reads*, not who runs it. The
  § "Canonical invocations" prose already speaks as though a step ran it — "so the step forwards the sets
  it already gathered" (`:1010`), "the step MUST NOT gate the merge on it" (`:1021`).
- **Impact:** D2's opening sentence is "A required reviewer returning materially fewer findings than a
  reviewer that actually reviewed the same diff **is reported**". In the tree, nothing reports it, because
  nothing calls it. The deliverable is a capability with no surface, and the observability the plan set out
  to add is not observable.
- **Task:** Add a step that runs it. The natural site is the `automatic-review` step's participation-guard
  block (`automatic-review/SKILL.md` § "Mark Step Complete"), immediately after the `check` call whose
  observation sets it already shares — forwarding the same flags including `--refused-causes` and
  `--refusal-size-caps`, as § "Canonical invocations → deficit" already mandates and
  `test_structural_refusal.py:799` already guards. Record the verdict as an INFO `decision` line (never as
  a gate, never in `display_detail`'s pass/fail sense) so the non-gating ceiling stays intact. If a
  workflow call is judged too costly, state that decision in `bot-participation-contract.md` § "The
  comparative deficit signal" — naming `deficit` an operator-invoked diagnostic — so the absence is a
  recorded choice rather than an unclosed deliverable.
- **Done when:** either a workflow document invokes `review_completeness deficit` and dispositions its
  verdict, or the contract states in as many words that the command is manual-only and why.
- **Suggested grouping:** automatic-review / review_completeness — deficit signal

## G4 — Bring the review-retrospective's graded `display_detail` inside the ≤80-character, plain-ASCII contract

- **Severity:** minor
- **Kind:** bug
- **Where:** `.claude/skills/finalize-step-review-retrospective/SKILL.md:190-192` (the three grade
  strings), against the contract the same file cites at `:447-448`
- **Evidence:** Measured with `len()` and `isascii()`: the `clean` string
  (`reviewed-clean — {k} reviewer(s) reviewed, 0 findings; nothing to compare`) is 72–73 characters, the
  `vacuous` string 50, and the `indeterminate` string
  (`indeterminate — 0 findings and no reviewer produced content; review-quality comparison could not be
  performed`) is **109**. All three carry a U+2014 em dash. The `indeterminate` string has no placeholder,
  so 109 is not a worst case but the only case. The governing contract is
  `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/external-step-contract.md` §
  "Required termination", whose constraint list gives "≤80 characters" (`:52`) and "Plain ASCII — no
  unicode glyphs" (`:55`) — the very document and section this skill cites at `:447-448` as its reason for
  keeping the Step 3b delta verdict *out* of `display_detail`.
- **Impact:** The skill invokes the ceiling as binding in one section and overruns it by 29 characters in
  another, on the string that carries this deliverable's headline distinction. The renderer does not
  truncate, so the overrun reaches the finalize output verbatim. It is also the string a reader sees on
  *every* zero-findings run while G1 stands.
- **Task:** Replace the em dash with an ASCII separator at all three sites and shorten the `indeterminate`
  string to ≤80 characters — the grade name plus the fact, with the reasoning left to the persisted
  artifact, which is the same division `:447-453` already argues for. Measure the rendered forms (widening
  `{k}` to its plausible maximum) and state the measured figures beside the table, as
  `phase-6-finalize/standards/branch-cleanup.md:1707` requires. Copy the shape of
  `test/plan-marshall/phase-6-finalize/test_pre_submission_self_review_verdict.py:219`,
  `test_every_verdict_fits_the_display_detail_budget`, which parses another step's SKILL.md verdict
  literals, widens every placeholder, and asserts `len <= 80`, `isascii()`, and no trailing period.
- **Done when:** every grade string is ASCII-only and ≤80 characters at its widest expansion, the
  measurement is stated in the skill, and a test parses the table and asserts the budget.
- **Suggested grouping:** finalize-step-review-retrospective — display_detail composition

## G5 — Bound the composed Branch A `display_detail` and bring it inside the ≤80-character, plain-ASCII contract

- **Severity:** minor
- **Kind:** bug
- **Where:** `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md:797`, `:800`, `:805`,
  `:850` (the em-dash template), and its own restatement of the rule at `:856`
- **Evidence:** The governing contract is
  `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/output-template.md:340` and `:343` —
  "**Max 80 characters** (softer limits encouraged; the renderer does not truncate)" and "**Plain ASCII** —
  no unicode glyphs" — repeated at
  `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/external-step-contract.md:52` and
  `:55`, with
  `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md:1707` requiring
  the length be checked "against its placeholders' **worst-case expansion**, never its literal form".
  Measured: `len('0 comment(s) found — 1 empty, 1 refused, 1 refused-structural (unified triage pending)')`
  is **86**, and `isascii()` is **False**. That case is ordinary for this repository's configured roster
  (`.plan/marshal.json:117-118`: `required_bots: pr-agent`, `optional_bots: coderabbit,sourcery` — pr-agent
  reviews clean, coderabbit rate-limits, sourcery size-refuses). The worst *three-bucket* expansion
  measures **98**, and there is no bounded worst case at all: `compose_review_state_summary` emits one
  segment per non-zero bucket (`review_completeness.py:606-610`), so a roster with one reviewer in each of
  the nine buckets renders **161**.
- **Impact:** The step emits a `display_detail` the renderer does not truncate and the contract forbids, in
  the ordinary three-reviewer case. `automatic-review/SKILL.md:856` restates the ≤80/ASCII rule inside the
  same section whose template breaks it, so the skill contradicts itself on the page.
- **Task:** Replace the em dash with an ASCII separator (`-`) at all four sites, and **bound the
  rendering** rather than only shortening labels — relabelling cannot discharge a 161-character worst case.
  Two workable shapes: drop the `(unified triage pending)` tail whenever the summary segment is present
  (the summary already tells the reader more than the tail does), and cap the summary at the N largest
  buckets with a `+K more` remainder so the rendered length has a ceiling independent of roster size.
  Shortening `refused-structural` (18 characters) and `not-triggered` (13) in `_STATE_SUMMARY_BUCKETS`
  (`review_completeness.py:294-310`) helps but does not suffice on its own. Then measure the worst-case
  expansion in the document, as `branch-cleanup.md:1707` requires, and state the measured figure.
- **Done when:** every rendered form of the Branch A `display_detail` is ASCII-only, its worst-case
  expansion over any roster size is ≤80 characters, and the measurement is stated in the skill.
- **Suggested grouping:** automatic-review — display_detail composition

## G6 — Make the retrospective's per-row `participation` distinguish reviewed-clean from never-ran

- **Severity:** minor
- **Kind:** incomplete
- **Where:** `.claude/skills/finalize-step-review-retrospective/scripts/review_retrospective.py:331`
  (`participation = 'measured' if raw_total > 0 else 'unmeasurable'`), the legend at `:380-383`, the
  row-population comment at `:312-317`, and the SKILL.md restatements at
  `.claude/skills/finalize-step-review-retrospective/SKILL.md:246-251` and `:306-316`
- **Evidence:** The row classifier reads only `raw_total`. A reviewer that reviewed and found nothing files
  no `pr-comment` records, so it renders `participation: unmeasurable` — the identical string a reviewer
  that never ran renders. The landing's own test says so:
  `test/plan-marshall/finalize-step-review-retrospective/test_review_retrospective.py:697`,
  `test_enabled_reviewer_with_no_findings_gets_an_unmeasurable_row`: *"'produced nothing', 'never ran', and
  'enabled-invoked-refused' all leave no record; without a row they render identically."*
  `SKILL.md:306-307` instructs the LLM pass to "classify each reviewer into exactly one of two states",
  so the two-valued field is restated as the contract downstream as well.
- **Impact:** A reader scanning the per-reviewer table — rather than the `comparison` grade above it —
  cannot tell a reviewer that did its pass and found nothing from one that never ran. #1170 (`b286928c`)
  closed this at the **aggregate** level by adding `_grade_comparison` (`:108-153`); the per-row field was
  not revisited, even though the signal it needs is already a parameter of the same `aggregate()` call
  (`:216-217`). This is the smaller half of G1's root cause and is inert until G1 lands, because the step
  supplies no `reviewed_reviewers`.
- **Task:** Thread `reviewed_reviewers` into the row loop. Classify each row over at least three values
  rather than two: `measured` (records exist), a positively-substantiated reviewed-but-silent value (the
  author is in `reviewed_reviewers` — a legitimate no-op, never scored), and `unmeasurable` (enabled, no
  record, no reviewed-at-all signal). Introduce `PARTICIPATION_*` constants and key the
  `participation_states` legend off them rather than off string literals, matching the `comparison_states`
  pattern at `:386-391` — whose own comment gives the reason ("the serialized legend cannot drift from the
  grades `_grade_comparison` can assign"). Update the SKILL.md participation table so the LLM pass reads
  the three-way field. Sequence after G1; without the handoff the third value is unreachable.
- **Done when:** `aggregate([], enabled_reviewers=['a','b'], reviewed_reviewers=['a'])` gives `a` and `b`
  different `participation` values, and a test asserts the two differ — the row-level counterpart of
  `test_nobody_reviewed_and_reviewed_clean_render_differently`.
- **Suggested grouping:** finalize-step-review-retrospective — participation rendering

## G7 — Guard that every taxonomy member has a display bucket

- **Severity:** minor
- **Kind:** missing-test
- **Where:** `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py:294-310`
  (`_STATE_SUMMARY_BUCKETS`) and `:602-611` (`compose_review_state_summary`)
- **Evidence:** `compose_review_state_summary` tallies every state into `counts` (`:602-605`) but emits only
  the states enumerated in `_STATE_SUMMARY_BUCKETS` (`:607-610`); an unbucketed state is silently dropped.
  Confirmed by execution: a two-bot roster carrying one unbucketed state renders `'1 refused'`, tallying to
  one for a population of two. `grep -rn "_STATE_SUMMARY_BUCKETS" test/ marketplace/ .claude/` returns three
  hits, all inside `review_completeness.py` — no test references the constant, and none asserts the bucket
  union covers the taxonomy.
- **Impact:** A taxonomy member added without a bucket vanishes from `review_state_summary`, so the tally
  stops summing to the roster size and a reader sees "2 refused" for a three-reviewer roster with no
  indication a reviewer is unaccounted for — an under-report of exactly the kind this plan exists to
  prevent. The hazard is live: the taxonomy gained `refused_structural` in #1167 and the bucket list was
  updated by hand, not by a failing test. The union is correct today (eleven bucketed states, eleven
  members, verified by set comparison), which is a survival by attention rather than by guard. The sibling
  drift guard for the taxonomy prose already exists
  (`test/plan-marshall/automatic-review/test_bot_participation_contract.py:501`), so the pattern to copy is
  in the same directory.
- **Task:** Add a test asserting that the union of the state tuples in `_STATE_SUMMARY_BUCKETS` equals the
  full member set (`_UNPROVEN_STATES | {STATE_PARTICIPATED, STATE_PARTICIPATED_BUT_EMPTY}`), and a second
  asserting that the bucket counts sum to `len(bot_states)` for a roster containing one bot in every member.
- **Done when:** adding a `STATE_*` constant to the taxonomy without adding it to `_STATE_SUMMARY_BUCKETS`
  fails a test.
- **Suggested grouping:** automatic-review / review_completeness — display buckets

## G8 — Extend the count guards to the restatements they do not reach

- **Severity:** minor
- **Kind:** missing-test
- **Where:** `test/plan-marshall/automatic-review/test_bot_participation_contract.py:501`
  (`test_the_contracts_closure_count_agrees_with_the_derived_member_count`) and its regex
  `_CLOSURE_COUNT` at `:174`
- **Evidence:** The guard applies `re.compile(r'classified into exactly one of (?P<count>\w+) members')` to
  the contract's own § "Failure taxonomy" only, and its docstring says so at `:528-529`: *"The
  closure-count check above reads the CONTRACT doc's one closure sentence, so a count restated anywhere
  else is outside its reach."* A whole-tree sweep finds **seven** taxonomy-count statements, all correct
  today: `bot-participation-contract.md:52` (the guarded one) and `:73`, `review_completeness.py:189`,
  `workflow-pr-doctor/standards/automated-review-lifecycle.md:56`,
  `phase-6-finalize/workflow/create-pr.md:201`, `automatic-review/SKILL.md:24`, and
  `tools-integration-ci/standards/pr-review-operations.md:248` — so **six** sit outside the guard. The
  sibling sweep at `:525` covers the whole tree but for `N blocking members`, a different and strictly
  smaller quantity. The same shape now exists one level down: the three-member deficit verdict vocabulary
  is restated at five sites — `review_completeness.py:171`, `:283-285`, `:646-647`,
  `bot-participation-contract.md:554-559`, `automatic-review/SKILL.md:1021-1024` — with no guard reading
  any of them.
- **Impact:** Those six taxonomy restatements are exactly the class of site the landing run's own
  verification sub-agent had to correct by hand when the taxonomy went from eight members to nine, and the
  five verdict restatements are the sites G2's fourth verdict will have to reach. A count restated in prose
  and guarded nowhere is the misleading-signal defect this epic exists to remove, one level of indirection
  out.
- **Task:** Widen the existing guard from one document to a tree-wide sweep. The `automated-review-lifecycle.md:56`
  wording already matches `_CLOSURE_COUNT` verbatim, so most of the reach comes free; add a second pattern
  for the `N-member` / `N non-participation members` forms and assert every match against
  `len(_NON_PARTICIPATION_MEMBERS)`. Add the same shape for the deficit verdict vocabulary, deriving the
  expected member set from the `DEFICIT_*` constants rather than a transcribed list. Keep the
  zero-match-is-a-pass rule the sibling guard at `:525` uses, with its population guard so the pass cannot
  go vacuous.
- **Done when:** changing the taxonomy's cardinality, or the deficit verdict set, without updating every
  prose restatement fails a test.
- **Suggested grouping:** automatic-review — count drift guards

## G9 — Restore the omitted flag to `review_completeness.py`'s own `deficit` usage line

- **Severity:** minor
- **Kind:** stale-doc
- **Where:** `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py:116`
  (the module docstring's `deficit` `Usage:` line), against `:115` (the `check` line) and `:1434` (where
  the flag is registered, inside `_add_bot_observation_flags` at `:1298`)
- **Evidence:** `:115` carries `[--refusal-size-caps [<csv>]]`; `:116` does not, though `deficit_parser`
  calls `_add_bot_observation_flags` (`:1525`) and therefore accepts it.
  `automatic-review/SKILL.md:1010-1018` marks the flag ⛔ **"the load-bearing one: a cap arriving WITHOUT
  its cause drives the fail-closed cause recovery, so a caller that passes it to `check` but not `deficit`
  reproduces exactly the disagreement the pair exists to prevent"**. The SKILL.md invocation block is
  machine-guarded against precisely this omission —
  `test/plan-marshall/automatic-review/test_structural_refusal.py:799`,
  `test_the_deficit_invocation_block_documents_the_cap_flag`, whose docstring notes that "plugin-doctor
  cannot catch it, because it validates documented invocations against the parser, not the parser against
  the docs" — but that guard reads `SKILL.md` and nothing else.
- **Impact:** The script's own docstring is the second documented invocation surface, and it prescribes the
  exact call the guarded surface forbids. A caller following it passes the cap to `check` and not to
  `deficit`, and the two commands then name different members for one bot's refusal — the disagreement
  `check_deficit`'s docstring calls one "no reader of the output could adjudicate".
- **Task:** Add `[--refusal-size-caps [<csv>]]` to the `deficit` `Usage:` line, and extend
  `test_the_deficit_invocation_block_documents_the_cap_flag` (or add a sibling) to read the module
  docstring's `Usage:` lines as well as the SKILL.md block, so both documented surfaces are guarded by the
  same assertion.
- **Done when:** both documented `deficit` invocations carry the flag, and a test fails if either drops it.
- **Suggested grouping:** automatic-review / review_completeness — deficit signal

## G10 — Make the empty-roster `display_detail` fallback state that no reviewer was configured

- **Severity:** minor
- **Kind:** incomplete
- **Where:** `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md:798` (the fallback form)
  and `review_completeness.py:611` (`compose_review_state_summary`'s join, empty when no bucket is
  non-zero), with the rationale in its docstring at `:597-600`
- **Evidence:** With an empty roster the summary is `''` (confirmed by execution, and pinned by
  `test_review_completeness.py:1931`, `assert result['review_state_summary'] == ''`), and `SKILL.md:798`
  prescribes falling back to `"{N} comment(s) found (unified triage pending)"` — character-for-character
  the string the plan's Problem section quotes as the defect. `automatic-review/SKILL.md:648` states that
  `required_bots` and `optional_bots` "both default EMPTY", so an unconfigured consumer project takes this
  path always.
- **Impact:** In the documented default configuration the fix is inert and the collapsed string returns.
  Returning `''` from the composer is defensible (inventing a bucket for reviewers that were never
  configured would be a claim about nothing), but the *display string* still reads to a cold reader as "a
  review happened and found nothing".
- **Task:** Give the empty-roster case its own honest rendering at the composition site rather than at the
  composer — e.g. `"{N} comment(s) found - no reviewers configured"` — leaving
  `compose_review_state_summary`'s `''` return and its rationale unchanged. Keep it ASCII and within the
  80-character bound (see G5).
- **Done when:** a run with an empty reviewer roster renders a `display_detail` that differs from the one a
  reviewed-clean run renders, and a test pins the difference.
- **Suggested grouping:** automatic-review — display_detail composition

## G11 — Correct the Branch A illustration that describes an unreachable state

- **Severity:** minor
- **Kind:** stale-doc
- **Where:** `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md:800`
- **Evidence:** The sentence reads, verbatim, "So a run where three required reviewers all refused renders
  `"0 comment(s) found — 3 refused (unified triage pending)"`". But every refusal member is in
  `_UNPROVEN_STATES` (`review_completeness.py:252-264`), `participation_complete = not required_unproven`
  (`:865`), and `SKILL.md:789` states Branch A is "entered only after the participation guard above returns
  `participation_complete: true`, or a force-done WARNING was recorded". Three refusing *required*
  reviewers therefore route to Branch C (loop-back, `SKILL.md:824`), not Branch A.
- **Impact:** The deliverable's headline example describes a path its own branch cannot normally take, so a
  reader calibrating on it mis-models when the new string appears. The ordinary case for "3 refused" is
  three refusing *optional* reviewers, or a force-done.
- **Task:** Rewrite the sentence to use refusing **optional** reviewers (or a required set satisfied
  alongside refusing optional ones), and note the force-done hatch as the only way a refusing required set
  reaches Branch A.
- **Done when:** the illustration names a configuration that reaches Branch A under the guard stated eleven
  lines above it.
- **Suggested grouping:** automatic-review — SKILL.md accuracy

## G12 — Test the required-reviewer-did-not-review case of the deficit signal

- **Severity:** minor
- **Kind:** missing-test
- **Where:** `test/plan-marshall/automatic-review/test_review_completeness.py`, class `TestDeficitSignal`
  (`:1939-2067`, nine tests)
- **Evidence:** `grep -rn "required_reviewed" test/` returns nothing. Of the nine deficit tests, none
  constructs a required reviewer with `reviewed: False` alongside a *reviewing* baseline;
  `test_rows_c_and_d_unassessable_when_every_baseline_refused` (`:1982`) sets `reviewed=False` on the
  required reviewer but also on both baselines, so the `not baseline` branch short-circuits at
  `review_completeness.py:681` before the gap can be observed, and
  `test_row_e_clean_zero_to_zero_with_a_real_baseline` (`:1972`) leaves the required reviewer's default
  `reviewed=True` in place.
- **Impact:** The blind spot in G2 is untested in either direction, so a fix for G2 has no regression net
  and the current false-clean has nothing pinning it as intentional.
- **Task:** Add a test for the mixed shape (baseline reviewed with N > 0, required reviewer
  `reviewed: False`) asserting the verdict is not `DEFICIT_CLEAN`, and a companion asserting both
  `baseline_reviewers` and `required_reviewed` appear in the rendered TOON even when empty. Land it
  together with G2.
- **Done when:** the mixed shape is covered and the test fails against the current
  `verdict = DEFICIT_DEFICIT if deficit_reviewers else DEFICIT_CLEAN`.
- **Suggested grouping:** automatic-review / review_completeness — deficit signal

## G13 — Restate the refusal pre-filter positively, or record it as open residue

- **Severity:** minor
- **Kind:** omission
- **Where:** `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py:155-187`
  (`_is_refusal_notice`), and its consumer
  `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py` `fetch_findings`
- **Evidence:** `_is_refusal_notice` returns True when the body matches one of the bot's registry
  `refusal_patterns` **or** the structural `_is_rate_limit_notice` shape (`:185-187`) — an enumeration of
  known refusal phrasings, with no positive test of what a review body must contain. The plan's
  Claim-labels table records the leak as OBSERVED ("three sibling refusal bodies filtered, a fourth stored
  as a pending finding") and its Notes carry the remedy: "restate it **positively** — a stored `pr-comment`
  finding must positively look like review feedback". `report-01.md`'s Claim re-derivation row defers this
  with "see 'Out of this plan (split)'" — a section that does not exist in the report (its eleven sections
  are: Skills loaded, Claim re-derivation, Scoping decision, Deliverables, Build gate, Findings, Reviewer
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

## G14 — Record the owed architecture insight about participation artifacts

- **Severity:** minor
- **Kind:** omission
- **Where:** `marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md`
  (the natural home — § "Participation is not review quality" at `:272`)
- **Evidence:** The plan's Notes state an insight this plan "should record": *a review bot's persistent
  summary card and its trigger acknowledgement are participation artifacts, not diff-derived claims —
  dispose of them as accepted without opening a fix task, and never read their presence as evidence the bot
  reviewed the current HEAD; check for a review object stamped with the live reviewed-commit SHA instead.*
  `grep -rn "summary card\|already reviewed\|trigger acknowledg\|Review finished" --include=*.md` over
  `automatic-review/` and `workflow-integration-github/` returns no output; widened to
  `"participation artifact\|persistent summary\|not diff-derived\|acknowledgement"` it returns two
  unrelated hits (`coderabbit.md:98`, `bot-participation-contract.md:520`). `report-01.md` does not claim
  to have recorded it, so this is an omission rather than a false claim.
- **Impact:** The mechanical half of the insight is already enforced — the currency rule
  (`bot-participation-contract.md:207`) and `STATE_DECLINED` (`:249`) both key on the reviewed-commit SHA,
  and the `contentless_review_markers` conditional drop (`:459`) keeps a clean card from consuming a triage
  decision — but the *reasoning* is nowhere, so the next reader has to re-derive why a summary card is not
  review evidence, and the disposition guidance ("accepted, no fix task, no reply") is not written down for
  a triage agent to follow. § "Obligation 3 — only diff-derived evidence discharges a review obligation"
  (`:307`) is the nearest existing prose and covers *body-derived* signals, not bot-produced participation
  artifacts.
- **Task:** Add a short subsection to `bot-participation-contract.md` § "Participation is not review
  quality" stating the insight and cross-referencing the currency rule and the `contentless_review_markers`
  drop rather than restating their mechanics.
- **Done when:** the contract states that a persistent summary card and a trigger acknowledgement are
  participation artifacts to be disposed of as accepted without a fix task, and that their presence is
  never evidence the bot reviewed the current HEAD.
- **Suggested grouping:** automatic-review — bot-participation-contract

## G15 — Reconsider the `min_deficit` default of 1

- **Severity:** minor
- **Kind:** bug
- **Where:** `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py:617`
  and its docstring at `:640-643`; the only restatement of the default is
  `automatic-review/SKILL.md:1011`
- **Evidence:** `min_deficit: int = 1`, documented as "a required reviewer that reviewed yet produced
  strictly fewer findings than a baseline reviewer that reviewed the same diff". The plan's D2 says
  "**materially** fewer findings", and the contract repeats "materially" at `:538` and `:555` without ever
  naming the threshold — `grep -rn "min_deficit\|min-deficit"` over `bot-participation-contract.md` returns
  nothing. Confirmed by execution: a 1-vs-2 split returns `deficit` at the default, and
  `test_min_deficit_threshold_is_honoured` (`:2017`) pins that behaviour.
- **Impact:** A one-finding gap between two reviewers on the same diff is ordinary variance, not a
  reviewer-quality bug. At the default the signal will fire routinely, which is how an observability signal
  becomes noise and stops being read — the failure mode the plan's own ⛔ on cases (b) and (c) warns about,
  arriving through the threshold instead of through the baseline.
- **Task:** Either raise the default to a genuinely material gap (2, or a proportional rule) with the
  reasoning recorded in the docstring and the contract, or state explicitly why 1 is the right floor for
  this signal. The threshold is already a parameter, so only the default and its justification change.
- **Done when:** the default is either changed or defended in `bot-participation-contract.md` §
  "The comparative deficit signal", and the test pins whichever value is chosen.
- **Suggested grouping:** automatic-review / review_completeness — deficit signal

## G16 — Close D0's corpus partition and D2's charter attribution, or restate both as satisfied by derivability

- **Severity:** minor
- **Kind:** incomplete
- **Where:** the plan's D0 *Done when* ("the contract is written with each population published, and the
  absence corpus is **partitioned by cause**") and D2's instruction-boundary clause ("D0 must establish,
  per PR in the corpus, which charter the reviewer was running"), against
  `marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md`
  § "Two axes: awaitability and CAUSE" (`:365-405`) and § "Do not pool measurements" (`:563-567`)
- **Evidence:** At the landing the contract said (`git show fd292004:…/bot-participation-contract.md:344-351`)
  "The cause partition is therefore **derivable from the tree**" and the cause member is "deliberately
  **not wired** here". No corpus was partitioned and no diff size was recovered from a merge commit, though
  the plan stated "Diff sizes are recoverable from merge commits, so this is cheaply derivable" and made
  the deliverable a HALT gate. `report-01.md` argues the HALT does not trigger because the *mechanism*
  exists — a different proposition from the one the clause states. For the charter axis, `grep -rni
  "charter"` across `marketplace/`, `.claude/`, and `test/` finds the invariant stated at `:566` and no
  per-PR attribution anywhere.
- **Impact:** Low today: the cause wiring landed in #1167 (`6ba4dace`), so the partition is now a computed
  signal and the contract says so at `:404` ("The partition is a computed signal, not merely a documented
  possibility"). What is still absent is any *measured* partition of the historical absence corpus, and any
  per-PR charter attribution — together the inputs a later plan needs before reporting a per-reviewer
  participation rate, which the contract's own invariant at `:402-404` forbids until they exist.
- **Task:** Derive both, or record that neither exists. The charter axis is nearly free:
  `git log -- marketplace/targets/pr_agent/target.py` returns exactly one commit, `f5493b43` (#1130,
  "route review charters by repository domain"), so every PR merged before it ran the pre-charter
  instructions and every PR after ran the domain-scoped packs — a two-bucket partition by merge date
  against one SHA. For the cause axis, recover each PR's diff size from its merge commit, attribute each
  observed absence to `size` or `quota`, and publish both population sizes. If either is declined, record
  in the contract that no measured partition exists and that the invariant therefore still blocks any
  participation rate.
- **Done when:** either both partitions exist with published population sizes, or the contract states in as
  many words that they do not and what that blocks.
- **Suggested grouping:** automatic-review — bot-participation-contract
