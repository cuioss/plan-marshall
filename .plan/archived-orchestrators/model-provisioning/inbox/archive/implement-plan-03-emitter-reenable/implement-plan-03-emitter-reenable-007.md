envelope_version=1
sender_type=plan
sender_id=implement-plan-03-emitter-reenable
epic=model-provisioning
kind=candidate-lesson
created=2026-09-16T11:19:21Z

component=plan-marshall:build-pyproject
category=bug

# mypy dict-item str|None error in test_variant_emitter.py:364 entry 1

Source plan: implement-plan-03-emitter-reenable (epic model-provisioning).
Signal: qgate 5-execute hash e57d76, resolution fixed in-run via TASK-008.

Observation: `test_variant_emitter.py:364` entry 1 carried `str | None` into a `dict[str, str]`, producing `Dict entry 1 has incompatible type "str": "str | None"; expected "str": "str" [dict-item]`.

Evidence: Q-Gate finding filed 2026-09-15T21:39:23Z, resolved 2026-09-16T07:11:15Z as `Will be addressed by TASK-008`.

Candidate lesson: same narrow-at-boundary rule as entry 0; both entries share one fixture-construction fix.
