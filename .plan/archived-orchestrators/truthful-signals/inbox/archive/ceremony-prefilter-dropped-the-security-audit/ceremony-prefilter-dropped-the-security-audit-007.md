envelope_version=1
sender_type=plan
sender_id=ceremony-prefilter-dropped-the-security-audit
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T15:48:06Z

component=plan-marshall:workflow-integration-sonar
category=improvement
created=2026-07-29

# The SonarCloud project key is re-derived ad hoc on every roundtrip, with nothing to verify it against

There is no persisted SonarCloud project-key configuration. Every `sonar-roundtrip` dispatch
re-derives `cuioss_plan-marshall` from context at run time.

The derivation happens to be right, which is what makes it worth filing: a per-run re-derivation
with no stored expectation has **no failure mode that surfaces**. If it ever resolved to a
non-existent or wrong project key, the most likely outcome is a clean-looking "0 new-code issues"
result — an empty answer from the wrong project is indistinguishable from a green answer from the
right one. This run reported `new-code issues: 0 (confirmed)`; the confirmation covers the query
result, not the identity of what was queried.

## Solution

- **Persist the project key in `marshal.json`** under the sonar provider's configuration, and have
  `workflow-integration-sonar` read it rather than derive it.
- **Fail closed on absence.** No configured key must be an explicit error, not a fallback to
  derivation — otherwise the config is decorative.
- **Verify the project exists before trusting an empty result.** A zero-issue response from a
  project key that resolves to nothing must be reported as an error, never as a clean gate.

## Impact

Applies to `sonar-roundtrip` in every plan in this repository, and to any consumer project onboarded
to the sonar provider. Generalizes: **an empty result from an unverified query target is not
evidence of cleanliness** — it is evidence of nothing, wearing the shape of a pass.
