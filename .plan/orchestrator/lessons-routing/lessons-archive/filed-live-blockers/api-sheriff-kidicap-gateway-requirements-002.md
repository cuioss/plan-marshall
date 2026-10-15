envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-kidicap-gateway-requirements
epic=lessons-routing
kind=candidate-lesson
created=2026-10-15T12:24:50Z

# Candidate lesson: affected files added without an assessment, or backed only by CERTAIN_EXCLUDE (phase-3-outline)

Forwarded from API-Sheriff epic `kidicap-gateway-requirements`, plan `plan-32-early-answer-it-timeouts` (PR cuioss/API-Sheriff#466).

Source messages: 002, 005, 007 (Q-Gate 56b731, a4dab9, d215b3). Three firings in one outline.

## Observation

Outline revisions added (read) affected or survey files with no assessment (D2 three files, D5 doc/LogMessages.adoc). Two nginx files kept earlier CERTAIN_EXCLUDE assessments ("not a mutation target") after they were added as read files. The coverage check needs a CERTAIN_INCLUDE assessment, with read intent, behind every listed file.

## Candidate rule

Adding a file to any deliverable list and recording or superseding its assessment are a single step. "Not a mutation target" is no reason to exclude a file the deliverable reads. Suggest a pre-gate self-check (every listed path has a CERTAIN_INCLUDE assessment) so the Q-Gate does not have to catch it, since it recurred three times.
