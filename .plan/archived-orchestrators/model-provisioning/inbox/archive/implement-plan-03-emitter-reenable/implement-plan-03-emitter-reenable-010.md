envelope_version=1
sender_type=plan
sender_id=implement-plan-03-emitter-reenable
epic=model-provisioning
kind=candidate-lesson
created=2026-09-16T11:19:42Z

component=plan-marshall:build-pyproject
category=bug

# Re-reported mypy dict-item error test_variant_emitter.py:364 entry 1 (verify re-filing)

Source plan: implement-plan-03-emitter-reenable (epic model-provisioning).
Signal: qgate 5-execute hash 9051ee, resolution fixed in-run via TASK-008.

Observation: same entry-1 `str | None` dict-item defect as hash e57d76, re-filed by execute-exit verify on 2026-09-16T06:57:20Z.

Evidence: Q-Gate finding `Dict entry 1 has incompatible type str: str | None; expected str: str`, path `test/marketplace/targets/opencode/test_variant_emitter.py:364`, resolved 2026-09-16T07:11:19Z as `Will be addressed by TASK-008`.

Candidate lesson: dedup consideration — this record and e57d76 describe one defect observed twice.
