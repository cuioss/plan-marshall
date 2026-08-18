# Gaps — 090-feed-pr-findings-back-into-local-review

Actionable follow-up derived from `verification.md`. Each entry is a task a later plan can pick up
without re-deriving the analysis.

## G1 — Make the count-prose detector able to see `the eight list flags`, and fix the stale count it names

- **Severity:** major
- **Kind:** incomplete
- **Where:**
  - `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/_self_review_patterns.py:178`
    (`_CARDINALITY_NOUNS`) and `:183-185` (`_COUNT_PROSE`)
  - the stale prose itself: `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md:684`,
    `:686`, `:691` (all say "eight") against `:980` ("nine") and
    `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py:1301`
    ("nine")
  - the authoritative population: `review_completeness.py:1309,1322,1334,1350,1362,1377,1398,1416,1435`
    — nine `nargs='?'` list flags
- **Evidence:** `report-01.md:45` advances PR #1167's finding as the corpus corroboration for D2's
  widening: *"a `count_prose`-archetype finding whose noun (`list flags`) sits OUTSIDE the detector's
  registered noun set."* The thread body (read via the GitHub review-comment surface, still
  `is_resolved: false`, no reply) reads: *"The nearby text still refers to 'six' list sets and
  'seven' list flags. The `check` command now declares eight list flags."* The landed detector does
  not match it, and adding `flags?` alone would still not match it, because `_COUNT_PROSE` requires
  the noun **immediately adjacent** to the number. Verified by direct regex evaluation with
  `operations?|fields?|steps?|rules?|commands?|checks?|flags?`: `'the eight list flags'` → no match,
  `'nine flags'` → match. Meanwhile the drift is worse than when it was raised: `SKILL.md:684` and
  `:691` say "eight list flags" while `:980` and `review_completeness.py:1301` say "nine", and
  `grep -n "nargs='?'"` proves nine is correct. CONFIRMED.
- **Impact:** the plan's only shipped code cannot detect the one real-world instance the run
  advances as its justification. The stale count remains in the tree, self-contradicting inside a
  single document, on exactly the archetype the detector exists to catch — and the reviewer already
  found it once and was never answered.
- **Task:** two separable changes.
  1. Correct the prose: change `SKILL.md:684`, `:686` and `:691` from "eight" to "nine", deriving the
     figure from the nine `nargs='?'` declarations in `review_completeness.py` rather than from the
     sibling paragraph.
  2. Widen the predicate so a modifier between the number and the noun does not defeat it — e.g.
     allow at most one intervening word token (`\s+(?:\w+\s+)?`) — and add `flag` to the closed
     cardinality-noun set. Re-derive the closed set from the corpus first (see G3); adjudicate at
     minimum `flag` (21 occurrences), `phase`/`phases` (37) and `states` (27), each against the
     "structural element of a skill contract that goes stale" criterion the pattern comment states.
     Add one positive test drawn from the real `the eight list flags` prose and one negative proving
     the intervening-word allowance does not admit an unbounded gap.
- **Done when:** `_detect_count_prose` surfaces `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md`
  line 691 when a sibling file in that skill directory is modified; the tree contains no
  "eight list flags" claim; and a test in `TestDetectCountProse` fails against the current
  adjacency-only predicate.
- **Suggested grouping:** ext-self-review-plan-marshall / count-prose detector

## G2 — Correct the misattributed PR number for the `--max-per-component` anchor

- **Severity:** major
- **Kind:** false-report-claim
- **Where:** `doc/plans/review-apparatus/090-feed-pr-findings-back-into-local-review/report-01.md:49`
- **Evidence:** the report states *"the flag AND its `if args.max_per_component < 0: … invalid_cap`
  guard were introduced together in the **same** squash-merged PR #1153 (`_lessons_query.py:232`),
  whose review threads are empty (Sourcery rate-limited, zero inline threads)."*
  `git log --oneline -S'max_per_component' -- marketplace/bundles/plan-marshall/skills/manage-lessons/scripts/_lessons_query.py`
  and the same search for `invalid_cap` each return exactly one commit: `010ea461`
  `feat(manage-lessons): surface active lessons prospectively (#1039)`. PR #1153 is `1296ede1`
  `feat(shims): give migration/back-compat shims an owner, floor, and removal trigger`, whose
  `--name-only` stat contains no `manage-lessons` path. CONFIRMED.
- **Impact:** the conclusion (the fix shipped with the flag, so it carries no posted review answer,
  so it is not in the answered corpus) survives — but the corroborating evidence attached to it
  ("whose review threads are empty, Sourcery rate-limited") was read off an unrelated PR and supports
  nothing. A later reader auditing the D0 anchor set would be sent to the wrong PR.
- **Task:** correct `report-01.md:49` to name PR **#1039** (commit `010ea461`), and either re-verify
  the "review threads are empty" observation against #1039 or drop that clause. Because the run
  report is a dated record of one execution, correct it in place with a short note rather than
  rewriting the surrounding analysis.
- **Done when:** `report-01.md:49` names the PR whose commit `git log -S'invalid_cap'` returns, and
  every corroborating clause on that line is verifiable against that PR.
- **Suggested grouping:** review-apparatus / plan-090 report corrections

## G3 — Land the noun-set derivation as a reproducible artifact, and adjudicate the candidates it surfaces

- **Severity:** minor
- **Kind:** omission
- **Where:** `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/_self_review_patterns.py:169-178`
  (the comment that carries the derivation's conclusion); `report-01.md:76` (the claim)
- **Evidence:** `plan.md:112-113` requires *"⚠ **Widening must be DERIVED, not guessed.** … Derive
  the noun set from the counts that actually appear in the corpus, and state whether the resulting
  set is closed."* `report-01.md:76` cites a 510-file scan via `scratchpad/derive_nouns.py`, which
  did not land. I re-ran the derivation over 517 `SKILL.md` + `standards/*.md` files: the report's
  characterisation reproduces (top followers `of` 307, `and` 123, `px` 116, `is` 87), but the added
  member was selected from the plan's docstring example, not from the distribution, and the
  distribution's own structural candidates were never adjudicated — `flags` 21, `phase`/`phases` 37,
  `states` 27, `columns` 16, `members` 14, against `check`/`checks` 13. CONFIRMED.
- **Impact:** the "derived, not guessed" discipline is claimed but not reproducible from a clone, and
  the un-adjudicated candidates include the exact noun G1 is about. A future widening has to redo the
  scan from scratch.
- **Task:** add a small, tested derivation utility (or a test that asserts the closed set against a
  derived candidate list) under the `ext-self-review-plan-marshall` scripts or its test tree, so the
  noun set's membership is checkable rather than asserted. Record in the `_CARDINALITY_NOUNS` comment
  which high-frequency candidates were considered and rejected, and why.
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
  deduplicates per `(file, line)`"* — and names neither `test_count_prose_surfaces_check_noun`
  (`test_self_review.py:1558`) nor `test_count_prose_does_not_fire_on_nouns_outside_closed_set`
  (`:1585`). Sibling rows in the same section (for example the flag-guard-pair row at `:369`) do
  enumerate every case, so this is drift, not a style difference. The repo's own rule at
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

## G5 — Correct `plan.md`'s own stale deliverable count

- **Severity:** minor
- **Kind:** stale-doc
- **Where:** `doc/plans/review-apparatus/090-feed-pr-findings-back-into-local-review/plan.md:59`
- **Evidence:** the Deliverables section opens *"Three. ⚠ **Expect a small yield — plausibly two or
  three detectors.**"* and then enumerates four numbered deliverables (D0 at `:62`, D1 at `:75`, D2
  at `:94`, D3 at `:117`). `report-01.md:17` records the correct arithmetic (*"The plan has four
  deliverables (D0 gate, D1, D2, D3)"*) without flagging the contradiction. CONFIRMED.
- **Impact:** a plan whose entire subject is stale count claims carries one in its own deliverables
  header. Cosmetic in effect, but it is the exact archetype and it undercuts the plan when quoted.
- **Task:** change `plan.md:59` to "Four." (or rephrase to avoid the bare count, e.g. "One gate and
  three deliverables"). Confirm the yield sentence that follows still reads correctly — it counts
  *detectors*, not deliverables, and should not be changed.
- **Done when:** the Deliverables section's stated count equals the number of numbered deliverables
  beneath it.
- **Suggested grouping:** review-apparatus / plan-090 report corrections

## G6 — Publish the re-derived detector-registry enumeration the plan's claim-labels table mandated

- **Severity:** minor
- **Kind:** omission
- **Where:** `plan.md:165` (the obligation); `report-01.md` §D0 (where the result is absent);
  `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/_self_review_detectors.py`
  (the registry)
- **Evidence:** the Claim-labels table states *"The detector registry is the unit of change and holds
  roughly eighteen `_detect_*` functions | OBSERVED — ⚠ the count is a lead | Enumerate the registry
  at HEAD. ⛔ **Re-derive; the list is actively grown and a shape this plan means to add may already
  have landed**"*. `grep -c "^def _detect_"` on the registry returns **20** at HEAD. The report never
  states the re-derived figure. CONFIRMED. The obligation's purpose was met in substance — the report
  checks `unguarded_boundaries` (`report-01.md:63`), `source_of_truth` and `scan_derived_keys`
  (`:119`) against specific candidates — but the enumeration is unrecorded.
- **Impact:** the plan's asserted-absence claim label ("no existing detector already covers a given
  candidate's shape") has no published population behind it, so a later reader cannot tell which
  detectors were checked against which candidate.
- **Task:** add the re-derived registry count and the per-candidate absence check to `report-01.md`'s
  D0 section — one line naming the count at the landing commit and, per "yes" candidate, which
  existing detectors were ruled out.
- **Done when:** `report-01.md` states the enumerated registry size and names the detectors excluded
  per candidate.
- **Suggested grouping:** review-apparatus / plan-090 report corrections

## Not gaps — checked and clear

Recorded so a later run does not re-derive them:

- **The landed code has no defect.** The `\b` sits outside the noun alternation, so `checks?` cannot
  match inside `checkpoints`; `(?i)` covers casing; both singular and plural branches are pinned by
  test; the added surface is a review anchor excluded from `counts.total`
  (`extension-api/standards/ext-point-self-review-surfacing.md:177`), so it cannot inflate the defect
  count; `check`/`checks` adds only 13 matches over 517 contract-source files.
- **D3's tests are discriminating, not vacuous.** Reproduced by mutation: the positive fixture fails
  against the pre-fix five-noun set; the negative fails under an any-noun mutant.
- **All four noun-set restatements are current at HEAD** (`_self_review_patterns.py:178`,
  `_self_review_detectors.py:1048`, `ext-self-review-plan-marshall/SKILL.md:256`,
  `phase-6-finalize/workflow/pre-submission-self-review.md:316`). The one later commit touching those
  files, `622f4484` (#1239), did not disturb them.
- **D1 is verified anchor-for-anchor** — `tier: full`, `persona: persona-security-expert`, `order: 9`,
  `_TIER_RANK`, `_apply_security_class_inactive` at `_manifest_rules.py:343-396`, the drop-reason
  string, `_CEREMONY_FINALIZE_DEFAULT = 'auto'`, and the #1201 traversal fix in `doc_references.py:253`.
- **Out-of-scope compliance is clean** — no `plugin-doctor` file, no simplify surface, no new knob,
  skill, standard or extension point; the two stop-rule candidates were routed out and recorded.
- **The four residue items are all still open**, but each is a deliberate hand-off recorded by the
  run, not an omission by it. They belong to their named owners (the cloud-plan-lane report gate,
  a future mirror-drift plan, and `manage-findings` / the triage contract) and are out of this plan's
  declared scope.
