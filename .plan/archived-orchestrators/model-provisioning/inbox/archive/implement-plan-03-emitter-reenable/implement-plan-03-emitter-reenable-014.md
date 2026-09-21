envelope_version=1
sender_type=plan
sender_id=implement-plan-03-emitter-reenable
epic=model-provisioning
kind=candidate-lesson
created=2026-09-16T11:20:13Z

component=plan-marshall:manage-execution-manifest
category=anti-pattern

# manage-execution-manifest unregistered verb in finalize verification-feedback

Source plan: implement-plan-03-emitter-reenable (epic model-provisioning).
Signal: script-failure cluster notation plan-marshall:manage-execution-manifest:manage-execution-manifest (2026-09-16T10:29:45Z, exit_code 2, argparse_rejection).

Observation: verification-feedback invoked `manage-execution-manifest` with an unregistered verb; parser lists registered verbs as `compose, lanes, read, reconcile, record-step, refire-report, step-params, validate, validate-loadable`. The run continued (triage completed), so the call was non-blocking but evidences verb paraphrase.

Evidence: work-log `[ERROR] (plan-marshall:execute-script:2) script_failure notation=plan-marshall:manage-execution-manifest:manage-execution-manifest exit_code=2 failure_kind=argparse_rejection detail=Use a registered verb`.

Candidate lesson: quote `manage-execution-manifest` verbs verbatim from `--help`; never invent a plausible verb from narrative.
