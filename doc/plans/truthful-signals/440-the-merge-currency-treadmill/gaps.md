# Gaps — 440-the-merge-currency-treadmill

**Source:** verification.md (same directory)   **Open items:** 5

## G1 — Bind a literal `verdict_inputs` glob to a path that exists

- **Kind:** missing-test
- **Severity:** high
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
- **Why it matters:** A stale literal glob silently skips a gate that needed to run. That is the
  fail-open direction the plan's D1 verification condition forbids ("D1's uncertain case must be
  verified to re-run, not to skip") and which `ext-point-finalize-step.md:44` itself classifies as
  "a correctness defect, not a cost one". The classifier reports it as a confident `preserved` with
  `reason: disjoint_from_verdict_inputs`, so the failure is indistinguishable from a correct skip.
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
- **Where:** `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md:1760` — § Resumability,
  "Special case — head-dependent steps"
- **What is wrong:** The file states the head-dependent re-entry decision twice. The Step 3 table at
  `:554` was changed to *"Consult the verdict-currency classifier … `preserved` → SKIP"*. The
  § Resumability table at `:1760` was not touched by the landed diff and still reads
  *"`done` | differs from live HEAD | Re-fire (treat as no record — HEAD has advanced past the
  validated SHA, e.g., after a loop-back commit)."* The section's only cross-reference (`:1754`)
  defers *membership* to Step 3, not the action, so the row reads as authoritative for the action.
- **Why it matters:** Two rows of the same document give opposite instructions for the same input.
  An executor that resumes finalize by reading § Resumability re-fires unconditionally and forfeits
  the entire saving the plan exists to create — while an executor reading Step 3 does not, so the
  behaviour becomes a function of which section was read.
- **Fix:** Replace the `:1760` action cell with a pointer to the Step 3 table rather than a second
  copy — e.g. "Consult the verdict-currency classifier; see § 'Special case — HEAD-dependent steps'
  in Step 3 for the single authoritative statement of the action." Keep the `matches` and
  `field absent` rows as they are; they still agree with `:553` and `:555`.
- **Done when:** `grep -n "differs from live HEAD" marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md`
  returns no row that prescribes an unconditional re-fire, and the file states the classifier consult
  exactly once as the authority.
- **Module/topic:** `plan-marshall:phase-6-finalize` — SKILL.md dispatcher contract.

## G3 — Route the two surviving "unconditional rebase" statements in `branch-cleanup.md`

- **Kind:** stale-statement
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md:1089`
  and `:1094` — the Pre-Merge Review-Completeness Barrier's structural-refusal WARNING and its
  operator note
- **What is wrong:** `:1089` tells the operator "this barrier re-resolves HEAD after an unconditional
  rebase, so grant against the HEAD the next pass resolves"; `:1094` says "each pass re-runs the
  unconditional rebase, an authoritative CI wait, and trigger A". On the `use_merge_queue == true`
  path the same document (`:367`, `:423`) skips the rebase entirely and downgrades the CI wait to a
  non-authoritative snapshot, so neither sentence is true there. `git log -S` attributes both to
  `9e9e9880` (#1241), which landed *after* PR #1235 — this is drift onto the surface plan 440
  established, not an omission by plan 440.
- **Why it matters:** `:1089` is embedded in a WARNING that instructs an operator when to issue a
  HEAD-bound `merge-authorization grant`. On the queue path HEAD does not advance, so the advice
  about "the HEAD the next pass resolves" is wrong guidance at the moment a human acts on it. `:1094`
  overstates the cost of an unattended retry on the queue path.
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
- **Fix:** On a local plan-marshall checkout, run one finalize on `origin/main` as the *before* and
  one with `ee78fd91` in force as the *after*, over the same plan shape. Report
  `refire-report --plan-id X --phase 6-finalize` for each, plus the billing-weighted cost, and state
  the `token_population` the payload names alongside the known floor
  (`default:pre-push-quality-gate` is inline and contributes zero tokens to any ledger figure).
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
