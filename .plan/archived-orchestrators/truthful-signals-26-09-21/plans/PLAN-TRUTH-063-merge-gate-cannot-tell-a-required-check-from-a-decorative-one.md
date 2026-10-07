# PLAN-TRUTH-063: The Merge Gate Cannot Tell a Required Check From a Decorative One

epic: truthful-signals
workstream: WS-01

> Staged plan spec — the SOURCE RECORD, authored BEFORE its cloud plan per
> `doc/plans/cloud-bridge.md` § Path 1. Derived cloud plan:
> `doc/plans/truthful-signals/030-merge-gate-cannot-tell-a-required-check-from-a-decorative-one.md`.

## Objective

Teach `cloud-plan-lane`'s merge gate to distinguish a **required** status check from a non-required
one, derived from the repository ruleset rather than asserted. Today the contract says "all checks are
green" with no notion of required-ness, so a run stalls on any pending decorative check — observed
twice on `license/cla`. Ship the general rule; record the CLA's root cause as an operator proposal
rather than fixing it inline.

## ⛔ Framing correction, made at staging

The operator's instruction was *"license CLA is not a hard gate — implement this accordingly in the
skill."* Writing that sentence into the contract is **refused as specified**, and the reason is this
epic's own subject:

- It hardcodes a **repo-specific, time-varying** fact. If `license/cla` is ever added to the ruleset,
  the contract would instruct the run to ignore a genuine blocker — a suppressed caveat inside the
  document whose job is to prevent suppressed caveats.
- It is an **assertion where a derivation is available**. The ruleset is machine-readable; required-ness
  can be read rather than believed. Per `author-cloud-plan` rule 3, a premise the scope rests on gets a
  gating derivation that HALTS, never an asserted fallback.
- The observation is nonetheless **correct and load-bearing** — it is the evidence that motivates the
  general rule, and it is recorded as such (twice observed, `mergeable_state: unstable`, both landed).

The general form delivers what the operator wants (runs stop stalling on the CLA) without the trap.

## Deliverables

1. **D0 — GATE: derive the required-check set from the ruleset.** Establish, from the GitHub ruleset /
   branch-protection API, which contexts are actually required on `main`, and confirm `license/cla` is
   not among them. ⛔ **If the required set cannot be derived programmatically, HALT** and report that —
   do NOT fall back to a hand-maintained list of required checks, which would be the same
   hand-maintenance defect `PLAN-TRUTH-061`'s D0 refused.
2. **D1 — Merge-gate condition 1 reads required-ness rather than greenness.** Reword `cloud-plan-lane`
   § Step 8 condition 1: the gate is satisfied when **every required context** is present on the exact
   head SHA and concluded successfully; a **non-required** check that is pending, failed, or absent
   does not block, and is **disclosed** rather than ignored.
3. **D2 — Record the CLA root cause as an operator proposal, not a fix.** The pending CLA is caused by
   cloud runs **authoring** commits as `Claude <noreply@anthropic.com>` where the convention is a
   `Co-Authored-By:` trailer. Record it in § What have we learned for an operator decision; do not
   change authorship in this run.

## Claim Labels

- OBSERVED: `cloud-plan-lane` § Step 8 condition 1 says "All checks are green" and carries no notion
  of required-ness — read 2026-08-08.
- OBSERVED: `license/cla` was pending on PR #1112 and PR #1117; both showed `mergeable_state: unstable`
  (not `blocked`) and **both were admitted and landed by the merge queue**. Two instances.
- OBSERVED: the CLA is pending because the cloud run authors commits as `Claude <noreply@anthropic.com>`
  — recorded in both runs' reports.
- HYPOTHESIS: the required-context set is readable from the ruleset/branch-protection API by the cloud
  run's GitHub access path — confirm/refute at D0, which HALTS on failure.
- HYPOTHESIS: no *other* non-required check has silently stalled a run (i.e. the CLA is the only
  instance of this class so far) — confirm/refute by re-reading both runs' check sets; a second
  instance strengthens D1's wording, it does not change it.

## Expected Surface

- OBSERVED: `.claude/skills/cloud-plan-lane/SKILL.md` § Step 8 (and the § Report contract-check row if
  it restates the condition).
- ⛔ NOT `doc/plans/cloud-bridge.md` — the merge gate is execution, not bridge lifecycle.

**Disjointness:** one skill file. Disjoint from `044` (`manage-lessons`/`manage-status`), `060`
(`manage-build-server`), `042` (`pm-dev-java`), `011` (`manage-logging`/`manage-providers`), and from
emitted `056`/`057`/`058`.

## Dependencies and Sequencing

- Depends on: none. ⚠ Touches the same file as `PLAN-TRUTH-061` (shipped #1112) — sequential, not
  concurrent.
- Adjacent to: `061`'s three open contract proposals, which touch Step 7/8/9 and are **operator-pending**.
  This plan touches Step 8 condition 1 only and must not silently resolve any of them.

## Hand-Off Command

```text
Execute doc/plans/truthful-signals/030-merge-gate-cannot-tell-a-required-check-from-a-decorative-one.md
```

## Write-Boundary

The cloud run writes only its own `doc/plans/truthful-signals/030-…/` directory and the skill file its
deliverables name. It creates and edits NO file under `.plan/local/orchestrator/`.
