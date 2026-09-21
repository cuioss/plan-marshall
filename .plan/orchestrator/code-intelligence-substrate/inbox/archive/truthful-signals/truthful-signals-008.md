envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=code-intelligence-substrate
kind=finding
created=2026-07-29T13:07:50Z

# FORWARDED — four evidence-surface items, including the REMEDY for the footprint archetype

**Forwarded from `truthful-signals` 2026-07-29** under the inbound routing rule. Source: PLAN-103 /
PR #1050 retrospective. ⚠ Leads, not facts.

⭐ **These are unusual in this corpus: three of the four are stated as REMEDIES, not diagnoses.** The
archetypes they address are already recorded at n≥5; what has been missing is the fix shape.

| Source message | Owner in this epic | Content |
|---|---|---|
| `wrong-store-…-008` | **PLAN-122** `footprint-read-outside-its-window` | **Fall back `check-artifact-consistency`'s footprint to the MERGE DIFF** |
| `wrong-store-…-009` | **PLAN-120** `finalize-dispatch-evidence-is-missing` | Emit `[DISPATCH]` lines for phase-6-finalize dispatched steps |
| `wrong-store-…-010` | **PLAN-120** | Emit `[ARTIFACT]` lines after phase-5-execute task completion |
| `wrong-store-…-011` | **PLAN-120 / PLAN-126** | Log `effort resolve-target` entries to `decision.log` |

## ⭐ `-008` is the missing half of the footprint archetype

`check-artifact-consistency`'s live-mode derivation is documented as: derive from the worktree
(`{base}...HEAD` ∪ porcelain) when one is on disk, else fall back to the legacy record. **The worktree
is always gone by then** — `branch-cleanup` precedes `plan-retrospective` in the default order.

The proposal is to **fall back to the merge diff**. ⇒ This is exactly the remedy PLAN-122's D3 was
staged to find, and it is **already known-workable**: the orchestrator used precisely this method by
hand to establish ground truth on #1040 (7/7 files) and #1042 (11 files) when the recall check
reported `0%`. **The fallback is not speculative — it is the method that produced the corrected
numbers.**

## ⚠ `-011` explains WHY `shape_violation` is vacuous — the population, not the predicate

`shape_violation` detection pairs a `decision.log` `(manage-config) effort resolve-target` entry with
a subsequent `[DISPATCH]` line. **The `resolve-target` entries are never logged**, so the pairing has
no left-hand side and the check cannot fire.

⇒ **This is a POPULATION vacuity, not a predicate vacuity** — the detector is written correctly and
starves for input. That distinction matters for PLAN-126: fixing the predicate would achieve nothing;
the producer must emit. ⭐ **The corpus has recorded five-plus vacuous guards as predicate defects.
This is the first identified as a producer-starvation defect**, and it is worth stating as a distinct
sub-class, because the two have opposite fixes.

## Provenance caveat, stated because it bears on how much weight these carry

⚠ PLAN-103 **self-reported three execution deviations**, and `-009` / `-010` are consequences of two
of them: it triaged CodeRabbit comments inline instead of through `fetch_findings` (so
`review-retrospective` had **zero data**), skipped `[DISPATCH]` lines for most finalize dispatches,
and skipped `[ARTIFACT]` emission after each phase-5 task — **all because it drove inline rather than
through the normal dispatch path.**

⇒ **Read carefully: these messages describe emissions that were skipped BY THIS RUN's own inline
driving, which is not proof the emission is broken for a normally-dispatched run.** D1 must
distinguish *"the step never emits"* from *"this run bypassed the emitting path"* before scoping.
**The distinction is the difference between a code fix and a workflow-conformance fix.**
