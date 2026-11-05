envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-11-02T16:42:36Z

Severity: MEDIUM, domain content issue. Bundle: pm-dev-java (junit-core), with pm-dev-java-cui:cui-http-testing as a secondary home. Checked at f6830b837.

Tests that cannot fail. Four shapes recurred: a relational or parity assertion with no anchor to a concrete value (passes on a uniformly wrong value); a test named for a builder default that passes the value explicitly instead of reaching the default through the production path; a negative assertion that goes vacuous when a new invariant makes the absence unreachable by construction (it needs a positive control); and a hardcoded name list or enum cardinality assertion that mirrors a set defined elsewhere. The java test-code review rules cover none of them.

Ground-truth evidence:
- `marketplace/bundles/pm-dev-java/skills/junit-core/SKILL.md:145-148` - the test-code review rules cover try/catch without `fail()`, assertion-free tests, order-dependent state and `Thread.sleep`. Nothing on anchoring, vacuity or derived sets.
- `pm-dev-java/skills/junit-core/standards/testing-junit-core.md` has no section on relational-assertion anchoring, negative-assertion positive controls, cardinality assertions or mirrored lists; a search for anchor/vacuous/cardinality/tautology across `pm-dev-java` and `pm-dev-java-cui` skills is empty.
- `plan-marshall/skills/persona-module-tester/standards/testing-methodology.md:332` and `:612-652` carry matched positive/negative controls and non-vacuity, but only for fixtures and runtime-derived parametrization, language-agnostic. They do not reach the Java cases.
- Per the operator's standing direction, the ask is a content rule in the domain bundle, not a per-language surfacer.

Source lessons:
- cui-http 2026-09-09-10-003
- cui-http 2026-09-16-15-004
- cui-http 2026-09-16-15-008 (in-scope part only; the test itself is cui-http project code)
- cui-http 2026-09-16-15-009
- cui-http 2026-10-04-06-008 (fixed-list part only)

Full bodies: `lessons-archive/filed-live-blockers/sweep-2026-11-02/cui-http/`
