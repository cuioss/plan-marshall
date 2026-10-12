envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-11T07:42:09Z

# Candidate lesson: ci-verify red-CI policy findings have no valid verification-feedback producer

Source: script failure cluster. verification-feedback rejected producer `ci-verify-policy` as `unknown_producer`.

The ci-verify step files red-CI policy findings, but the verification-feedback surface does not register `ci-verify-policy` as a producer. Feeding those findings back failed with `unknown_producer`, so the red-CI policy signal could not travel through the normal feedback path.

Candidate rule / fix direction: register `ci-verify-policy` in the verification-feedback producer set, or route ci-verify policy findings through an already registered producer. A finding producer and the feedback registry must be kept in sync, ideally guarded by a test that walks every producer that files findings.

Scope hint: plan-marshall framework (ci-verify and verification-feedback), not pm-mcp-core.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `plan-04-service-unit-008.md` from plan plan-04-service-unit (PLAN-04, #25)
