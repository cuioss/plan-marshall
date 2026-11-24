envelope_version=1
sender_type=orchestrator
sender_id=libraries-initial-implementation
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:06:47Z

component=plan-marshall:phase-3-outline
category=improvement
title=phase-3-outline: when an outline may change a ServiceLoader SPI signature, sweep for every implementer, test implementers included
source_lesson=2026-11-24-07-001
source_repo=git-document-repository (epic libraries-initial-implementation)
source_created=2026-11-24

# phase-3-outline: when an outline may change a ServiceLoader SPI signature, sweep for every implementer, test implementers included

Source: Q-Gate finding 5d7174 (phase 3-outline, scope_criterion_validator, resolution taken_into_account).

Observation: deliverable 1 could change the signature of `AnchorProvider.obtain`. The outline did not list the test implementer `git-store/src/test/java/de/cuioss/git/document/store/TestAnchorProvider.java` (registered through `META-INF/services`) under any deliverable's Affected files. The content sweep found it. In the end the implementation changed the file to follow the new `obtain` signature.

Possible lesson: when an outline may change a ServiceLoader SPI signature in this repository, sweep for every implementer, including test implementers registered through `META-INF/services`. List them as Affected files, conditional on the signature change.


Source: inbox plan-11-store-anchoring-signed-003 (Q-Gate finding 5d7174, phase 3-outline). Related: 2026-11-18-07-001 (sweep the corpus for statements of the old state).
