envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-11-02T16:42:42Z

Severity: LOW (weak), domain content issue. Bundle: pm-dev-java (junit-core) / pm-dev-java-cui (cui-testing). Checked at f6830b837.

A test comment that cites a specification without naming the clause can pin a fail-open security behaviour, and the citation then shields the defect from review. The incident is cui-http project code; the general part is a thin content gap: a security test that cites a spec should name the clause, and an assertion that a request is accepted (fail-open) should state why.

Ground-truth evidence:
- A search of `pm-dev-java` and `pm-dev-java-cui` skills finds no rule on clause-anchored spec citations in tests or on justifying a fail-open assertion.
- The primary lesson is project-only (a consumer test comment); only the general rule is applicable. Filed because domain-bundle content issues are applicable at any severity; the leaf grading flagged it marginal.

Source lessons:
- cui-http 2026-09-09-16-003

Full body: `lessons-archive/filed-live-blockers/sweep-2026-11-02/cui-http/2026-09-09-16-003.md`
