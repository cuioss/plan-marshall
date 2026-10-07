envelope_version=1
sender_type=plan
sender_id=implement-plan-03-emitter-reenable
epic=model-provisioning
kind=candidate-lesson
created=2026-09-16T11:19:51Z

component=plan-marshall:manage-findings
category=anti-pattern

# manage-findings qgate add argparse rejection during verification-feedback triage

Source plan: implement-plan-03-emitter-reenable (epic model-provisioning).
Signal: script-failure cluster notation plan-marshall:manage-findings:manage-findings (3 hits 2026-09-15T21:39:14-16Z, exit_code 2, argparse_rejection).

Observation: verification-feedback attempted `manage-findings qgate add` with a flag set the parser rejects; usage shows required `--plan-id --phase {2-refine,3-outline,4-plan,5-execute,6-finalize} --source {qgate,user_review} --type {...} --title --detail`. The triage recovered (findings were persisted via the verify path and TASK-008 was filed), but the add-path invocation shape is wrong.

Evidence: work-log `[ERROR] (plan-marshall:execute-script:2) script_failure notation=plan-marshall:manage-findings:manage-findings exit_code=2 failure_kind=argparse_rejection` x3.

Candidate lesson: quote the `qgate add` canonical invocation verbatim from `--help`; never extrapolate the add flag set from surrounding prose.
