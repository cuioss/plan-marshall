envelope_version=1
sender_type=plan
sender_id=implement-plan-03-emitter-reenable
epic=model-provisioning
kind=candidate-lesson
created=2026-09-16T11:19:10Z

component=plan-marshall:build-pyproject
category=bug

# mypy dict-item str|None error in test_variant_emitter.py:364 entry 0

Source plan: implement-plan-03-emitter-reenable (epic model-provisioning).
Signal: qgate 5-execute hash 57e2e6, resolution fixed in-run via TASK-008.

Observation: `test_variant_emitter.py:364` entry 0 carried `str | None` into a `dict[str, str]`, producing `Dict entry 0 has incompatible type "str": "str | None"; expected "str": "str" [dict-item]`.

Evidence: Q-Gate finding `mypy: dict-item type error in test_variant_emitter.py:364 (entry 0)`, filed 2026-09-15T21:39:22Z, resolved 2026-09-16T07:11:13Z as `Will be addressed by TASK-008`.

Candidate lesson: narrow emitter-test dict values to `str` before constructing the expected `dict[str, str]` fixture.
