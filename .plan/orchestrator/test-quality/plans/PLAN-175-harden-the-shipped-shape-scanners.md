# PLAN-175 — Harden the shipped shape scanners

workstream: WS-03
status: staged
source: PLAN-160's landing (#1486, 2026-09-14) — candidate-lessons -008, -009, -010

## Objective

PLAN-160 shipped the epic's first **mechanical** checks: `test/_shared/_test_shape_scan.py`
and the guards over it in `test/test_harness_shape_guards.py`. Those checks exist to stop a
guard from passing after it has stopped guarding — this epic's whole thesis.

**The checks have that defect inside them.** Review on #1486 filed at least ten findings
against the scanners, and they collapse into three families, every one of which makes a
scanner report clean over a population it never really evaluated:

1. **Recognizers enumerated from examples rather than from the construct** (5 findings) —
   each detector was written against the *canonical* spelling, so every grammatically
   equivalent spelling fell through. Two of the five are literally the same gap found twice,
   three days apart, because the first fix enumerated one more spelling instead of
   enumerating the construct.
2. **Guards credited with a property their predicate does not entail** (4 findings) — or
   entails about the *wrong subject*. `all(...)` over an empty mapping is `True`;
   `assert len(x) >= 0` proves nothing about cardinality; a whole-file containment check is
   satisfied by any unrelated line in the module. In one case the comment directly above the
   predicate names it a vacuity guard — **the vacuity guard is itself vacuous**.
3. **Asymmetric normalization in a path comparison** (1 finding) — one side resolved, the
   other not, so a same-directory exemption became unreachable and the detector silently
   over-reported.

⛔ **The through-line is that every one was found by a review bot, not by the author or by
the guards' own tests.** A scanner nobody can falsify is not a check; it is a claim. This
plan makes the scanners falsifiable and then fixes what that reveals.

⚠️ **This is not a re-litigation of PLAN-160.** Its sweeps and their verdicts stand. What is
in scope is the instrument it built, which is now load-bearing for every future sweep.

## Deliverables

1. **D1 — Give every detector a matched negative control over equivalent spellings.**
   For each detector in `_test_shape_scan.py`, enumerate the *construct* rather than a
   spelling: for each shape, write a control carrying at least one grammatically equivalent
   form the current detector misses (the `else`-arm restore, the `try/finally` yield, the
   `with ...: yield`, the `{**unpacking}` dict, the `!= 0` length comparison), and watch each
   control go red before the fix.
   ⛔ **Do not fix by adding one more spelling to an enumeration.** That is the authoring
   method that produced the defect; two of the five findings are the same gap re-opened by
   exactly that move. Where the construct admits an open set of spellings, match on the
   semantic node rather than on the surface form, or state explicitly that the detector is
   bounded and name what it does not see.
   *Done when:* every detector has a matched positive and negative control, each negative
   control is **observed failing** against the pre-fix detector, and any residual bounded
   coverage is named in the detector's own docstring.

2. **D2 — Re-express every guard whose predicate does not entail its claim.**
   For each of the four sites, either strengthen the predicate to entail the stated property
   or rename the guard to claim only what it proves. Attach each proof to the **right
   subject**: the returned population, not every name mentioned in a return expression; this
   control's tokens, not the whole file's.
   ⛔ **Assertion syntax is not proof of cardinality.** A scanner that accepts
   `assert len(cases) >= 0` as a non-vacuity proof has the defect it is scanning for.
   *Done when:* each of the four sites carries a predicate that entails its name, and a
   control demonstrates the pre-fix predicate passing in the scenario the guard exists for.

3. **D3 — Normalize both sides of every path comparison.**
   Fix the resolved-vs-unresolved comparison, and sweep the scanners for any other equality
   or containment test over paths where the two sides are produced differently.
   *Done when:* the same-directory exemption is demonstrated reachable under both relative
   and absolute caller paths, with a control that fails against the pre-fix code.

4. **D4 — Report the population each scanner actually evaluates.**
   Every scanner reports the count it scanned AND the count it could not classify, so a clean
   result states which zero it is.
   ⚠️ **This is the deliverable that prevents the next recurrence**, because it makes an
   unevaluated population visible without anyone having to suspect it.
   *Done when:* each scanner's output carries its scanned and unclassifiable populations, and
   the report names the before/after finding counts per detector with the command that
   produced them.

## Claim Labels

- OBSERVED: the ten-plus review findings and their sites, quoted from PLAN-160's landing
  candidate-lessons -008, -009 and -010, which tabulate each finding id against its site.
- OBSERVED: `test/_shared/_test_shape_scan.py` and `test/test_harness_shape_guards.py` exist
  at HEAD and were introduced by #1486 (merge `f21a0dc66`).
  - verdict: corroborated | checked_at: fb8aadc9c | by: test-quality/cleanup | rescoped: n/a | evidence: verified at HEAD fb8aadc9c: test/_shared/_test_shape_scan.py and test/test_harness_shape_guards.py are both present, and both were introduced by #1486 (merge f21a0dc66) per git show --stat. Additionally re-derived this pass: _test_shape_scan.py is 636 lines and is itself flagged by test-module-line-budget as over the 400-line budget by 236 - the instrument this plan hardens is also in PLAN-140's population, which is a sequencing fact both specs should carry.
- HYPOTHESIS: the three families are exhaustive over the review findings — confirm/refute at
  `test/_shared/_test_shape_scan.py` by re-reading every review thread on PR #1486 against the
  detector list (verify-at-outline).
- HYPOTHESIS: no detector outside the named sites carries the same defect — confirm/refute at
  `test/_shared/_test_shape_scan.py` § each detector function (verify-at-outline). ⛔ This is
  an ABSENCE claim and is the higher-risk half: an unverified absence ships a scanner that is
  still unfalsifiable.

## Expected Surface

- OBSERVED: `test/_shared/_test_shape_scan.py` — the scanners themselves, D1-D4
- OBSERVED: `test/test_harness_shape_guards.py` — the guards and their controls
- OBSERVED: `test/plan-marshall/phase-6-finalize/test_branch_cleanup_merge_queue_routing.py` — the vacuous vacuity guard, D2
- OBSERVED: `test/plan-marshall/manage-tasks/test_freshness_exempt_vs_verified_discrimination.py` — the whole-file containment control, D2

## Dependencies and Sequencing

- Depends on: PLAN-160 (shipped, #1486) — this plan hardens what that one built.
- Overlaps with: **PLAN-140** at `test/plan-marshall/**` if that plan's derived surface
  resolves over these directories. ⛔ Not concurrent with PLAN-140 until PLAN-140's surface is
  derived and checked.
- Adjacent to: the `test-conventions` rule set, which this plan does NOT edit.

## Out of Scope

- Re-running or re-litigating PLAN-160's four sweeps or their decline-on-merits verdicts.
- New defect classes. This plan hardens the instrument; it does not widen what the instrument
  looks for.
- The `empty_parameter_set_mark` adoption PLAN-160 shipped, which stands.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/test-quality/plans/PLAN-175-harden-the-shipped-shape-scanners.md"
```

## Write-Boundary

The plan touches only its own repository source and tests. It creates and edits NO file under
`.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message.
