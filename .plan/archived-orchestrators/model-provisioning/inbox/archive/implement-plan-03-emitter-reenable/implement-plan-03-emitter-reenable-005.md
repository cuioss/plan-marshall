envelope_version=1
sender_type=plan
sender_id=implement-plan-03-emitter-reenable
epic=model-provisioning
kind=candidate-lesson
created=2026-09-16T11:19:03Z

component=plan-marshall:build-pyproject
category=bug

# mypy str|None index error in opencode emitter tests required follow-up TASK-008

Source plan: implement-plan-03-emitter-reenable (epic model-provisioning).
Signal: qgate 5-execute hash 5a5e85, resolution fixed in-run via TASK-008.

Observation: `test_level_table_lockstep.py:91` indexed `dict[str, dict]` with `str | None`, producing `Invalid index type "str | None"` [index]. The pinned-contract emitter tests carried nullable values into a non-nullable map key.

Evidence: Q-Gate finding `mypy: invalid index type str|None in test_level_table_lockstep.py:91`, detail `Invalid index type "str | None" for "dict[str, dict[Any, Any]]"; expected type "str" [index]`, filed 2026-09-15T21:39:20Z, resolved 2026-09-16T07:11:12Z as `Will be addressed by TASK-008`.

Candidate lesson: type-narrow nullable emitter inputs at the test boundary before map indexing; do not let `str | None` reach a `dict[str, ...]` key.
