envelope_version=1
sender_type=orchestrator
sender_id=libraries-initial-implementation
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:07:32Z

component=plan-marshall:platform-runtime
category=bug
title=append the new session id to status.metadata.session_ids when a plan resumes in a new session
source_lesson=2026-11-22-13-005
source_repo=git-document-repository (epic libraries-initial-implementation)
source_created=2026-11-22

# append the new session id to status.metadata.session_ids when a plan resumes in a new session

# Candidate lesson: append the new session id to session_ids when a plan resumes in a new session

- Source signal: plan-retrospective of plan-09-store-release-index-listeners (inbox plan-09-store-release-index-listeners-023; logging-gap and chat-history aspects).

## What happened

The plan resumed once after an interpreter outage, in a second session. `status.metadata.session_ids` still holds only the first session id, and `session capture` at retrospective start stored the first id again. Session-keyed consumers (metrics enrichment from transcripts, the chat-history aspect) therefore see only part of the run; the landing's token total is a floor for that reason ("enrich measured one of two sessions").

## Candidate rule

On every plan entry (resume, re-entry, finalize dispatch from a new session) compare the live session id with `session_ids` and append it when new, and make the chat-history and metrics consumers iterate all recorded ids. Owning component: `plan-marshall:platform-runtime`.
