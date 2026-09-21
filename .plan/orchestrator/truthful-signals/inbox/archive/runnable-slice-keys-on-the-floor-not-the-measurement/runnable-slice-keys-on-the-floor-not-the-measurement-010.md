envelope_version=1
sender_type=plan
sender_id=runnable-slice-keys-on-the-floor-not-the-measurement
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T04:56:23Z

component=manage-execution-manifest
category=bug
created=2026-07-29

# Legacy config key survives in an execution-manifest snapshot after schema migration

This plan's execution-manifest step-params snapshot still carries the legacy
`enabled_bots` key, never migrated to the current required_bots/optional_bots
schema that `github_pr fetch_findings` and `review_completeness check` now
actually require — both scripts rejected `--enabled-bots` with exit 2 when
probed. `automatic-review/SKILL.md` and
`workflow-integration-github/SKILL.md` still narrate the retired flag in prose.

## Impact

A schema migration on a config key consumed by multiple scripts is incomplete
until every producer (execution-manifest composer), every consumer script's
argparse surface, AND every doc narrating the flag are updated together —
verify by probing the actual scripts with the new/old flag, not by reading the
schema doc alone.
