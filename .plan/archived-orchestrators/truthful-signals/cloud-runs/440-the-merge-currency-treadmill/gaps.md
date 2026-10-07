# Gaps — 440-the-merge-currency-treadmill

**Source:** verification.md (same directory)   **Open items:** 6

## G1 — Bind a literal `verdict_inputs` glob to a path that exists

- **Kind:** missing-test
- **Severity:** medium
- **Where:** `test/plan-marshall/phase-6-finalize/test_verdict_currency.py:492` —
  `test_every_declared_surface_is_non_empty_and_well_formed` (and the surrounding
  declaration-conformance guard block, lines 486–504)
- **What is wrong:** The guards pin that every declared surface is non-empty, well-formed, rides a
  `head_dependent: true` step, and uses no `**`. None pins that a **wildcard-free** declared glob
  names a path that exists. All three of the sole declarer's globs
  (`.claude/skills/finalize-step-era-stamp-fill/SKILL.md:16-19`) are literal full paths. When such a
  path is renamed, `classify_advance` (`verdict_currency.py:210-220`) matches nothing on it and
  returns `preserved` for a commit that changed exactly that file. The exposure is demonstrated, not
  theoretical: `test_audit.py` was renamed to `test_audit_check_era_model.py` by #1266 (`983a6a2b`)
  after this plan merged; the declaration was updated in that same commit by the author's care, and
  nothing in the tree would have failed had it not been.
  **Confirmed by mutation during adversarial review** (file byte-snapshotted, `git diff --quiet`
  clean before, `RESTORED_CLEAN` + byte-identical after): the second declared glob was rewritten to
  `test/plan-marshall/audit-archived-plan-retrospectives/test_audit_RENAMED_GONE.py`, a path that
  does not exist, and
  `pytest test/plan-marshall/phase-6-finalize/test_verdict_currency.py
  test/plan-marshall/audit-archived-plan-retrospectives/test_era_stamp_fill.py` reported
  **55 passed, 0 failed**.
- **Why it matters:** A stale literal glob silently skips a gate that needed to run. That is the
  fail-open direction the plan's D1 verification condition forbids ("D1's uncertain case must be
  verified to re-run, not to skip") and which `ext-point-finalize-step.md:44` itself classifies as
  "a correctness defect, not a cost one". The classifier reports it as a confident `preserved` with
  `reason: disjoint_from_verdict_inputs`, so the failure is indistinguishable from a correct skip.
  **Bounded, which is why this is `medium` and not `high`:** no glob is stale in today's tree (all
  three resolve), so no wrong behaviour is shipped — this is a latent fail-open, not a live one. A
  partial indirect net also exists for two of the three globs:
  `test/plan-marshall/audit-archived-plan-retrospectives/test_era_stamp_fill.py:95-98` pins
  `era.AUDIT_REL` / `era.TEST_REL` to their expected values *and* asserts both resolve to files on
  disk, so a rename that left the step's own constants behind goes red there. What nothing covers is
  the case the mutation reproduced — the **frontmatter declaration** drifting away from constants
  that are themselves still correct — and the third glob (`era_stamp_fill.py`) has no net at all.
- **Fix:** Add a guard to `test_verdict_currency.py` that, for every glob in `_declared_surfaces()`
  containing no `*` or `?`, asserts the path exists under the repository root and is git-tracked.
  Globs that do contain a wildcard are exempt (they legitimately name a family). Name the declaring
  step and the offending glob in the assertion message.
- **Done when:** Renaming or deleting any wildcard-free path named in any step's `verdict_inputs`
  makes `pytest test/plan-marshall/phase-6-finalize/test_verdict_currency.py` fail, and the message
  names the step and the glob.
- **Module/topic:** `plan-marshall:phase-6-finalize` — verdict-currency classifier and its
  declaration-conformance guards.

## G2 — Correct the second head-dependent re-entry table in `phase-6-finalize/SKILL.md`

- **Kind:** incomplete-sweep
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md:1755`, `:1760`
  and `:1768` — § Resumability, "Special case — head-dependent steps"
- **What is wrong:** The file states the head-dependent re-entry decision twice. The Step 3 table at
  `:554` was changed to *"Consult the verdict-currency classifier … `preserved` → SKIP"*. The
  § Resumability restatement was not touched by the landed diff, and it is wrong in **three** places,
  not one — a broader sweep than the phrase the original finding used turns up two more:
  - `:1760` (table row) — *"`done` | differs from live HEAD | Re-fire (treat as no record — HEAD has
    advanced past the validated SHA, e.g., after a loop-back commit)."*
  - `:1755` (the section's own lead sentence) — *"a head-dependent step's resumable check is
    augmented with a worktree-HEAD comparison so a loop-back commit re-fires the gate instead of
    skipping it on a stale `done`"*, which states the bare-SHA-inequality rule as the whole rule.
  - `:1768` (the closing summary) — *"the HEAD-dependent quality gate re-fires whenever the tree it
    validated has been superseded"*, which is exactly the behaviour the classifier narrowed.

  The section's only cross-reference (`:1755`) defers *membership* to Step 3 ("for the single
  authoritative statement of that membership and its governing discriminator"), not the action, so
  all three sites read as authoritative for the action.
- **Why it matters:** Two rows of the same document give opposite instructions for the same input.
  An executor that resumes finalize by reading § Resumability re-fires unconditionally and forfeits
  the entire saving the plan exists to create — while an executor reading Step 3 does not, so the
  behaviour becomes a function of which section was read.
- **Fix:** Three edits in § Resumability, all in
  `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md`.
  1. `:1760` — replace the action cell with a pointer to the Step 3 table rather than a second copy:
     "Consult the verdict-currency classifier; see § 'Special case — HEAD-dependent steps' in Step 3
     for the single authoritative statement of the action."
  2. `:1755` — extend the existing cross-reference so it defers the **action** as well as the
     membership, and drop the "re-fires the gate" clause that states the superseded rule.
  3. `:1768` — replace "re-fires whenever the tree it validated has been superseded" with
     "re-fires whenever the tree it validated has been superseded **in a way the verdict-currency
     classifier rules invalidating**".

  Keep the `matches` and `field absent` rows as they are; they still agree with `:553` and `:555`.
- **Done when:** Every sentence and table cell in
  `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md` § Resumability that describes
  what a head-dependent step does on a differing HEAD either defers to Step 3 or names the classifier
  consult — checked by `grep -n "differs from live HEAD\|re-fires the gate\|re-fires whenever"
  marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md`, which must return no site
  prescribing an unconditional re-fire.
- **Module/topic:** `plan-marshall:phase-6-finalize` — SKILL.md dispatcher contract.

## G3 — Route the two surviving "unconditional rebase" statements in `branch-cleanup.md`

- **Kind:** incomplete-sweep
- **Severity:** low
- **Where:** `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md:1089`
  and `:1094` — the Pre-Merge Review-Completeness Barrier's structural-refusal WARNING and its
  operator note
- **What is wrong:** `:1089` tells the operator "this barrier re-resolves HEAD after an unconditional
  rebase, so grant against the HEAD the next pass resolves"; `:1094` says "each pass re-runs the
  unconditional rebase, an authoritative CI wait, and trigger A". On the `use_merge_queue == true`
  path the same document (`:367`, `:423`) skips the rebase entirely and downgrades the CI wait to a
  non-authoritative snapshot, so neither sentence is true there.
  **Attribution corrected during adversarial review.** `git log -S` does attribute both sentences to
  `9e9e9880` (#1241) — but `9e9e9880` is dated **2026-08-15 15:46:11 UTC** and `ee78fd91` (#1235)
  **2026-08-15 16:27:33 UTC**, and `git merge-base --is-ancestor 9e9e9880 ee78fd91` returns 0 while
  the reverse returns 1. #1241 therefore landed **41 minutes BEFORE** plan 440, not after it, and
  `git show ee78fd91:…/branch-cleanup.md | grep -c "unconditional rebase"` returns **2** — both
  sentences are present in plan 440's own merge commit. This is an **incomplete sweep by plan 440**,
  not later drift onto its surface. (What cannot be settled from this clone: PR #1235 squash-merged,
  so whether the run's working tree carried these lines while its sweeps ran, or whether the
  pre-merge rebase pulled them in afterwards, is not reconstructible here.)
- **Why it matters:** `:1089` is embedded in a WARNING that instructs an operator when to issue a
  HEAD-bound `merge-authorization grant`, and `:1094` is read when deciding whether to enable an
  unattended retry — both are operator-facing at a decision point. The premise is false on the queue
  path in each case. Severity is `low` rather than `medium` because neither changes the action the
  operator should take: on `use_merge_queue == true` HEAD does not advance between passes, so
  "grant against the HEAD the next pass resolves" resolves to the current HEAD and a grant issued
  against it is correct; `:1094` only overstates a cost. The defect is a false premise in
  operator-facing text, not misdirection into a wrong grant.
- **Fix:** Route both sentences by `use_merge_queue`, matching the conditional form the rest of the
  document uses (`{… (if use_merge_queue == false) | … (if use_merge_queue == true)}`). At `:1089`,
  state that HEAD is re-resolved after the rebase on the `false` path and is unchanged on the `true`
  path. At `:1094`, list the per-pass cost per path — rebase + authoritative CI wait + trigger A on
  `false`; CI snapshot + trigger A on `true`.
- **Done when:** No sentence in `branch-cleanup.md` asserts a rebase or an authoritative CI wait
  without naming the `use_merge_queue` path it holds on, checked by
  `grep -n "unconditional rebase" marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md`.
- **Module/topic:** `plan-marshall:phase-6-finalize` — branch-cleanup merge routing.

## G4 — Take D4's before/after measurement

- **Kind:** omission
- **Severity:** medium
- **Where:** the plan's D4; instrument at
  `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/manage-execution-manifest.py:2791`
  — `cmd_refire_report`
- **What is wrong:** D4 required a before/after measurement on a real finalize, publishing the
  per-step re-fire count and its billing-weighted cost with their population. No measurement exists.
  The run reported it as not done because a cloud lane has no `.plan/` state and therefore no
  finalize to measure. The instrument and the denominator definition were delivered; the number was
  not.
- **Why it matters:** The plan's own Verification section says a savings claim with no denominator
  is "exactly what this epic files against others". Until the measurement is taken, the effect of
  the whole change — currently reaching exactly one of eleven head-dependent steps — is asserted
  rather than shown, and there is no evidence that a one-step reach moves the number at all.
- **Fix:** On a local plan-marshall checkout, run one finalize over the same plan shape in each of
  two arms. **Before** = a checkout of `87c71d3f` (`ee78fd91^`, the last commit without the
  classifier) — *not* `origin/main`, which already contains `ee78fd91` and would give two identical
  arms. **After** = `origin/main` (or any descendant of `ee78fd91`). Report
  `refire-report --plan-id X --phase 6-finalize` for each, plus the billing-weighted cost, and state
  the `token_population` the payload names alongside the known floor
  (`default:pre-push-quality-gate` is on the § "Inline steps" roster at
  `phase-6-finalize/standards/dispatch-inline-split.md:41`, so it records a zero token triple by
  contract and contributes nothing to any ledger figure).
- **Done when:** Both arms' `refires` per step and their billing-weighted costs are published with
  their populations, in a document the plan directory or a successor plan links to.
- **Module/topic:** `plan-marshall:phase-6-finalize` / `plan-marshall:manage-execution-manifest` —
  verdict-currency measurement.

## G5 — Correct the "three earliest head-dependent steps" claim in `report-01.md`

- **Kind:** stale-statement
- **Severity:** low
- **Where:** `doc/plans/truthful-signals/440-the-merge-currency-treadmill/report-01.md` — § D0,
  "Why the observed 5× / 7× / 7× falls where it does" (and the same claim in the merged PR #1235
  body)
- **What is wrong:** The report states the three named steps "are the three EARLIEST head-dependent
  steps in the pipeline (`order` 4, 6, 7)". Re-derived from frontmatter at HEAD, the head-dependent
  orders are 4, 5, 6, 7, 8, 9, 21, 22, 30, 40, 990. `default:pre-push-quality-gate` is `order: 5`
  (`marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/pre-push-quality-gate.md`),
  so the three earliest are 4, 5, 6. The follow-on sentence — that the reported counts are
  "consistent with that ordering" — rests on the same false premise; the cited counts (5× at order 4,
  7× at orders 6 and 7) increase with order, which the positional argument predicts should decrease.
- **Why it matters:** This is the report's only first-party explanation of the plan's headline
  observation, and it is the sentence a retrospective would cite when reasoning about where re-fires
  concentrate. It is also the epic's own subject matter: a derived-sounding claim that the derivation
  does not support.
- **Fix:** Correct the enumeration to the three earliest head-dependent steps by order
  (`finalize-step-lessons-housekeeping` 4, `pre-push-quality-gate` 5, `finalize-step-plugin-doctor` 6),
  and either drop the "consistent with that ordering" inference or restate it as an unverified
  observation, since the reported counts are not monotone in `order`.
- **Done when:** The report's D0 section names an ordering that matches the frontmatter-derived
  population, and makes no consistency claim the cited counts do not support.
- **Module/topic:** `doc/plans/truthful-signals/440` — run-report accuracy.

## G6 — The refusal-table guard is a substring check, so a renamed refusal section stays green

- **Kind:** vacuous-guard
- **Severity:** high
- **Where:** `test/plan-marshall/phase-6-finalize/test_verdict_currency.py:546-569` —
  `test_every_tabled_refusal_carries_its_section`, specifically the
  `assert _REFUSAL_HEADING in body` at `:565`
- **What is wrong:** `verdict-currency.md:164-170` states that the refusal table is illustrative and
  underivable, and that what *is* pinned by a guard is the link between each row and its evidence:
  *"`test_verdict_currency.py` asserts that every step named here carries the refusal section this
  table cites. A row whose section is deleted or renamed fails at quality-gate rather than rotting
  silently."* The guard does not do that. It reads the step's whole doc into `body` and tests
  `'Verdict-input surface — deliberately undeclared' in body` — a bare substring search over the
  entire file, with no anchoring to a heading. Both tabled steps carry that exact phrase **twice**:
  once as their own `###`/`##` heading, and once inside a cross-reference to the *other* step's
  section (`.claude/skills/finalize-step-plugin-doctor/SKILL.md:46` and `:55`;
  `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/pre-push-quality-gate.md:313`
  and `:371`). So for either row, deleting or renaming the heading the table cites leaves the guard
  green on the strength of the surviving cross-reference.
  **Demonstrated by mutation** (byte-snapshotted, `git diff --quiet` clean before, `RESTORED_CLEAN`
  and byte-identical after): renaming *only* the `### Verdict-input surface — deliberately
  undeclared` heading at `.claude/skills/finalize-step-plugin-doctor/SKILL.md:46` →
  `pytest test/plan-marshall/phase-6-finalize/test_verdict_currency.py` reported **39 passed**.
  Renaming *both* occurrences → **1 failed**,
  `test_every_tabled_refusal_carries_its_section`. The guard bites only when the phrase leaves the
  file entirely, which is not the defect it is written against.
- **Why it matters:** This is the rubric's `high` case exactly — a guard that passes against the
  defect it names. `verdict-currency.md` cites the guard as the reason the table's illustrative
  status is safe ("a row whose section is deleted or renamed fails at quality-gate rather than
  rotting silently"), so the document's own risk disclosure rests on a check that does not hold.
  A refusal is the record of *why* a head-dependent step declines to declare a `verdict_inputs`
  surface; if that section is renamed away and nothing fails, the table asserts evidence that is
  gone — and a later author reading the table has no way to tell. The failure mode is silent and
  affects **both** currently-tabled rows, not one.
- **Fix:** In `test/plan-marshall/phase-6-finalize/test_verdict_currency.py`, replace the
  `assert _REFUSAL_HEADING in body` substring test with a heading-anchored match — e.g.
  `re.search(rf'^#{{1,6}}\s+{re.escape(_REFUSAL_HEADING)}\s*$', body, re.MULTILINE)` — so only a
  real ATX heading in that step's own doc satisfies the row. Keep the existing assertion message and
  add the matched-or-not heading level to it.
- **Done when:** Renaming the `### Verdict-input surface — deliberately undeclared` heading in
  `.claude/skills/finalize-step-plugin-doctor/SKILL.md` (leaving the cross-reference on the following
  lines untouched) makes `pytest test/plan-marshall/phase-6-finalize/test_verdict_currency.py` fail,
  and the same holds for the `##` heading in
  `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/pre-push-quality-gate.md`.
- **Module/topic:** `plan-marshall:phase-6-finalize` — verdict-currency refusal-table guards.
