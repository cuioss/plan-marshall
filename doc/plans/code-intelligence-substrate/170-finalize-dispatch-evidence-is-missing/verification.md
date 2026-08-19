# Verification — 170-finalize-dispatch-evidence-is-missing

**Audited:** `plan.md`, `report-01.md` (the only two files in the plan directory)
**Tree state:** originally audited at `62e3807` on `claude/code-intelligence-substrate-analysis-kah884`;
adversarially re-derived at `a90adeb` on the same branch, with
`check-dispatch-audit.py` confirmed byte-identical across both readings
(md5 `c66b54c9a44ed44e6ec90678f448f0c4`). The plan landed as squash commit `c93431f`,
"fix(plan-retrospective): make the dispatch audit deterministic and fail-able (#1225)".
**Overall verdict:** PARTIAL — the deliverables shipped and work, but D1 and D3 fall short of their
literal *Done when* and D2's accepted mechanism deviation carries an undisclosed blind spot

All five deliverables are present in the tree, the detector was built, is registered, is tested, and
its `not_evaluated` guard is proven load-bearing by mutation. Three of the five meet their literal
*Done when* outright; **D1 and D3 do not**.

- **D1** requires *"never a bare `0`"*, and the shipped `counts.by_category` block emits four bare
  zeros — in the same output where the nested `shape_violation` block correctly says
  `not_evaluated` (G3, raised to high on adversarial review).
- **D3**'s `channel_completeness` pairs an all-caller numerator with two finalize-only denominators
  and so reports `confidence: nominal` in exactly the situation D3 exists to expose (G1), and has no
  "did not evaluate" state at all (G2).
- **D2** meets its literal *Done when* but its accepted mechanism deviation carries an undisclosed
  blind spot: the token-record discriminator's `ran_inline` branch is a fall-through default, not a
  measurement, so `missing_dispatch_emission` — D2's own headline finding — cannot fire for the
  class of step whose instrumentation failed (G13, found on adversarial review).

Beyond those: one production branch has no test at all, one code comment in the D4 change states a
deferral to a guard that provably cannot fire, and the run left two plan-mandated cross-notes
unwritten.

## Deliverable verdicts

| # | Deliverable (short) | Report claim | Ground truth | Verdict |
|---|---|---|---|---|
| D1 | Make the audit able to fail; population beside every count; never a bare `0` | New deterministic `check-dispatch-audit.py`; `not_evaluated` when Surface B empty; fires on a divergent site | `check-dispatch-audit.py:303-356`; `not_evaluated` branch verified load-bearing by mutation (2 tests go red); divergent-site test present and green. **But `counts.by_category` (`:542-550`) publishes four bare zeros** | PARTIAL — first clause met, "never a bare `0`" clause not (G3; also G4/G10) |
| D2 | Consumer distinguishes dispatched / ran-inline / no-evidence; `missing_dispatch_emission` against the dispatcher | Token record is the discriminator; old "ran inline" finding gone; both mis-attributions tested | `check-dispatch-audit.py:359-413`; `dispatch_coverage_violation` absent from the whole tree; both directions tested (`test_check_dispatch_audit.py:168`, `:199`). The discriminator's `ran_inline` branch is a fall-through default, not a measurement | CONFIRMED against the literal *Done when*; mechanism deviation not outcome-equivalent (G13, G8) |
| D3 | Publish dispatch-line count vs envelope-completion count; sparse channel downgrades confidence | `channel_completeness` with `none`/`low`/`nominal` | `check-dispatch-audit.py:416-451`. Block exists and grades, but its numerator is **all-caller** dispatch lines while its two denominators are **finalize-only** — a fixture with zero finalize dispatch lines reports `nominal` | PARTIAL (G1, G2, G6) |
| D4 | Per-task artifact emission complete, or its scope limit declared as an N-of-M **population** | `artifact_emission: {completed_tasks, tasks_with_artifacts, tasks_without_artifacts}`; WARNING only for `0 < N < M` | `analyze-logs.py:928-975`, emitted at `:1678`, finding at `:1571-1586`. Population always published — Done-when met. The code comment's deferral of the `N == 0` case to the plan-level floor is false | CONFIRMED (with G7) |
| D5 | Tests, each verified to FAIL pre-fix, incl. one asserting a deliberately-divergent step | 13 tests; D4 tests verified red pre-fix | `test_check_dispatch_audit.py` — **13 collected, 13 passed** (re-run at audit time). Divergent-site test present. One production branch has no test | CONFIRMED (with G6) |

## Per-deliverable detail

### D1 — make the audit able to fail

- **Required (plan):** *"the check either produces a finding against a deliberately divergent site,
  or reports `not_evaluated` with its reason — and never a bare `0`"*, with the population published
  beside every count and the detector population-derived rather than literal.
- **Claimed (report):** a new `check-dispatch-audit.py` whose `shape_violation` pairs Surface B
  (`effort resolve-target` decision-log records) against Surface A (`[DISPATCH]` work-log lines),
  reports `not_evaluated` when Surface B is empty, and fires on a divergent site.
- **Found:**
  - `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/check-dispatch-audit.py:303-356`
    — `evaluate_shape_violation`. `population = len(resolves)` (line 317) is read from the log, not a
    literal. Lines 318-331 return `status: not_evaluated` with a reason string.
  - Divergent-site test: `test/plan-marshall/plan-retrospective/test_check_dispatch_audit.py:127-143`.
  - Clean-with-population test: `:146-160`. Empty-population test: `:108-124`.
  - Registered as a script-backed aspect: `plan-retrospective/SKILL.md:192`, `:258`, `:497`, and
    `standards/execution-context-dispatch-audit.md:127-134`; `retro_sections.py:56` carries the key,
    guarded by `test_registered_aspects_render.py:266`.
- **Checks run:**
  - `uv run python -m pytest test/plan-marshall/plan-retrospective/test_check_dispatch_audit.py -o addopts=""`
    → `13 passed in 10.27s`.
  - **Mutation (guard is load-bearing):** replaced `if population == 0:` with `if False:` at
    `check-dispatch-audit.py:318` → `2 failed, 11 passed`
    (`test_shape_violation_not_evaluated_when_surface_b_empty`, `test_absent_inputs_degrade_cleanly`).
    File restored byte-for-byte from `/tmp/verify-170-mutsweep/check-dispatch-audit.py.orig`
    (md5 `c66b54c9a44ed44e6ec90678f448f0c4` before and after); `git status --porcelain` clean for the
    file.
  - **Live run against a hand-built plan with no logs at all** (`/tmp/verify170/base/plans/empty`):
    `shape_violation.status: not_evaluated` with its reason. Confirmed.
- **Verdict:** PARTIAL. The *Done when*'s first clause is met — the check fires on a divergent site
  and reports `not_evaluated` with its reason — and the guard is non-vacuous under mutation. The
  clause *"and never a bare `0`"* is **not** met: the same output's `counts.by_category` block
  (`:542-550`) publishes `shape_violation: 0` with nothing beside it in exactly the never-evaluated
  case, re-derived live against a log-less plan directory. The plan's own § Verification names this
  as the acceptance test (*"for each zero, whether the check evaluated anything. If it cannot tell,
  D1 has not been met"*), so this is a shortfall against the deliverable rather than a stylistic
  residue — G3 is raised to high accordingly. G4 (no population anywhere for the two preserved
  checks) and G10 (a navigation defect in the standard, downgraded to low) remain alongside.

### D2 — consumer distinguishes dispatched / ran-inline / no-evidence

- **Required (plan):** a step with envelope evidence but no dispatch line is
  `missing_dispatch_emission` against the **dispatcher**, never a coverage violation against the
  step; a conditionally-dispatching step that legitimately runs inline is not reported at all; both
  mis-attributions reproduced in tests and corrected. The plan named a *roster qualifier* as the
  mechanism for the conditional case.
- **Claimed (report):** classification by the `execution.toon` `execution_log[]` token record, with a
  **declared deviation** — token record instead of a roster qualifier.
- **Found:**
  - `check-dispatch-audit.py:359-413` — `evaluate_dispatch_coverage`; three states at lines 380-386;
    `missing_dispatch_emission` at lines 388-404 with the message explicitly attributing the fault to
    the DISPATCHER (line 400-402).
  - The old category is gone: grepping `dispatch_coverage_violation` across `marketplace/` and
    `test/` returns exactly three hits — the removal note at
    `standards/execution-context-dispatch-audit.md:60` and `:62`, and one *negative* assertion at
    `test_check_dispatch_audit.py:196`. No producer emits it.
  - Both directions tested: `test_check_dispatch_audit.py:168-196` (dispatched-but-unlogged →
    `missing_dispatch_emission`, and *not* a coverage violation) and `:199-219` (conditional inline →
    `ran_inline`, `_categories(data) == []`). Third state at `:222-239`.
  - **Surface E's premise holds in one direction only, and the original audit quoted the half that
    holds.** The quotation attributed here to `phase-6-finalize/SKILL.md:1151` was neither at that
    line (`:1151` is blank; the text is at `:1153`) nor verbatim: it ended *"with zero token
    attribution for inline steps"*, dropping the six words the source actually carries — *"…for
    inline steps **that carry no `<usage>` tag**"*. Corrected, the contract reads: every finalize
    step lands an `execution_log` row (true, and that is what makes `no_evidence` meaningful), **but
    a zero in that row does not identify an inline step.** `:1163` says the triple is *"the SAME
    triple captured by 5b"*, and `:1081` says *"Inline steps and timed-out steps skip this call"*;
    the producer states the consequence outright at
    `manage-execution-manifest.py:2613-2614` — *"a step dispatched without a `<usage>` tag reports
    zeros rather than a missing column"* — and again at `:2799-2803` (*"`total_tokens` is a
    FLOOR"*). The forward direction of the docstring's claim (dispatched ⇒ non-zero) is therefore
    **not** guaranteed, and the converse it actually classifies on (zero ⇒ inline) is false. → **G13.**
- **Checks run:** the 13-test file green; the negative assertion `'dispatch_coverage_violation' not in
  _categories(data)` is real (the category exists nowhere as a producer, so the assertion is
  structurally satisfied rather than behaviourally — noted under Test adequacy). Live runs against
  two hand-built fixtures settle the discriminator empirically: a terminal step whose `execution_log`
  row carries `{outcome: error, total_tokens: 0}` and no `[DISPATCH]` line reports
  `dispatched: 0, ran_inline: 1, missing_dispatch_emission: 0`; the same fixture with the
  `total_tokens` column **absent entirely** reports identically — `ran_inline`, not `no_evidence`,
  because `finalize_token_records`' `else: value = 0` (`:278-279`) manufactures the "measured zero"
  the classifier then treats as proof.
- **Verdict:** CONFIRMED against the literal *Done when* (*"both mis-attributions are reproduced in
  tests and both are corrected"*) — both are. But the accepted mechanism deviation is **not**
  outcome-equivalent, as originally recorded here. Substituting the token record for the plan's
  literal *roster qualifier* is equivalent for the conditional-inline case (and the plan's claim
  table does cite token attribution as ground truth *for that case*); it is not equivalent for the
  dispatched-but-unmeasured case, where a roster qualifier would still have marked the row as
  dispatching and surfaced the missing emission. The deviation traded one blind spot for another and
  the trade was never stated. → **G13** (high). The aggregate-rather-than-per-step pairing is G8.

### D3 — the channel-completeness report

- **Required (plan):** *"Publish dispatch-line count against envelope-completion count, so a sparse
  channel downgrades the audit's own confidence… Done when: the ratio is reported alongside the
  findings and a deliberately sparse channel lowers the reported confidence."*
- **Claimed (report):** `channel_completeness` publishes `dispatch_line_count` against
  `completion_count` and `dispatched_step_count` and grades `none` / `low` / `nominal`.
- **Found:** `check-dispatch-audit.py:416-451`, wired at `:535-537`.
- **Checks run — the block does not do what D3 requires in the case D3 exists for.** I built a plan
  fixture at `/tmp/verify170/base/plans/xp` shaped like a real plan post-#1232: **6 phase-5
  `[DISPATCH]` lines**, **3 finalize `[STEP] … Completed step:` lines**, **3 finalize
  `execution_log` rows with `total_tokens: 5000`**, and **zero finalize `[DISPATCH]` lines**. Live
  run output:

  ```
  dispatch_coverage:
    dispatched: 3
    missing_dispatch_emission: 3
  channel_completeness:
    dispatch_line_count: 6
    completion_count: 3
    dispatched_step_count: 3
    ratio: 2.0
    confidence: nominal
  ```

  The audit simultaneously reports three missing dispatch emissions **and** `confidence: nominal`.
  The cause is at `cmd_run`: `evaluate_channel_completeness(len(dispatch_lines), …)`
  (`check-dispatch-audit.py:535-537`) passes the **all-caller** line count, while the same function
  already computed `finalize_dispatch_line_count` at `:522-524` and passes *that* to
  `evaluate_dispatch_coverage`. `completion_count` is finalize-only by construction — the emitter is
  phase-scoped (`manage-status/scripts/_cmd_mark_step.py:195-198`: *"Scoped to the finalize phase …
  a phase-5 `mark-step-done` writes no such line"*). Numerator and denominators are therefore drawn
  from different populations. → **G1.**
- **Second check:** a plan directory containing only an empty `logs/` (no work log, no decision log,
  no manifest, no status) produces `confidence: nominal`, `ratio: null`, all counts `0`. The module
  docstring at `check-dispatch-audit.py:58-59` promises *"a missing input degrades the affected block
  to `not_evaluated` / `no_evidence` with a reason, never a false clean"*; `channel_completeness` has
  no such state, and `test_absent_inputs_degrade_cleanly:396` pins `confidence == 'nominal'` as
  correct. → **G2.**
- **Verdict:** PARTIAL. The block exists, publishes both counts and a ratio, and the two tested
  sparse cases do downgrade — so the plan's literal *Done when* is technically met by the fixtures the
  run chose. It is not met by the fixture that reproduces the real defect the plan describes.

### D4 — per-task artifact emission population statement

- **Required (plan):** *"either emission is complete, or the output states both numbers"*, and the
  scope limit must be a POPULATION statement (`N of M`), never a non-zero assertion.
- **Claimed (report):** `analyze-logs.py` publishes
  `artifact_emission: {completed_tasks, tasks_with_artifacts, tasks_without_artifacts}`; the bare
  `artifact_entries == 0` floor is preserved; a WARNING fires only for `0 < N < M`.
- **Found:** `analyze-logs.py:928-975` (`artifact_emission_population`), emitted into the payload at
  `:1678`, finding constructed at `:1571-1586`. Message carries both numbers verbatim
  (`"{N} of {M} completed task(s) emitted >= 1 [ARTIFACT] line"`). Tests at
  `test_analyze_logs.py:1760-1840` (`TestArtifactEmissionPopulation`, three cases).
- **Checks run:** wrote a temporary probe test (since deleted; tree verified clean afterwards) with
  **M = 3** completed tasks, **N = 0** per-task `[ARTIFACT]` lines, and two ordinary phase-1
  `[ARTIFACT]` lines in the work log. Result:
  `EMISSION: {'completed_tasks': 3, 'tasks_with_artifacts': 0, 'tasks_without_artifacts': ['TASK-001','TASK-002','TASK-003']}`,
  `ARTIFACT_ENTRIES: 2`, and **zero findings of any kind**. The comment at `analyze-logs.py:1566`
  reads *"`N == 0` is left to the plan-level floor"*, but that floor is
  `elif footprint and artifact_entries == 0` (`:1551`) over a caller-agnostic tag count (`:1519`),
  and `phase-1-init/SKILL.md:454` and `:1027` emit `[ARTIFACT]` unconditionally on every plan. The
  floor therefore cannot fire for a real plan, and the total-failure case is silent. → **G7.**
- **Verdict:** CONFIRMED against the literal *Done when* — the population is always published, which
  is what the plan required. The deferral claimed in the code comment is false.

### D5 — tests, each verified to FAIL pre-fix

- **Required (plan):** tests, each verified to fail pre-fix, including one asserting the audit
  reports a deliberately-divergent step.
- **Claimed (report):** 13 tests; every detector exercises a divergent site and a clean site; the D4
  tests were run against the pre-fix `analyze-logs.py` and confirmed red; for the new detector
  "red pre-fix" is inherent.
- **Found / checks run:** 13 tests collected and green. Every category has a firing test
  (`shape_violation` `:127`, `missing_dispatch_emission` `:168`, `envelope_violation` `:355`,
  `generic_subagent_violation` `:370`) and a non-firing counterpart (`:146`, `:199`, `:222`, `:242`).
  The D1 guard mutation above proves the not_evaluated branch is genuinely guarded.
- **Gap found:** the third `confidence` branch is untested. Mutating
  `check-dispatch-audit.py:441` from
  `elif ratio is not None and ratio < _SPARSE_RATIO and completion_count > 0:` to
  `elif False and …` left the suite at **13 passed** (run twice: `13 passed in 7.83s`,
  `13 passed in 3.79s`). The `_SPARSE_RATIO` threshold and its branch are dead to the test suite. →
  **G6.**
- **Verdict:** CONFIRMED with one uncovered branch.

## Correctness review

Read in full: `check-dispatch-audit.py` (598 lines), `analyze-logs.py:900-975` and `:1512-1600`,
`standards/execution-context-dispatch-audit.md` (152 lines), the aspect wiring in
`plan-retrospective/SKILL.md`, `manage-config/scripts/_cmd_effort.py:440-570`,
`manage-status/scripts/_cmd_mark_step.py:182-222`. Defects found:

1. **Cross-population comparison in `channel_completeness`** —
   `check-dispatch-audit.py:535-537` passes `len(dispatch_lines)` (every caller) while
   `completion_count` (`:521`) and `dispatched_step_count` are finalize-only. Failing input: any plan
   with more phase-5 dispatch lines than finalize dispatched steps and a missing finalize dispatch
   channel. Consequence: `confidence: nominal` and `ratio > 1` on a channel that is provably empty
   for the phase the audit covers — the audit's own trust grade is wrong in exactly the direction it
   was built to prevent. Reproduced above. (G1)
2. **`channel_completeness` fails open on an empty population** —
   `check-dispatch-audit.py:436-444`: no branch produces a "did not evaluate" verdict, so all-zero
   inputs fall through to `confidence: nominal`. This contradicts the module docstring at `:58-59`.
   Reproduced against a log-less plan directory. (G2)
3. **`counts.by_category` publishes four bare zeros with no population** —
   `check-dispatch-audit.py:542-550`. In the log-less run, `shape_violation: 0` appears in `counts`
   while the nested block correctly says `not_evaluated`; a consumer reading only `counts` sees the
   exact ambiguity the plan's ⭐ paragraph forbids. (G3)
4. **`envelope_violation` and `generic_subagent_violation` publish no population anywhere** —
   `check-dispatch-audit.py:454-490` return bare finding lists; neither the number of `[DISPATCH]`
   lines inspected nor the number of work-log lines scanned is stated beside their counts. A `0` from
   a missing `work.log` is indistinguishable from a `0` over a populated log. (G4)
5. **`dispatch_coverage` has no not-evaluated state** — `check-dispatch-audit.py:405-413` returns
   `evaluated_population: 0` and four zeros when `status.json` is absent or malformed
   (`load_status_metadata:195-205` swallows both `OSError` and `JSONDecodeError` into `{}`). The
   population is published, so it is legible; but unlike its sibling it carries no `status` and no
   `reason`. (G5)
6. **`missing_dispatch_emission` is a count comparison, not a pairing** —
   `check-dispatch-audit.py:388`: `missing = max(0, len(dispatched) - finalize_dispatch_line_count)`.
   Since #1232 every re-firing re-emits a `[DISPATCH]` line (`phase-6-finalize/SKILL.md:629`), extra
   lines from a re-fire cancel a genuine missing emission one-for-one, and the finding names no step.
   The code documents this as "a floor" (`:373-375`), so it is a declared limitation, not a
   surprise — but it is a limitation on the deliverable's own headline case. (G8)
7. **D4's `N == 0` deferral cannot happen** — `analyze-logs.py:1566` vs `:1551` and `:1519`, proved
   empirically above. (G7)
8. **`shape_violation` is near-tautological at HEAD** — `_cmd_effort.py:503-518` writes Surface B and
   Surface A from one call with the same `role` value, and since #1232 finalize passes `--workflow`
   (`phase-6-finalize/SKILL.md:618`). A resolve that emits its decision-log record therefore emits
   its `[DISPATCH]` line in the same breath; the only way the pairing can diverge is a partial
   best-effort logging failure. The standard records the corroboration limit
   (`standards/execution-context-dispatch-audit.md:40`) but the LLM interpretation rule at `:122`
   still reads a `shape_violation` count as a live signal without warning that at HEAD a `0` over a
   populated Surface B is almost forced. (G10)

9. **`ran_inline` is a fall-through default, not a measurement** — `check-dispatch-audit.py:380-386`
   classifies `no_evidence` only when the step has no `execution_log` row at all; every row that is
   not a positive integer — an explicit zero, a dispatched step whose `<usage>` tag never arrived
   (`manage-execution-manifest.py:2611-2614`, `:2650`), or a row with no `total_tokens` column,
   which the detector's own `else: value = 0` at `:278-279` converts into a "measured zero" —
   collapses into `ran_inline`, which `:366-369` and the shipped standard `:62` both call *proof*
   that the step ran inline. `dispatched` therefore under-counts, and `missing_dispatch_emission`
   (`:388`) is computed by subtracting from that under-count, so D2's headline finding cannot fire
   for exactly the class of step whose instrumentation failed; `dispatched_step_count` carries the
   same under-count into D3's shortfall branch (`:439`). Reproduced against two fixtures. (G13)
10. **The `else: value = 0` coercion is dead to the test suite** — mutating it to `value = 999999`
    left `test_check_dispatch_audit.py` at **13 passed**. Every test supplies an integer
    `total_tokens`, so no test exercises the branch that manufactures the ambiguity in 9. (G13's
    *Done when* covers it.)

No defect was found in: the regexes (`_DISPATCH_LINE_RE` correctly requires the `(caller)` paren and
the `target=` guard excludes phase-entry markers), `_canon_step` (matches `record-step`'s
`default:`-stripping canonicalisation), `finalize_token_records`' `bool`/`int` ordering (`bool` is
excluded before the `int` branch at `:271-273`) and its `max()` at `:281` (which correctly prevents a
later zero masking an earlier dispatched measurement — note this is what keeps a re-entry `skipped`
row from erasing a genuine earlier dispatch), the `ratio` computation at `:436` (it divides before
rounding, not after), `FINALIZE_DISPATCH_CALLER` (both finalize dispatch sites —
`phase-6-finalize/SKILL.md:618` and `:950-953` — pass `--caller plan-marshall:phase-6-finalize`), or
`read_log_lines` / `load_manifest` (absent files degrade rather than raise). The `else: value = 0`
coercion inside `finalize_token_records` is the one part of that function that IS defective — see 9
and 10 above; the original audit's clean bill for the function as a whole is corrected here.

## Test adequacy

| Deliverable | Covering tests | Non-vacuity evidence |
|---|---|---|
| D1 | `test_check_dispatch_audit.py:108`, `:127`, `:146` | Mutation `if population == 0:` → `if False:` turned 2 tests red. Guard is load-bearing. |
| D2 | `:168`, `:199`, `:222`, `:242` | Positive-fire test asserts a specific finding category and count; the "conditional inline" test asserts `_categories(data) == []` against a populated fixture. Both are behavioural. **But all four supply an integer `total_tokens`**, so the `else: value = 0` coercion at `:278-279` is untested: mutating it to `value = 999999` left 13/13 green. The `dispatched`/`ran_inline` boundary is pinned only where the input is already unambiguous. |
| D3 | `:271` (`none`), `:296` (`nominal`), `:320` (`low`) | All three exercise real fixtures. **But the fourth path — `ratio < _SPARSE_RATIO` at `:441` — is untested**: disabling it with `elif False and …` left 13/13 green (two independent runs). |
| D4 | `test_analyze_logs.py:1791`, `:1810`, `:1825` | Partial-case test asserts the floor is satisfied (`artifact_entries >= 1`) *and* the population finding fires — the exact defect. Behavioural. |
| Preserved checks | `:355`, `:370` | Both fire on a divergent fixture. Clean counterparts are implicit in the `_categories(data) == []` assertions of other tests. |

One weak assertion: `test_check_dispatch_audit.py:196`
(`assert 'dispatch_coverage_violation' not in _categories(data)`) cannot fail, because no producer
anywhere in the tree emits that category — it is a regression epitaph, not a guard. Harmless, but it
is not evidence that the mis-attribution was corrected; the *positive* assertion on line 193-194 is.

## Report accuracy

Claims re-derived at audit time. Everything material held; three items are stale or imprecise.

- ✅ *"`check-dispatch-audit.py` (new)"*, *"wired aspect 11 to it"* — true; `SKILL.md:192` names the
  script, `retro_sections.py:56` registers the key, guarded by `test_registered_aspects_render.py:266`.
- ✅ *"13 tests"* — re-measured: 13 collected, 13 passed.
- ✅ *"only **two** phase-5 sites pass `--workflow`; every finalize dispatch site still hand-writes
  Surface A only"* — true **at the time of the run**; superseded at HEAD by #1232 (see Residue).
- ✅ *"`_cmd_effort.py` and the dispatch-line seam untouched — confirmed absent from `git diff
  --name-only`"* — verified: `git show --stat c93431f` lists exactly ten paths, none of them
  `_cmd_effort.py` or `phase-6-finalize/`.
- ⚠️ *"Three imprecise 'LLM aspects' labels in sibling docs — FIXED … Relabelled to 'analytical
  aspects' (count unchanged)"* — the **relabel** is verified at
  `plan-marshall/standards/effort-roles.md:65` and `ref-workflow-architecture/standards/call-graph.md:323`
  and `:462`, all now reading "analytical aspects". The **count** was carried over, not re-derived,
  and does not hold: `plan-retrospective/SKILL.md:180-196` lists 15 aspects and the SKILL's own LLM
  enumeration at `:251` names six. `git log -L 65,65` on `effort-roles.md` shows "eight" arrived with
  `59b716d` (#1035), so the staleness is inherited rather than introduced — but the run asserted the
  count still held and this document originally accepted that. → **G14.** (The accompanying *"No
  further known stale sites"* claim in Residue is separately false — see the residue table and G12.)
- ✅ *"the sibling's `build_time` block and this PR's `artifact_emission` block coexist"* — verified:
  `analyze-logs.py:1667` and `:1678`; `TestBuildTimeFromLedger` at `test_analyze_logs.py:1877` and
  `TestArtifactEmissionPopulation` at `:1760` both present.
- ⚠️ **Stale line citations.** The Reviewer-participation table cites `coderabbit.md:27`,
  `pr-agent.md:55`, `sourcery.md:25`. At HEAD the `author_login` keys sit at `coderabbit.md:36`,
  `pr-agent.md:58`, `sourcery.md:29`. The three login values and `M = 3` are correct; only the line
  anchors drifted. Report-only, harmless. (G9)
- ⚠️ **Overstated in D3.** *"`channel_completeness` publishes `dispatch_line_count` against
  `completion_count` … and downgrades the audit's own `confidence` … when the channel is sparse."*
  True of the three fixtures the run built; false of the finalize-sparse case, which is the case the
  plan's Problem section describes. See G1.
- ⚠️ **Overstated in D4.** *"The bare `artifact_entries == 0` floor is preserved but a WARNING fires
  only for unambiguous partiality (`0 < N < M`) — the exact defect."* The floor is preserved but
  cannot fire for a real plan, so `N == 0` is covered by nothing. See G7.
- ❌ **Omission against the plan's explicit instruction.** `plan.md` § Out of scope says of the
  execute-phase re-entry-marker defect *"Record it rather than absorbing it"*, and of the
  aspect-naming defect *"cross-noted only"*. `report-01.md` records neither anywhere — not in
  Residue, not in Findings. The two excluded defects left the run with no written trace. (G11)
- ⊘ **UNVERIFIABLE:** *"Full `./pw verify`: SUCCESS — 19621 passed, 14 skipped, 0 failed"* and
  *"Per-commit `./pw quality-gate` ran clean (`total_issues: 0`, 36 plugin-doctor rules)"*. The brief
  forbids a full-suite run, and the tree has advanced many commits since; the figures cannot be
  re-derived. Not treated as a pass.
- ⊘ **UNVERIFIABLE:** the CI narrative (check conclusions on `9b4be92` / `da659fc`, the auto-merge
  arming, the mid-flight base advance and the `test_analyze_logs.py` append-conflict resolution).
  These are GitHub-side facts; the *outcome* is corroborated — `c93431f` is a squash merge of #1225
  and both conflicting test classes are present and green in one file.

## Declared residue — current status

| Residue item (from report) | Still open? | Evidence |
|---|---|---|
| "Finalize resolves still don't pass `--workflow`" — Surface B stays empty for finalize | **CLOSED by a later plan** | `7ad4d1b` "fix(finalize): emit dispatch per-spawn and fuse the step-completion marker (plan 180) (#1232)" — `phase-6-finalize/SKILL.md:618` now instructs every dispatched step to pass `--workflow`, `--plan-id` and `--caller plan-marshall:phase-6-finalize`, and `:629` forbids hand-writing the line. Surface B is now populated for finalize, which makes `shape_violation` evaluable — and near-tautological (G10). |
| "Per-task `[ARTIFACT]` emission cannot be made deterministically complete" — a future emitter driving it from the shared task-close path would let N reach M | **STILL OPEN** | `phase-5-execute/SKILL.md:604` and `phase-5-execute/standards/workflow.md:82-113` still specify the emission as a hand-written per-file `manage-logging work` step after `[OUTCOME]`. No shared-seam emitter exists. |
| "Three sibling docs carried 'LLM aspects' labels … fixed in this run (`d38ce99`). No further known stale sites." | **PARTIALLY CLOSED — the "no further sites" half is FALSE, and the three "fixed" sites are still wrong in their count** | The three named sites carry the new adjective. But a repo-wide grep for `LLM aspects` (re-run at adversarial review; three hits, none in `doc/plans/`) also returns `phase-6-finalize/standards/dispatch-inline-split.md:30` — *"its LLM aspects iterate inside one envelope"* — carrying the identical imprecision the run relabelled three times elsewhere (`plan-retrospective/SKILL.md:240` and `:251` are correct: they name the genuinely-LLM aspects 4-7, 9, 14). See G12. And all three relabelled sites still say "eight"/"8" aspects against a 15-row aspect table — see G14. |

## Out-of-scope and collateral

- **Emission seam — respected.** `git show --stat c93431f` touches no `_cmd_effort.py`, no
  `phase-6-finalize/`, no `dispatch-logging.md`. The "two writers for one emitter" the plan warned
  about did not happen.
- **Declared collateral, accepted.** `plan-marshall/standards/effort-roles.md` (1 line) and
  `ref-workflow-architecture/standards/call-graph.md` (2 lines) fall outside the plan's
  `## Expected surface`, but the report declares both under Findings with a rationale (the label
  became imprecise *because of* this change). Correctly disclosed; not a gap.
- **Undeclared collateral:** none found. The ten paths in the squash are: the plan file rename, the
  new report, the two doc relabels, `plan-retrospective/SKILL.md`, `analyze-logs.py`,
  `check-dispatch-audit.py`, `standards/execution-context-dispatch-audit.md`, and the two test files.
- **Nothing the plan forbade was built.** The per-task `[ARTIFACT]` *emitter* was not changed — only
  the consumer — which is what the plan's D4 second route allows.

## Method and coverage

**Checked, with the method:**

- Read `plan.md` and `report-01.md` in full, then `check-dispatch-audit.py` (all 598 lines),
  `analyze-logs.py` §§ `artifact_emission_population` and the findings assembly,
  `standards/execution-context-dispatch-audit.md` in full, `plan-retrospective/SKILL.md` §§ aspect
  table / capture pattern / canonical invocations, plus the two upstream emitters
  (`_cmd_effort.py::_emit_dispatch_records`, `_cmd_mark_step.py::_emit_completion_marker`) to settle
  what each surface actually guarantees.
- Ran `test_check_dispatch_audit.py` (13/13 green) and, under two mutations, twice more.
- Ran the shipped detector directly against two hand-built plan fixtures (a cross-phase one and a
  log-less one) to observe real output rather than infer it.
- Ran a temporary probe test against `analyze-logs.py` to settle the `N == 0` behaviour empirically.
  The probe file was deleted; `git status --porcelain` afterwards showed no trace of it, and the
  mutated detector was restored from a byte snapshot (`md5 c66b54c9a44ed44e6ec90678f448f0c4`
  matching before and after), never with `git checkout`/`restore`/`stash`.
- Re-derived every count stated here at the moment of stating it (13 tests; 3 residue items; 10 paths
  in the squash; 3 reviewer logins).
- Confirmed grep negatives against a known positive before believing them (e.g. the
  `dispatch_coverage_violation` sweep returns the two live mentions in test and standard, so the
  absence of a producer is a real absence, not a filtered search).

**Not checked, and why:**

- `./pw verify` / `./pw quality-gate` totals — explicitly out of the brief's scope and no longer
  re-derivable at this HEAD.
- GitHub-side facts (check conclusions, review-comment surfaces, auto-merge state, the mid-flight
  base advance). No repository-side artefact records them.
- Whether the detector has ever been run against a real archived plan (`--mode archived`). No
  archived-plan corpus is present in this clone (`.plan/` is git-ignored and absent), so the archived
  path is exercised only by argument parsing, not by any fixture. *(Adversarial addendum: `--mode
  archived` was subsequently exercised end-to-end against a hand-built archived fixture while
  re-deriving G7, so the archived path is no longer untried — only untried against a real corpus.)*

## Adversarial review

Independent review of this document and `gaps.md`. Attacks run: A1 false positives, A2 false
negatives, A3 vacuous evidence, A4 counts and quotes, A5 actionability, A6 severity/topic,
A7 coverage, A8 internal consistency.

| # | Attack | What was found | Correction applied |
|---|---|---|---|
| A1 | False positives | **None.** Every gap's `path:line` was opened and every claim re-derived at `a90adeb`. G1 and G3 reproduced with byte-identical output by running the shipped script against a rebuilt cross-phase fixture (`dispatch_line_count: 6, completion_count: 3, dispatched_step_count: 3, ratio: 2.0, confidence: nominal` alongside `missing_dispatch_emission: 3`). G2, G4 and G5 reproduced against a log-less plan directory. G6 reproduced by mutation. G7 re-derived against a **pristine** copy of `analyze-logs.py` taken from `git show HEAD:…` (a concurrent agent had the in-tree file mutated at `:1538` while I measured — the pristine copy is why the reading is trustworthy). G9's three registry line numbers re-checked (36/58/29 vs the report's 27/55/25). G11 confirmed by grepping the report for both excluded defects (zero hits). G12's repo-wide `LLM aspects` sweep re-run: three hits, exactly as claimed. | Two citations re-anchored: G3's risk note cited `compile-report.py:235-250` for a function that begins at `:213` → now `:213-250`; G14's aspect-table citation set to `SKILL.md:180-196` (the header row is 180, not 181). |
| A2 | False negatives | **One, and it is the most consequential finding in this review.** D2's discriminator does not discriminate. `evaluate_dispatch_coverage` (`:380-386`) calls a step `no_evidence` only when it has no `execution_log` row at all; *everything else that is not a positive integer* falls through to `ran_inline`, which `:366-369` and the shipped standard `:62` both present as **proof** the step ran inline. Three distinct inputs collapse there: a genuine measured zero; a dispatched step whose `<usage>` tag never arrived (the producer says so verbatim — `manage-execution-manifest.py:2613-2614`); and a row with no `total_tokens` column, which the detector's own fail-open `else: value = 0` (`:278-279`) converts into a "measured zero" before the classifier sees it. Because `dispatched` under-counts, `missing_dispatch_emission` — D2's headline finding, computed as `max(0, len(dispatched) − finalize_dispatch_line_count)` — cannot fire for exactly the class of step whose instrumentation failed, and `dispatched_step_count` carries the same under-count into D3's `low` branch. Reproduced with two fixtures: `{outcome: error, total_tokens: 0}` and no dispatch line → `ran_inline: 1, missing_dispatch_emission: 0`; the same row with the column **absent** → identical. Separately, D1's *Done when* clause *"never a bare `0`"* is violated by the shipped `counts.by_category` block, which the original document recorded as a residual legibility issue rather than a shortfall against the deliverable. | **G13 added (high).** D2's verdict corrected: still CONFIRMED against the literal *Done when*, but the accepted mechanism deviation is **not** outcome-equivalent, and that is now stated. D1's verdict changed CONFIRMED → **PARTIAL**; G3 raised medium → **high**. Overall verdict changed CONFIRMED WITH GAPS → **PARTIAL**. |
| A3 | Vacuous evidence | Both mutation sweeps this document claims were **re-run from scratch, not trusted**. `if population == 0:` → `if False:` at `:318` → `2 failed, 11 passed` (`test_shape_violation_not_evaluated_when_surface_b_empty`, `test_absent_inputs_degrade_cleanly`) — matches. `:441` → `elif False and …` → `13 passed` — matches, G6 stands. A third mutation was added: `else: value = 0` → `value = 999999` at `:278-279` → `13 passed`, proving the coercion branch behind G13 is dead to the suite. One weak assertion the document already flags (`:196`, `'dispatch_coverage_violation' not in _categories`) re-confirmed structurally satisfied. Every mutation was snapshot-restored from `$TMPDIR/adv-170-mutsweep/check-dispatch-audit.py.orig`; md5 `c66b54c9a44ed44e6ec90678f448f0c4` before and after each, `git status --porcelain` clean for the file. No `git checkout`/`restore`/`stash` was used. | Test-adequacy table extended with the coercion-branch result; correctness item 10 added. |
| A4 | Counts and quotes | **One quote defect, and it is load-bearing.** The D2 section attributed to `phase-6-finalize/SKILL.md:1151` the words *"(with zero token attribution for inline steps)"*. `:1151` is blank — the text is at `:1153` — and the source actually reads *"for inline steps **that carry no `<usage>` tag**"*. The six dropped words are precisely what makes a zero ambiguous, so the truncation is what let the D2 premise pass. Separately, the report's *"count unchanged"* claim about the relabelled docs was accepted with a ✅ without the count being re-derived; it does not hold (15 aspects in the table, six in the SKILL's LLM enumeration, "eight" in the docs). Counts re-derived independently and all held: 13 tests collected/passed; 10 paths in `git show --stat c93431f`; exactly 3 `dispatch_coverage_violation` hits; exactly 3 `LLM aspects` hits; 3 reviewer logins at lines 36/58/29. | Quote corrected in place with the right line and the full clause, and the one-directional nature of the premise spelled out. The relabel bullet re-graded ✅ → ⚠️. **G14 added (low).** |
| A5 | Actionability | One entry failed: G10's action ended *"Consider re-labelling the block `seam_write_consistency`"* — a suggestion, not a change, with no observable outcome. Every other entry names a concrete path, a concrete change and a checkable *Done when*. | G10's action rewritten to a single concrete edit (name the shared emitter in the `:122` rule and cross-reference `:40`) with a *Done when* a reader can check. |
| A6 | Severity and topic | Four mis-gradings. G3 was medium but violates D1's *Done when* verbatim and defeats the in-tree ambiguity probe (`compile-report.py::_names_checked_set` accepts a non-empty `counts` dict as attribution, because `counts` is in `ZERO_ATTRIBUTION_FIELDS` — so the log-less fragment passes the "names what it checked" test on the strength of the block that names nothing) → **high**. G7 was medium but the floor it names is *provably dead*, which the calibration puts under "a guard cannot fire" → **high**. G10 was medium on the premise that the corroboration limit was undisclosed; it is disclosed, prominently, at `:40`, so the gap reduces to a missing cross-reference → **low**. G7's topic `measurement/metrics` and G11's topic `plan-lane-contract` both pointed away from the owning surface — G7's fix is in `analyze-logs.py` alongside G1-G5, and G11's fix edits `report-01.md` alongside G9 → **detectors/auditor** and **documentation-surface**. | All four re-graded/re-topiced, each with the reason recorded in the entry. |
| A7 | Coverage | **Complete.** All five deliverables have a verdict row and a detail section; out-of-scope compliance, undeclared collateral, report accuracy and the three declared residue items are each covered. No deliverable is silently unmentioned. The document is also honest about what it did not check (build totals, GitHub-side facts, archived-corpus runs). | None needed beyond the archived-mode addendum noted above. |
| A8 | Internal consistency | The overall verdict did **not** follow from the rows: the summary asserted *"each satisfies its literal Done when"* while the table graded D3 PARTIAL, and D1's own detail conceded a bare `0` in the shipped output while the row said CONFIRMED. Gap↔finding tracing is otherwise sound in both directions: all twelve original gaps trace to a numbered correctness defect, a report-accuracy bullet, a test-adequacy row or a residue row, and every finding warranting action appears in `gaps.md`. | Summary rewritten to state per-deliverable outcomes; D1 → PARTIAL; overall verdict → PARTIAL. The two new gaps are traced from the D2 detail (G13) and the report-accuracy bullet (G14). |

**Residual doubt:** the most likely next finding is on the same axis as G13 — the *other* direction of
the token discriminator. This review proved that zero does not imply inline; it did **not** prove
that non-zero implies dispatched. If any inline finalize step can ever record a non-zero
`total_tokens` (a hand-passed value, a mis-attributed re-entry, or a future change that starts
costing inline steps), then `dispatched` over-counts and `missing_dispatch_emission` becomes a false
positive against the dispatcher — the mirror of the defect the plan was written to kill. Settling it
needs the producer-side call sites for inline steps enumerated and checked, which is a wider sweep
than this review's scope. A second, smaller residue: `evaluate_shape_violation` compares
per-role *counts*, not pairs, so a hand-written `[DISPATCH]` line can cancel a genuinely unmatched
resolve of the same role — and hand-written lines still exist at HEAD
(`plan-marshall/workflow/planning-outline.md:112`, `:146`, `:431`, `:484`, `planning.md:286`, `:326`,
`workflow-pr-doctor/SKILL.md:38`, all resolving without `--workflow` and then logging by hand). That
is the D1-side analogue of G8 and was left unfiled because at HEAD the roles involved do not overlap
with any seam-emitting role; a later change to those workflows would make it live.

**Verdict on the audit:** SOUND AFTER CORRECTION — every gap it filed is real and reproducible and
its method was honest, but it accepted a truncated quote as proof of D2's central premise, and that
one omission hid the highest-severity defect in the shipped change.
