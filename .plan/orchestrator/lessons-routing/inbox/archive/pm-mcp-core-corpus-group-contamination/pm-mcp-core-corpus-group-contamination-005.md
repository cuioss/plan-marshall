envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-corpus-group-contamination
epic=lessons-routing
kind=candidate-lesson
created=2026-10-18T08:05:15Z

# Candidate lesson: Read the Sonar project key from the provider configuration (plan-marshall:sonar-roundtrip / provider configuration)

Forwarded from pm-mcp-core, plan corpus-group-contamination (PR plan-marshall/pm-mcp-core#86, merged e935da3), archived at pm-mcp-core/.plan/local/archived-plans/2026-10-18-corpus-group-contamination. The pm-mcp-core lesson store refused it as wrong_store (it names a plan-marshall component).

### Observation

The Sonar project key is not in the provider configuration; the sonar-roundtrip leaf had to find it in `.github/project.yml` (retrospective INFO). The step completed (0 new-code issues), but only because the leaf searched for it.

### Candidate rule (for orchestrator classification)

The Sonar project key belongs in the provider configuration that sonar-roundtrip reads, or the step resolves it from `.github/project.yml` by a documented, scripted rule instead of a leaf's search.
