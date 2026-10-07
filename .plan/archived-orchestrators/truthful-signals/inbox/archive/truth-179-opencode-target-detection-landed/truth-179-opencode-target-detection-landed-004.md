envelope_version=1
sender_type=plan
sender_id=truth-179-opencode-target-detection-landed
epic=truthful-signals
kind=candidate-lesson
created=2026-09-25T13:26:42Z

title=Transient plugin-doctor runner timeouts accepted as environmental in python
category=improvement
component=python

## Candidate lesson (insight for module python)

Enrich verb: insight.

Generalized hint: the project tolerates transient machine-speed timeouts (pytest-timeout inside plugin-doctor quality-gate/plan-path scans) as environmental rather than code failures — accepted repeatedly within one run with zero assertions failed, with remote CI governing correctness.

Evidence: 4 accepted `test-failure` dispositions on `test_runner.py:384` in plan truth-179-opencode-target-detection-landed (all `Timeout (>300s)` inside scan passes), recurrence 4 >= threshold 2.
