envelope_version=1
sender_type=plan
sender_id=implement-plan-03-emitter-reenable
epic=model-provisioning
kind=candidate-lesson
created=2026-09-16T11:19:36Z

component=plan-marshall:build-pyproject
category=bug

# Re-reported mypy dict-item error test_variant_emitter.py:364 entry 0 (verify re-filing)

Source plan: implement-plan-03-emitter-reenable (epic model-provisioning).
Signal: qgate 5-execute hash 30e42c, resolution fixed in-run via TASK-008.

Observation: same entry-0 `str | None` dict-item defect as hash 57e2e6, re-filed by execute-exit verify on 2026-09-16T06:57:16Z.

Evidence: Q-Gate finding `Dict entry 0 has incompatible type str: str | None; expected str: str`, path `test/marketplace/targets/opencode/test_variant_emitter.py:364`, resolved 2026-09-16T07:11:17Z as `Will be addressed by TASK-008`.

Candidate lesson: dedup consideration — this record and 57e2e6 describe one defect observed twice.
