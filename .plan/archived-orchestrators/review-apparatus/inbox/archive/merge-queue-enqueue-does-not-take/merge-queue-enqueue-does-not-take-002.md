envelope_version=1
sender_type=plan
sender_id=merge-queue-enqueue-does-not-take
epic=review-apparatus
kind=candidate-lesson
created=2026-08-03T20:57:04Z

component=pm-plugin-development:ext-self-review-plan-marshall
category=anti-pattern
title=A residual sweep must search the CLAIM and declare its scope, not the removed phrasing
confidence=high
source_plan=merge-queue-enqueue-does-not-take
source_pr=1087
severity=live-defect-in-merged-main

# A residual sweep must search the CLAIM and declare its scope, not the removed phrasing

## Context

`pre-submission-self-review` ran **5 iterations** on this plan and produced **15 findings** (all in the QGATE store, `manage-findings qgate list --phase 6-finalize`). The findings-per-iteration curve was 6, 4, 3, 1, 1 — converging, and every finding was marked fixed.

It still shipped the defect it was closing. **This is live in merged main at `ca7cf9bd4`.**

Finding `7a535a` (round 4) observed that `test_ci_base.py` still quoted the pre-change `--head` help wording `alternative to --pr-number` after the source had been rewritten to `in place of --pr-number`. Its recorded resolution states:

> "Verified the dead literal now appears in zero test and source files. The single remaining marketplace occurrence is the pr-operations.md table row..."

That claim is false. At `ca7cf9bd4`, `test/plan-marshall/tools-integration-ci/test_ci_base.py` still carries the retired phrasing at **lines 548, 561 and 569** — three sibling test docstrings in the very file the fix edited at lines 502 and 543.

## Root cause

**Scope-of-sweep ≠ scope-of-claim.** The resolution's own words give it away: "The single remaining **marketplace** occurrence". The sweep was scoped to `marketplace/**`. The survivors live in `test/**`, structurally outside that scope — while the claim asserted "zero **test** and source files".

Compounding it: the survivors are PRE-EXISTING (introduced by PR #184, confirmed via `git log -S`). The author swept the sites *this diff authored* and then generalised the result to the corpus.

**The recurrence migrated granularity under fixing** — each iteration's miss was finer than the last:
- Round 2 (`660eee`): swept 3 of 4 docs; **a whole FILE was missed**.
- Round 3 (`140aae`): patched the named location while "the survivor sits inside the very line the fix edited" — **a CLAUSE inside an edited sentence**. That finding explicitly notes it is "the third consecutive iteration in which a restating site was patched at the named location while an adjacent restatement survived."
- Round 4 (`7a535a`): fixed 2 named sites, asserted a corpus-wide zero, **3 siblings in the same file survived**.

The sweeps searched for the **removed phrasing** rather than the **claim**, and `architecture search --content` is case-sensitive with no `--ignore-case` (see sibling candidate-lesson), so near-miss casings never surfaced.

## Proposed action

1. **A residual-zero claim MUST publish its scope.** "Zero occurrences" is meaningless without the searched population. Require the sweep to emit `scope_searched` + `files_scanned` alongside the count, so `marketplace/**` cannot be reported as "test and source".
2. **Search the claim, not the string.** The invariant is "no doc asserts a help wording that the source does not emit". Enumerate doc-quoted literals and match each against the live source symbol (finding `a494d3` did exactly this and closed its class exhaustively — 2 occurrences, both verified). Make that the default shape.
3. **A fix for a restatement defect must sweep the whole file it edits**, not the named lines. Three of five iterations failed this specific way.
4. Fold `(?i)` into the sweep by default.

## Evidence

- qgate `7a535a` resolution vs `test_ci_base.py:548,561,569` at `ca7cf9bd4` — verified by `architecture search --content --pattern "alternative to --pr-number"` → 3 matches, and by `Read`.
- `git log -1 -S "as alternative to --pr-number" -- test/.../test_ci_base.py` → `97bb1130d` (#184), i.e. pre-existing.
- qgate `660eee`, `140aae`, `4f6091`, `09d0d2` — the granularity-migration chain.

## Dedup context for the orchestrator

Related to the standing `volume-read-as-coverage` and `a reviewer's list of call sites is a SAMPLE, not an enumeration` archetypes, but distinct: this is about a **verification claim** whose scope silently differs from its wording, not about an enumeration. Gate 1 dedup NOT run (`orchestrated: true`).
