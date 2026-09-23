envelope_version=1
sender_type=plan
sender_id=module-budget-campaign-completion
epic=test-quality
kind=candidate-lesson
created=2026-09-23T14:46:38Z

component=plan-marshall:tools-script-executor
category=anti-pattern
title=Invented manage-info verb and flag guesses fail argparse and recover via --help without retry
plan_id=module-budget-campaign-completion
source_aspects=work-log-script-failures
confidence=high

# Invented manage-info verb and flag guesses fail argparse and recover via --help without retry

## Context

Work log for this test-only carve (PR #1593) carries 9 distinct failing script notations across phases 2-refine through post-run-review, all exit_code=2 argparse rejections or narrow internal failures, each handled by falling back to --help or a documented verb without retrying the intended read.

## Root cause

Agents paraphrased plausible verb/flag names from workflow narrative instead of quoting the argparse declaration: show for manage-status/manager-tasks, --file on manage-files list, --deliverable on manage-solution-outline read, list for manage-plan-documents, missing required --phase on manage-findings qgate list, --output-file on check-artifact-consistency run, planning-lane verb slot filled with a plan id, plus two internal failures (phase_handshake main-dirty leak, scope_creep_check invalid finding type scope_creep_warning).

## Proposed action

Quote subcommand and flag names verbatim from executor mappings or --help output; never extrapolate from prose. When in doubt, run --help first. Treat the five canonical argparse-rejection signatures as a pre-invocation checklist.

## Evidence

- plan-marshall:manage-status:manage-status show rejected; planning-lane with plan id as verb rejected
- plan-marshall:manage-files:manage-files list --file rejected (flag lives on exists/read siblings)
- plan-marshall:manage-solution-outline:manage-solution-outline read --deliverable rejected (canonical --deliverable-number)
- plan-marshall:manage-plan-documents:manage-plan-documents list rejected (choices list-types/request)
- plan-marshall:manage-tasks:manage-tasks show rejected
- plan-marshall:manage-findings:manage-findings qgate list without --phase rejected (twice, 6-finalize and lessons-capture)
- plan-marshall:plan-retrospective:check-artifact-consistency run --output-file rejected
- plan-marshall:plan-marshall:phase_handshake main_checkout_dirtied_during_plan; plan-marshall:phase-5-execute:scope_creep_check invalid type scope_creep_warning
- signal: signal_script_failure_clusters_count=9 (union dedup by distinct notation)
