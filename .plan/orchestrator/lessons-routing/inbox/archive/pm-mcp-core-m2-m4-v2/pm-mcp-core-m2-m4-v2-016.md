envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4-v2
epic=lessons-routing
kind=candidate-lesson
created=2026-11-12T17:47:09Z

component=plan-marshall:workflow-integration-sonar
category=improvement
title=Add an unauthenticated read path to sonar fetch_findings for public projects

# Add an unauthenticated read path to sonar fetch_findings for public projects

## Context

`sonar fetch_findings` and `sonar_rest search` both returned "No credentials configured for workflow-integration-sonar" (`credentials list`: 0 configured, global and project). All three sonar-roundtrip firings (heads 53413611, bca5ff23, bf9d510a) fell back to hand-run unauthenticated GETs against sonarcloud.io (`api/issues/search`, `api/project_pull_requests/list`, `api/ce/component`, `api/hotspots/search`) and filed findings by hand. No `sonar-scan-summary.jsonl` marker row was written in any firing.

## Root cause

The producer verb has no read path without a credential, even though SonarCloud serves public-project PR issues unauthenticated, so the fallback is LLM work each time and skips the marker contract.

## Proposed action

Give `fetch_findings` (and `read_open_issues`) an unauthenticated mode for public SonarCloud projects that performs the analysis-revision and CE-settled checks, writes schema-conformant findings and the marker row; keep `post_responses` credential-gated.

## Evidence

- aspect: chat_history_analysis — "IMPORTANT DEVIATION: the producer verb could not run in this environment"
- aspect: llm_to_script_opportunities — repetition 3, complexity medium
- plan: plan-v2-132-coverage-parser-hardening, PR #388
