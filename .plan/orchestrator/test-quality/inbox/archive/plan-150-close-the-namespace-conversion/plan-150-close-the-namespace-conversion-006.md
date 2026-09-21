envelope_version=1
sender_type=plan
sender_id=plan-150-close-the-namespace-conversion
epic=test-quality
kind=candidate-lesson
created=2026-09-02T21:54:18Z

component=plan-marshall:phase-5-execute
category=improvement
confidence=medium
source_plan=plan-150-close-the-namespace-conversion

# Emit a [VERIFY] line per deliverable verification run

## Context

The plan's work log carries 773 entries. A tag census over it finds 198 `[MANAGE-STATUS]`,
107 `[BUILD-SERVER]`, 67 `[STATUS]`, 55 `[MANAGE-TASKS]`, 42 `[ARTIFACT]`, 41 `[SKILL]`,
41 `[STEP]`, 19 `[DISPATCH]`, 14 `[OUTCOME]`, 13 `[ATTEMPT]` — and 3 `[VERIFY]`.

Three, against 8 deliverables that each declare a verification command and explicit success
criteria, plus three manifest-declared `phase_5.verification_steps`. The ratio is 0.38,
below the aspect's 0.5 warning floor.

Verification unambiguously ran and was green: whole-tree verify passed with 23,739 tests,
the pre-push quality gate was green on both the scoped bundle and the whole tree, and every
deliverable's criteria were met. The strongest evidence this plan produced is the least
visible in its own log.

## Root cause

`[VERIFY]` emission is not wired to the per-deliverable verification path the way
`[ARTIFACT]` and `[OUTCOME]` are wired to task completion. Those two pair exactly (9 of 9
outcomes paired, 0 unpaired in either direction); `[VERIFY]` has no equivalent guard, so
it is emitted opportunistically rather than structurally.

## Proposed action

Emit one `[VERIFY]` work-log line per deliverable verification run and per manifest
verification step, naming the command and its verdict. This is a legibility fix, not a
behaviour change: it makes an already-correct verification path auditable by the same
population-pairing logic that already guards outcomes and artifacts.

## Evidence

- aspect: logging_gap_analysis — `expected_vs_actual`: `VERIFY, expected_min 8, observed 3`; gap `phase-5-execute / VERIFY` at ratio 0.38
- tag census over `logs/work.log` (773 entries) — `[VERIFY]: 3`, the second-rarest tag in the log after `[BLOCKED]: 1`
- contrast: `OUTCOME_COVERAGE` pairs 9 of 9 and `RE_ENTRY_COVERAGE` pairs 2 of 2, both with zero unpaired entries in either direction — the guarded categories are complete, the unguarded one is not
