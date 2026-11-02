envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=candidate-lesson
created=2026-10-22T09:57:50Z

# Candidate lesson: weakened_test counts assertions per file, so a move-only test split is flagged as lost assertions on every head (plan-marshall:phase-6-finalize)

Forwarded from API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-43-validator-reserved-header-topology-rules (PR cuioss/API-Sheriff#505), local lesson 2026-10-22-08-001.

RECURRENCE of api-sheriff-api-sheriff-0-2-0-036 (weakened_test per-path count flags git-mv test moves); here it forced operator closes of functional-review and code-review at three heads (841609fc, ee067536, 1094af28).

## What happened

PLAN-V02-43 (PR #505) split `ConfigValidatorTest` into `TopologyRulesTest`, `HeaderRulesTest` and `ReservedPathRulesTest` and kept the rest in `ConfigValidatorTest`. The cases were moved, not removed: 130 assertion lines in the original file, 136 across the four files afterwards, and 58 test methods before and after.

The test-integrity check in both the functional review and the code review still reported `weakened_test: 120 assertion(s) present at origin/main are gone from the file` on `ConfigValidatorTest.java`, with severity `error`. It counts assertions per file and has no idea that they moved to another file.

The code-review verifier refused the finding twice (Q-Gate 31a15f at head 841609f, 57f6a2 at head ee06753): it sampled the removed tests and found every one in the new classes ("1256 lines moved"). The finding stayed open anyway and needed an operator close each time. In total six Q-Gate findings (37531c, 943bac, 31a15f, 7647aa, 5eb913, 57f6a2) were recorded and accepted by the operator for this one false positive, over two heads.

## Why it matters

A move-only test extraction is a normal refactor. Each time it happens, the run stops for an operator decision on a finding the verifier has already shown to be wrong. Operators learn to accept `weakened_test` without looking, which removes the value of the check for real test removals.

## Suggested direction (for plan-marshall)

- Make the assertion count move-aware: compare the total across the files the change touched (deleted plus added test files in the same module or package), not file by file. Report a loss only when the total drops, or when named test methods disappear from all files.
- When the verifier answers `verdict_refused` with "moved, not weakened", let that close the finding without an operator step, or at least lower it from `error`.
- Related: the per-head re-open in lesson 2026-10-22-08-002 makes this cost repeat on every push.

## Provenance

Observed in plan `plan-v02-43-validator-reserved-header-topology-rules`, epic `api-sheriff-0-2-0`, PR #505 (merged as 1e53ab4f). Filed in the API-Sheriff store only because the plan-marshall `lessons-routing` inbox could not be written from the lessons-capture step. Route it to that inbox and remove this local copy afterwards.
