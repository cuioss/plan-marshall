envelope_version=1
sender_type=plan
sender_id=plan-03-review-currency
epic=finalize-machinery
kind=candidate-lesson
created=2026-09-17T18:03:27Z

# Candidate lesson from plan-03-review-currency

## Title

Record participation-site expectations when adding CI read sites

## Component

plan-marshall:automatic-review

## Category

improvement

## Context

During plan-03-review-currency execution, the participation-site guard failed at collection because a CI read site in workflow-integration-github had no SITE_EXPECTATIONS record.

## Root cause

New read sites were added without updating the participation-site expectation registry.

## Proposed action

Update the participation-site registry alongside any new CI read site, and keep the guard test green.

## Evidence

- aspect: script_failure_analysis — UnrecordedSiteError for _github_ci.py in test_bot_participation_contract.py
- aspect: plan_efficiency — plan completed with 8 tasks done across 2 deliverables
