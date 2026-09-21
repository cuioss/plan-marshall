envelope_version=1
sender_type=plan
sender_id=implement-plan-03-emitter-reenable
epic=model-provisioning
kind=candidate-lesson
created=2026-09-16T11:19:29Z

component=plan-marshall:build-pyproject
category=bug

# Re-reported mypy index error test_level_table_lockstep.py:91 (verify re-filing)

Source plan: implement-plan-03-emitter-reenable (epic model-provisioning).
Signal: qgate 5-execute hash 1cee47, resolution fixed in-run via TASK-008.

Observation: same `str | None` index defect as hash 5a5e85, re-filed by the execute-exit verify pass on 2026-09-16T06:57:13Z. Duplicate row evidences the double-reporting path (triage filing plus verify filing) for one defect.

Evidence: Q-Gate finding `Invalid index type str | None for dict[str, dict[Any, Any]]; expected type str`, path `test/marketplace/targets/opencode/test_level_table_lockstep.py:91`, resolved 2026-09-16T07:11:16Z as `Will be addressed by TASK-008`.

Candidate lesson: dedup consideration for the orchestrator — this record and 5a5e85 describe one defect observed twice.
