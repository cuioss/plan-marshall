envelope_version=1
sender_type=plan
sender_id=lb-14-launch-gate-scope
epic=live-blockers
kind=candidate-lesson
created=2026-10-08T14:55:36Z

component=plan-marshall:phase-3-outline
category=improvement

# Multi-site rule rewrites need one canonical statement and pointers elsewhere

## Context

Plan lb-14-launch-gate-scope rewrote one superseded overlap rule at ten prose sites in eight files. The task description for the document deliverable prescribed that each site state the replacement rule "in its own words and at its own length". Pre-submission self-review then returned findings in 7 of its 9 firings, never converged, and hit the loop-back ceiling of 5 twice. Of the 18 findings it filed, 15 were contract_drift or same_document_contradiction: a comment or paragraph claiming something wider than the code or than a sibling site (for example "the roll-up is the conjunction of the rows" while the code and SKILL.md say it is the stricter reading). Each fix round touched prose and seeded the next round's findings; finalize consumed 58 percent of the plan's tokens.

## Root cause

The outline duplicated one contract into ten places, so every restatement is an independent claim that can drift from the code and from the other nine, and every fix is itself new prose that can drift again.

## Proposed action

When a plan corrects a rule at many sites, have the outline name one canonical home, require every other site to carry a one-line pointer to it rather than a restatement, and add the pointer-only check to the deliverable's success criteria. Fix the wording once at the canonical site, then run the superseded-wording absence test over the others.

## Evidence

- aspect: plan_efficiency - 6-finalize 4.59M of 7.92M tokens
- aspect: chat_history_analysis - loop-back ceiling breached twice, operator closed past the round limit
- solution outline deliverable 4 - ten superseded-wording sites in eight files
- findings store qgate-6-finalize - 15 of 18 findings are contract_drift or same_document_contradiction
