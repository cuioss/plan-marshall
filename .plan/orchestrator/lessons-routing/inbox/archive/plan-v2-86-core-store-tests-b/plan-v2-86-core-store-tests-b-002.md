envelope_version=1
sender_type=plan
sender_id=plan-v2-86-core-store-tests-b
epic=lessons-routing
kind=candidate-lesson
created=2026-11-06T11:21:29Z

# Sonar producer 'unconfigured' makes the finalize sonar step record work_performed=false while the plan falls back to public HTTP

- component: plan-marshall:workflow-integration-sonar
- category: improvement
- source plan: plan-v2-86-core-store-tests-b (pm-mcp-core, PR 301)

With no Sonar credentials configured, the sonar producer reports unconfigured and the finalize sonar-roundtrip step records work_performed=false. The plan still had to read the public SonarCloud API by hand to see the PR's issues. The producer could use the public read path for public projects, or the step could report the gap so the operator sees it, instead of letting a manual fallback hide it.

Evidence: sonar fetch_findings --project plan-marshall_pm-mcp-core --pr 301 returned status unconfigured ('No credentials configured for workflow-integration-sonar') on both finalize passes; the step records say 'Sonar producer unconfigured, no scan summary obtained (HTTP check only)'.
