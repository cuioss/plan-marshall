envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4-v2
epic=lessons-routing
kind=candidate-lesson
created=2026-11-20T17:37:51Z

component=plan-marshall:workflow-integration-git
category=improvement
created=2026-11-20
bundle=plan-marshall
title=Infer the manifest step id for finalize triage commits or name it in the refusal

# Infer the manifest step id for finalize triage commits or name it in the refusal

## Context

During the PLAN-V2-158 finalize, the commit of the first unified-triage inline fixes (CodeRabbit wording dispositions) was refused by the gate-bearing commit verb. The refusal came at 2026-11-20T14:37:03Z, exit 1, recorded by script-failure-analysis as a script_internal_error with an empty stderr excerpt. The cause was a missing manifest step id. It was resolved by re-issuing the commit with `--step automatic-review`. The triage dispatch's own hand-back only said that "the dispatcher commits and pushes" the edits, under `fix(review): apply inline review dispositions`, and did not name the step id the gate requires.

## Root cause

The commit gate needs a manifest step id for a finalize-phase commit. The unified-triage hand-back does not carry one, and the refusal surfaces as an exit-1 internal error rather than a named, actionable refusal.

## Proposed action

Either have the triage hand-back (finalize-feedback producer) return the step id its inline edits belong to, so the dispatcher can pass it on, or let `git-workflow commit` infer it from the producer / current finalize step. In any case, return a structured refusal (`error: missing_step_id`, naming the accepted step ids) at exit 0 instead of an internal error.

## Evidence

- aspect: script_failure_analysis — plan-marshall:workflow-integration-git:git-workflow commit, exit 1, script_internal_error, 2026-11-20T14:37:03Z
- dispatcher fact — "a commit gate refused a triage commit without a manifest step id (resolved with --step automatic-review)"
