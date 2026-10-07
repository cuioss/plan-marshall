envelope_version=1
sender_type=plan
sender_id=implement-plan-03-emitter-reenable
epic=model-provisioning
kind=candidate-lesson
created=2026-09-16T11:19:57Z

component=plan-marshall:manage-references
category=anti-pattern

# manage-references get missing required field flag in lessons-housekeeping

Source plan: implement-plan-03-emitter-reenable (epic model-provisioning).
Signal: script-failure cluster notation plan-marshall:manage-references:manage-references (2026-09-16T08:14:27Z, exit_code 2, argparse_rejection).

Observation: lessons-housekeeping called `manage-references get` without the required `--field`; the parser refused with `Add the required flag(s) to manage-references get: ['field']`. The step recovered (0 removed, 0 promoted, 189 retained).

Evidence: work-log `[ERROR] (plan-marshall:execute-script:2) script_failure notation=plan-marshall:manage-references:manage-references exit_code=2`.

Candidate lesson: `manage-references get` always requires `--field`; consult `--help` before invoking the get verb.
