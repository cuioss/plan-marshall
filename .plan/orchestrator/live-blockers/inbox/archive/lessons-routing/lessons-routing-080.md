envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-11-02T16:42:48Z

Severity: LOW (weak), domain content issue. Bundle: pm-dev-java-cui (cui-http-testing). Checked at f6830b837.

Raw bidirectional control characters written into Java test literals for attack tests fail the Sonar gate (text:S6389). The cui-http-testing guidance on attack databases says nothing about building invisible or bidi characters from code points instead of embedding them raw. Only Sonar triggered the finding, and Sonar is not enabled for this project, so the weight is on the guidance gap alone.

Ground-truth evidence:
- `marketplace/bundles/pm-dev-java-cui/skills/cui-http-testing/SKILL.md:122-124` documents the attack databases and says nothing about constructing invisible or bidi characters from code points.
- A search for unicode, bidi and codepoint in `cui-http-testing`, `cui-http` and `cui-testing` finds no mention.
- Filed because domain-bundle content issues are applicable at any severity; the leaf grading flagged it marginal.

Source lessons:
- cui-http 2026-10-04-06-001

Full body: `lessons-archive/filed-live-blockers/sweep-2026-11-02/cui-http/2026-10-04-06-001.md`
