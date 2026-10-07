# Gaps — 090-feed-pr-findings-back-into-local-review

Actionable follow-up derived from `verification.md`. Each entry is a task a later plan can pick up
without re-deriving the analysis. Nine entries: one major, seven minor, one cosmetic.

## G1 — Correct the misattributed PR number for the `--max-per-component` anchor

- **Severity:** major
- **Kind:** false-report-claim
- **Where:** `doc/plans/review-apparatus/090-feed-pr-findings-back-into-local-review/report-01.md:49`
- **Evidence:** the report states *"the flag AND its `if args.max_per_component < 0: … invalid_cap`
  guard were introduced together in the **same** squash-merged PR #1153 (`_lessons_query.py:232`),
  whose review threads are empty (Sourcery rate-limited, zero inline threads)."*
  `git log --oneline -S'max_per_component' -- marketplace/bundles/plan-marshall/skills/manage-lessons/scripts/_lessons_query.py`
  and the same search for `invalid_cap` each return exactly one commit: `010ea461`
  `feat(manage-lessons): surface active lessons prospectively (#1039)`. PR #1153 is `1296ede1`
  `feat(shims): give migration/back-compat shims an owner, floor, and removal trigger
  (truthful-signals/050)`, whose `--name-only` stat contains no `manage-lessons` path. CONFIRMED.
- **Impact:** the conclusion (the fix shipped with the flag, so it carries no posted review answer,
  so it is not in the answered corpus) survives — but the corroborating evidence attached to it
  ("whose review threads are empty, Sourcery rate-limited") was read off an unrelated PR and supports
  nothing. A later reader auditing the D0 anchor set would be sent to the wrong PR.
- **Task:** correct `report-01.md:49` to name PR **#1039** (commit `010ea461`), and either re-verify
  the "review threads are empty" observation against #1039 or drop that clause. Because the run
  report is a record of one execution, correct it in place rather than rewriting the surrounding
  analysis.
- **Done when:** `report-01.md:49` names the PR whose commit `git log -S'invalid_cap'` returns, and
  every corroborating clause on that line is verifiable against that PR.
- **Suggested grouping:** review-apparatus / plan-090 report corrections

## G2 — Give the count-prose detector reach past the number-noun adjacency limit

- **Severity:** minor
- **Kind:** incomplete
- **Where:**
  - `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/_self_review_patterns.py:178`
    (`_CARDINALITY_NOUNS`) and `:183-185` (`_COUNT_PROSE`)
  - the corpus instance: `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md:684`
    (*"the quoting discipline below governs the eight list flags only"*)
- **Evidence:** `report-01.md:45` advances PR #1167's finding as the corpus corroboration for D2's
  widening: *"a `count_prose`-archetype finding whose noun (`list flags`) sits OUTSIDE the detector's
  registered noun set."* The thread body (read through the GitHub review-comment surface; the thread
  is still `is_resolved: false`, `total_count: 1`, no reply) reads: *"The nearby text still refers to
  'six' list sets and 'seven' list flags. The `check` command now declares eight list flags."* The
  landed detector does not surface that shape, and the report's diagnosis names only half the reason.
  Adding `flags?` alone still does not match, because `_COUNT_PROSE` requires the noun **immediately
  adjacent** to the number. Verified by direct regex evaluation with
  `operations?|fields?|steps?|rules?|commands?|checks?|flags?`: `'the eight list flags'` → no match,
  `'nine list flags'` → no match, `'nine flags'` → match; and reproduced through the real
  `_detect_count_prose` with `_COUNT_PROSE` monkey-patched to that set (zero entries surfaced for a
  contract source carrying the real sentence). CONFIRMED.
  ⚠ The prose the #1167 finding named is **not** stale — see G6. This gap is about detector reach
  only; the two live figures are each correct for their own call site.
- **Impact:** the plan's only shipped code cannot detect the one real-world instance the run advances
  as its justification. The limit is general, not particular to this phrase: over the detector's
  517-file contract-source domain the landed predicate matches **189** lines, and allowing at most one
  intervening word token would add **113** more — so the reach gap is broad, and so is the noise a
  naive loosening would admit.
- **Task:** derive, do not loosen. Measure the intervening-modifier population over the
  contract-source domain, decide whether a bounded allowance (at most one word token,
  `\s+(?:\w[\w-]*\s+)?`) pays for its noise, and adjudicate `flag`/`flags` (20 occurrences) for
  membership in the closed set on the "structural element of a skill contract that goes stale"
  criterion the pattern comment states (see G3). If the allowance is taken, add one positive case
  drawn from the real `the eight list flags` prose and one negative proving the allowance does not
  admit an unbounded gap.
- **Done when:** either `_detect_count_prose` surfaces `automatic-review/SKILL.md:684` when a sibling
  file in that skill directory is modified and a test pins both the new positive and the bounded-gap
  negative, or the pattern comment records the measured reason the allowance was rejected.
- **Suggested grouping:** ext-self-review-plan-marshall / count-prose detector

## G3 — Land the noun-set derivation as a reproducible artifact, and adjudicate the candidates it surfaces

- **Severity:** minor
- **Kind:** omission
- **Where:** `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/_self_review_patterns.py:169-178`
  (the comment that carries the derivation's conclusion); `report-01.md:76` (the claim)
- **Evidence:** `plan.md:111-113` requires *"⚠ **Widening must be DERIVED, not guessed.** … Derive
  the noun set from the counts that actually appear in the corpus, and state whether the resulting
  set is closed."* `report-01.md:76` cites a 510-file scan via `scratchpad/derive_nouns.py`, which
  did not land. Re-derived here over the detector's real domain — `marketplace/bundles/*/skills/*/SKILL.md`
  ∪ `marketplace/bundles/*/skills/*/standards/*.md`, 517 files at HEAD (510 at the landing commit
  `bb9ab493` via `git ls-tree -r`, so the report's figure is exact at its own commit) — matching the
  detector's line-scoped reading rather than a whole-file one: the report's characterisation
  reproduces (top followers `of` 303, `and` 123, `px` 116, `is` 87), but the added member was selected
  from the plan's docstring example, not from the distribution. Structural-noun candidates outside the
  closed set, singular + plural, case-insensitive: `deliverable`/`deliverables` **67**,
  `module`/`modules` **44**, `state`/`states` **25**, `phase`/`phases` **24**, `flag`/`flags` **20**,
  `column`/`columns` **16**, `member`/`members` **13** — against `check`/`checks` at **5**, the lowest
  of the set. CONFIRMED.
  ⚠ The top two are **not** un-adjudicated: `deliverables` and `modules` are exactly the negative
  test's fixtures (`test_self_review.py:1597`), pinned as must-not-fire. The un-adjudicated candidates
  are `state`, `phase`, `flag`, `column`, `member` — and `flag` is the noun G2 is about.
- **Impact:** the "derived, not guessed" discipline is claimed but not reproducible from a clone, so a
  future widening has to redo the scan from scratch, and the five un-adjudicated candidates are all
  more frequent than the one member the widening added.
- **Task:** add a committed derivation utility, or a test that asserts the closed set against a
  derived candidate list, under the `ext-self-review-plan-marshall` scripts or test tree. The repo
  already carries a working precedent for the shape:
  `test/plan-marshall/automatic-review/test_bot_participation_contract.py:501-523` reads a closure
  count stated in prose out of a contract doc and asserts it against the derived member set — follow
  that pattern rather than inventing one. Record in the `_CARDINALITY_NOUNS` comment which
  high-frequency candidates were considered and rejected, and why, naming `deliverable` and `module`
  as the two the negative test already pins.
- **Done when:** a committed artifact reproduces the follower distribution over the detector's
  contract-source domain, and the pattern comment names each rejected high-frequency candidate with
  its reason.
- **Suggested grouping:** ext-self-review-plan-marshall / count-prose detector

## G4 — Update the `## Tests` coverage index for the count-prose detector

- **Severity:** minor
- **Kind:** stale-doc
- **Where:** `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/SKILL.md:379`
- **Evidence:** the row enumerates the pre-existing cases exhaustively — *"a modified sibling file
  plus a SKILL.md whose prose carries `twelve fields` / `5 rules` … a count planted in a sibling
  `standards/*.md` doc … a digit NOT adjacent to a cardinality noun surfaces nothing; a modified file
  outside any skill directory surfaces nothing; the same skill dir reached via two modified siblings
  deduplicates per `(file, line)`"* — six of the eight cases in `TestDetectCountProse`, and names
  neither `test_count_prose_surfaces_check_noun` (`test_self_review.py:1558`) nor
  `test_count_prose_does_not_fire_on_nouns_outside_closed_set` (`:1585`). Sibling rows in the same
  section (for example the flag-guard-pair row at `:369`) do enumerate every case, so this is drift,
  not a style difference. The repo's own rule at
  `marketplace/bundles/plan-marshall/skills/persona-plan-marshall-agent/standards/agent-behavior-rules.md:270`
  states: *"When you add a member to the indexed set, add its index row in the SAME change."*
  CONFIRMED — found by reading the full `## Tests` section, which the run's five-noun-enumeration
  sweep (`report-01.md:114`) did not cover.
- **Impact:** the skill's advertised test coverage understates what the suite proves, so a later
  editor reading the index would not know the closed-set negative exists and could widen the noun set
  without realising a test guards against it.
- **Task:** extend the `:379` row with the `check`-noun positive (including the singular `one check`
  branch) and the closed-set negative (`5 deliverables` / `3 modules` / `5 checkpoints`, the last
  pinning the trailing word boundary).
- **Done when:** every case in `TestDetectCountProse` has a clause in the `SKILL.md:379` row.
- **Suggested grouping:** ext-self-review-plan-marshall / documentation index

## G5 — Publish the re-derived detector-registry enumeration the plan's claim-labels table mandated

- **Severity:** minor
- **Kind:** omission
- **Where:** `plan.md:165` (the obligation); `report-01.md` §D0 (where the result is absent);
  `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/_self_review_detectors.py`
  (the registry)
- **Evidence:** the Claim-labels table states *"The detector registry is the unit of change and holds
  roughly eighteen `_detect_*` functions | OBSERVED — ⚠ the count is a lead | Enumerate the registry
  at HEAD. ⛔ **Re-derive; the list is actively grown and a shape this plan means to add may already
  have landed**"*. `grep -c "^def _detect_"` on the registry returns **20** at HEAD, matching the 20
  names `self_review.py:45-64` imports; the emitted surface is **22** candidate lists
  (`len(CANDIDATE_LISTS)`, imported and evaluated). The report states neither figure. CONFIRMED. The
  obligation's purpose was met in substance — the report checks `unguarded_boundaries`
  (`report-01.md:63`), `source_of_truth` and `scan_derived_keys` (`:119`) against specific candidates
  — but the enumeration is unrecorded.
- **Impact:** the plan's asserted-absence claim label ("no existing detector already covers a given
  candidate's shape") has no published population behind it, so a later reader cannot tell which
  detectors were checked against which candidate.
- **Task:** add the re-derived registry count and the per-candidate absence check to `report-01.md`'s
  D0 section — one line naming the count at the landing commit and, per "yes" candidate, which
  existing detectors were ruled out.
- **Done when:** `report-01.md` states the enumerated registry size and names the detectors excluded
  per candidate.
- **Suggested grouping:** review-apparatus / plan-090 report corrections

## G6 — `automatic-review/SKILL.md` never states its eight-versus-nine scope split

- **Severity:** minor
- **Kind:** unclear-doc
- **Where:** `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md:684`, `:686`, `:691`
  ("eight") against `:980` ("nine") and
  `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py:1301`
  ("nine")
- **Evidence:** ⛔ both figures are **correct**, and the count CodeRabbit flagged on PR #1167 is **not**
  still stale — `git log -S"eight list flags"` shows `064560ab` (*"fix(review-apparatus): address
  CodeRabbit review comments from #1167 (#1168)"*) raised the FIND-step figures from six/seven to
  seven and the parser-surface figure from seven to eight, and `9e9e9880` (#1241) then raised the
  FIND-step figures to eight and the parser-surface figure to nine in one commit. The two figures
  count two different populations: `:684`/`:686`/`:691` are scoped to the `review_completeness check`
  invocation printed immediately above them at `:675-682`, which passes exactly eight list flags;
  `:980` and `review_completeness.py:1301` are scoped to the parser's whole flag surface, and nine is
  authoritative — `grep -n "nargs='?'"` on `review_completeness.py` returns nine hits
  (`--required-bots`, `--optional-bots`, `--participated-bots`, `--in-progress-bots`,
  `--refused-bots`, `--stale-participation-bots`, `--declined-bots`, `--refused-causes`,
  `--refusal-size-caps`). The ninth, `--declined-bots`, is supplied only from the phase-6 re-review
  path (`phase-6-finalize/standards/branch-cleanup.md:833`), which is why the FIND-step call omits it.
  What is missing is any statement of that scoping: nothing in the document says the two figures
  answer different questions. CONFIRMED.
- **Impact:** the document reads as self-contradictory to anyone re-counting it — including the
  count-prose check this plan exists to feed, which cannot tell scoped-correct from stale. A reader
  acting on the apparent contradiction would "fix" a correct figure.
- **Task:** state the scope on each figure — e.g. "the eight list flags **this call passes**" at
  `:684`/`:686`/`:691` and "all nine list flags **the parser declares**" at `:980` — so the two
  populations are named where the numbers appear.
- **Done when:** every list-flag count in `automatic-review/SKILL.md` names the population it counts,
  and the eight- and nine-figures can be reconciled without leaving the document.
- **Suggested grouping:** automatic-review / list-flag documentation

## G7 — Two live stale count claims in the automatic-review test contract, outside the detector's file scope

- **Severity:** minor
- **Kind:** stale-doc
- **Where:** `test/plan-marshall/automatic-review/test_bot_participation_contract.py:850` and `:983`
- **Evidence:** two count claims in that file contradict the file's own derived data.
  1. `:983` — the docstring of `test_confirmed_site_carries_its_own_flag_set_fully_quoted` reads *"the
     sites genuinely differ — the pre-merge barrier passes five flags, not the participation guard's
     six."* `_CONFIRMED_SITES` (`:817-846`) declares **6** for both family-A sites, and the module
     comment at `:807-809` says *"the pre-merge barrier's Predicate 2 passes six"*. The block at
     `phase-6-finalize/standards/branch-cleanup.md:829-836` interpolates six `--*-bots` flags
     (`--required-bots`, `--optional-bots`, `--participated-bots`, `--refused-bots`,
     `--stale-participation-bots`, `--declined-bots`). So both the "five" and the "genuinely differ"
     rationale are false as written.
  2. `:850` — *"a sixth flag reaches the quoting scan automatically."* `_ALL_LIST_FLAGS` is derived
     live from the parser (`derive_bot_flags(_RC_SCRIPT, 'check')`) and holds **seven** members
     (computed under pytest, so the shared helper's `conftest` import resolves).
  The suite passes (78 passed), because neither claim is asserted — they are prose. Neither is visible
  to `_detect_count_prose`, whose domain is `SKILL.md` plus `standards/*.md` only
  (`_collect_skill_contract_sources`, `_self_review_detectors.py:276`), so a `.py` docstring or
  comment is outside its file scope entirely. CONFIRMED.
- **Impact:** two live instances of the exact archetype this plan exists to catch, in the file that
  guards the very flag population G6 is about — and a third reach axis the run never names: beyond
  the noun set (G3) and the number-noun adjacency (G2), the detector's **file scope** excludes every
  `.py` docstring and comment in the tree.
- **Task:** correct both sentences against the derived data (`:983` → both family-A sites pass six,
  and drop or restate the "genuinely differ" rationale; `:850` → phrase the future-proofing without a
  bare ordinal). Separately, record the file-scope reach axis alongside G2's adjacency axis so a
  future widening decision weighs all three.
- **Done when:** no count claim in `test_bot_participation_contract.py` contradicts
  `_CONFIRMED_SITES` or the parser-derived flag family, and the reach discussion in the
  `_CARDINALITY_NOUNS` comment names file scope as a known limit.
- **Suggested grouping:** automatic-review / list-flag documentation

## G8 — D2's and D3's *Done when* clauses were restated rather than met

- **Severity:** minor
- **Kind:** false-report-claim
- **Where:** `plan.md:114-115` and `:117-120` (the clauses); `report-01.md:81` and `:95` (the
  restatements)
- **Evidence:** D2's clause reads *"each yes has either a new detector or a justified widening, and
  the docstring contradiction is fixed"* (`plan.md:114-115`). The run's three "yes" answers
  (`report-01.md:39-41`) produced neither: #8 is already covered by markdownlint, #30 and #38 were
  routed out to the cloud-plan-lane. The report writes *"Done-when satisfied: the one
  yes-that-produces-code has a justified widening; the docstring contradiction is fixed; the other
  yes-answers are recorded and routed"* (`:81`) — a different clause. D3's clause requires *"one
  **positive** case drawn from the real accepted finding that motivated it"* (`plan.md:117-118`); no
  accepted finding motivated the widening (the corroborator on #1167 is **unanswered**, not accepted,
  and the motivating case is the plan's own docstring observation plus the real
  `phase-1-init/SKILL.md:857` instance *"The two checks are ordered: source-origin is primary"*). The
  report does not name that substitution. CONFIRMED.
  ⚠ The dispositions themselves are correct and plan-sanctioned — the plan's own Out-of-scope rules
  require routing such candidates out. The defect is that the run marked two clauses satisfied by
  rewording them instead of reporting the deviation.
- **Impact:** the back-feed premise — that the accepted-finding corpus yields the detectors — produced
  no code at all, and the record does not say so plainly. A later reader auditing whether the exercise
  paid off reads two green *Done when* lines that answer questions the plan did not ask.
- **Task:** either record the deviation in `report-01.md` (naming that no yes produced a detector or
  widening, and that the positive fixture substitutes the docstring example for an accepted finding),
  or reconcile the plan text: D0's rules make "already covered" and "routed out" legitimate yes
  answers, which D2's per-yes clause does not admit. Whichever is chosen, the next back-feed run
  inherits a clause it can satisfy honestly.
- **Done when:** the report states the substitution for both clauses, or `plan.md`'s D2/D3 clauses
  admit the dispositions D0's own rules produce.
- **Suggested grouping:** review-apparatus / plan-090 report corrections

## G9 — Reconcile `plan.md`'s "Three." against its four numbered deliverables

- **Severity:** cosmetic
- **Kind:** unclear-doc
- **Where:** `doc/plans/review-apparatus/090-feed-pr-findings-back-into-local-review/plan.md:59`
- **Evidence:** the Deliverables section opens *"Three. ⚠ **Expect a small yield — plausibly two or
  three detectors.**"* and then enumerates four numbered deliverables (D0 at `:62`, D1 at `:75`, D2
  at `:94`, D3 at `:117`). `report-01.md:17` records the correct arithmetic (*"The plan has four
  deliverables (D0 gate, D1, D2, D3)"*) without flagging the mismatch. D0 is labelled "GATE, mutates
  nothing", so "three deliverables plus a gate" is a defensible reading of the same text — an
  ambiguity, not a demonstrable stale count. CONFIRMED as ambiguity.
- **Impact:** a plan whose subject is unverified count claims opens with one a reader cannot resolve
  from the page. Cosmetic in effect, but it undercuts the plan when quoted.
- **Task:** rephrase `plan.md:59` to make the reading explicit — e.g. "One gate and three
  deliverables." The yield sentence that follows counts *detectors*, not deliverables, and should not
  be changed.
- **Done when:** the Deliverables section's opening states a count a reader can match against the
  numbered items beneath it without inferring the gate/deliverable distinction.
- **Suggested grouping:** review-apparatus / plan-090 report corrections

## Not gaps — checked and clear

Recorded so a later run does not re-derive them:

- **The landed code has no defect.** The `\b` sits outside the noun alternation, so `checks?` cannot
  match inside `checkpoints`; `(?i)` covers casing; both singular and plural branches are pinned by
  test; the added surface is a review anchor excluded from `counts.total`
  (`extension-api/standards/ext-point-self-review-surfacing.md:177`), so it cannot inflate the defect
  count; `check`/`checks` adds only **5** matched lines over the 517-file contract-source domain
  (`marshall-steward/SKILL.md:672`, `phase-1-init/SKILL.md:857`, `phase-4-plan/SKILL.md:825`,
  `phase-6-finalize/SKILL.md:498`, `ext-self-review-plan-marshall/SKILL.md:232`), smaller than any
  other candidate considered.
- **D3's tests are discriminating, not vacuous.** Reproduced twice — at the regex level and by
  monkey-patching `_COUNT_PROSE` in process and running both fixtures through the real
  `_detect_count_prose`: the positive fails against the pre-fix five-noun set, the negative fails
  under an any-noun mutant, and the negative asserts `out == []` (`test_self_review.py:1602`), so it
  cannot pass vacuously.
- **The documentation is not wrong about reach.** The pattern comment (`_self_review_patterns.py:162`,
  `:179`), Detection Rule 14 (`SKILL.md:256`) and the plan's mandated cold read (`report-01.md:110`)
  all state the *immediately adjacent* requirement correctly. The adjacency limit in G2 is a design
  limit to be re-decided, not a docstring defect reproduced by its own fix.
- **All four noun-set restatements are current at HEAD** (`_self_review_patterns.py:178`,
  `_self_review_detectors.py:1048-1049`, `ext-self-review-plan-marshall/SKILL.md:256`,
  `phase-6-finalize/workflow/pre-submission-self-review.md:316`). The one later commit touching those
  files, `622f4484` (#1239), did not disturb them (`git log -S'commands?|checks?'` on the pattern
  module returns `bb9ab493` alone).
- **D1 is verified anchor-for-anchor** — `tier: full`, `persona: persona-security-expert`, `order: 9`,
  `_TIER_RANK` (`_manifest_lanes.py:23`, keep predicate at `:203`),
  `_apply_security_class_inactive` at `_manifest_rules.py:343-396` (at the landing commit), the
  drop-reason string at `:340`, `_CEREMONY_FINALIZE_DEFAULT = 'auto'` at `:620`, the manifest
  emission lines, and the #1201 traversal fix in `doc_references.py:253` with its `/etc/passwd`
  comment at `:281`.
- **`_detect_count_prose`'s `except OSError: continue`** (`_self_review_detectors.py:1081-1082`) is a
  silent-skip fail-open: an unreadable contract source is dropped with no counter and no note. It
  predates this plan, is unchanged by the landing, and cannot flip a verdict because `count_prose` is
  excluded from `counts.total`. Out of this plan's scope; recorded so it is not re-discovered as new.
- **No production string literal restates the noun set.** `self_review.py:565` derives its help prose
  from the registry (`f'Emit {len(CANDIDATE_LISTS)} candidate lists '`), so it cannot go stale;
  `:556` is a noun-agnostic `description=`. `grep -rni "cardinality noun"` over `*.py`/`*.md`
  (excluding `doc/plans/`) returns eight hits, all documentation, comments, one noun-agnostic schema
  row and one test comment.
- **`plugin-doctor` was not duplicated.** It carries its own `_NUMBER_WORDS` table and count-claim
  regex (`_analyze_literal_count.py:179`, `:208`), scoped to the `persona-security-expert` standards
  population only — no overlap with the cardinality-noun set.
- **The hand-maintained sibling-list mirror is complete.**
  `test_self_review_reachability_regression.py:114-136` enumerates 21 sibling lists plus the one under
  test = 22, matching `len(CANDIDATE_LISTS)`; its comment states the hand-maintenance is deliberate.
  `ext-self-review-plan-marshall/SKILL.md:60`'s "twenty-two candidate lists" is therefore correct.
- **Out-of-scope compliance is clean** — no `plugin-doctor` file, no simplify surface, no new knob,
  skill, standard or extension point; the two stop-rule candidates were routed out and recorded.
- **The four residue items are all still open**, but each is a deliberate hand-off recorded by the
  run, not an omission by it. They belong to their named owners (the cloud-plan-lane report gate, a
  future mirror-drift plan, and `manage-findings` / the triage contract) and are out of this plan's
  declared scope.
