envelope_version=1
sender_type=plan
sender_id=close-the-leftover-gate-gaps
epic=test-quality
kind=candidate-lesson
created=2026-09-19T09:20:06Z

component=pm-plugin-development:plugin-doctor
category=bug
source_findings=02ad26,9d0ea1,260429,a2e5a0
source_type=pr-comment
signal=signal_automated_review_count
bot=coderabbit

# Review-bot functional correctness trio in test-convention analyzer caught and fixed in-run

CodeRabbit posted 3 actionable inline findings plus a follow-up review_body on `_analyze_test_conventions.py`, all remediated in-run via TASK-4/TASK-005 follow-up commits on this branch.

## Observations

- `02ad26` (line 315): module-wide env binding map lets an unreachable assignment exempt env=settings; resolve each Name against definitions visible at that call (scope, order, reachability).
- `9d0ea1` (line 366): `-m` stdlib check insufficient because `python -m unittest repo_pkg` imports repo code via loadTestsFromName; exempt only the literal `py_compile` launcher.
- `260429` (line 428): scrub guard tested the value target instead of the key; require a direct key-not-in-container comparison for PYTHONPATH.
- `a2e5a0` (review_body): doc stated any `-m` stdlib exempt while code exempts only py_compile; describe the exemption as literal `-m py_compile`.

## Candidate lesson direction (for orchestrator classification)

Slipped-then-caught defect class: static-analysis guard predicates must be checked against the scenario the guard exists for (reachability, launcher imports later args, key vs value target, doc-code exemption parity).

## Source

Plan close-the-leftover-gate-gaps, PR 1534, file marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_test_conventions.py, resolutions fixed 2026-09-18/19.
