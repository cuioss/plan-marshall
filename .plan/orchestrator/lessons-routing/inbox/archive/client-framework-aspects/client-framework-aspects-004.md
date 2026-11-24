envelope_version=1
sender_type=orchestrator
sender_id=client-framework-aspects
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:04:52Z

> Routed from epic `client-framework-aspects` (repository Token-Sheriff) by its orchestrator on 2026-11-24, at the operator's direction. Original message `plan-12-documentation-review-consolidation-004.md`, sender plan `plan-12-documentation-review-consolidation`, created 2026-11-23T20:28:23Z. The lessons store of that repository refuses bundle-prefixed `plan-marshall:*` components (`wrong_store`), so the lesson is handed to this repository, which owns the components.

# Candidate lesson: condensing an ADR must keep its Status section a single status token

Source signal: Q-Gate finding d60f5e (6-finalize, code-review, severity error, fix_kind correction), resolution
taken_into_account (code review closed at ddad84a3 with no blocking finding after the loop-back).

## Observation

While condensing ADR-0010 (`doc/adr/0010-A_refresh_token_the_authorization_server_declares_invalid_is_a_third_classification_state.adoc:17`),
the Status section stopped being a single status token. `manage-adr` parses that section, so the ADR dropped out of
the Accepted listing. Code review caught it and forced a loop-back iteration in finalize.

## Candidate rule

When editing or condensing an ADR, keep the Status section machine-readable: exactly one status token
(e.g. `Accepted`). Put amendment or supersession prose elsewhere in the record. After an ADR-reduction pass, run
the `manage-adr` listing and confirm every surviving ADR still appears under its status.

Component hint: plan-marshall:manage-adr (format contract), or project docs convention for doc/adr.
