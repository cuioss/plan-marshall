# Gaps — 050-coverage-shortfall-disclosed-against-the-roster-not-the-required-set

Actionable follow-up derived from `verification.md`. Each entry is a task a later plan can pick up
without re-deriving the analysis. **Sixteen entries: 4 major, 12 minor, 0 blockers.**

## G1 — Grade the comparison on the ACTIONABLE count, and grade the non-empty path too

- **Severity:** major
- **Kind:** bug
- **Where:** `.claude/skills/finalize-step-review-retrospective/scripts/review_retrospective.py:360-364`
  (the `len(records)` argument), `:147-148` (`total_findings > 0 → measured`),
  `:387` (the `measured` legend string);
  `.claude/skills/finalize-step-review-retrospective/SKILL.md:134` (the exit is gated on
  `filtered_count is 0`), `:443` (the ungraded fallback `--display-detail`)
- **Evidence:** the grade is computed from the raw store size —
  `comparison = _grade_comparison(len(records), …)` — while the module's own contract is that META
  records "never inflate `actionable_count`" (`:234-237`) and "cannot dilute the ratio" (`:41-42`).
  Executed against the current module:
  `aggregate([{'author':'coderabbitai','kind':'issue_comment'}], enabled_reviewers=['coderabbitai','cuioss-review-bot'], reviewed_reviewers=[])`
  → `comparison: measured`, `total_findings: 1`, every reviewer `actionable_count: 0`. The test
  module's own docstring (`:32-33`) pins "the full CodeRabbit review shape (5 inline + 1
  status-summary `review_body` + 1 walkthrough `issue_comment`)", so META-only stores demonstrably
  occur. CONFIRMED by execution.
- **Impact:** a PR on which CodeRabbit posted only its walkthrough and an "Actionable comments
  posted: 0" summary — and no reviewer filed anything — is graded `measured`, *"the review-quality
  comparison was performed"*, when nothing was compared. Because `filtered_count` is non-zero it also
  bypasses the graded exit entirely and records the untouched
  `"{N} reviewers compared, {M} actionable comments"` display-detail: a benign no-op summary on a run
  with zero actionable content. This is the exact defect D2 exists to close, displaced by one record.
- **Task:** (a) pass the actionable count, not `len(records)`, into `_grade_comparison` — compute it
  from the same `_is_actionable` predicate the per-reviewer loop already applies, so no second notion
  of "a real review comment" can drift; emit it as a first-class payload field beside `total_findings`
  so the grade's operand is visible. (b) Rewrite the `measured` legend string to name *actionable*
  findings. (c) Change `SKILL.md:134` to route on the **grade**, not on `filtered_count`, so a
  META-only store reaches the graded display-detail table at `:188-192` instead of `:443`; that table
  has no `measured` row today, so add one and give `:443` a grade-aware form for the `measured` path.
- **Done when:** `aggregate` over a store of only `issue_comment`/status-summary records with a
  configured roster and no reviewed-at-all signal returns `indeterminate`, a test pins that case, and
  no SKILL path can reach a `mark-step-done` whose `--display-detail` was chosen without reading
  `comparison`.
- **Suggested grouping:** finalize-step-review-retrospective / the `comparison` grade

## G2 — Build the persisted reviewed-at-all handoff, or stop claiming the grade discriminates

- **Severity:** major
- **Kind:** incomplete
- **Where:** producer absent repo-wide;
  `.claude/skills/finalize-step-review-retrospective/SKILL.md:151-164` ("pass `--reviewed-reviewers`
  **bare**"), `:225-231`; `review_retrospective.py:151` (the `clean` branch)
- **Evidence:** `grep -rn "reviewed_reviewers\|reviewed-reviewers"` over the repo returns hits only in
  the aggregator, its SKILL, its test file, the `bot-participation-contract.md:664` Consumers row, two
  `__pycache__` artefacts, the git-ignored generated executor's flag-surface cache
  (`.plan/execute-script.py:382`), and a plugin-doctor help cache. **No code anywhere computes or
  writes the set.** The SKILL says so plainly: *"No persisted handoff of that classification currently
  reaches this step… pass `--reviewed-reviewers` bare."* CONFIRMED by the producer sweep. Recorded by
  `report-01.md` § Residue, so disclosed rather than hidden.
- **Impact:** `enabled_reviewers & reviewed_reviewers` is empty at every real invocation, so `clean`
  is **unreachable in production** and the deployed grade is a three-valued function of
  `(record count, roster)`. D2's requirement — *"it must distinguish reviewers ran and found nothing
  from no reviewer produced content"* — holds for the pure function and fails for the pipeline: in
  production those two facts still render identically. And because `indeterminate` then fires on
  every zero-record run with a configured roster, the grade takes one value over the whole population
  it is computed on and therefore distinguishes nothing on that path. (It is not a *false* alarm —
  `indeterminate` correctly says "could not be established" when no substantiating input exists. The
  defect is missing information, not a wrong claim, and the remedy is the producer, not a looser
  default.)
- **Task:** persist `review_completeness check`'s `bot_states` `{bot_kind, state}` classification
  where an `order: 990` step can read it (a plan-dir artifact via `manage-files`, or a findings/status
  record), map the `_REVIEWED_STATES` members
  (`review_completeness.py:279` — `participated`, `participated_but_empty`) to `author_login` via the
  registry, and have the retrospective read it instead of passing the flag bare. Update
  `SKILL.md:151-164` and `:225-231` accordingly. ⛔ **Ship G3 in the same change** — this handoff is
  what arms G3's false-clean.
- **Done when:** a finalize run on a PR whose required reviewer posted a "nothing to report" card and
  filed no finding records `comparison: clean` rather than `indeterminate`, and no SKILL text instructs
  the flag be passed bare.
- **Suggested grouping:** automatic-review ↔ finalize-step-review-retrospective handoff

## G3 — Make the `clean` grade required-denominated, not roster-denominated

- **Severity:** major (latent today — see the precondition)
- **Kind:** bug
- **Where:** `.claude/skills/finalize-step-review-retrospective/scripts/review_retrospective.py:151`
  (`if enabled_reviewers & reviewed_reviewers`), `:122-126` (the docstring that sanctions it);
  `.claude/skills/finalize-step-review-retrospective/SKILL.md:209-212` (the roster is
  `required_bots ∪ optional_bots`)
- **Evidence:** the SKILL derives `--enabled-reviewers` from *"the automatic-review step's
  `required_bots ∪ optional_bots` config"*, and the grade earns `clean` on **any** member of that
  union being substantiated. Executed: `_grade_comparison(0, {'req','opt'}, {'opt'})` → `clean`. So
  `required = {pr-agent}` silent + `optional = {coderabbit}` reviewed-and-found-nothing + 0 findings
  → `clean`. CONFIRMED by execution and by reading both files.
- **Impact:** this is the plan's own false-clean scenario — *"the required reviewer resolved to
  `participated_but_empty` … while an optional reviewer produced 16 records"* — rebuilt inside the
  fix. A required-side collapse would be graded a legitimate no-op because an optional reviewer spoke.
  It is also the one axis D2 says to extend to the instrument ("Extend the rule to the review-quality
  instrument itself"), and the grade collapses exactly the distinction the counting rule keeps.
  ⚠ **Precondition, stated rather than assumed:** this cannot occur in production *today*, because
  `reviewed_reviewers` is always empty (G2) and `clean` is unreachable. It is latent, not live — and
  it goes live the instant G2's handoff is built, which is precisely why the severity stays major and
  why the two must land in one change rather than in sequence.
- **Task:** give the aggregator the required set as its own input (a `--required-reviewers` flag,
  `author_login` values from `required_bots`) and split the grade so `clean` requires a **required**
  reviewer to be substantiated; where only optional reviewers are substantiated, emit a distinct grade
  (e.g. `optional_only`) or `indeterminate`, and name the population in `comparison_states`. Do **not**
  narrow `enabled_reviewers`: the row domain must stay the enabled roster (that is plan 040's landed
  contract, `bot-participation-contract.md` § "The counting rule").
- **Done when:** a zero-findings aggregate with the required reviewer absent from `reviewed_reviewers`
  and an optional one present does not return `clean`, a test pins that case, and the emitted legend
  names which population each grade is computed over.
- **Suggested grouping:** finalize-step-review-retrospective / the `comparison` grade

## G4 — Re-anchor the D1a/D1b proposals against the current `cloud-plan-lane/SKILL.md`

- **Severity:** major
- **Kind:** stale-doc
- **Where:** `doc/plans/review-apparatus/050-…/report-01.md` § PROPOSAL D1a and § PROPOSAL D1b;
  target span `.claude/skills/cloud-plan-lane/SKILL.md:1199-1259` and `:1436-1444`
- **Evidence:** D1a instructs *"Replace from '**Record a verdict per reviewer, derived from the stored
  comment bodies**' through '…not merely unmentioned.'"* Both anchors still exist — the opening at
  `:1199`, the closing at `:1259` — but the span between them has grown two later landings: the
  `unreadable` verdict row (`:1209`) with its ⛔ block (`:1211`) and merge-gate paragraph (`:1226`)
  (`git log -S'unreadable' -- .claude/skills/cloud-plan-lane/SKILL.md` → `b814d2fd`, PR #1281), and
  the whole `Reopens?` subsection with its table (`:1241-1243`) (`git log -S'Reopens?'` → `dc188529`,
  PR #1244). D1a's replacement table has four rows — `reviewed` / `reviewed-empty` / `rate-limited` /
  `silent` — with no `unreadable` row and no `Reopens?` integration. D1b's target has likewise moved:
  condition 4 is now **condition 5** (`:1436`) and carries a `Reopens?` clause (`:1441`). CONFIRMED by
  reading the current file.
- **Impact:** applying the proposals verbatim silently reverts two landed improvements — the
  unreadable-surface distinction (which exists precisely to stop a tool failure being recorded as a
  clean signal) and the reopens-or-not column. A proposal whose whole value is being applied without
  re-derivation is now a regression if used as written.
- **Task:** re-derive D1a/D1b against the current text: keep the `unreadable` row and its ⛔ block,
  keep the `Reopens?` subsection and fold the awaitable-vs-hard wording of D1a's `rate-limited` row
  into it rather than duplicating it, add `reviewed-empty` and the required/optional classification,
  and re-point D1b at Step 8 **condition 5**. Then apply — the proposal-only prohibition binds a run
  governed by that contract, not a run outside the lane.
- **Done when:** `cloud-plan-lane/SKILL.md` carries a `reviewed-empty` verdict, a required/optional
  classification, and a required-set shortfall predicate, while `unreadable` and `Reopens?` survive
  unchanged.
- **Suggested grouping:** cloud-plan-lane / reviewer participation and the shortfall disclosure

## G5 — Supply replacement text for the third emission site, the report template

- **Severity:** minor
- **Kind:** omission
- **Where:** `.claude/skills/cloud-plan-lane/SKILL.md:1736-1746` (§ Report → Reviewer participation),
  whose closing line (`:1746`) is *"State the coverage as N-of-M, and whether the § Step 8 shortfall
  disclosure fired and what it said."*
- **Evidence:** D2 names three emission sites — "the merge-gate disclosure, the report's
  reviewer-participation table, and the run report's coverage line". D1a covers `:1258` and D1b covers
  the merge-gate condition; the report template is addressed by one clause — *"The report's **Reviewer
  participation** template (§ Report) gains the required/optional column and the two-ratio coverage
  line"* — with no column layout and no replacement text. CONFIRMED by reading both the proposal and
  the current template, whose header row at `:1742` still enumerates only
  `reviewed`/`rate-limited`/`silent`/`unreadable`.
- **Impact:** the site that still emits a bare "N-of-M" is the one a reader of every future run report
  sees, and it is the one an applier has to invent text for — reintroducing the hand-derivation the
  proposal exists to remove.
- **Task:** write the exact replacement for `:1736-1746`: the table header gaining a
  `Class (required / optional / unclassified)` column and a `reviewed-empty` verdict value, and the
  closing line replaced by the two named ratios (required `k of |required_bots|`, with "met by empty
  participation" where it applies; optional `j of |optional_bots|` with each silence's cause; and the
  record's own `roster r of |roster|`).
- **Done when:** the § Report template contains no unqualified "N-of-M" and every ratio in it names its
  population.
- **Suggested grouping:** cloud-plan-lane / reviewer participation and the shortfall disclosure

## G6 — Carry the `comparison` grade into the persisted artifact, or stop saying it is there

- **Severity:** minor
- **Kind:** stale-doc
- **Where:** `.claude/skills/finalize-step-review-retrospective/SKILL.md:196-197` (the claim) vs
  `:388-425` (Step 4, the artifact spec)
- **Evidence:** `:196-197` states *"The `indeterminate` grade lives in the `--display-detail` and the
  persisted artifact, not in the lifecycle outcome."* Step 4 enumerates precisely what the artifact
  carries — the deterministic metrics table, the `## Review-versus-Gate Delta` section with its named
  fields, `## Qualitative Quality Assessment`, `## Comparative Verdict` — and never names `comparison`
  or `comparison_states`. `grep -n "comparison"` over the whole SKILL returns ten lines, none of them
  inside Step 4. CONFIRMED.
- **Impact:** the `display_detail` ceiling is small and the artifact is where signals accumulate across
  PRs (the SKILL says so of the delta at `:404-406`). A grade that reaches neither the artifact nor the
  lifecycle outcome survives only in one truncated status line, so `indeterminate` cannot be trended.
  And the SKILL asserts a property it does not implement.
- **Task:** add `comparison` (with its `comparison_states` gloss and the `enabled_reviewers` /
  `reviewed_reviewers` populations beside it) to the Step 4 artifact spec, in the same
  figure-beside-its-population style the delta section already uses.
- **Done when:** Step 4 names the grade, and no sentence in the SKILL claims the artifact carries
  something Step 4 does not instruct it to write.
- **Suggested grouping:** finalize-step-review-retrospective / the `comparison` grade

## G7 — Honour `bot_lists_provenance` in the `vacuous` grade

- **Severity:** minor
- **Kind:** incomplete
- **Where:** `.claude/skills/finalize-step-review-retrospective/scripts/review_retrospective.py:149-150`
  and the `vacuous` legend at `:389`
- **Evidence:** `if not enabled_reviewers: return COMPARISON_VACUOUS`, glossed as *"0 findings and no
  reviewer roster configured — nothing was expected to compare"*. `grep -rn "bot_lists_provenance"`
  over `marketplace/`, `.claude/`, `test/` and `.plan/marshal.json` returns hits in `marshal.json`
  itself, `manage-config` (SKILL + `standards/data-model.md`), `marshall-steward` (SKILL +
  `scripts/upgrade.py`), `ci_base.py:1410`, `create-pr.md:253-257`, and four test modules — and none
  in the retrospective. D3 requires *"no required reviewers configured — quorum vacuously satisfied"*
  (`answered`) and *"reviewer requirements not configured — the question has not been put"*
  (`never_asked`, treated as **unestablished**) be distinct renderings. CONFIRMED.
- **Impact:** `never_asked` is the **default** for any project that has not run the wizard, and it
  currently renders as the deliberate operator answer of *none* — the vacuous-authority archetype D3
  names, reachable by default, in shipped code.
- **Task:** pass the provenance to the aggregator and split `vacuous` into the established-empty case
  (`answered` and `migrated` alike) and an `unestablished` case for `never_asked` alone; name both in
  `comparison_states`. ⛔ `migrated` is an **established** posture and belongs with `answered`; only
  `never_asked` takes the unestablished rendering. Mirror the distinction in `SKILL.md:188-192`'s
  display-detail table. ⭐ **The house pattern already exists** — `create-pr.md:256-257` splits exactly
  this pair for the `skip-bot-review` label, applying it on an empty-plus-`answered`/`migrated`
  posture and refusing to on an empty-plus-`never_asked` one ("**A never-asked posture does NOT mean
  'skip review'** … Fail toward being reviewed"); mirror it rather than inventing a second rule.
- **Done when:** an empty roster with provenance `never_asked` does not grade identically to one with
  provenance `answered`, and a test pins the pair.
- **Suggested grouping:** finalize-step-review-retrospective / the `comparison` grade

## G8 — Stop asserting "no reviewer roster configured" from an argument that may simply be absent

- **Severity:** minor
- **Kind:** bug (fail-open) + missing-test
- **Where:** `.claude/skills/finalize-step-review-retrospective/scripts/review_retrospective.py:434-438`
  (`--enabled-reviewers` is `nargs='?', const='', default=''`), `:149-150` (the `vacuous` branch),
  `:389` (the legend string); `.claude/skills/finalize-step-review-retrospective/SKILL.md:191` (the
  operator-facing rendering), `:482-483` (the bare form sanctioned);
  `test/plan-marshall/finalize-step-review-retrospective/test_review_retrospective.py:814`
- **Evidence:** the flag's argparse shape makes **flag omitted**, **flag bare**, and **flag with an
  empty value** all reach `aggregate` as the same empty list, and the SKILL sanctions the bare form in
  as many words ("It may be supplied bare (no value), which reads as the empty roster"). The grade
  then returns `vacuous`, whose emitted gloss is *"0 findings and **no reviewer roster configured** —
  nothing was expected to compare"* and whose `--display-detail` is *"no reviewer roster configured —
  nothing to compare"*. Executed: `aggregate([], enabled_reviewers=None)` → `vacuous`;
  `aggregate([], enabled_reviewers=[])` → `vacuous`. CONFIRMED by execution.
  The existing test `test_comparison_vacuous_when_no_roster_configured` (`:814`) **pins** the
  conflation rather than catching it: it passes `enabled_reviewers=[]` and names that case "no roster
  configured".
- **Impact:** the instrument publishes a **configuration fact it never read**, in the most benign of
  its four grades, on exactly the path where the caller supplied nothing. That is the plan's own
  archetype — a predicate satisfiable without the thing it exists to establish — one argument to the
  left of where the fix was placed. It is also the fail-open twin of the `--reviewed-reviewers`
  fail-closed default the same function gets right two lines below.
- **Task:** distinguish *roster absent* from *roster empty*: change `--enabled-reviewers` to
  `default=None` (keeping `const=''` so the bare form still means the deliberate empty roster), thread
  that three-valued input to `_grade_comparison`, and grade an unsupplied roster as `indeterminate` (or
  a named `roster_unknown`) rather than `vacuous`. Emit the distinguishing input as a payload field so
  the grade's operand is visible, and correct the legend so `vacuous` claims only what was read.
- **Done when:** an invocation that omits `--enabled-reviewers` does not grade identically to one that
  passes it bare, a test pins the pair, and no emitted string asserts "configured" on an input the run
  did not read.
- **Suggested grouping:** finalize-step-review-retrospective / the `comparison` grade

## G9 — Resolve the `{reviewed_author_logins}` placeholder contradiction

- **Severity:** minor
- **Kind:** stale-doc
- **Where:** `.claude/skills/finalize-step-review-retrospective/SKILL.md:169` and `:235` (the two
  invocation blocks), against `:155` and `:225-231` (the prose)
- **Evidence:** `grep -n "reviewed_author_logins\|enabled_author_logins"` over the file returns exactly
  four lines — `:168`, `:169`, `:234`, `:235`. Both bash blocks read
  `--reviewed-reviewers "{reviewed_author_logins}"`, and `{reviewed_author_logins}` is defined nowhere,
  while the prose at `:155` orders the flag passed **bare** and `:225-231` repeats it. Compare
  `{enabled_author_logins}`: the token likewise appears only in the two blocks, but `:209-218`
  instructs the reader how to derive the value it stands for ("derive the enabled reviewer roster…
  never transcribe a reviewer list here"). No such instruction exists for the reviewed set. CONFIRMED.
- **Impact:** an agent following the command literally passes the token `{reviewed_author_logins}`,
  which the CSV split at `:472` turns into a single bogus `author_login`. It cannot intersect the
  roster, so the grade is unaffected, but the payload's `reviewed_reviewers` — echoed "so the
  population behind the `comparison` grade is visible" (`:371-372`) — then publishes a fabricated
  reviewer name.
- **Task:** make the two blocks match the prose — either write `--reviewed-reviewers` bare, or define
  `{reviewed_author_logins}` beside the `{enabled_author_logins}` derivation at `:209-218`. Also define
  `{k}` in the `clean` display-detail row at `:190`.
- **Done when:** every placeholder in the SKILL's invocation blocks is either defined in the SKILL or
  removed, and the block and its surrounding prose prescribe the same call.
- **Suggested grouping:** finalize-step-review-retrospective / SKILL instructions

## G10 — Test the CLI path of `--reviewed-reviewers`

- **Severity:** minor
- **Kind:** missing-test
- **Where:** `test/plan-marshall/finalize-step-review-retrospective/test_review_retrospective.py`
- **Evidence:** `grep -n "rr.main\|main(\[\|argv\|sys.argv"` in that file returns **no matches** —
  every test drives `rr.aggregate` or `rr._grade_comparison` directly. So the flag's
  `nargs='?' / const='' / default=''` shape, the CSV split at `:472`, and the wiring into `aggregate`
  at `:474-478` are unexercised. CONFIRMED by the search.
- **Impact:** a wiring defect — a wrong `dest`, a dropped kwarg, the bare-flag form parsing to `None`
  — would pass the whole suite while the grade silently degraded to the fail-closed default on every
  run, which is indistinguishable from correct behaviour today (see G2). The same untested boundary is
  where G8's three-valued fix has to land.
- **Task:** add CLI-level tests over `main` (with `_read_pr_comment_findings` and `serialize_toon`
  stubbed) covering: flag omitted, flag bare, flag with a CSV value, and flag with surrounding
  whitespace — asserting the parsed set that reaches `aggregate`. Cover `--enabled-reviewers` in the
  same shapes, since G8 turns "omitted" and "bare" into different inputs.
- **Done when:** at least one test invokes `main` and pins the parsed `reviewed_reviewers` for the bare
  and valued forms.
- **Suggested grouping:** finalize-step-review-retrospective / tests

## G11 — Pin the legend against the grades the code can ASSIGN, not against the same literals

- **Severity:** minor
- **Kind:** missing-test
- **Where:** `test/plan-marshall/finalize-step-review-retrospective/test_review_retrospective.py:862-876`
  (`test_comparison_states_legend_matches_the_four_graded_constants`) against
  `review_retrospective.py:386-391`
- **Evidence:** the legend dict is keyed by `COMPARISON_MEASURED` … `COMPARISON_INDETERMINATE`, and the
  test asserts `set(legend) == {rr.COMPARISON_MEASURED, …}` — the same four constants. It never calls
  `_grade_comparison`. Its docstring nevertheless claims *"The emitted legend enumerates exactly the
  four grades the code can assign"*. **Proved by mutation:** a fifth constant plus a fifth
  `_grade_comparison` return branch, with no legend entry added, leaves the whole module suite at
  **43 passed**. (Source bytes snapshotted to `$TMPDIR/adv-050-mutsweep/` and restored from that
  snapshot in a `finally`; `git status --porcelain` clean afterwards.) The CodeRabbit fix that made the
  legend key off constants (report § Findings, item 2) is what removed the test's remaining
  discrimination: before it, literals were compared against constants.
- **Impact:** this is the epic's own catalogued archetype — a guard whose expectation is derived from
  the code it guards. A fifth grade added to `_grade_comparison` and omitted from the legend passes
  this test unchanged, and G3, G7 and G8 each propose adding one.
- **Task:** derive the expectation from behaviour: collect `_grade_comparison` outputs over a spanning
  set of inputs (and/or the module's `COMPARISON_*` constants discovered by introspection) and assert
  every value the function can return has a legend entry. Correct the docstring to say what the test
  actually establishes.
- **Done when:** a grade returnable by `_grade_comparison` but missing from `comparison_states` fails
  the test — verifiable by re-running the fifth-grade mutation above and seeing it go red.
- **Suggested grouping:** finalize-step-review-retrospective / tests

## G12 — Perform and record the plan's cold read, verbatim

- **Severity:** minor
- **Kind:** omission
- **Where:** `doc/plans/review-apparatus/050-…/plan.md` § Verification (the ⭐ "Cold read, and it is the
  central check here" and the ⭐ empty-`required_bots` read) vs `report-01.md` § Findings, the
  verification sub-agent bullet
- **Evidence:** the plan demands a cold reader answer three questions — *(1) was the diff reviewed?
  (2) is this a gap I must act on, or an accounted-for absence? (3) how many reviewers were required,
  and how do I know?* — and **"Report the answers verbatim."** `grep -in "cold read\|cold-read\|verbatim"`
  over `report-01.md` returns 8 hits (`:106`, `:138`, `:281`, `:311`, `:313`, `:353`, `:354`, `:363`);
  the only reported outcome is the paraphrase *"Q2 'gap or accounted-for absence?' **is** answerable"*
  plus a paraphrase of the empty-`required_bots` answer. Q1 and Q3 have no reported answers. CONFIRMED.
- **Impact:** the plan calls this the central check, and Q3 is the one that tests whether the proposal
  actually publishes its denominator — the plan's entire subject. An unreported answer leaves the
  proposal's central property unverified, and the plan says so: *"If question 2 cannot be answered from
  the text, the proposal has reproduced the defect it describes."*
- **Task:** when G4's re-anchored text is produced, have a fresh reader with no plan context read the
  shortfall statement and the empty-`required_bots` rendering and answer all three questions plus *"was
  a required review performed?"*; record the answers verbatim in the follow-up plan's report.
- **Done when:** four verbatim cold-read answers are recorded against the re-anchored proposal text.
- **Suggested grouping:** cloud-plan-lane / reviewer participation and the shortfall disclosure

## G13 — Render the vacuous quorum as vacuous in the in-lifecycle barrier

- **Severity:** minor
- **Kind:** omission
- **Where:** `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py:110-112`
  and the `check_completeness` return at `:902-925`;
  `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md:721-728`
  (the caller's config read) and `:982` (the clean path)
- **Evidence:** the module docstring states *"An EMPTY `required_bots` is a valid configured state —
  the quorum is vacuously satisfied and `participation_complete` is `true`."* The returned envelope
  carries `participation_complete`, `proves`, `pending_bots`, `unproven_bots`, `bot_states`,
  `review_state_summary`, `measured_diff_size`, `refusal_causes` — **no vacuous marker and no
  provenance**. `review_state_summary` does not cover the case either: `compose_review_state_summary`
  returns `''` only when `bot_states` is *wholly* empty (`:597-600`), and `bot_states` spans
  required ∪ optional, so an empty `required_bots` beside a populated `optional_bots` yields a
  non-empty summary and a vacuously-true boolean. `branch-cleanup.md:728` confirms both lists "default
  EMPTY", and `:982` gates the clean path on that boolean. CONFIRMED. `report-01.md` describes the
  in-lifecycle mechanism as "correct on this axis" without recording this.
- **Impact:** D3's ⛔ — *"must never render [no required bots configured] as [required quorum met]"* —
  is violated by the boolean the merge-gate barrier actually gates on, in the default posture of any
  project that has not answered the wizard question. The plan scoped the vacuous rendering to the lane
  disclosure, so this is not a plan violation; it is the same archetype, live, one surface over.
- **Task:** emit a distinguishing field from `check_completeness` (e.g. `quorum_basis: required |
  vacuous | unestablished`), derived from `required_bots` emptiness **and from a provenance the caller
  must start reading** — `grep -c "bot_lists_provenance"` over `branch-cleanup.md` returns **0**, so
  the barrier reads `required_bots`/`optional_bots` (`:721-728`) and nothing else; adding the
  provenance read to that step is part of this task, not an assumption about it. Then have the barrier
  render the field rather than a bare `participation_complete: true`.
- **Done when:** a `check` with empty `required_bots` produces an envelope a consumer can tell apart
  from one with a satisfied non-empty quorum, a test pins the pair, and `branch-cleanup.md` reads and
  renders the provenance.
- **Suggested grouping:** automatic-review / review_completeness

## G14 — Surface the un-awaited recoverable refusal as a live configuration fact

- **Severity:** minor
- **Kind:** omission
- **Where:** `.plan/marshal.json` →
  `plan.phase-6-finalize.steps["plan-marshall:automatic-review"].review_rate_window_await: false`;
  `doc/plans/review-apparatus/050-…/plan.md` § Notes
- **Evidence:** the plan's Note says *"On one run a reviewer was `refused_awaitable` while the
  rate-window await was **off for that plan**, so the one refusal convertible into real review content
  was dropped **silently by configuration** … Surface it."* `grep -n "rate_window_await\|awaited\|refused_awaitable"`
  over `report-01.md` returns exactly one hit (`:89`) — inside the D1a proposal's `rate-limited` row, a
  general awaitable-vs-hard statement. The repository's own `review_rate_window_await: false` (read
  directly from `marshal.json`, which also carries `review_rate_window_timeout_seconds: 3600`) is never
  named. CONFIRMED.
- **Impact:** the concrete, checkable instance of the lead stays unrecorded, so a later reader has to
  rediscover that the knob exists and is off here. The generic prose in a proposal that has not been
  applied surfaces nothing operationally.
- **Task:** record the live value and its consequence — an awaitable refusal is discarded rather than
  awaited under the current configuration — in whichever plan takes G4, and state whether the
  disclosure should name the knob when it reports an awaitable refusal.
- **Done when:** the awaitable-refusal disclosure names the governing config key and its current value,
  or a recorded decision says why it should not.
- **Suggested grouping:** automatic-review / rate-window handling

## G15 — Add the `comparison` grade to the test module's coverage list

- **Severity:** minor
- **Kind:** stale-doc
- **Where:** `test/plan-marshall/finalize-step-review-retrospective/test_review_retrospective.py:19-33`
  (the module docstring's `Coverage:` enumeration)
- **Evidence:** the list enumerates grouping, `raw_total`/`actionable_count`/`meta_count`, the
  resolution buckets, `pct_resolved_as_fixed` and its denominator contract, `unattributed`,
  `unknown`-kind, empty-input, and the full CodeRabbit shape (`:32-33`) — and stops there. The
  `comparison` grade section, which runs from its banner at `:760` to EOF at `:914`, is absent from it.
  CONFIRMED by reading the docstring.
- **Impact:** the docstring is the file's index of what is pinned; a property missing from it reads as
  a property nobody guards, and the next author extending the file will not know the section exists.
- **Task:** add a `Coverage:` bullet for the `comparison` grade naming the four grades, the fail-closed
  default, and the discrimination test.
- **Done when:** the docstring enumerates the `comparison` section.
- **Suggested grouping:** finalize-step-review-retrospective / tests

## G16 — Reconcile the reported suite figure with what landed

- **Severity:** minor
- **Kind:** false-report-claim
- **Where:** `doc/plans/review-apparatus/050-…/report-01.md` § Build gate ("**38 passed** — including
  all 8 new `comparison`-grade tests") and the PR body ("**Tests:** eight `comparison`-grade cases")
- **Evidence:** `git show b286928c^:…test_review_retrospective.py | grep -c "^def test_"` → **30**;
  the same at `b286928c` → **40**; at HEAD → **43** (three later renames/additions from `6514cf24`
  and `622f4484`, none of them `comparison` tests). A name-level `diff` of the pre- and post-fix lists
  shows exactly **ten** additions, all `comparison`-grade. Ten tests landed, not eight, and the module
  suite was 40 at merge, not 38. The report itself names the two extra regression tests in § Findings
  (`test_comparison_clean_requires_an_ENABLED_reviewer_not_any_reviewer`,
  `test_comparison_empty_roster_is_vacuous_even_with_an_off_roster_reviewer`), so the figure is a stale
  pre-review-fix measurement carried forward rather than an invention. CONFIRMED.
- **Impact:** small on its own; it matters because this plan's subject is figures published without
  their population, and a run report that carries a count measured against an earlier tree is the same
  class of defect at the reporting layer. A retrospective auditor reconciling suite sizes across the
  epic would find an unexplained two-test gap.
- **Task:** in whichever plan takes G4, note the corrected figures (30 → 40 at merge, 43 at HEAD; ten
  tests) so the epic's retrospective corpus is not reconciled against the stale one. Do not edit the
  landed report — it is a dated record.
- **Done when:** the corrected counts appear in a successor report with the reason for the discrepancy.
- **Suggested grouping:** review-apparatus / epic bookkeeping
