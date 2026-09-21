envelope_version=1
sender_type=plan
sender_id=implement-plan-08-slug-semantics-model-compliance
epic=tooling-truthfulness
kind=candidate-lesson
created=2026-09-14T08:09:49Z

# Folded global logs carry 172 error lines worth a triage look

## Context

The plan's folded-in global log copies (2 files, 4681 lines) hold 172 error/non-INFO
lines. The log-analysis aspect flags them as a warning; none was triaged during this
run because the finalize tail ran unattended on resume.

## Root cause

Untriaged by capacity, not by verdict — the resume tail prioritized the merge gate and
post-merge steps, and the folded error lines were never sampled.

## Proposed action

The orchestrator may drain the folded logs for this plan when convenient; if the 172
lines prove to be routine retry noise, no further action is needed.

## Evidence

- aspect: log_analysis — global_log_signals error_count 172 over 2 folded files, warning finding GLOBAL_LOG_ERRORS
