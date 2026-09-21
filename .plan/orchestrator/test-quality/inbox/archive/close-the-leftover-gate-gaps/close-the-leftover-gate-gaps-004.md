envelope_version=1
sender_type=plan
sender_id=close-the-leftover-gate-gaps
epic=test-quality
kind=candidate-lesson
created=2026-09-19T09:19:56Z

component=pm-plugin-development:ext-self-review-plan-marshall
category=bug
source_finding=a68da6
source_phase=6-finalize
source_type=qgate
signal=signal_qgate_pending_count

# Contract drift: Class-3 exemption narrowed to literal py_compile but doc still exempts any stdlib -m

When the diff narrowed the Class-3 exemption in `_analyze_test_conventions.py:467` to literal `-m py_compile` only (new test asserts `-m unittest repo_pkg` still fires), the detection doc `doctor-test-conventions.md` step 2 still exempted any `-m` stdlib invocation as importing nothing from the tree.

## Observation

Q-Gate finding `a68da6` (contract_drift, 6-finalize) caught the mismatch. Fixed in-run by doc commit b8cce0470 qualifying Class-3 as py_compile-only; full-surface re-examination at same HEAD clean (38 candidates, no check matched).

## Candidate lesson direction (for orchestrator classification)

Qualify doc exemption text in the same commit that narrows the code exemption; add a negative control asserting the narrowed-out case still fires.

## Source

Plan close-the-leftover-gate-gaps, PR 1534, file marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_test_conventions.py:467, resolution fixed 2026-09-18.
