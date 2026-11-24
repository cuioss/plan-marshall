envelope_version=1
sender_type=orchestrator
sender_id=libraries-initial-implementation
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:07:00Z

component=plan-marshall:phase-6-finalize
category=bug
title=phase-6-finalize: dispatcher passes --step to post_run_source_guard check, which takes --step-id; a rejected guard call must not count as a pass
source_lesson=2026-11-18-07-003
source_repo=git-document-repository (epic libraries-initial-implementation)
source_created=2026-11-18

# phase-6-finalize: dispatcher passes --step to post_run_source_guard check, which takes --step-id; a rejected guard call must not count as a pass

# Candidate lesson: finalize dispatcher called `post_run_source_guard check --step` (argparse rejection)

- Source signal: plan-retrospective, script-failure aspect (not covered by lessons-capture, which ran before the call)
- Script log: 2026-11-18T06:53:22Z, hash 39e33c, exit_code=2, `plan-marshall:phase-6-finalize:post_run_source_guard check --plan-id git-testing-fixtures --step lessons-capture`
- Detail: "`--step` is not declared for `plan-marshall:phase-6-finalize:post_run_source_guard check`: ['fail-on-dirty', 'project-dir', 'step-id']"

## What happened

Right after `lessons-capture` returned, the finalize dispatcher ran the post-run source guard for that step and passed `--step` instead of `--step-id`. The call was rejected by argparse, so the guard that checks a post-run-review step left tracked sources untouched did not run for `lessons-capture`. The dispatcher went on to the next step.

## Candidate rule

`--step` is the flag name of `manage-status mark-step-done`, used a few lines earlier in the same dispatcher flow; `post_run_source_guard check` takes `--step-id`. This is the verb-scoped flag-paraphrase form of the invented-flag error. Possible fixes: quote the canonical `post_run_source_guard check --step-id` invocation at the dispatcher call site in phase-6-finalize, or accept `--step` as an alias. A rejected guard call should also be treated as a guard that did not run, not as a pass.
