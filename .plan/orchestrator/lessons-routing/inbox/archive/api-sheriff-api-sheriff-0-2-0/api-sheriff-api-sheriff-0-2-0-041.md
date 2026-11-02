envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=candidate-lesson
created=2026-10-22T05:50:08Z

# Candidate lesson: Outline deliverable coverage: criterion mechanisms, shared test files, conditional doc edits (phase-3-outline)

Forwarded from API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-45-request-body-and-h2-buffer-bounds (PR cuioss/API-Sheriff#506), source message 002, 003, 004.

Three Q-Gate findings in one outline, all caught (the gate worked) and all of one shape: a deliverable's declared scope did not cover what its own text promised.

- 002 (scope_criterion_validator under_coverage): a success criterion required reset + credit release + permit release, but the deliverable declared only the file performing the permit release; the other two live in two undeclared files.
- 003 (profile overlap): a test-only deliverable with depends: none edited test files that two other deliverables also edited; no owner and no ordering.
- 004 (under_coverage): a docs deliverable promised "no doc states a changed value" but conditioned the user-doc edit on one deliverable while three could change the bounds that doc states.

Candidate rules for phase-3-outline guidance:
- for each verb in a success criterion, name the file that performs it;
- two deliverables touching one test file: state the owner and order them with depends; a test-only deliverable that edits shared files never gets depends: none;
- condition a doc edit on every deliverable that can change a value the doc states (content-search the docs for the bound's name/status code to get the list).
