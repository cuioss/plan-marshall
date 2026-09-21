# PLAN-10: Dead Aspects + Never-Emitted Markers

<!-- Title widened 2026-07-28: the two operator folds make this a "documented-signal-that-does-not-fire"
     plan rather than a narrow retrospective-completeness one. 4 deliverables — split-guard clear. -->


epic: test-suite-quality
workstream: WS-03

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> See `persona-marshall-orchestrator/standards/orchestration-model.md` for the hand-off contract.

## Objective

Close four defects that share one archetype: **a signal the system documents but does not actually
produce.** Two aspects that cannot register (so their findings never reach the report), two markers that
never fire (so their counters read low and their silence is mistaken for health), and one count that
drifted after its enumeration grew. In every case the artifact asserting the signal exists is present and
correct-looking; only the emission is missing.

D1–D2 are the residues PLAN-09 (#998) uncovered — the reason its two trimmed lessons stayed active.
D3–D4 were folded in by operator decision 2026-07-28 from PLAN-08's (#1026) retrospective and its
untriaged bot finding. Staging these rather than carrying them as watches is the operator's explicit
choice (AskUserQuestion 2026-07-25 and 2026-07-28) — the same "don't let verified defects evaporate"
discipline that drove the epic reopen.

**Every set-guarding detector in this plan MUST be population-derived**, never a pinned list of today's
members. That is the epic's most-recurrent defect archetype (four occurrences, the most recent inside
PLAN-08's own regression test, which parsed a roster and then discarded it while staying green over a real
hole). D1's two missing keys, D3's 17 steps, and D4's sibling sites are all populations — derive each from
its governing source at test time.

## ✅ PREP BLOCKER CLEARED — D1 re-grounded against the implementing source (2026-07-28)

The blocker is discharged. `2026-06-20-17-003` remains **`not_found`** (re-confirmed 2026-07-28), so
the *binding* stays refuted and there is **nothing to retire for D1**. But the underlying defect is
**REAL and LIVE**, verified at source rather than inferred — a lesson's absence never was evidence its
defect was fixed.

**Claim label: `OBSERVED`.** Confirming artifacts, file plus symbol:

- `plan-retrospective/scripts/retro_sections.py:26` — `SECTION_SPEC` carries 16 rows; **neither
  `direct-gh-glab-usage` nor `execution-context-dispatch-audit` appears in it.**
- `retro_sections.py:80` — `valid_aspect_keys()` derives the registerable set **from `SECTION_SPEC`**.
- `collect-fragments.py:280` — `_registerable_aspect_keys()` = `valid_aspect_keys() | _domain_aspect_keys()`,
  and `cmd_add` rejects any `--aspect` outside that union. Neither aspect is domain-contributed (both are
  core plan-marshall aspects), so **`collect-fragments add --aspect direct-gh-glab-usage` is rejected
  outright.**
- Both aspects have live producers that instruct exactly that call:
  `scripts/direct-gh-glab-usage.py:229` emits `'aspect': 'direct-gh-glab-usage'`;
  `references/direct-gh-glab-usage.md:87` and `standards/execution-context-dispatch-audit.md:122`
  both document the `collect-fragments add --aspect {name}` registration step.
- `plan-retrospective/SKILL.md:152-153` registers both as aspects 10 and 11.

**⚠ The inherited mechanism framing is CORRECTED — do not carry it forward.** PLAN-09's residue note
described this as *"the completeness guard scans only `SKILL.md`"*; that was an inference, and it is not
what the source shows. The actual mechanism is narrower and more precise: **`SECTION_SPEC` is the single
source from which registerable aspect keys are derived, and two core aspects are missing from it.** The
consequence is also sharper than "the section renders empty" — registration **hard-fails**, so the aspect
does its work and then cannot land its fragment at all. Scope D1 to the observed mechanism, not to a
guard-scanning generalization that may not exist.

**⭐ Recorded because it sharpens the archetype:** the `routing-decisions` row's own inline comment in
`SECTION_SPEC` cites *"lesson 2026-06-20-17-003: a producer without this render row ships the aspect
dead"* — the registry documents this exact defect class **inline, in the same tuple**, and then commits
it twice more. A doc-comment naming a defect class is not a guard against it.

`2026-07-17-11-001` (D2) re-verified 2026-07-28: **present and active**, four confirmed occurrences,
remediation unchanged. D2's binding is sound and D2 retires it on landing.

## Verified-cause inputs

| Residue | Cause (from PLAN-09) | Lesson |
|---------|----------------------|--------|
| Two core aspects are absent from `SECTION_SPEC` | `OBSERVED` 2026-07-28 at source: `SECTION_SPEC` (`retro_sections.py:26`) is the single source `valid_aspect_keys()` derives from (`:80`), and `cmd_add` rejects any aspect outside `_registerable_aspect_keys()` (`collect-fragments.py:280`). `direct-gh-glab-usage` and `execution-context-dispatch-audit` are missing from `SECTION_SPEC` and are not domain-contributed, so **their registration hard-fails** — both ship dead despite live producers and documented registration steps. Same `SECTION_SPEC`-missing defect a 2nd and 3rd time | **NO BINDING** — `2026-06-20-17-003` is `not_found`; nothing to retire for D1 |
| `starting_markers` structurally always 0 | `phase-5-execute` never emits its documented "Starting execute phase" marker line, so the retrospective's `starting_markers` count is 0 by construction — the `analyze-logs` consumer was correct once PLAN-09 fixed its own overcount; the residual defect is the missing **producer** emission | `2026-07-17-11-001` (trimmed + reassigned to phase-5-execute by PLAN-09) |

## Deliverables

1. **Register the two missing `SECTION_SPEC` keys, and make the registry/producer gap detectable.**
   Add rows for `direct-gh-glab-usage` and `execution-context-dispatch-audit` to `SECTION_SPEC`
   (`retro_sections.py:26`) at their SKILL.md aspect positions (10 and 11), so registration stops
   hard-failing and their findings reach the report. Then close the class, not just the two instances:
   add a regression test that **derives the expected aspect population from the producers** — the
   documented `collect-fragments add --aspect {name}` registration sites and/or the SKILL.md aspect
   table — and fails when any producer's aspect has no registerable key. ⚠ **The detector MUST be
   population-derived, never a hardcoded two-key list**: a pinned list is the vacuous-guard archetype
   this epic has now hit four times, most recently inside PLAN-08's own regression test. PLAN-08's
   `test/_shared/_dispatch_roster.py` is the shape to copy — it enumerates the roster from the governing
   doc at test time. Confirm the seam at outline; `#998` and `#1009` both changed this area.
2. **Emit the phase-5 "Starting execute phase" marker line.** Make `phase-5-execute` actually emit the
   documented marker so `starting_markers` is a real signal, not a structural 0. Add a test asserting
   the line is emitted. Verify at outline that the marker's documented text and the
   retrospective's expected pattern agree (a producer/consumer contract — fix both ends if they drift).

3. **Make the finalize `[STEP] Completed step:` emission fire for every step.** Folded in by operator
   decision 2026-07-28 from PLAN-08's retrospective — D2 and D3 are the same archetype (a documented
   marker that does not fire, so its counter is structurally wrong), which is why they belong in one plan.

   - `OBSERVED` — there is exactly **ONE** emission site: `phase-6-finalize/SKILL.md:1089`, numbered
     item **7 "Log step completion"** inside the per-step loop. Being in the loop, it should fire once
     per step; PLAN-08's retrospective observed it firing for **2 of 17** steps.
   - `HYPOTHESIS` (verify at outline; confirm/refute artifact = `phase-6-finalize/SKILL.md` item 7 vs the
     three sites PLAN-08 fixed) — **the cause is the same shape D1 just fixed.** PLAN-08 closed the
     `[DISPATCH]` gap by fusing the emit to the spawn as "ONE indivisible pair" at three sites; item 7 is
     a *standalone numbered instruction after* the step returns — precisely the unfused shape that got
     skipped for `[DISPATCH]`. If this holds, the fix is the same pairing language plus a detector, and
     PLAN-08's `test/_shared/_dispatch_roster.py` is again the shape to copy.
   - ⚠ **The counter is UNDER-reporting, so its silence is not evidence of health** — the same polarity
     trap as `starting_markers: 0` in D2. Do not treat a low `[STEP]` count as "few steps ran".

4. **Fix the stale corollary count in `agents.md`.** Folded in by operator decision 2026-07-28. `OBSERVED`
   2026-07-28: `agents.md:162` enumerates **four** corollaries of the leaf/dispatch-topology invariant
   (cannot spawn a subagent, cannot reach the operator, must record its terminal outcome before composing
   its return, cannot reap a backgrounded build), while **`:131` and `:174` both still say "the other
   **two** leaf-cannot-do-it cases"**. Adopt CodeRabbit's own suggested remedy — a **count-free**
   phrasing ("the other leaf-cannot-do-it cases") so no site carries a count that can drift again.

   This is a bot finding from #1026 that **escaped triage because the review posted 58 s after the merge
   commit**; folding it here returns it to the pipeline. Check whether PLAN-08's lock-step tests (which
   pin the ordinal/enumeration sentence) should extend to cover these sibling sites — a count pinned at
   one site and free at two others is how this drifted.

## Lessons consumed — retire from the global store on landing

**D1 has NO lesson to retire.** `2026-06-20-17-003` is `not_found` in the store (re-confirmed
2026-07-28) — the binding is refuted, the defect is not. Do not attempt to retire it; do not treat its
absence as evidence D1's work is unnecessary.

| Lesson | Resolved by | Retire? |
|--------|-------------|---------|
| ~~`2026-06-20-17-003`~~ | — | **NO — already absent from the store; nothing to retire** |
| `2026-07-17-11-001` | D2 | yes — verified present + active 2026-07-28; verify no surviving member at finalize, else trim rather than falsely retire |

**Verify retirement against the LIVE store, not against the housekeeping report.** That control is
4-for-4 in WS-03 at catching false retirements (PLAN-09 trimmed 2, PLAN-07 adapted 1, PLAN-08 retired 4
correctly) and is bound into this plan too.

## Expected Surface

Widened 2026-07-28 by the two folds. `OBSERVED` — every path below was read at source:

- `plan-retrospective` — `scripts/retro_sections.py` (`SECTION_SPEC`, `valid_aspect_keys`) and
  `scripts/collect-fragments.py` (`_registerable_aspect_keys`, `cmd_add`) (D1).
- `phase-5-execute` — the marker-emission point + its documented marker text (D2).
- `phase-6-finalize/SKILL.md` — item 7 at `:1089`, the single `[STEP] Completed step:` emission site (D3).
- `ref-workflow-architecture/standards/agents.md` — `:131` and `:174` only (D4).
- Regression tests for all four, each **population-derived** where it guards a set.
- **OFF-LIMITS**: the five checks PLAN-09 already fixed; PLAN-07's surfaces; and everything PLAN-08
  landed in `phase-6-finalize` beyond item 7 and the two `agents.md` lines named above — in particular do
  NOT re-touch D1's three `[DISPATCH]` emit sites, D3's record-before-return reach-points, or D4's
  whole-tree `quality-gate` arm. This plan extends PLAN-08's work at two named points; it does not revisit it.

## Dependencies and Sequencing

- Depends on: PLAN-09 (shipped) — rebase D1 on its rewritten `plan-retrospective` shape.
- Depends on: **PLAN-08 (shipped #1026)** — D3 and D4 both extend surfaces #1026 changed. Rebase on the
  merged shape at `f14cb2d07`; D3 in particular should copy the emit/spawn pairing language and the
  `test/_shared/_dispatch_roster.py` population-derived detector shape rather than inventing new ones.
- No plan is in flight (the epic is at `R = 0` of `N = 1`), so no disjointness constraint binds.
- **This is the epic's last plan** — on its landing the epic re-closes (rewriting `history.md`, superseding
  the 2026-07-24 close).

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/test-suite-quality/plans/PLAN-10-retrospective-completeness-and-phase5-marker.md"
```

## Status Trail

- plan_marshall_plan_id: {set at launch}
- pr: {set when the PR opens}
- landing: {set when the landing analysis is recorded at landings/PLAN-10.md}
