envelope_version=1
sender_type=plan
sender_id=daemon-baseline-interpreter-is-unregistrable
epic=truthful-signals
kind=candidate-lesson
created=2026-08-08T21:25:17Z

component=pm-plugin-development:ext-self-review-plan-marshall
category=improvement
confidence=medium
source_aspects=findings-store,request-result-alignment

# Pre-submission self-review passed clean over a docstring-vs-code overclaim in a plan whose whole subject was docstring-vs-code overclaims

## Context

This plan's D2 deliverable was, verbatim, *"correct every doc that calls it registered"* — the `manage-build-server` docs asserted the daemon held a **registered** baseline interpreter while no registry surface existed to register one. The plan is a docs-assert-X / code-does-Y correction, end to end.

Two consecutive finalize steps then ran over the resulting diff:

| Order | Step | Outcome |
|---|---|---|
| 1 | `pre-submission-self-review` | "self-review clean: **7 candidates examined**" (dispatched — `total_candidates=7 > 5` threshold, `cov_scope=inherit`) |
| 2 | `finalize-step-security-audit` | raised `3d1669` — the docstring in the file the plan had just rewritten asserts `command[0]` is never an arbitrary client-supplied binary, which the adjacent basename-only `_interpreter_ok` check does not establish |

Same file, same diff, same archetype the plan existed to fix — surfaced by the security audit, not by the self-review that ran first and reported clean over seven candidates.

The overclaim was **carried through** rather than freshly invented (the finding is explicit: *"pre-existing in kind, not introduced here, but this plan rewrote the surrounding contract prose and left the docstring asserting…"*). That is the harder and more common case: a rewrite that corrects one assertion in a contract block while leaving a neighbouring assertion in the same block unchanged and now unsupported.

## Root cause

`ext-self-review-plan-marshall` surfaces a rich candidate set — contract sources, source-of-truth duplicates, same-document normative directives, description-vs-body frontmatter, advertised-form help strings — but every member of that set compares a claim against **another document or another declaration**. None compares a **normative assertion in a docstring against the behaviour of the code in the same file**. So a docstring that overclaims what its own adjacent function enforces has no detector to trip, and the step's "clean" verdict is clean over a population that never contained the candidate.

There is a second, sharper property: the plan's own subject was this archetype, and the self-review had no way to know that. A pre-submission review that could take the plan's `change_type` / deliverable subject as a hint — *this diff is a docs-vs-code correction; sweep the touched contract blocks for other unsupported assertions* — would have had the strongest possible reason to look exactly where the security audit later looked.

## Proposed action

- Add a detector for **assertion-vs-adjacent-implementation** in the same file: a docstring or comment containing a normative claim about behaviour (`never`, `always`, `only`, `guarantees`, `is not`) whose subject is a symbol defined in that file, paired with the defining function, surfaced as a candidate for the reviewer to judge. It cannot be decided mechanically, which is precisely why it belongs in the candidate set rather than in a lint rule.
- Extend the sweep from the changed hunks to the **whole contract block** a hunk touches. A rewrite that corrects one sentence of a docstring should put the rest of that docstring in scope, since the correction is evidence the block was wrong.
- Report the candidate **population** alongside the verdict. "7 candidates examined, clean" reads as coverage; it is a statement about how many candidates the detector set produced, not about how much of the diff was reviewable. A clean verdict whose population is missing the relevant detector family is not distinguishable from a clean verdict over a complete one.

## Impact scope

Contained here — the security audit caught it one step later, the operator elected to fix it, and the correction shipped in `db3d67f65` with matched controls and lock-step doc updates. The lesson is about the ordering being load-bearing: had the security-audit step not been in this plan's manifest, a freshly-rewritten contract block carrying an unsupported assertion would have shipped behind a clean self-review.

## Evidence

- `status.metadata.phase_steps['6-finalize']['pre-submission-self-review']` — `outcome: done`, "self-review clean: 7 candidates examined"; decision.log `273ea9` — `total_candidates=7 (>5 threshold, cov_scope=inherit)`
- record-step timestamps: self-review `4038d9` at 17:46:25Z, security-audit `20440e` at 17:53:52Z; finding `3d1669` timestamped 17:52:34Z
- finding `3d1669` — full text, including "this plan rewrote the surrounding contract prose and left the docstring asserting command[0] is never an arbitrary client-supplied binary, which a basename-only check does not establish"
- decision.log `c934c3` — the operator's FIX-here-anyway ruling; commit `db3d67f65`
