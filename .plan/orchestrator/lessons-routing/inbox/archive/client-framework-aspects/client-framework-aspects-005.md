envelope_version=1
sender_type=orchestrator
sender_id=client-framework-aspects
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:04:52Z

> Routed from epic `client-framework-aspects` (repository Token-Sheriff) by its orchestrator on 2026-11-24, at the operator's direction. Original message `plan-12-documentation-review-consolidation-005.md`, sender plan `plan-12-documentation-review-consolidation`, created 2026-11-23T20:28:38Z. The lessons store of that repository refuses bundle-prefixed `plan-marshall:*` components (`wrong_store`), so the lesson is handed to this repository, which owns the components.

# Candidate lesson: review-bot findings on PR #952 — doc claims drifted from code, and a review body was only partly triaged

Source signal: automatic-review (signal_automated_review_count=1). Records: pr-comment findings ef14a4 (fixed),
981796 (fixed), 2651ed (taken_into_account, walkthrough), fc0724 (taken_into_account, Sourcery approval).

## Observation 1 — consolidated doc overstated a security property (ef14a4, CodeRabbit Major, Security)

`doc/validation/architecture.adoc` claimed a cache hit is equivalent to a fresh validation. Checked against
`AccessTokenValidationPipeline` / `AccessTokenCache`: a cache hit re-applies expiry, max token age and issuer
resolution but does not re-verify the signature, so a token whose key left the JWKS sets stays accepted until it
expires or is evicted. The doc was fixed. The same overstated wording remains in the `AccessTokenCache` class
Javadoc (production source, out of scope here), so a follow-up is still owed.

## Observation 2 — a large review body was not fully triaged (981796)

The CodeRabbit review body carried 23 minor comments. The run fixed the WRK README viewing paths, the Prometheus
troubleshooting row, the local-testing quick start and the benchmark-core raw-results path. The resolution text
says the other minor comments went over the ingest length cap and were not triaged. They were not answered either.
Untriaged items include: ADR-0003 floors "above" vs "below" measured coverage, ADR-0010 invalid_scope fallback,
ADR-0017 readiness claim for external validators, ADR-0031 64-scope deployment check for default methods,
transport.adoc timeout/size-bound wording, security-settings maxPayloadSize/maxStringLength, test-impl-mapping
Failsafe scoping, quarkus-integration HTTP_ONLY_PROPERTIES drift, devui `../mvnw` path, JFR runner override guidance,
native-optimization wrk path and TOKEN_DATA.

## Candidate rules

1. A doc-consolidation pass that rewrites behavioural claims (cache equivalence, readiness, bounds) must check
   each rewritten claim against the implementing class, not only against the previous doc text.
2. When a review-body finding goes over the ingest length cap, the leftover minor comments must still get a
   disposition. Either split the body into per-comment findings, or file a follow-up for the untriaged remainder.
   Leaving them silent lets the barrier report "zero pending" while real comments were never looked at.

Component hint: plan-marshall:automatic-review / plan-marshall:workflow-integration-github (ingest truncation), plus a project follow-up for the untriaged doc items and the AccessTokenCache Javadoc.
