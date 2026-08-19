> ⛔ **FIRST INSTRUCTION — do not skip, do not delete, do not move below the title.**
>
> Before reading the rest of this plan and before any other action, load the working contract that
> governs this run:
>
> ```text
> Skill: cloud-plan-lane
> ```
>
> It owns the branch/PR/review-comment cycle, the build gate, the pre-PR verification sub-agent, the
> run report, and the closing self-check. **Nothing in this plan overrides it** — where this plan and
> the contract disagree, the contract wins, and the disagreement is reported.
>
> If the skill cannot be loaded, **stop and report the run blocked**. Do not reconstruct the workflow
> from this file: the parts that matter most — the merge gate, the verification dispatch, the report
> — are not in here.
>
> This block is part of the plan, not part of the template. It survives into every copy.

# Nobody-reviewed and reviewed-clean become two signals, on both surfaces that claim to separate them

**Epic:** review-apparatus
**Branch prefix:** fix

## Problem

Two surfaces in this repository exist specifically to tell *"a reviewer ran the diff and found
nothing"* apart from *"no reviewer produced anything"*. Both still render the two facts identically,
and they do it for one shared reason.

**Surface 1 — the comparative deficit signal.**
`marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py`,
`assess_deficit`, ends with `verdict = DEFICIT_DEFICIT if deficit_reviewers else DEFICIT_CLEAN`
(around line 691). `deficit_reviewers` is built only over `required_reviewed`, and
`required_reviewed` is filtered on `r.get('reviewed')` (around lines 675–678). So a required
reviewer that never reviewed contributes no row, the loop body never executes, and the `else` branch
fires: the function returns **`clean`** for a run in which the required reviewer refused outright
while a baseline reviewer found four defects. The rendered TOON makes it worse rather than better —
`_emit_deficit_toon` (around lines 1140–1149) prints `baseline_reviewers` and `required_reviewed`
**only when non-empty**, so the population that is empty — the one that *is* the finding — is the
one the reader never sees. On the `unassessable` payload both lists are empty and the whole block
carries no population at all. Nothing in the tree calls `deficit` either: the only occurrence of the
invocation is inside `automatic-review/SKILL.md` § "Canonical invocations" (around line 1002), so the
signal has no surface even when it is right.

**Surface 2 — the review-retrospective `comparison` grade.**
`.claude/skills/finalize-step-review-retrospective/scripts/review_retrospective.py`,
`_grade_comparison` (around lines 147–153), returns `COMPARISON_CLEAN` only when
`enabled_reviewers & reviewed_reviewers` is non-empty. That intersection is empty at every real
invocation, because **nothing in the repository ever computes or writes `reviewed_reviewers`**. The
step's own skill says so in as many words, at
`.claude/skills/finalize-step-review-retrospective/SKILL.md` around lines 151–156 and repeated
around 225–230: *"⚠ No persisted handoff of that classification currently reaches this step …
So pass `--reviewed-reviewers` bare here, and the zero-findings grade fails closed to
`indeterminate`."* So the deployed grade takes exactly one value — `indeterminate` — over the whole
zero-findings population it is computed on, and therefore distinguishes nothing there. The
fail-closed *direction* is correct and must be preserved; the defect is the missing input, never the
grading rule.

**The shared cause is a missing handoff.** `review_completeness.check_completeness` computes the
reviewed-at-all classification and returns it as `bot_states` (around line 911); `automatic-review`
reads it in-process (`automatic-review/SKILL.md` around line 700) and discards it. A whole-tree sweep
for `bot_states` returns **only** in-process reads, prose about them, and test assertions — **no
writer anywhere**. The retrospective runs at `order: 990`, after the merge gate, in a process that
never saw that TOON. So the one fact both surfaces need — *did this reviewer review the diff at
all?* — is produced once, consumed once, and never persisted. Surface 1 fails by inferring it from
the wrong operand; surface 2 fails by not having it at all.

Two further shapes ride on the same cause and are fixed with it. First, **an empty required
population rendered as a positive result** appears on *both* envelopes of the same script:
`assess_deficit` returns `clean` over an empty `required_reviewed`, and `check_completeness` returns
`participation_complete: true` over an empty `required_bots` with no field a consumer can use to tell
a vacuous quorum from a satisfied one (see the return dict around lines 902–925 — it carries no
vacuous marker and no provenance). Second, the retrospective **grades on the operand it says it must
not**: `aggregate` passes `len(records)` into `_grade_comparison` (around lines 360–364) while the
module's own contract is that META records "never inflate `actionable_count`", so a store holding
only a walkthrough and an "Actionable comments posted: 0" summary grades `measured` — *"the
comparison was performed"* — with zero actionable content compared.

Every claim in this section was read at HEAD; the detailed evidence, with the executions that
produced it, is in the two `gaps.md` files named under Notes.

## Goal

The reviewed-at-all classification is produced once, persisted where a post-merge-gate step can read
it, and consumed by both surfaces. A required reviewer that did not review can no longer be reported
as `clean` by the deficit signal or as a benign no-op by the retrospective, and every verdict either
surface renders names the population it was computed over — including when that population is empty.
The strings a human actually reads at the end of a finalize run fit the contract they cite and say
which of the two facts occurred.

## Deliverables

Seven items: a gating **D0** that establishes the plan's premise or halts, and six work
deliverables. Each names the gap ids it discharges, so nothing is silently dropped, and each carries
an observable *Done when*. Gap ids are written `040/G2` and `050/G3` — see Notes for the two source
files. **Every line number in this plan is a lead**: re-derive it by reading the file before editing.

### D0 — Derive the handoff's populations and its persistence channel, or HALT

**This is a stop condition, not a survey.** D1–D3 rest on the premise that the reviewed-at-all
handoff can be built entirely from things already derivable from the tree. Establish all four legs
below by reading the repository. **If any leg cannot be derived, stop, write what failed into the run
report, and do not proceed to D1.** In particular: **do not author a hand-maintained
`bot_kind → author_login` list, and do not hard-code a reviewer roster anywhere.** A transcribed
reviewer list is the same defect class this plan is closing, so a fallback of that shape would
rebuild the defect inside the fix.

1. **The reviewed-at-all set is derivable from the classifier.** `_REVIEWED_STATES` in
   `review_completeness.py` (around line 279) is the predicate — confirm its members and confirm
   `bot_states` rows carry `{bot_kind, state}`.
2. **`bot_kind → author_login` is machine-readable.** `automatic-review/scripts/bot_registry.py`
   exposes the mapping (there is a login map and a `bot_kind_for_login` helper around lines 546 and
   605), sourced from the per-bot registry docs
   `automatic-review/standards/{bot_kind}.md`. Re-derive **how many** registry docs exist by listing
   that directory — do not trust any count stated here or in the gaps files.
3. **The required set is separable from the enabled roster.** `required_bots` and `optional_bots` are
   distinct configured lists, and `bot_lists_provenance` is a three-valued key
   (`never_asked` / `migrated` / `answered`) — confirm from `manage-config/SKILL.md` (around line
   762) and `manage-config/standards/data-model.md`.
4. **A plan-scoped artifact channel exists that spans the two steps.** `plan-marshall:manage-files`
   has `write` and `read` verbs over plan-directory files. Confirm both, and confirm the
   retrospective already reads and writes plan-dir artifacts by that route (its Step 4 uses
   `manage-files write`).

*Done when:* the run report states, per leg, the file and symbol that settled it and the value
derived — or states which leg failed and that the plan halted there. No `bot_kind → author_login`
pair is written as a literal into any file this plan changes.

### D1 — Build the reviewed-at-all handoff, producer to consumer

**Gaps: 040/G1, 050/G2, 050/G9.**

The missing write, both ends of it, and the instructions that currently prescribe the workaround.

- **Producer.** At the `automatic-review` step — the classification's only producer, at the point it
  already reads `bot_states` (`automatic-review/SKILL.md` around line 700, fed by the
  `review_completeness check` call around line 676) — persist the reviewed-at-all set as a plan-dir
  artifact via `manage-files write`. The set is `bot_states` filtered to `_REVIEWED_STATES` and
  mapped `bot_kind → author_login` through the registry (the mapping the retrospective's skill
  already specifies around lines 145–149). Persist the **required** and **optional** classifications
  alongside it, since D2 needs them.
- **Consumer.** Have `finalize-step-review-retrospective` read that artifact and pass the real value
  to `--reviewed-reviewers`, at both invocation sites (SKILL.md around lines 166–170 and 232–236).
  **Keep the fail-closed default**: when the artifact is absent or unreadable, the flag stays bare
  and the grade stays `indeterminate`. A missing handoff must never become `clean`.
- **Remove the workaround text.** Replace the ⚠ block at SKILL.md ~151–156 and its repeat at ~225–230
  with the mechanism. No sentence may still instruct the flag to be passed bare as the normal path.
- **Fix the placeholders (050/G9).** `{reviewed_author_logins}` appears in both bash blocks and is
  defined nowhere, so an agent following the block literally passes the literal token, which the CSV
  split turns into a fabricated `author_login` that is then echoed in the payload. Define it beside
  the existing `{enabled_author_logins}` derivation (around lines 209–218), in the same
  derive-never-transcribe style. Also define `{k}` in the `clean` display-detail row (around line
  190).

*Done when:* a test exercises the **step's** path — not `aggregate()` directly — and shows that a
zero-findings run in which an enabled reviewer is present in the persisted artifact produces a
different `--display-detail` from one in which the artifact is absent or names no reviewer; the ⚠
block is gone; and no placeholder in either invocation block is undefined in the skill.

### D2 — Make the `comparison` grade compute over the populations it names

**Gaps: 050/G1, 050/G3, 050/G6, 050/G7, 050/G8, 040/G6.**

Every item here is one shape: *a field asserting something the code did not read, or read from the
wrong operand.*

- **Grade on the actionable count, not the raw store size (050/G1).** `aggregate` passes
  `len(records)` into `_grade_comparison` (around lines 360–364) while the module contract is that
  META records never inflate `actionable_count`. Compute the operand from the same `_is_actionable`
  predicate the per-reviewer loop already applies — one predicate, no second notion of "a real review
  comment" — and emit it as a first-class payload field beside `total_findings` so the grade's
  operand is visible. Rewrite the `measured` legend to name *actionable* findings. Then route
  `SKILL.md` on the **grade** rather than on `filtered_count` (the gate around line 134), so a
  META-only store reaches the graded display-detail table (around lines 188–192) instead of the
  ungraded fallback (around line 443); that table has no `measured` row today — add one, and give the
  fallback a grade-aware form.
- **Make `clean` required-denominated (050/G3).** `_grade_comparison` earns `clean` on **any** member
  of `required_bots ∪ optional_bots` being substantiated, so a silent required reviewer beside a
  reviewed-clean optional one grades `clean`. Give the aggregator the required set as its own input
  (a `--required-reviewers` flag carrying `author_login` values) and split the grade: `clean`
  requires a **required** reviewer to be substantiated; where only optional reviewers are, emit a
  distinct grade and name its population in `comparison_states`. **Do not narrow
  `enabled_reviewers`** — the row domain stays the enabled roster, which is a landed contract
  (`bot-participation-contract.md` § "The counting rule"). This defect is latent while D1 is unbuilt
  and goes live the instant D1 lands, which is why the two ship together.
- **Split `vacuous` on provenance (050/G7).** `if not enabled_reviewers: return COMPARISON_VACUOUS`
  is glossed *"no reviewer roster configured"*, but `never_asked` — the default for any project that
  has not run the wizard — renders as the deliberate operator answer *none*. Pass
  `bot_lists_provenance` in and split `vacuous` into the answered-empty case and an unestablished
  case for `never_asked`/`migrated`. The house pattern already exists and is to be mirrored rather
  than reinvented: `phase-6-finalize/workflow/create-pr.md` around lines 253–257 splits exactly this
  pair for the `skip-bot-review` label ("**A never-asked posture does NOT mean 'skip review'** … Fail
  toward being reviewed").
- **Distinguish roster-absent from roster-empty (050/G8).** `--enabled-reviewers` is
  `nargs='?', const='', default=''` (around lines 434–448), so **omitted**, **bare**, and
  **explicitly empty** all reach `aggregate` as the same empty list — and the grade then publishes
  *"no reviewer roster configured"*, a configuration fact the run never read. Change `default=None`
  (keeping `const=''` so the bare form still means the deliberate empty roster), thread the
  three-valued input through, and grade an unsupplied roster as `indeterminate` or a named
  `roster_unknown`. Emit the distinguishing input as a payload field, and correct the legend so
  `vacuous` claims only what was read.
- **Make the per-row `participation` three-valued (040/G6).** `participation = 'measured' if
  raw_total > 0 else 'unmeasurable'` (around line 331) reads only `raw_total`, so a reviewer that
  reviewed and found nothing renders the identical string to one that never ran. Thread
  `reviewed_reviewers` into the row loop and classify over at least three values: `measured`,
  a positively-substantiated reviewed-but-silent value (never scored), and `unmeasurable`. Introduce
  `PARTICIPATION_*` constants and key the `participation_states` legend off them rather than off
  string literals, matching the `comparison_states` pattern whose own comment gives the reason.
  Update the SKILL's participation table (around lines 306–316), which currently instructs the LLM
  pass to "classify each reviewer into exactly one of two states".
- **Carry the grade into the persisted artifact (050/G6).** The skill states (around lines 196–197)
  that the grade "lives in the `--display-detail` and the persisted artifact", but Step 4's artifact
  spec (around lines 388–425) never names `comparison` or `comparison_states`. Add them, with the
  `enabled_reviewers` / `reviewed_reviewers` / required populations beside them, in the same
  figure-beside-its-population style the delta section already uses — so the grade can be trended
  across PRs rather than surviving only in one truncated status line.

*Done when:* (a) an aggregate over a store of only `issue_comment`/status-summary records with a
configured roster and no reviewed-at-all signal returns `indeterminate`; (b) a zero-findings
aggregate with the required reviewer absent and an optional one present does not return `clean`;
(c) an empty roster with provenance `never_asked` does not grade identically to one with provenance
`answered`; (d) an invocation that omits `--enabled-reviewers` does not grade identically to one that
passes it bare; (e) `aggregate([], enabled_reviewers=['a','b'], reviewed_reviewers=['a'])` gives `a`
and `b` different `participation` values; (f) Step 4 names the grade, and no sentence in the skill
claims the artifact carries something Step 4 does not instruct it to write. A test pins each of
(a)–(e).

### D3 — Stop rendering an empty required population as a positive result

**Gaps: 040/G2, 040/G3, 040/G12, 050/G13.**

The same defect on two envelopes of `review_completeness.py`, plus the wiring that makes the first
one observable at all.

- **A fourth deficit verdict (040/G2).** Add the required-side companion of `unassessable` — a name
  such as `DEFICIT_REQUIRED_ABSENT` — alongside `DEFICIT_DEFICIT` / `DEFICIT_CLEAN` /
  `DEFICIT_UNASSESSABLE` (around lines 283–285), and return it from `assess_deficit` when `baseline`
  is non-empty and `required_reviewed` is empty. Order the branches so the baseline check still wins:
  no baseline stays `unassessable`.
- **Publish the empty populations (040/G2).** Make `_emit_deficit_toon` print `baseline_reviewers`
  and `required_reviewed` **unconditionally**, as explicit empty lists rather than omitted lines, so
  an absent population is visible instead of inferred. This is the plan's own principle applied to
  its own output: the empty population is the finding.
- **Update every restatement in lock-step (040/G2).** The three-member vocabulary is restated at five
  sites — `review_completeness.py` around lines 171 (the TOON shape), 175–176 (the
  "emitted only when non-empty" annotations, which this fix invalidates), 283–285, and 646–647
  (`assess_deficit`'s Returns); `bot-participation-contract.md` around lines 554–559; and
  `automatic-review/SKILL.md` around lines 1021–1024. **Re-derive that list by searching the tree** —
  the number of sites is a lead, not a fact.
- **Give the signal a caller (040/G3).** Nothing in the tree invokes `deficit`; the only occurrence
  is the § "Canonical invocations" block. Add the call to the `automatic-review` step's
  participation-guard block, immediately after the `check` call whose observation sets it already
  shares, forwarding the same flags **including `--refused-causes` and `--refusal-size-caps`**.
  Record the verdict as an INFO `decision` line — never as a gate, never in `display_detail`'s
  pass/fail sense — so the non-gating ceiling stated in the envelope (`gates_merge: false`,
  `proves: reviewer_quality_only`) stays intact.
- **Test the blind spot (040/G12).** No test in the tree constructs a required reviewer with
  `reviewed: False` alongside a *reviewing* baseline: the nearest case sets `reviewed=False` on the
  baselines too, so the `not baseline` branch short-circuits before the gap can be observed. Add the
  mixed shape, asserting the verdict is not `clean`, plus a companion asserting both
  `baseline_reviewers` and `required_reviewed` appear in the rendered TOON when empty.
- **Mark the vacuous quorum on the participation envelope (050/G13).** `check_completeness` returns
  `participation_complete: true` for an empty `required_bots` — a vacuously satisfied quorum — and
  the envelope carries no field distinguishing that from a met one. Emit a distinguishing field
  (e.g. `quorum_basis: required | vacuous | unestablished`) derived from `required_bots` emptiness
  **and** from `bot_lists_provenance`, and have the merge-gate barrier render it rather than a bare
  boolean. The barrier currently reads `required_bots`/`optional_bots` and nothing else
  (`phase-6-finalize/standards/branch-cleanup.md`, the config read around lines 721–728, the clean
  path around line 982) — **adding the provenance read to that step is part of this deliverable, not
  an assumption about it.**

*Done when:* `assess_deficit` with a reviewing baseline and zero reviewing required reviewers returns
the new verdict and never `clean`; the rendered TOON shows both populations explicitly in that case
and on `unassessable`; a workflow document invokes `review_completeness deficit` and dispositions its
verdict as non-gating; a `check` with empty `required_bots` produces an envelope a consumer can tell
apart from a satisfied non-empty quorum, and `branch-cleanup.md` reads and renders the provenance.
Tests pin the deficit cases and the quorum pair.

### D4 — Bound and de-glyph every operator-facing string these surfaces render

**Gaps: 040/G4, 040/G5, 040/G10, 040/G11, 050/G14.**

The governing contract is
`marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/external-step-contract.md` §
"Required termination" (**≤80 characters**, **plain ASCII — no unicode glyphs**), restated in
`phase-6-finalize/standards/output-template.md`, with
`phase-6-finalize/standards/branch-cleanup.md` (around line 1707) requiring the length be checked
against **worst-case placeholder expansion**, never the literal form. The renderer does not truncate.

- **The three retrospective grade strings (040/G4)** sit at SKILL.md ~190–192. Measured at HEAD: the
  `clean` string is **73** characters, `vacuous` **50**, `indeterminate` **109** — and all three
  carry a U+2014 em dash, so none is ASCII. The `indeterminate` string has no placeholder, so 109 is
  not a worst case but the only case, and it is the string a reader sees on *every* zero-findings run
  while D1 is unbuilt. **Re-measure all three before editing; do not trust these figures.** Replace
  the em dash with an ASCII separator and shorten `indeterminate` to the grade name plus the fact,
  leaving the reasoning to the persisted artifact — the same division the skill already argues for
  where it keeps the delta verdict out of `display_detail`.
- **The composed Branch A string (040/G5)** sits at `automatic-review/SKILL.md` ~797, ~800, ~805 and
  ~850, with the skill restating the ≤80/ASCII rule at ~856 — inside the same section whose template
  breaks it. Measured at HEAD: the ordinary three-reviewer form
  `0 comment(s) found — 1 empty, 1 refused, 1 refused-structural (unified triage pending)` is **86**
  characters and not ASCII, and there is **no bounded worst case at all**, because
  `compose_review_state_summary` emits one segment per non-zero bucket. **Re-measure, and re-derive
  the worst case by counting the buckets in `_STATE_SUMMARY_BUCKETS` rather than trusting a figure
  here.** Relabelling cannot discharge an unbounded worst case: **bound the rendering**. Two workable
  shapes, and the run may take either or both — drop the `(unified triage pending)` tail whenever the
  summary segment is present (the summary already tells the reader more), and cap the summary at the
  N largest buckets with a `+K more` remainder so the length has a ceiling independent of roster
  size.
- **The empty-roster fallback (040/G10)** at `automatic-review/SKILL.md` ~798 falls back to
  `"{N} comment(s) found (unified triage pending)"` — character-for-character the collapsed string
  this whole epic exists to remove — and `required_bots`/`optional_bots` **both default empty**, so an
  unconfigured project takes that path always. Give the empty-roster case its own honest rendering at
  the *composition* site (e.g. `"{N} comment(s) found - no reviewers configured"`), leaving
  `compose_review_state_summary`'s `''` return and its stated rationale unchanged — inventing a
  bucket for reviewers that were never configured would be a claim about nothing.
- **The illustration that describes an unreachable state (040/G11)** at `automatic-review/SKILL.md`
  ~800 reads *"a run where three required reviewers all refused renders `0 comment(s) found — 3
  refused …`"*. Every refusal member is in `_UNPROVEN_STATES`, `participation_complete = not
  required_unproven`, and the skill states eleven lines above that Branch A is entered only on
  `participation_complete: true` or a recorded force-done. Three refusing **required** reviewers
  therefore route to Branch C. Rewrite the sentence around refusing **optional** reviewers, and note
  the force-done hatch as the only way a refusing required set reaches Branch A.
- **Name the governing knob in the awaitable-refusal disclosure (050/G14).** `review_rate_window_await`
  defaults to **`false`** (`automatic-review/SKILL.md` around line 366: *"When
  `review_rate_window_await == false`, skip this entire subsection … a detected refusal is treated as
  an ordinary settle"*), so under the default posture the one refusal class that is convertible into
  real review content is discarded rather than awaited — **silently, by configuration**. State that
  consequence where the refusal is disclosed, and require any disclosure naming a `refused_awaitable`
  bot to name the governing key and the effective value the run read from `step-params`. **Do not go
  looking for this repository's own configured value:** it lives in a machine-local, git-ignored file
  that a cloud clone does not have. Read the default and the mechanism from the skill, which is
  git-tracked, and write the disclosure so it reports whatever value the run observes.

*Done when:* every rendered form of both `display_detail` families is ASCII-only and ≤80 characters
at its widest expansion **over any roster size**; each measurement is stated beside its table in the
skill that owns it; a run with an empty reviewer roster renders a string that differs from a
reviewed-clean run's; the Branch A illustration names a configuration that actually reaches Branch A;
and the awaitable-refusal disclosure names its governing config key. Tests pin the length/ASCII
budget and the empty-roster difference.

### D5 — Replace guards that cannot fail with guards derived from behaviour

**Gaps: 040/G7, 040/G8, 040/G9, 050/G10, 050/G11, 050/G15.**

Each item is a guard whose expectation is transcribed from — or derived from — the very thing it
guards, or a documented surface with no guard at all.

- **Bucket coverage (040/G7).** `compose_review_state_summary` tallies every state but emits only the
  states enumerated in `_STATE_SUMMARY_BUCKETS`; an unbucketed state is silently dropped, so the
  tally stops summing to the roster size with no indication a reviewer is unaccounted for. No test
  references the constant. Assert that the union of the bucket state tuples equals the full member
  set, and that the bucket counts sum to `len(bot_states)` for a roster carrying one bot in every
  member. The sibling drift guard for the taxonomy prose already exists in
  `test/plan-marshall/automatic-review/test_bot_participation_contract.py`, so the pattern to copy is
  in the same directory.
- **Count-drift reach (040/G8).** The existing closure-count guard applies its regex to the contract
  document's own § "Failure taxonomy" section only — its own docstring says a count restated
  elsewhere is outside its reach. Widen it to a tree-wide sweep and assert every match against the
  derived member count, adding a second pattern for the `N-member` / `N non-participation members`
  forms. Add the same shape for the deficit verdict vocabulary, deriving the expected member set from
  the `DEFICIT_*` constants by introspection rather than a transcribed list. Keep the
  zero-match-is-a-pass rule the sibling guard uses, **with its population guard so the pass cannot go
  vacuous**. **Re-derive how many restatement sites exist by sweeping the tree** — the count is a
  lead.
- **The second documented invocation surface (040/G9).**
  ⚠ **Shared line with plan `510`.** `510-a-refusal-is-recorded-as-a-refusal-and-the-contract-says-so`
  § D3 carries the same defect (as `120 G5`) and **owns the docstring edit**. This plan's share is the
  regression guard, not the edit: extend
  `test_the_deficit_invocation_block_documents_the_cap_flag` to cover the module docstring's own
  `deficit` line, so the flag cannot go missing there again. Make the edit here **only if the line
  still lacks the flag** when this run reaches it — meaning `510` has not landed — and say in the run
  report which case held. Never revert or reformat the flag if it is already present.
  The defect: `review_completeness.py`'s module docstring
  carries `[--refusal-size-caps [<csv>]]` on the `check` `Usage:` line (around line 115) and **not**
  on the `deficit` line (around line 116), though `deficit_parser` accepts it. The skill marks that
  flag ⛔ load-bearing — *a cap arriving without its cause drives the fail-closed cause recovery, so a
  caller that passes it to `check` but not `deficit` reproduces exactly the disagreement the pair
  exists to prevent*. The existing guard reads `SKILL.md` and nothing else. Add the flag to the
  docstring line and extend the guard (or add a sibling) to read the module docstring's `Usage:`
  lines too, so both documented surfaces are held by one assertion.
- **The untested CLI boundary (050/G10).** Every test in the retrospective's test module drives
  `aggregate` or `_grade_comparison` directly; nothing invokes `main`. So the flags'
  `nargs='?' / const='' / default=''` shapes, the CSV split, and the wiring into `aggregate` are
  unexercised — a wiring defect would degrade the grade to the fail-closed default on every run and
  be indistinguishable from correct behaviour. Add CLI-level tests over `main` covering: flag
  omitted, flag bare, flag with a CSV value, and flag with surrounding whitespace, for
  `--reviewed-reviewers` and `--enabled-reviewers` alike — D2 makes "omitted" and "bare" different
  inputs for the latter.
- **A legend guard that can actually fail (050/G11).** The legend test asserts
  `set(legend) == {the same four constants}` and never calls `_grade_comparison`, while its docstring
  claims it enumerates "exactly the four grades the code can assign". It does not: a fifth grade
  returnable by `_grade_comparison` and missing from the legend passes it unchanged — and D2 adds
  grades. Derive the expectation from behaviour: collect `_grade_comparison` outputs over a spanning
  input set, and/or discover the `COMPARISON_*` constants by introspection, and assert every value
  the function can return has a legend entry. Correct the docstring to say what the test establishes.
- **The test module's coverage index (050/G15).** The module docstring's `Coverage:` enumeration
  stops before the `comparison` grade section, so a property that *is* pinned reads as one nobody
  guards. Add a bullet naming the grades, the fail-closed default, and the discrimination test.

*Done when:* adding a `STATE_*` constant without a bucket fails a test; changing the taxonomy's
cardinality or the deficit verdict set without updating every prose restatement fails a test; both
documented `deficit` invocations carry the cap flag and a test fails if either drops it; at least one
test invokes `main` and pins the parsed sets for the bare and valued forms; a grade returnable by
`_grade_comparison` but absent from `comparison_states` fails the legend test — **demonstrate this
by adding such a grade temporarily, watching the test go red, and reverting**; and the module
docstring enumerates the `comparison` section.

### D6 — Record three open decisions instead of taking them

**Gaps: 040/G13, 040/G15, 050/G5.**

This run has no operator to ask, so each of these is authored to **record a proposal**, never to make
the call. Write each into the run report as a clearly-labelled proposal carrying: the current
behaviour with its file and symbol, the proposed change, the argument both ways, and what would
settle it. **Change none of the three targets.**

- **The `min_deficit` default (040/G15).** `assess_deficit` takes `min_deficit: int = 1`, documented
  as "a required reviewer that reviewed yet produced strictly fewer findings than a baseline reviewer
  that reviewed the same diff" — while the deliverable it serves says "**materially** fewer" and the
  contract repeats "materially" without ever naming the threshold. A one-finding gap between two
  reviewers on the same diff is ordinary variance, so at the default the signal fires routinely,
  which is how an observability signal becomes noise and stops being read. Record the proposal —
  raise to 2, adopt a proportional rule, or defend 1 as the right floor — with the reasoning for
  each. The threshold is already a parameter, so only the default and its justification are at stake.
  **Do not change the default in this run.**
- **The refusal pre-filter (040/G13).** `workflow-integration-github/scripts/_github_pr.py`,
  `_is_refusal_notice` (around lines 155–187), returns True when a body matches one of the bot's
  registry `refusal_patterns` **or** a structural rate-limit shape — an enumeration of known refusal
  phrasings with no positive test of what a review body must *contain*. The remedy on record is to
  restate it positively: a stored `pr-comment` finding must positively look like review feedback,
  e.g. by matching a bot's declared `actionable_content_markers` — a predicate that already exists in
  the registry and is already used by `github_pr.py`'s contentless-boilerplate layer. Record it as a
  proposal rather than implementing it: the pre-filter governs what gets filed as a finding across
  the entire review pipeline, so changing it moves surfaces well outside this plan's two, with no
  operator positioned to catch a regression.
- **The run-report reviewer-participation template (050/G5).** `cloud-plan-lane/SKILL.md` § Report →
  Reviewer participation (around lines 1735–1749) still enumerates only
  `reviewed`/`rate-limited`/`silent`/`unreadable` in its header row, carries no required/optional
  class column, and closes with an unqualified *"State the coverage as N-of-M"* — the bare ratio a
  reader of every future run report sees. Write the exact replacement text as a proposal: the header
  gaining a `Class (required / optional / unclassified)` column and a `reviewed-empty` verdict value,
  and the closing line replaced by named ratios (required `k of |required_bots|`, optional
  `j of |optional_bots|` with each silence's cause, and the record's own `roster r of |roster|`).
  Record it and **do not apply it**: `cloud-plan-lane` is the contract governing this very run, and
  the lane forbids self-approving a change to it.

*Done when:* the run report carries three labelled proposals, each naming its target file and symbol,
its proposed text or value, and the argument both ways; and `git diff` shows no change to
`_is_refusal_notice`, to `min_deficit`'s default, or to `cloud-plan-lane/SKILL.md`.

## Out of scope

Each entry names **why** — with no operator watching, the written reason is the only thing that
holds the line against a tempting adjacent change.

- **Applying the three D6 proposals.** Two of them (`min_deficit`, the refusal pre-filter) require a
  judgement this run cannot make and cannot have reviewed before merging; the third edits the
  contract that governs this run, which the lane forbids self-approving. Recording is the whole
  deliverable.
- **The proposals re-anchoring `cloud-plan-lane`'s merge-gate shortfall disclosure and its verdict
  table** (recorded as gaps `050/G4` and `050/G12` in the file named under Notes). Same reason as
  above, and they belong with a plan that owns the lane contract rather than with this one, which
  owns two scripts and two skills. This plan touches the lane only to *propose* the report-template
  replacement.
- **Turning the deficit signal into a gate.** The envelope states `gates_merge: false` and
  `proves: reviewer_quality_only` in as many words, and the reason is structural: gating would block
  a merge on a third party's output. D3 wires the signal to a caller and records its verdict as INFO;
  it must not become a merge condition.
- **Narrowing the retrospective's row domain to the required set.** The row population is the enabled
  roster by landed contract (`bot-participation-contract.md` § "The counting rule"), because a
  reviewer that produced nothing must still get a row. D2 adds a *required* input beside it; it does
  not replace it.
- **Loosening the fail-closed defaults.** `indeterminate` on an unsubstantiated review, and
  `unassessable` when no baseline reviewed, are correct and stay. Every defect here is missing
  information, never a wrong claim, so the remedy is always the producer and never a looser default.
- **Reconciling the epic's historical suite-size figures, and the historical absence-corpus /
  charter partitions** (gaps `050/G16` and `040/G16`). Both are bookkeeping over landed records
  rather than defects in the two surfaces this plan fixes, and one of them explicitly says not to
  edit a landed report.
- **Backfilling the reviewed-at-all artifact for PRs already merged.** The handoff is a
  forward-looking channel between two steps of one finalize run; there is no stored input to
  reconstruct it from for a past run, so a backfill would fabricate the exact classification this
  plan exists to substantiate.

## Expected surface

- `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py` — the
  deficit verdict, the unconditional population emission, the vacuous-quorum marker, the docstring
  usage line.
- `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md` — the producer write, the
  `deficit` wiring, the Branch A `display_detail` bound and its illustration, the empty-roster
  fallback, the awaitable-refusal disclosure, the verdict-vocabulary restatement.
- `marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md`
  — the verdict-vocabulary restatement.
- `.claude/skills/finalize-step-review-retrospective/scripts/review_retrospective.py` — the grade
  operand, the required-denominated `clean`, the provenance split, the three-valued roster input, the
  three-valued row `participation`, the legend.
- `.claude/skills/finalize-step-review-retrospective/SKILL.md` — the consumer read, the removed ⚠
  block, the placeholders, the display-detail table, the routing on grade, the Step 4 artifact spec,
  the participation table.
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md` — the
  provenance read and the quorum-basis rendering at the merge-gate barrier.
- `test/plan-marshall/automatic-review/` and
  `test/plan-marshall/finalize-step-review-retrospective/` — the new and widened guards.

Not expected to change, and a change here is collateral to be reported:
`workflow-integration-github/scripts/_github_pr.py`, `automatic-review/scripts/bot_registry.py`, and
`.claude/skills/cloud-plan-lane/SKILL.md`.

## Claim labels

Every line number below is a **lead** — re-derive it. `OBSERVED` means the file and symbol were read
at HEAD while authoring this plan.

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| `assess_deficit` returns `clean` when `required_reviewed` is empty and a baseline reviewed | OBSERVED | `review_completeness.py`, `assess_deficit` — the `verdict = DEFICIT_DEFICIT if deficit_reviewers else DEFICIT_CLEAN` line and the `required_reviewed` filter above it |
| `_emit_deficit_toon` omits `baseline_reviewers` / `required_reviewed` when empty | OBSERVED | `review_completeness.py`, `_emit_deficit_toon` — the two `if …:` guards |
| Nothing in the tree persists `bot_states`; every occurrence is an in-process read, prose, or a test assertion | OBSERVED (asserted **absence**) | A whole-tree search for `bot_states` across `marketplace/`, `.claude/`, `test/`. **Re-run it; an asserted absence is the higher-risk half of this plan** — if a writer exists, D1's producer half is already built and the plan must say so instead of building a second one |
| Nothing in the tree invokes `review_completeness deficit`; the only occurrence is § "Canonical invocations" | OBSERVED (asserted **absence**) | A whole-tree search for `review_completeness deficit`, `check_deficit`, `assess_deficit` outside `review_completeness.py` and `test/`. Re-run it |
| `_grade_comparison` grades on `len(records)`, not on an actionable count | OBSERVED | `review_retrospective.py`, `aggregate` — the `_grade_comparison(len(records), …)` call |
| `clean` is earned by any member of the enabled roster, required or optional | OBSERVED | `review_retrospective.py`, `_grade_comparison` — `if enabled_reviewers & reviewed_reviewers` |
| `--enabled-reviewers` collapses omitted / bare / empty into one input | OBSERVED | `review_retrospective.py`, `main` — the `nargs='?', const='', default=''` declaration |
| The skill instructs `--reviewed-reviewers` to be passed bare, twice | OBSERVED | `finalize-step-review-retrospective/SKILL.md` — the ⚠ block in Step 1 and its repeat in Step 2 |
| `{reviewed_author_logins}` is used in two invocation blocks and defined nowhere | OBSERVED | `finalize-step-review-retrospective/SKILL.md` — a search for the token returns only the two blocks |
| Step 4's artifact spec never names `comparison` or `comparison_states` | OBSERVED (asserted **absence**) | `finalize-step-review-retrospective/SKILL.md` § Step 4. Re-read it before adding |
| `check_completeness`'s return carries no vacuous-quorum marker and no provenance | OBSERVED (asserted **absence**) | `review_completeness.py`, `check_completeness` — the return dict |
| `branch-cleanup.md` never reads `bot_lists_provenance` | OBSERVED (asserted **absence**) | A search for `bot_lists_provenance` across `marketplace/` returns `manage-config`, `marshall-steward`, `create-pr.md`, `ci_base.py` — not `branch-cleanup.md`. Re-run it |
| No test references `_STATE_SUMMARY_BUCKETS` or `required_reviewed` | OBSERVED (asserted **absence**) | A search for both tokens under `test/` returned nothing. Re-run it |
| No test in the retrospective's module invokes `main` | OBSERVED (asserted **absence**) | A search for `rr.main` / `sys.argv` in `test/plan-marshall/finalize-step-review-retrospective/test_review_retrospective.py` returned nothing. Re-run it |
| The three grade strings measure 73 / 50 / 109 characters and none is ASCII | OBSERVED | Measured with `len()` and `isascii()` on the literals in the SKILL's display-detail table. **Re-measure — the table may have changed** |
| The ordinary three-reviewer Branch A string measures 86 characters and is not ASCII, and its worst case is unbounded | OBSERVED | Measured on the literal; the unboundedness follows from `compose_review_state_summary` emitting one segment per non-zero bucket. Re-measure and re-derive |
| `bot_kind → author_login` is machine-readable from the registry, so the handoff needs no transcribed list | OBSERVED | `automatic-review/scripts/bot_registry.py` — the login map and `bot_kind_for_login`; the per-bot `standards/{bot_kind}.md` docs. **D0 re-establishes this as its gate** |
| `manage-files` `write`/`read` can carry a plan-dir artifact between the automatic-review step and an `order: 990` step | HYPOTHESIS | `manage-files/SKILL.md` § Operations (both verbs exist, and the retrospective's Step 4 already writes a plan-dir artifact by that route). **D0 settles it**; what is unverified is the ordering property, not the verbs |
| The repository's build (`./pw verify`) exercises both `test/plan-marshall/automatic-review/` and `test/plan-marshall/finalize-step-review-retrospective/` | HYPOTHESIS | Run the build gate per the lane contract and read which test directories the report names. If the retrospective's tests are not collected, say so in the report — several *Done when* conditions rest on them |
| `review_rate_window_await` defaults to `false`, so an awaitable refusal is discarded rather than awaited under the default posture | OBSERVED | `automatic-review/SKILL.md` § "Rate-limit refusal recovery" — the `review_rate_window_await == false` sentence and the config declaration in the frontmatter block |

## Verification

Beyond each deliverable's *Done when*:

1. **Build gate.** This plan changes Python, so the build gate is not optional. Run it per the lane
   contract, and report the suite figure **with the population it was measured over** (which test
   paths, at which commit). Do not carry forward a figure measured before the final commit.
2. **The two-surface discrimination test, stated as one property.** For each surface, a test must
   show two runs that differ *only* in whether a required reviewer reviewed, and must assert the two
   render **different** strings. Surface 1: `assess_deficit` with a reviewing baseline, once with a
   reviewing required reviewer and once without. Surface 2: the retrospective step's path — not
   `aggregate()` directly — once with the persisted reviewed-at-all artifact naming a required
   reviewer and once without it. A test that only exercises the pure function proves the library and
   not the pipeline, which is precisely how this defect survived its first fix.
3. **⭐ Cold read — the central check.** The rendered operator-facing strings are text whose value is
   what a later reader *does* with them, so "implemented as specified" cannot verify them. Dispatch
   an independent reader with **no context from this plan** and give it only the rendered strings
   (not the code, not this file): (a) the new `indeterminate` display-detail, (b) the new
   `clean` display-detail, (c) the new empty-roster Branch A string, (d) the rendered deficit TOON
   for a run where the required reviewer did not review, and (e) the rendered `check` envelope for an
   empty `required_bots`. Ask four questions and **record the answers verbatim in the run report**:
   *Was the diff reviewed? By whom, and how do you know? Is this a gap I must act on, or an
   accounted-for absence? How many reviewers were required, and how do you know?* If the reader
   cannot answer question 3 from the text, the wording has reproduced the defect it describes,
   however complete the implementation looks — fix the wording and re-read.
4. **Length and ASCII budget, measured not asserted.** Parse the display-detail tables out of both
   skills, widen every placeholder to its plausible maximum, and assert `len <= 80`, `isascii()`, and
   no trailing period. A pattern for exactly this already exists at
   `test/plan-marshall/phase-6-finalize/test_pre_submission_self_review_verdict.py` (a test that
   parses another step's SKILL.md verdict literals) — copy its shape rather than inventing one.
   Additionally assert a **bounded** worst case for the composed Branch A string over a roster
   carrying one reviewer in every bucket.
5. **Prove the legend guard can fail.** Temporarily add a grade returnable by `_grade_comparison`
   and absent from `comparison_states`, confirm the widened test goes red, then revert. Record the
   before/after result in the report. A guard nobody has seen fail is not yet a guard.
6. **Re-derive every count this plan states.** The five verdict-restatement sites, the taxonomy
   restatement sites, the registry-doc count, the string lengths, and the suite figures are all
   leads written at authoring time. Re-derive each at the moment you claim it, and report the derived
   value beside the claim.
7. **Collateral check.** Confirm by `git diff --stat` that nothing outside the Expected surface
   changed, and that the three D6 targets are untouched.

## Notes

**The detailed evidence.** Each gap id in the Deliverables sections maps to an entry in one of two
git-tracked files, which carry the executions, the file:line citations, and the reasoning behind each
task:

- `doc/plans/review-apparatus/040-canned-no-op-indistinguishable-from-a-review/gaps.md` — entries
  G1, G2, G3, G4, G5, G6, G7, G8, G9, G10, G11, G12, G13, G15 are the ones this plan discharges,
  written here as `040/GN`. Each directory also holds a `verification.md` with the supporting
  analysis.
- `doc/plans/review-apparatus/050-coverage-shortfall-disclosed-against-the-roster-not-the-required-set/gaps.md`
  — entries G1, G2, G3, G5, G6, G7, G8, G9, G10, G11, G13, G14, G15, written here as `050/GN`.

**This plan is self-sufficient without them.** They are useful corroboration, not required reading:
every mechanism, file, symbol, and threshold this plan depends on is restated above. If either file
is absent from the clone, proceed — and note the absence in the report.

**Do not go looking for `.plan/`, with one stated exception.** It is git-ignored — no orchestrator
ledger, no generated `execute-script.py`, no plan state — **except for two tracked paths**,
`.plan/marshal.json` and `.plan/project-architecture/` (per `.gitignore:45-47`). Re-derive that from
`.gitignore` rather than trusting this sentence. Three consequences bind this run. The configured
`required_bots` / `optional_bots` / `bot_lists_provenance` values for *this* repository are
therefore readable in `marshal.json`, but **no deliverable may depend on them.** D0 leg 3 settles
only that the required set is *separable* from the enabled roster and what the provenance schema is
— `manage-config/SKILL.md` documents both lists as defaulting EMPTY, so it yields no repository's
actual roster and cannot stand in for one. Every value the run reports must therefore be one it
observed at run time, never one transcribed from this plan, from a gaps file, or from a documented
default. The
`review_rate_window_await` value is readable for the same reason, and D4 still uses the documented
git-tracked default, so that the fix holds for a consumer whose knob differs from this repository's.
And no `python3 .plan/execute-script.py …` command in this repository's skills can be executed from
this run; those command lines are **the text being edited**, not commands to run.

**No plugin-cache sync is owed.** This plan edits `marketplace/bundles/`, and in the standalone lane
that neither triggers a sync nor records one as owed — the merged bundle source is authoritative.

**Sequencing inside the plan.** D0 gates D1–D3. D1 must land **with** D2's required-denominated
`clean`, not before it: `clean` is unreachable in production today precisely because the handoff is
missing, so building the handoff alone arms a false-clean that is latent right now. D2's row-level
three-valued `participation` is likewise inert until D1 lands. D4, D5 and D6 are independent of that
ordering and can land in any order relative to it.

**Two gaps deliberately kept together.** `040/G2` (the fourth deficit verdict) and `040/G8` (the
count-drift guard for the verdict vocabulary) ship in the same change: the verdict set is restated at
several prose sites, and landing the widened verdict without the guard leaves the next widening to be
reconciled by hand — which is how the current restatements came to need reconciling at all.

**Prior art in this epic.** The landed plans `040` and `050` each closed this defect at one level and
left the other open: `040` added the state-distribution summary and the deficit signal, `050` added
the `comparison` grade. Both were verified against their pure functions and both pass; both surfaces
still collapse the two facts in production. That is the specific lesson this plan is built on — a
test that drives the library is not a test of the pipeline, and this plan's Verification requires the
step's path for exactly that reason.
