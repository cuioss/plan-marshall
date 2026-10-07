envelope_version=1
sender_type=plan
sender_id=implement-plan-03-emitter-reenable
epic=model-provisioning
kind=candidate-lesson
created=2026-09-16T11:20:05Z

component=plan-marshall:manage-config
category=anti-pattern

# manage-config verb and flag rejections in finalize self-review and ci-verify

Source plan: implement-plan-03-emitter-reenable (epic model-provisioning).
Signal: script-failure cluster notation plan-marshall:manage-config:manage-config (2 hits: 2026-09-16T08:31:14Z unrecognized --plan-id; 2026-09-16T09:59:54Z unregistered verb, exit_code 2, argparse_rejection).

Observation: pre-submission-self-review passed `--plan-id` to a `manage-config` verb that declares no such flag, and ci-verify invoked an unregistered `manage-config` verb. Both are the invented-subcommand/flag defect class: plausible names that do not exist in argparse choices.

Evidence: work-log script_failure lines for notation plan-marshall:manage-config:manage-config with `unrecognized arguments: --plan-id` and `Use a registered verb for manage-config`.

Candidate lesson: resolve `manage-config` verbs/flags via live `--help` (or the SCRIPTS mapping), never from workflow-prose paraphrase; `--plan-id` is per-verb, not universal.
