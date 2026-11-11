envelope_version=1
sender_type=plan
sender_id=plan-v2-86-core-store-tests-b
epic=lessons-routing
kind=candidate-lesson
created=2026-11-06T11:21:29Z

# Sonar finding schema of the untrusted-ingestion containment boundary refuses the sonar_key field the sonar producer writes

- component: plan-marshall:untrusted-ingestion
- category: bug
- source plan: plan-v2-86-core-store-tests-b (pm-mcp-core, PR 301)

The validate_struct sonar-finding schema of untrusted-ingestion does not allow the sonar_key field that workflow-integration-sonar fetch_findings writes into raw_input. Because of that, the ingest automatically refused a real SonarCloud issue, which then had to be filed and resolved by hand. The producer output and the validator schema need to agree, and a test should run the producer's actual output through validate_struct.

Evidence: finding 126666 (sonar-issue java:S5778 MetricsStoreTest:557): its raw_input carries sonar_key AaGuAFnmjCCkOFuU6Vrs. The auto-refusal reason ('Field has undeclared key sonar_key (additionalProperties:false)') was reported by the triage agent of the unified wait-region triage; the refusal line itself was not found in the work log.
