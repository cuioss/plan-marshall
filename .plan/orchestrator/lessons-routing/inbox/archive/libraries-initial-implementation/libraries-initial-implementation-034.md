envelope_version=1
sender_type=orchestrator
sender_id=libraries-initial-implementation
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:07:22Z

component=plan-marshall:phase-3-outline
category=improvement
title=phase-3-outline: look at the project's managed test libraries and loaded domain skills before recommending test infrastructure or a result shape
source_lesson=2026-11-19-19-003
source_repo=git-document-repository (epic libraries-initial-implementation)
source_created=2026-11-19

# phase-3-outline: look at the project's managed test libraries and loaded domain skills before recommending test infrastructure or a result shape

# Candidate lesson: outline design questions recommended options built from first principles, not from the project's own test libraries

- Source signal: plan plan-05-git-core-merge-read-notes (inbox plan-05-git-core-merge-read-notes-009), retrospective chat-history pivots (2 of 2 outline questions answered against the recommended option), component `plan-marshall:phase-3-outline` (`outline_prompt` question composition), confidence high.
- Evidence: aspect chat_history_analysis (two pivots at the outline questions), aspect request_result_alignment (deliverable 3 and item 5 d shipped as the operator redesigned them, not as first outlined).

## What happened

The outline asked the operator two design questions and both recommended options were rejected:

- Redirect end-to-end test: the outline recommended a JDK `HttpsServer` with a self-signed PKCS12 keystore committed under `git-core/src/test/resources/redirect/`. The operator answered "why not cuihttpmock", meaning `de.cuioss.test:cui-test-mockwebserver-junit5`, which the parent BOM (`cui-java-bom` 1.7.7) already manages and for which the loaded domain has a skill (`pm-dev-java-cui:cui-http-testing`).
- Merge conflict carrier: the outline recommended `CONFLICT` with the paths in the detail plus a public `conflictingPaths(...)`. The operator asked for "an object carrying the content", which became the sealed `MergeResult`.

Each rejection forced an outline revision and a success-criteria refreeze, which needed one more operator approval.

## Root cause

The options were built from first principles. The outline did not first look at the test libraries the project's BOM already manages, or at the domain skills it had loaded, and it ranked "no new dependency" above using the project's own tooling.

## Candidate rule

For an outline question about test infrastructure, look first in the resolved domain skills (for java-cui: `cui-http-testing`, `cui-testing`) and in the BOM-managed test artifacts, include the matching project library as an option, and recommend it when it fits. For a result-shape question, list a dedicated result type as an option whenever the existing result type cannot carry a value on a non-success. Same family as lesson `2026-11-18-07-004` (the outline's own questions are answered after the criteria were frozen), and the cost is the same: a second outline dispatch and a refreeze.
