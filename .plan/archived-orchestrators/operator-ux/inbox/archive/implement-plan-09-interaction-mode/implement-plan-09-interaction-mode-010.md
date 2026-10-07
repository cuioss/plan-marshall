envelope_version=1
sender_type=plan
sender_id=implement-plan-09-interaction-mode
epic=operator-ux
kind=candidate-lesson
created=2026-09-16T16:13:05Z

component=plan-marshall:workflow-integration-github:github_pr
category=bug

# Place router-scoped flags before the CI verb on read surfaces

Source: work-log script_failure 2026-09-16T13:48:40Z and 2026-09-16T15:02:35Z, notation plan-marshall:workflow-integration-github:github_pr exit 2 with unrecognized --plan-id after the verb.

Defect: automatic-review passed --plan-id after a read verb whose subparser declares no such flag; the router consumes that flag only before the verb token on the checks and pr read verbs.

Rule: consult each script canonical-invocation block for flag position; never append --plan-id by rote after the verb on CI read verbs.

Evidence: repeated identical rejection across two loop-back rounds confirms a systematic call-site pattern rather than a one-off typo.
