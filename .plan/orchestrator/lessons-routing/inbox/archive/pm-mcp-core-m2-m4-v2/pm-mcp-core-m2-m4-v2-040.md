envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4-v2
epic=lessons-routing
kind=candidate-lesson
created=2026-11-20T13:43:25Z

component=traced-implementation
category=improvement

# Diff every removed clause against origin/main in condensation reviews

## Context

In plan-v2-155 (R05 condensation of model-work 02, 04, 05) the condensation introduced behaviour regressions. The first functional review caught one (the `lost` row widened to every closing reason). Two further functional and code-review rounds then passed, and CodeRabbit found five real issues on the PR: the dropped "`job_ended` first" fencing clause (a regression), the re-offer rule that ignored `awaiting_answer`, an ambiguous lease bullet, an inaccurate watch pointer and an Owed obligation missing from runtime-launch.adoc.

## Root cause

The reviews checked that kept sentences were true, but did not systematically check each removed or rewritten clause against the text at origin/main, which is where a condensation loses behaviour.

## Proposed action

For condensation plans, require the cut ledger to quote the origin/main text of every removed or merged clause and have the functional review check each one against its claimed new home, before the PR is opened.

## Evidence

- aspect: request-result-alignment — two regressions in D5, only one caught before the bot review
- aspect: chat-history-analysis — unified triage fixed CodeRabbit findings 1c97a9, e13d34, a7633c, ccfb4c, 20b25c inline
