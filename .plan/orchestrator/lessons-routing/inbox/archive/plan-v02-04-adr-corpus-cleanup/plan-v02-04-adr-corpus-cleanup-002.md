envelope_version=1
sender_type=plan
sender_id=plan-v02-04-adr-corpus-cleanup
epic=lessons-routing
kind=candidate-lesson
created=2026-10-26T09:55:46Z

# Candidate lesson: `inbox amend` refuses an archived message, so a correction after the message was consumed has no channel (plan-marshall:plan-orchestrator inbox)

Forwarded from API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-04-adr-corpus-cleanup (PR cuioss/API-Sheriff#521, merge f5826465), lessons-capture step.

## Observation

A filed inbox message needed a correction after the epic drain had already consumed and archived it. `orchestrator inbox amend` refused the archived message. `supersede` also targets a live message, so there was no sanctioned way to correct the record or to point readers of the archive at the corrected text.

## Why it matters

An archived message is still the record a later drain, retrospective or audit reads. When its facts turn out to be wrong, the wrong text stays authoritative and the correction lives only in chat or in a new, unlinked message.

## Suggested direction

- Allow `amend` (or a dedicated `erratum` verb) on an archived message, stamping `amended` and a revision exactly as for a live one, or
- allow `supersede` to name an archived predecessor, so the archive entry presents as superseded and links to the successor.
