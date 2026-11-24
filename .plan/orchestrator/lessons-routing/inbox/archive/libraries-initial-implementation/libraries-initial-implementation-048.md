envelope_version=1
sender_type=orchestrator
sender_id=libraries-initial-implementation
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:07:31Z

component=plan-marshall:workflow-integration-sonar
category=bug
title=fetch_findings pre-filter drops java:S1135 TODO issues that still count against the Sonar gate
source_lesson=2026-11-22-13-002
source_repo=git-document-repository (epic libraries-initial-implementation)
source_created=2026-11-22

# fetch_findings pre-filter drops java:S1135 TODO issues that still count against the Sonar gate

# Candidate lesson: the Sonar fetch pre-filter drops java:S1135 TODO issues as suppressable, but they still count against the quality gate

- Source signal: orchestrator observation in plan plan-09-store-release-index-listeners (inbox plan-09-store-release-index-listeners-008; TASK-018 "Remove the five open Sonar java:S1135 TODO markers from new code").

## What happened

`fetch_findings` dropped five `java:S1135` (TODO comment) issues as suppressable, so triage never saw them. They stayed open on the pull request and still counted on the SonarCloud quality gate; they were found only in the second loop-back round. The TODOs came from the OpenRewrite recipe placeholder that `-Ppre-commit` puts in front of a deliberate `catch (RuntimeException ...)`.

## Candidate rule

The pre-filter must not drop an issue that still counts toward the quality gate: keep it in triage, or mark it dismissed on the server through `post_responses`. Otherwise the local view and the gate disagree. Owning component: `plan-marshall:workflow-integration-sonar`.

## Project-side half

A deliberate `catch (RuntimeException ...)` gets an OpenRewrite TODO placeholder: write the justification comment in the form the recipe accepts, or suppress the recipe at that site, before the commit, so no such catch becomes an S1135 issue on new code.
