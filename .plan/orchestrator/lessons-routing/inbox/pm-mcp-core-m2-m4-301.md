envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-17T20:22:09Z

# Candidate lesson: offer concrete proposed names in any rename option of a refine question

Component: plan-marshall:phase-2-refine (version 0.1.1947)
Category: improvement
Source: plan-retrospective of work-package-redistribution (session transcript)

## Context

Refine asked q2: "The request lets you adjust the names of the two new packages ... Keep the names?" with the
options "Keep both names as specified" and "Rename one or both (give the names in your answer)". The operator chose
to rename. The follow-up question asked "Which new names should the two packages get? Pick 'Other' to type them"
and again offered no names. The operator then had to type "what new names do you propose?" before accepting the
proposals (`start-source-intake`, `epic-resource-and-release`).

## Root cause

The question offered the decision without the candidates the decision is about, so one answer took three turns.

## Proposed action

When refine asks whether to rename something, each rename option carries concrete proposed names (one or two
candidates with a one-line reason), and "Other" stays available for the operator's own name.

## Evidence

- chat-history-analysis: pivot at the q2 follow-up; operator turn "hwat new names do you propose?" followed by
  "proposals acepted, continue"
