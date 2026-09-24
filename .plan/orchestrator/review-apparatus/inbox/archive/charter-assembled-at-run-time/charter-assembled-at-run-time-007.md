envelope_version=1
sender_type=plan
sender_id=charter-assembled-at-run-time
epic=review-apparatus
kind=candidate-lesson
created=2026-09-24T11:12:30Z

component=plan-marshall:automatic-review
category=improvement
confidence=high

# Probe a repo rename live before trusting redirects for App-token mint

## Context

Plan `charter-assembled-at-run-time` renamed the settings repository (pr-agent-settings to cuioss-review-bot) and the reviewer surfaces. D0 carried rename-path hypotheses (p1)-(p7) for whether each consumer path follows GitHub's rename redirect. The live (p4) probe showed that the GitHub App installation-token mint does not follow a repository rename. Consumers depending on it broke until the fix was shipped forward in the cuioss-organization 0.30.0 release.

## Root cause

GitHub's rename redirect covers git and REST reads by old name, but the App-token mint for a named repository resolves against the current name. A redirect-is-enough assumption made by reading, rather than by live probing, does not hold for that path.

## Proposed action

In the reviewer/automatic-review rename guidance (`standards/cuioss-review-bot.md` or the landing-cycle reference), require that any path which mints an App installation token for a named repository be migrated to the new name, never left on the redirect. Require a live probe before a rename is declared safe. Record (p4) as a known non-following path.

## Evidence

- orchestrator run fact: the live (p4) rename-redirect probe proved the mint does not follow; fixed forward via 0.30.0 (#1603 updated plan-marshall's workflows to v0.30.0)
- aspect: request_result_alignment: D7/D11 rename work and the fix-forward
